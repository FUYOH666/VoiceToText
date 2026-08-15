import Foundation

public enum STTClientError: Error, Equatable, Sendable {
    case unreachable(String)
    case healthFailed(Int)
    case httpStatus(Int, String)
    case timeout
    case invalidResponse
}

public struct STTClient: Sendable {
    public let config: AppConfig
    private let session: URLSession
    private let sleeper: @Sendable (TimeInterval) async -> Void

    public init(
        config: AppConfig,
        session: URLSession? = nil,
        sleeper: (@Sendable (TimeInterval) async -> Void)? = nil
    ) {
        self.config = config
        if let session {
            self.session = session
        } else {
            let sessionConfig = URLSessionConfiguration.ephemeral
            sessionConfig.timeoutIntervalForRequest = config.timeoutSeconds
            sessionConfig.timeoutIntervalForResource = config.timeoutSeconds + config.warmupWaitSeconds
            self.session = URLSession(configuration: sessionConfig)
        }
        self.sleeper = sleeper ?? { seconds in
            try? await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
        }
    }

    public func healthOK() async throws -> Bool {
        let url = endpoint("healthz")
        let (data, response) = try await data(from: url)
        guard let http = response as? HTTPURLResponse else {
            throw STTClientError.invalidResponse
        }
        if http.statusCode != 200 {
            throw STTClientError.healthFailed(http.statusCode)
        }
        _ = data
        return true
    }

    /// Transcribe WAV. `readyz` 503 is OK (idle unload). POST retries 503 until warmup deadline.
    public func transcribe(wav: Data) async throws -> String {
        try await assertProcessUp()

        let readyURL = endpoint("readyz")
        if let (_, response) = try? await data(from: readyURL),
           let http = response as? HTTPURLResponse,
           http.statusCode != 200
        {
            AppLog.info("readyz=\(http.statusCode) — POST will load on demand")
        }

        let url = endpoint(config.path)
        let deadline = Date().addingTimeInterval(config.warmupWaitSeconds + config.timeoutSeconds)
        var attempt = 0

        while true {
            attempt += 1
            let request = try multipartRequest(url: url, wav: wav)
            do {
                let (data, response) = try await session.data(for: request)
                guard let http = response as? HTTPURLResponse else {
                    throw STTClientError.invalidResponse
                }
                if http.statusCode == 200 {
                    return try Self.parseText(data)
                }
                if http.statusCode == 503, Date() < deadline {
                    let detail = String(data: data, encoding: .utf8) ?? ""
                    AppLog.info("STT 503 (warmup/busy) attempt=\(attempt): \(detail.prefix(200))")
                    await sleeper(2)
                    continue
                }
                let body = String(data: data, encoding: .utf8) ?? ""
                throw STTClientError.httpStatus(http.statusCode, String(body.prefix(200)))
            } catch let error as STTClientError {
                throw error
            } catch let error as URLError where error.code == .timedOut {
                throw STTClientError.timeout
            } catch {
                throw STTClientError.unreachable(error.localizedDescription)
            }
        }
    }

    private func assertProcessUp() async throws {
        let url = endpoint("healthz")
        do {
            let (_, response) = try await data(from: url)
            guard let http = response as? HTTPURLResponse else {
                throw STTClientError.invalidResponse
            }
            if http.statusCode != 200 {
                throw STTClientError.healthFailed(http.statusCode)
            }
        } catch let error as STTClientError {
            throw error
        } catch {
            throw STTClientError.unreachable(
                "Cannot reach local STT (\(config.baseURL.absoluteString)): \(error.localizedDescription). Start ai.vtt2.stt."
            )
        }
    }

    private func endpoint(_ relative: String) -> URL {
        let trimmed = relative.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        return trimmed.split(separator: "/").reduce(config.baseURL) { url, part in
            url.appendingPathComponent(String(part))
        }
    }

    private func data(from url: URL) async throws -> (Data, URLResponse) {
        do {
            return try await session.data(from: url)
        } catch let error as URLError where error.code == .timedOut {
            throw STTClientError.timeout
        } catch let error as STTClientError {
            throw error
        } catch {
            throw STTClientError.unreachable(error.localizedDescription)
        }
    }

    private func multipartRequest(url: URL, wav: Data) throws -> URLRequest {
        let boundary = "vtt-\(UUID().uuidString)"
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append(
            "Content-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\n".data(using: .utf8)!
        )
        body.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
        body.append(wav)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body
        return request
    }

    static func parseText(_ data: Data) throws -> String {
        guard
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            throw STTClientError.invalidResponse
        }
        let text = (object["text"] as? String) ?? (object["transcription"] as? String) ?? ""
        return text.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
