import Foundation
import Testing
@testable import VoiceToTextCore

@Suite struct STTClientTests {
    private func client(sleeper: (@Sendable (TimeInterval) async -> Void)? = nil) -> STTClient {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [MockURLProtocol.self]
        configuration.timeoutIntervalForRequest = 2
        return STTClient(
            config: .loopbackDefault,
            session: URLSession(configuration: configuration),
            sleeper: sleeper ?? { _ in }
        )
    }

    @Test func transcribe200ReturnsText() async throws {
        MockURLProtocol.reset()
        MockURLProtocol.handler = { request in
            let path = request.url?.path ?? ""
            if path.hasSuffix("healthz") || path.hasSuffix("readyz") {
                return (200, Data(#"{"status":"ok"}"#.utf8))
            }
            return (200, Data(#"{"text":"привет"}"#.utf8))
        }
        let text = try await client().transcribe(wav: Data([1, 2, 3]))
        #expect(text == "привет")
    }

    @Test func transcribeRetries503ThenSucceeds() async throws {
        MockURLProtocol.reset()
        let posts = LockBox(0)
        MockURLProtocol.handler = { request in
            let path = request.url?.path ?? ""
            if path.hasSuffix("healthz") {
                return (200, Data(#"{}"#.utf8))
            }
            if path.hasSuffix("readyz") {
                return (503, Data(#"{"ready":false}"#.utf8))
            }
            let n = posts.increment()
            if n == 1 {
                return (503, Data(#"{"detail":"loading"}"#.utf8))
            }
            return (200, Data(#"{"text":"after warmup"}"#.utf8))
        }
        let text = try await client().transcribe(wav: Data([1]))
        #expect(text == "after warmup")
        #expect(posts.value == 2)
    }

    @Test func transcribeConnectFail() async {
        MockURLProtocol.reset()
        MockURLProtocol.handler = { _ in
            throw URLError(.cannotConnectToHost)
        }
        do {
            _ = try await client().transcribe(wav: Data([1]))
            Issue.record("expected unreachable")
        } catch let error as STTClientError {
            guard case .unreachable = error else {
                Issue.record("expected unreachable, got \(error)")
                return
            }
        } catch {
            Issue.record("unexpected \(error)")
        }
    }

    @Test func healthFailedStatus() async {
        MockURLProtocol.reset()
        MockURLProtocol.handler = { _ in (503, Data(#"{}"#.utf8)) }
        do {
            _ = try await client().healthOK()
            Issue.record("expected healthFailed")
        } catch let error as STTClientError {
            #expect(error == .healthFailed(503))
        } catch {
            Issue.record("unexpected \(error)")
        }
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
