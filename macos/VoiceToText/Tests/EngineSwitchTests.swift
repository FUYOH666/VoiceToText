import Foundation

func runEngineSwitchTests() {
    let yaml = """
    stt_server:
      host: "127.0.0.1"
      engine: mlx_whisper  # mlx_whisper | whisper_cpp
    transcription:
      engine: local_stt
      local_stt:
        base_url: "http://127.0.0.1:8765"
      mlx_whisper:
        language: "ru"
    """
    expect(EngineConfig.read(from: yaml) == .whisper, "read whisper")
    let qwen: String
    do {
        qwen = try EngineConfig.write(.qwen, into: yaml)
    } catch {
        expect(false, "write qwen threw \(error)")
        return
    }
    expect(EngineConfig.read(from: qwen) == .qwen, "read qwen")
    expect(qwen.contains("engine: local_stt"), "menubar engine stays local_stt")
    expect(qwen.contains("engine: qwen3_asr  # mlx_whisper | whisper_cpp"), "comment kept")
    expect(qwen.contains("model_name: \"moona3k/mlx-qwen3-asr-1.7b-8bit\""), "qwen model")
    expect(qwen.contains("quantization_bits: null"), "prequantized, no second pass")
    expect(qwen.contains("language: \"ru\""), "qwen language ru")
    let again = (try? EngineConfig.write(.qwen, into: qwen)) ?? ""
    expect(again == qwen, "qwen block inserted once")
    let back = (try? EngineConfig.write(.whisper, into: qwen)) ?? ""
    expect(EngineConfig.read(from: back) == .whisper, "back to whisper")
    expect(back.contains("qwen3_asr:"), "qwen block kept")
    expect(back.contains("engine: local_stt"), "local_stt kept on the way back")

    let file = writeTempConfig("config.yaml", yaml)
    let original = readText(file)

    let missing = EngineController(configURL: file, uvExecutable: "/bin/uv") { _, args, _ in
        if args.contains("import mlx_qwen3_asr") {
            return ProcessResult(status: 1, stderr: "missing")
        }
        return ProcessResult(status: 0, stderr: "")
    }
    do {
        try missing.select(.qwen)
        expect(false, "missing extra should throw")
    } catch let error as EngineSwitchError {
        expect(error == .qwenExtraMissing, "qwen extra missing")
    } catch {
        expect(false, "unexpected \(error)")
    }
    expect(readText(file) == original, "config untouched when extra missing")

    let calls = CallLog()
    let failedRestart = EngineController(configURL: file, uvExecutable: "/bin/uv") { _, args, _ in
        calls.add(args.joined(separator: " "))
        if args.contains("kickstart") {
            return ProcessResult(status: 1, stderr: "no")
        }
        return ProcessResult(status: 0, stderr: "")
    }
    do {
        try failedRestart.select(.qwen)
        expect(false, "restart failure should throw")
    } catch let error as EngineSwitchError {
        expect(error == .restartFailed, "restart failed")
    } catch {
        expect(false, "unexpected \(error)")
    }
    expect(readText(file) == original, "config reverted after restart failure")

    calls.reset()
    let ok = EngineController(configURL: file, uvExecutable: "/bin/uv") { _, args, _ in
        calls.add(args.joined(separator: " "))
        return ProcessResult(status: 0, stderr: "")
    }
    do {
        try ok.select(.qwen)
    } catch {
        expect(false, "successful switch threw \(error)")
    }
    let switched = readText(file)
    expect(EngineConfig.read(from: switched) == .qwen, "file is qwen")
    expect(switched.contains("engine: local_stt"), "local_stt after switch")
    expect(calls.values.contains { $0.contains("kickstart") && $0.contains("ai.vtt2.stt") }, "kickstart stt only")
    do {
        try ok.select(.qwen)
    } catch {
        expect(false, "same engine should be a no-op \(error)")
    }
    expect(calls.values.filter { $0.contains("kickstart") }.count == 1, "second click does not restart")
}

/// Same shape as the repo config.yaml (header comments, Cyrillic, comments inside
/// blocks, sibling blocks after `transcription`) in its Whisper state, before the
/// menu ever inserted a qwen3_asr block. Replaces reading the live repo file.
let liveShapedConfig = """
# VTTv2 Configuration — profile: idle_unload (default)
#
# HTTP process always runs. The model loads on the first request.

app:
  version: "1.7.0"
  name: "VTTv2"

# Локальный STT HTTP (владелец модели). Menubar и агенты — клиенты.
stt_server:
  host: "127.0.0.1"
  port: 8765
  max_upload_mb: 80  # headroom for ~20 min 16 kHz mono 16-bit WAV
  engine: mlx_whisper  # mlx_whisper | whisper_cpp | qwen3_asr — что грузит ai.vtt2.stt
  # Do not load the checkpoint at login
  preload_on_start: false
  idle_unload_seconds: 900

# ⭐ Движок транскрипции (menubar)
transcription:
  # local_stt — HTTP к ai.vtt2.stt (одна модель)
  engine: local_stt  # local_stt | mlx_whisper | whisper_cpp | remote_asr
  local_stt:
    base_url: "http://127.0.0.1:8765"
    path: "/v1/audio/transcriptions"
    timeout_seconds: 600
    # Wait for on-demand model load (cold start after idle)
    warmup_wait_seconds: 180
  mlx_whisper:
    # Модель MLX (автоматически скачивается при первом использовании)
    model_name: "mlx-community/whisper-large-v3-mlx"
    language: "ru"  # "ru" | "en" | "auto"
    batch_size: 4
  whisper_cpp:
    model_path: "./models/ggml-medium-q5_0.bin"
    language: "ru"
  remote_asr:
    host: "YOUR_TAILSCALE_IP"
    port: 8001

# Аудио
audio:
  sample_rate: 16000
  channels: 1

"""

/// Whisper → Qwen → Whisper → Qwen through EngineController on a temp copy of a
/// live-shaped config. The second Qwen switch covers today's repo shape, where
/// the qwen3_asr block already exists.
func runLiveShapedSwitchTests() {
    let file = writeTempConfig("config.yaml", liveShapedConfig)
    let calls = CallLog()
    let controller = EngineController(configURL: file, uvExecutable: "/bin/uv") { _, args, _ in
        calls.add(args.joined(separator: " "))
        return ProcessResult(status: 0, stderr: "")
    }
    func qwenBlocks(_ text: String) -> Int {
        text.components(separatedBy: "qwen3_asr:").count - 1
    }
    func lineCount(_ text: String) -> Int {
        text.components(separatedBy: "\n").count
    }

    expect(EngineConfig.read(from: liveShapedConfig) == .whisper, "live: starts on whisper")
    do {
        try controller.select(.qwen)
    } catch {
        expect(false, "live: switch to qwen threw \(error)")
    }
    let qwen = readText(file)
    expect(EngineConfig.read(from: qwen) == .qwen, "live: file is qwen")
    expect(qwen.contains("engine: local_stt  # local_stt"), "live: menubar engine stays local_stt")
    expect(
        qwen.contains("engine: qwen3_asr  # mlx_whisper | whisper_cpp | qwen3_asr — что грузит ai.vtt2.stt"),
        "live: engine comment kept"
    )
    expect(qwen.contains("moona3k/mlx-qwen3-asr-1.7b-8bit"), "live: prequantized checkpoint")
    expect(qwen.contains("quantization_bits: null"), "live: no second quantization")
    expect(qwen.contains("mlx-community/whisper-large-v3-mlx"), "live: whisper checkpoint kept")
    expect(qwenBlocks(qwen) == 1, "live: one qwen block, got \(qwenBlocks(qwen))")
    expect(lineCount(qwen) == lineCount(liveShapedConfig) + 5, "live: only the 5-line qwen block added")
    expect(qwen.hasSuffix("  channels: 1\n"), "live: tail of the file untouched")
    if let transcription = qwen.range(of: "\ntranscription:\n"),
       let block = qwen.range(of: "\n  qwen3_asr:\n"),
       let whisper = qwen.range(of: "\n  mlx_whisper:\n")
    {
        expect(
            transcription.upperBound <= block.lowerBound && block.upperBound <= whisper.upperBound,
            "live: qwen block inside transcription, before mlx_whisper"
        )
    } else {
        expect(false, "live: qwen block not found at transcription level")
    }
    expect(AppConfig.parseYAML(qwen) == AppConfig.parseYAML(liveShapedConfig), "live: local_stt settings untouched")

    do {
        try controller.select(.whisper)
    } catch {
        expect(false, "live: switch back to whisper threw \(error)")
    }
    let back = readText(file)
    expect(EngineConfig.read(from: back) == .whisper, "live: back to whisper")
    expect(qwenBlocks(back) == 1, "live: qwen block kept on the way back")

    do {
        try controller.select(.qwen)
    } catch {
        expect(false, "live: second switch to qwen threw \(error)")
    }
    expect(readText(file) == qwen, "live: existing qwen block reused, not duplicated")
    expect(calls.values.filter { $0.contains("kickstart") }.count == 3, "live: one restart per switch")
}
