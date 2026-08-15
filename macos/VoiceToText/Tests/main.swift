import Foundation

var failed = 0

func expect(_ cond: Bool, _ message: String) {
    if !cond {
        fputs("FAIL: \(message)\n", stderr)
        failed += 1
    }
}

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
    let wav = WAVEncoder.pcm16kMono(floats: [0, 0.5, -0.5])
    expect(String(data: wav.prefix(4), encoding: .ascii) == "RIFF", "wav header")
    expect(wav.count > 44, "wav size")
}

func runSTTClientTests() async {
    MockURLProtocol.reset()
    MockURLProtocol.handler = { request in
        let path = request.url?.path ?? ""
        if path.hasSuffix("healthz") || path.hasSuffix("readyz") {
            return (200, Data(#"{"status":"ok"}"#.utf8))
        }
        return (200, Data(#"{"text":"привет"}"#.utf8))
    }
    do {
        let text = try await makeClient().transcribe(wav: Data([1, 2, 3]))
        expect(text == "привет", "transcribe 200, got \(text)")
    } catch {
        expect(false, "transcribe 200 threw \(error)")
    }

    MockURLProtocol.reset()
    let posts = LockBox(0)
    MockURLProtocol.handler = { request in
        let path = request.url?.path ?? ""
        if path.hasSuffix("healthz") { return (200, Data(#"{}"#.utf8)) }
        if path.hasSuffix("readyz") { return (503, Data(#"{}"#.utf8)) }
        if posts.increment() == 1 {
            return (503, Data(#"{"detail":"loading"}"#.utf8))
        }
        return (200, Data(#"{"text":"after warmup"}"#.utf8))
    }
    do {
        let text = try await makeClient().transcribe(wav: Data([1]))
        expect(text == "after warmup", "503 retry, got \(text)")
        expect(posts.value == 2, "expected 2 POSTs, got \(posts.value)")
    } catch {
        expect(false, "503 retry threw \(error)")
    }

    MockURLProtocol.reset()
    MockURLProtocol.handler = { _ in throw URLError(.cannotConnectToHost) }
    do {
        _ = try await makeClient().transcribe(wav: Data([1]))
        expect(false, "connect fail should throw")
    } catch let error as STTClientError {
        if case .unreachable = error {
            expect(true, "unreachable")
        } else {
            expect(false, "expected unreachable, got \(error)")
        }
    } catch {
        expect(false, "connect fail unexpected \(error)")
    }

    MockURLProtocol.reset()
    MockURLProtocol.handler = { _ in (503, Data(#"{}"#.utf8)) }
    do {
        _ = try await makeClient().healthOK()
        expect(false, "health 503 should throw")
    } catch let error as STTClientError {
        expect(error == .healthFailed(503), "healthFailed 503, got \(error)")
    } catch {
        expect(false, "health unexpected \(error)")
    }
}

private final class LockBox: @unchecked Sendable {
    private let lock = NSLock()
    private var n: Int
    init(_ n: Int) { self.n = n }
    var value: Int { lock.withLock { n } }
    func increment() -> Int {
        lock.withLock {
            n += 1
            return n
        }
    }
}

func makeClient() -> STTClient {
    let configuration = URLSessionConfiguration.ephemeral
    configuration.protocolClasses = [MockURLProtocol.self]
    configuration.timeoutIntervalForRequest = 2
    return STTClient(
        config: .loopbackDefault,
        session: URLSession(configuration: configuration),
        sleeper: { _ in }
    )
}

runAppConfigTests()
let sem = DispatchSemaphore(value: 0)
Task {
    await runSTTClientTests()
    sem.signal()
}
sem.wait()

if failed > 0 {
    fputs("\(failed) test(s) failed\n", stderr)
    exit(1)
}
print("All VoiceToTextCore tests passed")
