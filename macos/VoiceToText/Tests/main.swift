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

    let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    let file = dir.appendingPathComponent("config.yaml")
    try? yaml.write(to: file, atomically: true, encoding: .utf8)
    let original = (try? String(contentsOf: file, encoding: .utf8)) ?? ""

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
    let afterMiss = (try? String(contentsOf: file, encoding: .utf8)) ?? ""
    expect(afterMiss == original, "config untouched when extra missing")

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
    let reverted = (try? String(contentsOf: file, encoding: .utf8)) ?? ""
    expect(reverted == original, "config reverted after restart failure")

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
    let switched = (try? String(contentsOf: file, encoding: .utf8)) ?? ""
    expect(EngineConfig.read(from: switched) == .qwen, "file is qwen")
    expect(switched.contains("engine: local_stt"), "local_stt after live-shaped switch")
    expect(calls.values.contains { $0.contains("kickstart") && $0.contains("ai.vtt2.stt") }, "kickstart stt only")
    do {
        try ok.select(.qwen)
    } catch {
        expect(false, "same engine should be a no-op \(error)")
    }
    expect(calls.values.filter { $0.contains("kickstart") }.count == 1, "second click does not restart")
    try? FileManager.default.removeItem(at: dir)

    let repo = URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent("config.yaml")
    if let repoText = try? String(contentsOf: repo, encoding: .utf8), repoText.contains("stt_server:") {
        expect(repoText.contains("engine: local_stt"), "live menubar engine stays")
        expect(repoText.contains("mlx-community/whisper-large-v3-mlx"), "whisper checkpoint kept")
        if EngineConfig.read(from: repoText) == .whisper,
           let edited = try? EngineConfig.write(.qwen, into: repoText) {
            expect(EngineConfig.read(from: edited) == .qwen, "live yaml would switch")
            expect(edited.contains("moona3k/mlx-qwen3-asr-1.7b-8bit"), "live insert uses prequant")
            expect(edited.contains("quantization_bits: null"), "live insert does not requantize")
            let qwenKeys = edited.components(separatedBy: "qwen3_asr:").count - 1
            expect(qwenKeys == 1, "one qwen block, got \(qwenKeys)")
        }
    }
}

private final class CallLog: @unchecked Sendable {
    private let lock = NSLock()
    private var items: [String] = []
    func add(_ item: String) { lock.withLock { items.append(item) } }
    func reset() { lock.withLock { items.removeAll() } }
    var values: [String] { lock.withLock { items } }
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
runEngineSwitchTests()
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
