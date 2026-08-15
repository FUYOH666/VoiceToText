import Foundation
import Testing
@testable import VoiceToTextCore

@Suite struct AppConfigTests {
    @Test func parseLocalSTTBlock() {
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
        #expect(config.baseURL.absoluteString == "http://127.0.0.1:8765")
        #expect(config.path == "/v1/audio/transcriptions")
        #expect(config.timeoutSeconds == 600)
        #expect(config.warmupWaitSeconds == 180)
    }

    @Test func missingBlockUsesDefaults() {
        let config = AppConfig.parseYAML("app:\n  name: VTTv2\n")
        #expect(config == .loopbackDefault)
    }

    @Test func wavHeaderIsRIFF() {
        let wav = WAVEncoder.pcm16kMono(floats: [0, 0.5, -0.5])
        #expect(String(data: wav.prefix(4), encoding: .ascii) == "RIFF")
        #expect(wav.count > 44)
    }
}
