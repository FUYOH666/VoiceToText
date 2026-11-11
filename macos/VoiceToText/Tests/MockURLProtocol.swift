import Foundation

final class MockURLProtocol: URLProtocol, @unchecked Sendable {
    private static let lock = NSLock()
    private static var _handler: ((URLRequest) throws -> (Int, Data))?
    private static var _requests: [URLRequest] = []

    static var handler: ((URLRequest) throws -> (Int, Data))? {
        get { lock.withLock { _handler } }
        set { lock.withLock { _handler = newValue } }
    }

    static var requests: [URLRequest] {
        lock.withLock { _requests }
    }

    private static var _headers: [String: String] = [:]

    /// Extra response headers (e.g. Retry-After) for every response.
    static var headers: [String: String] {
        get { lock.withLock { _headers } }
        set { lock.withLock { _headers = newValue } }
    }

    static func reset() {
        lock.withLock {
            _handler = nil
            _requests = []
            _headers = [:]
        }
    }

    override class func canInit(with request: URLRequest) -> Bool { true }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let current = request
        Self.lock.withLock { Self._requests.append(current) }
        do {
            guard let handler = Self.handler else {
                throw URLError(.badURL)
            }
            let (status, data) = try handler(current)
            let response = HTTPURLResponse(
                url: current.url ?? URL(string: "http://127.0.0.1/invalid")!,
                statusCode: status,
                httpVersion: "HTTP/1.1",
                headerFields: ["Content-Type": "application/json"].merging(Self.headers) { $1 }
            )!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}
