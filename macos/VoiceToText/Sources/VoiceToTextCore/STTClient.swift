import Foundation

public enum STTClientError: Error, Equatable, Sendable {
    case unreachable(String)
    case healthFailed(Int)
    /// Non-retryable server answer: status and the server's message.
    case httpStatus(Int, String)
    case timeout
    case invalidResponse
    case cancelled
    /// The server stayed busy or kept loading past the retry budget.
    case gaveUp(Int)
    /// Translation was asked of a model that can't translate (Qwen, Whisper turbo).
    case translationUnsupported(String)

    /// Short Russian text for the menu status line.
    public var userMessage: String {
        switch self {
        case .unreachable: return "Сервер распознавания не запущен"
        case .healthFailed(let code): return "Сервер распознавания не отвечает (\(code))"
        case .httpStatus(400, _): return "Не удалось прочитать запись"
        case .httpStatus(413, _): return "Запись слишком длинная"
        case .httpStatus(500, _): return "Модель не загрузилась"
        case .httpStatus(504, _): return "Распознавание заняло слишком долго"
        case .httpStatus(let code, _): return "Ошибка сервера (\(code))"
        case .timeout: return "Сервер не ответил вовремя"
        case .invalidResponse: return "Непонятный ответ сервера"
        case .cancelled: return "Отменено"
        case .gaveUp: return "Сервер занят, попробуйте ещё раз"
        case .translationUnsupported: return "Перевод умеет Whisper large-v3 — выберите его в меню «Модель»"
        }
    }
}

/// How the client treats a non-200 answer. Mirrors docs/STT_API.md.
public enum RetryDecision: Equatable, Sendable {
    case retry(after: TimeInterval)
    case fail
}

public enum RetryPolicy {
    /// 429 busy: honour Retry-After. 503: only while the model is loading.
    /// Everything else (400, 413, 500 load failed, 504 timeout) fails at once.
    public static func decide(
        status: Int,
        errorCode: String?,
        retryAfter: String?,
        serverSaysLoading: Bool
    ) -> RetryDecision {
        switch status {
        case 429:
            let seconds = retryAfter.flatMap { TimeInterval($0.trimmingCharacters(in: .whitespaces)) } ?? 2
            return .retry(after: min(max(seconds, 0.5), 10))
        case 503 where errorCode == "model_loading" || (errorCode == nil && serverSaysLoading):
            return .retry(after: 1.5)
        default:
            return .fail
        }
    }

    /// `{"error": {"message", "code"}}` (current server) or `{"detail": ...}` (older).
    public static func parseError(_ data: Data) -> (code: String?, message: String) {
        guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return (nil, String(data: data, encoding: .utf8).map { String($0.prefix(200)) } ?? "")
        }
        if let error = object["error"] as? [String: Any] {
            return (error["code"] as? String, (error["message"] as? String) ?? "")
        }
        if let detail = object["detail"] as? String {
            return (nil, detail)
        }
        return (nil, "")
    }
}

public struct STTClient: Sendable {
    public let config: AppConfig
    private let session: URLSession
    private let probeSession: URLSession
    private let sleeper: @Sendable (TimeInterval) async -> Void

    /// Give up on 429/503-loading after this long. Never the 10+ minute lockups of old.
    public static let maxRetryWait: TimeInterval = 180
    /// /healthz must answer fast; a hung server should not freeze the hotkey.
    public static let probeTimeout: TimeInterval = 3
    public static let translationsPath = "/v1/audio/translations"

    public init(
        config: AppConfig,
        session: URLSession? = nil,
        sleeper: (@Sendable (TimeInterval) async -> Void)? = nil
    ) {
        self.config = config
        if let session {
            self.session = session
            self.probeSession = session
        } else {
            let sessionConfig = URLSessionConfiguration.ephemeral
            sessionConfig.timeoutIntervalForRequest = config.timeoutSeconds
            sessionConfig.timeoutIntervalForResource = config.timeoutSeconds + Self.maxRetryWait
            self.session = URLSession(configuration: sessionConfig)
            let probeConfig = URLSessionConfiguration.ephemeral
            probeConfig.timeoutIntervalForRequest = Self.probeTimeout
            probeConfig.timeoutIntervalForResource = Self.probeTimeout
            self.probeSession = URLSession(configuration: probeConfig)
        }
        self.sleeper = sleeper ?? { seconds in
            try? await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
        }
    }

    public func healthOK() async throws -> Bool {
        _ = try await health()
        return true
    }

    /// Transcribe WAV. Retries only what the server marks as temporary, and stops
    /// as soon as the surrounding Task is cancelled.
    /// `prompt` (optional) goes out as the OpenAI `prompt` field: Whisper's initial
    /// prompt / Qwen's context. The app fills it from the user's glossary.
    /// `translate` sends the audio to `/v1/audio/translations` (speech → English).
    public func transcribe(wav: Data, prompt: String? = nil, translate: Bool = false) async throws -> String {
        try checkCancelled()
        _ = try await health()

        let url = endpoint(translate ? Self.translationsPath : config.path)
        let deadline = Date().addingTimeInterval(min(config.warmupWaitSeconds, Self.maxRetryWait))
        var attempt = 0

        while true {
            try checkCancelled()
            attempt += 1
            let request = try multipartRequest(url: url, wav: wav, prompt: prompt)
            let (data, http) = try await send(request)
            if http.statusCode == 200 {
                return try Self.parseText(data)
            }
            let (code, message) = RetryPolicy.parseError(data)
            var loading = false
            if http.statusCode == 503, code == nil {
                loading = (try? await health())?["loading"] as? Bool ?? false
            }
            let decision = RetryPolicy.decide(
                status: http.statusCode,
                errorCode: code,
                retryAfter: http.value(forHTTPHeaderField: "Retry-After"),
                serverSaysLoading: loading
            )
            switch decision {
            case .retry(let wait):
                guard Date().addingTimeInterval(wait) < deadline else {
                    AppLog.warning("STT \(http.statusCode) still after retries; giving up")
                    throw STTClientError.gaveUp(http.statusCode)
                }
                AppLog.info("STT \(http.statusCode) \(code ?? "") attempt=\(attempt); retry in \(wait)s")
                await sleeper(wait)
            case .fail:
                AppLog.error("STT \(http.statusCode) \(code ?? ""): \(message.prefix(200))")
                if code == "translation_unsupported" {
                    throw STTClientError.translationUnsupported(String(message.prefix(200)))
                }
                throw STTClientError.httpStatus(http.statusCode, String(message.prefix(200)))
            }
        }
    }

    // MARK: - Transport

    @discardableResult
    private func health() async throws -> [String: Any] {
        let url = endpoint("healthz")
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await probeSession.data(from: url)
        } catch {
            throw mapTransport(error, unreachableHint: true)
        }
        guard let http = response as? HTTPURLResponse else {
            throw STTClientError.invalidResponse
        }
        if http.statusCode != 200 {
            throw STTClientError.healthFailed(http.statusCode)
        }
        return (try? JSONSerialization.jsonObject(with: data) as? [String: Any]) ?? [:]
    }

    private func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw STTClientError.invalidResponse
            }
            return (data, http)
        } catch let error as STTClientError {
            throw error
        } catch {
            throw mapTransport(error, unreachableHint: false)
        }
    }

    private func mapTransport(_ error: Error, unreachableHint: Bool) -> STTClientError {
        if error is CancellationError { return .cancelled }
        if let urlError = error as? URLError {
            if urlError.code == .cancelled { return .cancelled }
            if urlError.code == .timedOut { return .timeout }
        }
        if let clientError = error as? STTClientError { return clientError }
        let detail = error.localizedDescription
        if unreachableHint {
            return .unreachable(
                "Cannot reach local STT (\(config.baseURL.absoluteString)): \(detail). Start ai.vtt2.stt."
            )
        }
        return .unreachable(detail)
    }

    private func checkCancelled() throws {
        if Task.isCancelled { throw STTClientError.cancelled }
    }

    private func endpoint(_ relative: String) -> URL {
        let trimmed = relative.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        return trimmed.split(separator: "/").reduce(config.baseURL) { url, part in
            url.appendingPathComponent(String(part))
        }
    }

    func multipartRequest(url: URL, wav: Data, prompt: String? = nil) throws -> URLRequest {
        let boundary = "vtt-\(UUID().uuidString)"
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        var body = Data()
        if let prompt, !prompt.isEmpty {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"prompt\"\r\n\r\n".data(using: .utf8)!)
            body.append(prompt.data(using: .utf8)!)
            body.append("\r\n".data(using: .utf8)!)
        }
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
