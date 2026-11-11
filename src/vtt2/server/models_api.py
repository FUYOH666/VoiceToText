"""Model picker API: list, download, activate, delete, add a custom HF repo.

Contract (docs/STT_API.md):
- ``GET  /v1/models``                 catalog + installed/active/recommended/fits_memory
- ``POST /v1/models/{id}/download``   202, background download (never blocks dictation)
- ``GET  /v1/models/{id}/download``   progress
- ``POST /v1/models/{id}/activate``   switch the loaded model; persisted in user settings
- ``DELETE /v1/models/{id}``          remove from the Hugging Face cache
- ``POST /v1/models/custom``          ``{"repo": "org/name"}`` → validated custom entry
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import Body, FastAPI

from model_catalog.downloads import DownloadManager
from model_catalog.registry import (
    ALLOW_PATTERNS,
    ModelSpec,
    active_selection,
    add_user_model,
    config_with,
    custom_id,
    describe,
    is_installed,
    load_catalog,
    system_memory_gb,
    write_selection,
)
from server import errors as err
from server.errors import APIError

logger = logging.getLogger(__name__)

_REPO_RE = re.compile(r"^[A-Za-z0-9][\w.-]*/[\w.-]+$")


@dataclass
class ModelHost:
    """What the API needs from the STT server, injected to keep this module testable."""

    get_config: Callable[[], Any]
    switch: Callable[[Any], Awaitable[None]]  # unload current, load new config; raises APIError


def _spec_or_404(model_id: str) -> ModelSpec:
    spec = load_catalog().get(model_id)
    if spec is None:
        raise APIError(404, err.MODEL_NOT_FOUND, f"Unknown model id: {model_id}")
    return spec


def _list_models(host: ModelHost, downloads: DownloadManager) -> dict:
    catalog = load_catalog()
    memory = system_memory_gb()
    recommended = catalog.recommended(memory)
    family, repo = active_selection(host.get_config())
    active = catalog.find(family, repo)
    data = [
        describe(m, memory_gb=memory, recommended_id=recommended, active=active is not None and m.id == active.id)
        for m in catalog.models
    ]
    if active is None and repo:
        # Configured by hand to something outside the catalog; show it as active.
        data.append(
            {
                "id": "configured",
                "object": "model",
                "title": repo,
                "family": family,
                "repo": repo,
                "installed": True,
                "active": True,
                "recommended": False,
                "fits_memory": True,
                "custom": True,
            }
        )
    for item in data:
        job = downloads.get(item["id"])
        if job is not None and job.state in ("queued", "downloading", "error"):
            item["download"] = job.progress()
    return {
        "object": "list",
        "data": data,
        "system_memory_gb": round(memory, 1),
        "recommended": recommended,
        "active": active.id if active is not None else ("configured" if repo else None),
    }


def _delete_from_cache(repo: str) -> int:
    from huggingface_hub import scan_cache_dir

    info = scan_cache_dir()
    for cached in info.repos:
        if cached.repo_id == repo and cached.repo_type == "model":
            strategy = info.delete_revisions(*[rev.commit_hash for rev in cached.revisions])
            freed = int(strategy.expected_freed_size)
            strategy.execute()
            return freed
    return 0


def detect_family(config: dict, files: list[str]) -> str | None:
    """Which local backend can load this repo, from its config.json and files."""
    has_weights = any(f.endswith((".safetensors", ".npz")) for f in files)
    if not has_weights:
        return None
    model_type = str(config.get("model_type", "")).lower()
    architectures = " ".join(config.get("architectures") or []).lower()
    if "qwen3_asr" in model_type or "qwen3asr" in architectures:
        return "qwen3_asr"
    # mlx-whisper checkpoints carry ModelDimensions (n_mels, n_audio_ctx), not a HF config.
    if "n_mels" in config and "n_audio_ctx" in config:
        return "mlx_whisper"
    return None


def inspect_repo(repo: str) -> ModelSpec:
    """Validate a Hugging Face repo for local use; raise APIError when it can't be used."""
    from fnmatch import fnmatch

    from huggingface_hub import HfApi, hf_hub_download
    from huggingface_hub.utils import RepositoryNotFoundError

    try:
        info = HfApi().model_info(repo, files_metadata=True)
    except RepositoryNotFoundError as exc:
        raise APIError(404, err.MODEL_NOT_FOUND, f"Hugging Face repo not found: {repo}") from exc
    except Exception as exc:
        raise APIError(502, err.INTERNAL_ERROR, f"Hugging Face is unreachable: {exc}") from exc

    files = [s.rfilename for s in info.siblings]
    if "config.json" not in files:
        raise APIError(422, err.UNSUPPORTED_MODEL, "No config.json: not an MLX ASR checkpoint")
    try:
        config = json.loads(Path(hf_hub_download(repo, "config.json")).read_text(encoding="utf-8"))
    except Exception as exc:
        raise APIError(422, err.UNSUPPORTED_MODEL, f"Cannot read config.json: {exc}") from exc

    family = detect_family(config, files)
    if family is None:
        raise APIError(
            422,
            err.UNSUPPORTED_MODEL,
            "Supported: MLX Whisper checkpoints (mlx-community/whisper-*) and Qwen3-ASR (MLX or original).",
        )
    size = sum(
        (s.size or 0) for s in info.siblings if any(fnmatch(s.rfilename, p) for p in ALLOW_PATTERNS[family])
    )
    download_gb = round(size / 1e9, 2)
    ram_gb = round(download_gb * 1.25 + 0.3, 1)
    return ModelSpec(
        id=custom_id(repo),
        title=repo.split("/")[-1],
        family=family,
        repo=repo,
        quantization="unknown",
        download_gb=download_gb,
        ram_gb=ram_gb,
        min_memory_gb=8 if ram_gb < 3 else 16,
        note="Своя модель с Hugging Face",
        verified_revision=getattr(info, "sha", None),
        custom=True,
    )


def register_model_routes(app: FastAPI, host: ModelHost) -> DownloadManager:
    downloads = DownloadManager()
    app.state.model_downloads = downloads

    @app.get("/v1/models")
    async def list_models() -> dict:
        return await asyncio.to_thread(_list_models, host, downloads)

    @app.post("/v1/models/{model_id}/download", status_code=202)
    async def start_download(model_id: str) -> dict:
        spec = _spec_or_404(model_id)
        return (await asyncio.to_thread(downloads.start, spec)).progress()

    @app.get("/v1/models/{model_id}/download")
    async def download_status(model_id: str) -> dict:
        spec = _spec_or_404(model_id)
        job = downloads.get(model_id)
        if job is not None:
            return job.progress()
        installed = await asyncio.to_thread(is_installed, spec)
        return {
            "model": model_id,
            "state": "done" if installed else "idle",
            "bytes_done": None,
            "bytes_total": None,
            "progress": 1.0 if installed else 0.0,
            "error": None,
        }

    @app.post("/v1/models/{model_id}/activate")
    async def activate(model_id: str) -> dict:
        spec = _spec_or_404(model_id)
        if downloads.is_running(model_id):
            raise APIError(409, err.MODEL_DOWNLOADING, f"{model_id} is still downloading")
        if not await asyncio.to_thread(is_installed, spec):
            raise APIError(409, err.MODEL_NOT_INSTALLED, f"{model_id} is not downloaded yet")
        current = host.get_config()
        if active_selection(current) == (spec.family, spec.repo):
            await asyncio.to_thread(write_selection, spec)
            return {"active": spec.id, "changed": False}
        await host.switch(config_with(current, spec))
        await asyncio.to_thread(write_selection, spec)
        logger.info("Active model is now %s (%s)", spec.id, spec.repo)
        return {"active": spec.id, "changed": True}

    @app.delete("/v1/models/{model_id}")
    async def delete_model(model_id: str) -> dict:
        spec = _spec_or_404(model_id)
        if active_selection(host.get_config()) == (spec.family, spec.repo):
            raise APIError(409, err.MODEL_ACTIVE, "Switch to another model before deleting this one")
        if downloads.is_running(model_id):
            raise APIError(409, err.MODEL_DOWNLOADING, f"{model_id} is still downloading")
        freed = await asyncio.to_thread(_delete_from_cache, spec.repo)
        return {"deleted": model_id, "freed_bytes": freed}

    @app.post("/v1/models/custom")
    async def add_custom(payload: dict = Body(...)) -> dict:
        repo = str((payload or {}).get("repo", "")).strip()
        if not _REPO_RE.match(repo):
            raise APIError(400, err.INVALID_REQUEST, "repo must look like 'org/name'")
        spec = await asyncio.to_thread(inspect_repo, repo)
        await asyncio.to_thread(add_user_model, spec)
        catalog = load_catalog()
        memory = system_memory_gb()
        return describe(
            catalog.get(spec.id) or spec,
            memory_gb=memory,
            recommended_id=catalog.recommended(memory),
            active=False,
        )

    return downloads
