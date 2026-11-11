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
