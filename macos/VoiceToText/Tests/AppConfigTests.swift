import Foundation

func runAppConfigTests() {
    let yaml = """
    transcription:
      engine: local_stt
      local_stt:
        base_url: "http://127.0.0.1:8765"
        path: "/v1/audio/transcriptions"
        timeout_seconds: 600
        warmup_wait_seconds: 180
      mlx_whisper:
        language: "ru"
    """
    let config = AppConfig.parseYAML(yaml)
    expect(config.baseURL.absoluteString == "http://127.0.0.1:8765", "base_url")
    expect(config.path == "/v1/audio/transcriptions", "path")
    expect(config.timeoutSeconds == 600, "timeout")
    expect(config.warmupWaitSeconds == 180, "warmup")
    expect(AppConfig.parseYAML("app:\n  name: x\n") == .loopbackDefault, "defaults")
}

func runWAVEncoderTests() {
    let wav = WAVEncoder.pcm16kMono(floats: [0, 0.5, -0.5])
    expect(String(data: wav.prefix(4), encoding: .ascii) == "RIFF", "wav header")
    expect(wav.count > 44, "wav size")
}
