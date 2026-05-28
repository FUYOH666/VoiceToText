#!/usr/bin/env python3
"""
Unified VoiceToText CLI — golden standard entry point.

  vtt doctor [--profile NAME]
  vtt mac run [--profile NAME] [--health] ...
  vtt linux run [--profile NAME] [--health]
  vtt profiles list
  vtt validate-config
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VTT2_SRC = REPO_ROOT / "src" / "vtt2"
LINUX_SRC = REPO_ROOT / "clients" / "linux" / "src"

MAC_PROFILES = (
    "mac-m1-local",
    "mac-m1-remote",
    "mac-m4-local",
    "mac-m4-remote",
)
F9_PROFILES = ("linux-f9-local", "linux-f9-edge")
ALL_PROFILES = MAC_PROFILES + F9_PROFILES

IP_PATTERN = re.compile(r"100\.\d{1,3}\.\d{1,3}\.\d{1,3}")
USER_PATH_PATTERN = re.compile(r"/Users/[^/\s]+")


def _ensure_paths() -> None:
    for p in (REPO_ROOT / "src", VTT2_SRC, LINUX_SRC):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)


def cmd_profiles_list(_: argparse.Namespace) -> int:
    print("VoiceToText profiles (SKU):\n")
    print(f"{'Profile':<20} {'Platform':<8} {'Mode'}")
    print("-" * 50)
    for name in MAC_PROFILES:
        mode = "remote ASR" if "remote" in name else "local MLX"
        print(f"{name:<20} {'mac':<8} {mode}")
    for name in F9_PROFILES:
        mode = "edge ASR" if "edge" in name else "local ASR"
        print(f"{name:<20} {'linux':<8} {mode}")
    print("\nSet active: config.yaml active_profile or VTT2_PROFILE / --profile")
    print("Secrets: .env.local (LOCAL_AI_ASR_BASE_URL)")
    return 0


def cmd_validate_config(_: argparse.Namespace) -> int:
    _ensure_paths()
    from config.loader import Config, Config as VTTConfig
    from config.f9_loader import F9Config, VALID_F9_PROFILES

    ok = True
    for profile in MAC_PROFILES:
        try:
            cfg = VTTConfig.from_yaml("config.yaml", REPO_ROOT, profile=profile)
            if cfg.transcription.engine == "remote_asr":
                url = (cfg.transcription.remote_asr.base_url or "").strip()
                if not url or "YOUR_ASR_HOST" in url:
                    if not os.getenv("LOCAL_AI_ASR_BASE_URL"):
                        print(f"WARN  {profile}: remote ASR URL not set (need .env.local)")
                    else:
                        print(f"OK    {profile}: remote ASR via env")
                else:
                    print(f"OK    {profile}: {cfg.transcription.engine}")
            else:
                print(f"OK    {profile}: {cfg.transcription.engine}")
        except Exception as e:
            print(f"FAIL  {profile}: {e}")
            ok = False

    for profile in VALID_F9_PROFILES:
        try:
            F9Config.from_profile(REPO_ROOT, profile=profile)
            print(f"OK    {profile}: F9 config")
        except Exception as e:
            print(f"FAIL  {profile}: {e}")
            ok = False

    return 0 if ok else 1


def _audit_repo_secrets() -> list[str]:
    issues = []
    for path in (REPO_ROOT / "config").rglob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        if IP_PATTERN.search(text):
            issues.append(f"Tailscale-like IP in {path.relative_to(REPO_ROOT)}")
        if USER_PATH_PATTERN.search(text):
            issues.append(f"User path in {path.relative_to(REPO_ROOT)}")
    return issues


def cmd_doctor(args: argparse.Namespace) -> int:
    print("=== vtt doctor ===\n")
    issues = _audit_repo_secrets()
    if issues:
        for i in issues:
            print(f"FAIL  {i}")
    else:
        print("OK    No IPs or /Users/ paths in config/")

    env_local = REPO_ROOT / ".env.local"
    if env_local.is_file():
        print("OK    .env.local present")
    else:
        print("WARN  .env.local missing — copy from .env.example")

    if args.profile and args.profile in MAC_PROFILES:
        return _mac_health(args)
    if args.profile and args.profile in F9_PROFILES:
        return _linux_health(args)

    print("\n--- Mac (default profile from config.yaml) ---")
    mac_code = _mac_health(argparse.Namespace(profile=None, health=True))
    print("\n--- Linux F9 (linux-f9-local) ---")
    linux_code = _linux_health(
        argparse.Namespace(profile="linux-f9-local", health=True)
    )
    return 0 if mac_code == 0 and linux_code == 0 else 1


def _mac_health(args: argparse.Namespace) -> int:
    _ensure_paths()
    os.chdir(REPO_ROOT)
    cmd = [sys.executable, str(VTT2_SRC / "main.py"), "--health"]
    if args.profile:
        cmd.extend(["--profile", args.profile])
    return subprocess.call(cmd)


def _linux_health(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(LINUX_SRC), str(REPO_ROOT / "src" / "vtt2"), str(REPO_ROOT / "src")]
    )
    cmd = [sys.executable, "-m", "f9_asr.main", "--health"]
    if args.profile:
        cmd.extend(["--profile", args.profile])
    else:
        cmd.extend(["--profile", "linux-f9-local"])
    return subprocess.call(cmd, cwd=str(REPO_ROOT), env=env)


def cmd_mac_run(args: argparse.Namespace) -> int:
    os.chdir(REPO_ROOT)
    cmd = [sys.executable, str(VTT2_SRC / "main.py")]
    if args.profile:
        cmd.extend(["--profile", args.profile])
    if args.health:
        cmd.append("--health")
    if args.extra:
        cmd.extend(args.extra)
    return subprocess.call(cmd)


def cmd_linux_run(args: argparse.Namespace) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(LINUX_SRC), str(REPO_ROOT / "src" / "vtt2"), str(REPO_ROOT / "src")]
    )
    cmd = [sys.executable, "-m", "f9_asr.main"]
    if args.profile:
        cmd.extend(["--profile", args.profile])
    if args.health:
        cmd.append("--health")
    if args.extra:
        cmd.extend(args.extra)
    return subprocess.call(cmd, cwd=str(REPO_ROOT), env=env)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="vtt",
        description="VoiceToText — unified CLI (golden standard)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser("doctor", help="Diagnose config, secrets, health")
    p_doc.add_argument("--profile", choices=ALL_PROFILES)
    p_doc.set_defaults(func=cmd_doctor)

    p_prof = sub.add_parser("profiles", help="Profile commands")
    sub_prof = p_prof.add_subparsers(dest="profiles_cmd", required=True)
    p_list = sub_prof.add_parser("list", help="List hardware profiles")
    p_list.set_defaults(func=cmd_profiles_list)

    p_val = sub.add_parser("validate-config", help="Validate all 6 profiles")
    p_val.set_defaults(func=cmd_validate_config)

    p_mac = sub.add_parser("mac", help="macOS VTT2")
    sub_mac = p_mac.add_subparsers(dest="mac_cmd", required=True)
    p_mac_run = sub_mac.add_parser("run", help="Run menu-bar app")
    p_mac_run.add_argument("--profile", choices=MAC_PROFILES)
    p_mac_run.add_argument("--health", action="store_true")
    p_mac_run.add_argument("extra", nargs=argparse.REMAINDER)
    p_mac_run.set_defaults(func=cmd_mac_run)

    p_linux = sub.add_parser("linux", help="Linux F9 client")
    sub_linux = p_linux.add_subparsers(dest="linux_cmd", required=True)
    p_linux_run = sub_linux.add_parser("run", help="Run F9 hotkey client")
    p_linux_run.add_argument("--profile", choices=F9_PROFILES)
    p_linux_run.add_argument("--health", action="store_true")
    p_linux_run.add_argument("extra", nargs=argparse.REMAINDER)
    p_linux_run.set_defaults(func=cmd_linux_run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
