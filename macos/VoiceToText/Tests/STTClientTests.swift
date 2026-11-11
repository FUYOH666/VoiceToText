import Foundation

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

    // 503 model_loading (current server) is retried.
    MockURLProtocol.reset()
    let posts = LockBox(0)
    MockURLProtocol.handler = { request in
        let path = request.url?.path ?? ""
        if path.hasSuffix("healthz") { return (200, Data(#"{}"#.utf8)) }
        if posts.increment() == 1 {
            return (503, Data(#"{"error":{"message":"loading","type":"server_error","code":"model_loading"}}"#.utf8))
        }
        return (200, Data(#"{"text":"after warmup"}"#.utf8))
    }
    do {
        let text = try await makeClient().transcribe(wav: Data([1]))
        expect(text == "after warmup", "503 model_loading retry, got \(text)")
        expect(posts.value == 2, "expected 2 POSTs, got \(posts.value)")
    } catch {
        expect(false, "503 model_loading retry threw \(error)")
    }

    // Older server: bare 503 is retried only while /healthz says loading.
    MockURLProtocol.reset()
    let legacyPosts = LockBox(0)
    MockURLProtocol.handler = { request in
        let path = request.url?.path ?? ""
        if path.hasSuffix("healthz") { return (200, Data(#"{"loading":true}"#.utf8)) }
        if legacyPosts.increment() == 1 { return (503, Data(#"{"detail":"loading"}"#.utf8)) }
        return (200, Data(#"{"text":"legacy ok"}"#.utf8))
    }
    do {
        let text = try await makeClient().transcribe(wav: Data([1]))
        expect(text == "legacy ok" && legacyPosts.value == 2, "legacy 503 while loading retried")
    } catch {
        expect(false, "legacy 503 loading threw \(error)")
    }

    // ...and a bare 503 when nothing is loading fails at once (no 13-minute lockup).
    await expectFailure(status: 503, body: #"{"detail":"STT model load failed: boom"}"#, posts: 1, label: "bare 503")
    await expectFailure(status: 500, body: #"{"error":{"message":"x","code":"model_load_failed"}}"#, posts: 1, label: "500 load failed")
    await expectFailure(status: 504, body: #"{"error":{"message":"x","code":"transcription_timeout"}}"#, posts: 1, label: "504 timeout")
    await expectFailure(status: 400, body: #"{"error":{"message":"bad","code":"invalid_audio"}}"#, posts: 1, label: "400 invalid")

    // 429 busy is retried, honouring Retry-After.
    MockURLProtocol.reset()
    MockURLProtocol.headers = ["Retry-After": "3"]
    let busyPosts = LockBox(0)
    let waits = WaitLog()
    MockURLProtocol.handler = { request in
        if request.url?.path.hasSuffix("healthz") == true { return (200, Data(#"{}"#.utf8)) }
        if busyPosts.increment() == 1 { return (429, Data(#"{"error":{"message":"busy","code":"busy"}}"#.utf8)) }
        return (200, Data(#"{"text":"after busy"}"#.utf8))
    }
    do {
        let text = try await makeClient(sleeper: { waits.add($0) }).transcribe(wav: Data([1]))
        expect(text == "after busy" && busyPosts.value == 2, "429 retried, got \(text)")
        expect(waits.values == [3], "Retry-After honoured, waited \(waits.values)")
    } catch {
        expect(false, "429 retry threw \(error)")
    }

    // Busy past the retry budget gives up instead of hanging.
    MockURLProtocol.reset()
    MockURLProtocol.handler = { request in
        if request.url?.path.hasSuffix("healthz") == true { return (200, Data(#"{}"#.utf8)) }
        return (429, Data(#"{"error":{"message":"busy","code":"busy"}}"#.utf8))
    }
    do {
        _ = try await makeClient(retryBudget: 0).transcribe(wav: Data([1]))
        expect(false, "endless 429 should give up")
    } catch let error as STTClientError {
        expect(error == .gaveUp(429), "gaveUp(429), got \(error)")
    } catch {
        expect(false, "gaveUp unexpected \(error)")
    }

    // A cancelled task stops without sending anything.
    MockURLProtocol.reset()
    MockURLProtocol.handler = { _ in (200, Data(#"{"text":"late"}"#.utf8)) }
    let outcome = await Task { () -> String in
        withUnsafeCurrentTask { $0?.cancel() }  // deterministic: cancelled before the call
        do {
            _ = try await makeClient().transcribe(wav: Data([1]))
            return "returned"
        } catch let error as STTClientError {
            return error == .cancelled ? "cancelled" : "\(error)"
        } catch {
            return "other \(error)"
        }
    }.value
    expect(outcome == "cancelled", "cancelled transcribe, got \(outcome)")
    expect(MockURLProtocol.requests.isEmpty, "cancelled transcribe sent no request")

    runRetryPolicyTests()

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

func makeClient(
    retryBudget: TimeInterval? = nil,
    sleeper: (@Sendable (TimeInterval) async -> Void)? = nil
) -> STTClient {
    let configuration = URLSessionConfiguration.ephemeral
    configuration.protocolClasses = [MockURLProtocol.self]
    configuration.timeoutIntervalForRequest = 2
    var config = AppConfig.loopbackDefault
    if let retryBudget { config.warmupWaitSeconds = retryBudget }
    return STTClient(
        config: config,
        session: URLSession(configuration: configuration),
        sleeper: sleeper ?? { _ in }
    )
}

final class WaitLog: @unchecked Sendable {
    private let lock = NSLock()
    private var items: [TimeInterval] = []
    func add(_ value: TimeInterval) { lock.withLock { items.append(value) } }
    var values: [TimeInterval] { lock.withLock { items } }
}

/// A non-retryable status: exactly `posts` POSTs, then `.httpStatus(status, …)`.
func expectFailure(status: Int, body: String, posts expected: Int, label: String) async {
    MockURLProtocol.reset()
    let posts = LockBox(0)
    MockURLProtocol.handler = { request in
        if request.url?.path.hasSuffix("healthz") == true { return (200, Data(#"{"loading":false}"#.utf8)) }
        _ = posts.increment()
        return (status, Data(body.utf8))
    }
    do {
        _ = try await makeClient().transcribe(wav: Data([1]))
        expect(false, "\(label) should throw")
    } catch let error as STTClientError {
        if case .httpStatus(let code, _) = error {
            expect(code == status, "\(label): status \(code)")
        } else {
            expect(false, "\(label): expected httpStatus, got \(error)")
        }
        expect(posts.value == expected, "\(label): \(posts.value) POSTs, expected \(expected)")
    } catch {
        expect(false, "\(label) unexpected \(error)")
    }
}

func runRetryPolicyTests() {
    expect(RetryPolicy.decide(status: 429, errorCode: "busy", retryAfter: "4", serverSaysLoading: false) == .retry(after: 4), "429 Retry-After")
    expect(RetryPolicy.decide(status: 429, errorCode: nil, retryAfter: nil, serverSaysLoading: false) == .retry(after: 2), "429 default wait")
    expect(RetryPolicy.decide(status: 429, errorCode: nil, retryAfter: "600", serverSaysLoading: false) == .retry(after: 10), "429 wait capped")
    expect(RetryPolicy.decide(status: 503, errorCode: "model_loading", retryAfter: nil, serverSaysLoading: false) == .retry(after: 1.5), "503 loading")
    expect(RetryPolicy.decide(status: 503, errorCode: nil, retryAfter: nil, serverSaysLoading: true) == .retry(after: 1.5), "legacy 503 loading")
    expect(RetryPolicy.decide(status: 503, errorCode: nil, retryAfter: nil, serverSaysLoading: false) == .fail, "legacy 503 not loading")
    expect(RetryPolicy.decide(status: 503, errorCode: "busy", retryAfter: nil, serverSaysLoading: true) == .fail, "503 other code")
    for status in [400, 404, 413, 500, 504] {
        expect(RetryPolicy.decide(status: status, errorCode: nil, retryAfter: nil, serverSaysLoading: true) == .fail, "\(status) fails")
    }
    let parsed = RetryPolicy.parseError(Data(#"{"error":{"message":"m","code":"c"}}"#.utf8))
    expect(parsed.code == "c" && parsed.message == "m", "parse error envelope")
    let legacy = RetryPolicy.parseError(Data(#"{"detail":"d"}"#.utf8))
    expect(legacy.code == nil && legacy.message == "d", "parse legacy detail")
}
