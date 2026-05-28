# Shared paths for VoiceToText repo (source from other scripts)
_vtt_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export VTT_REPO_ROOT="$(cd "${_vtt_script_dir}/../../../.." && pwd)"
export F9_CONFIG_FILE="${F9_CONFIG_FILE:-${VTT_REPO_ROOT}/config/f9_base.yaml}"
export F9_PROFILE="${F9_PROFILE:-linux-f9-local}"
