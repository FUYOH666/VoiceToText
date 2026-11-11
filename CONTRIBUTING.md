# Contributing

Thanks for helping. Bug reports and ideas go to [Issues](https://github.com/FUYOH666/VoiceToText/issues); the templates ask for your macOS version, Mac chip, the model you use and the relevant lines from `~/Library/Logs/vtt2/`.

## Setup

Apple Silicon Mac, macOS 13+, Xcode Command Line Tools, [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/FUYOH666/VoiceToText.git && cd VoiceToText
uv sync --frozen --extra dev --extra qwen
bash macos/scripts/setup-local-signing.sh   # once: stable signature keeps macOS permissions across rebuilds
bash macos/scripts/build.sh
uv run python src/vtt2/main.py --install
```

## Before a pull request

```bash
uv run pytest -q
bash macos/scripts/test.sh
bash macos/scripts/build.sh
uv run python scripts/sync_version.py --check
uv lock --check
```

CI runs the same on macOS arm64. Keep pull requests focused, describe what you verified (and what you could not), and update `docs/STT_API.md` when the API changes. Repository layout and conventions are in [AGENTS.md](AGENTS.md); they apply to humans too.

## Ground rules

- Audio and text stay on the user's Mac. The server binds to loopback only.
- Tests never download models or touch the network.
- No secrets or personal paths in tracked files.
