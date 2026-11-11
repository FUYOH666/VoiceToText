import Foundation

/// One entry of `GET /v1/models` (see docs/STT_API.md).
public struct ModelInfo: Codable, Equatable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let family: String?
    public let repo: String?
    public let quantization: String?
    public let downloadGB: Double?
    public let ramGB: Double?
    public let minMemoryGB: Double?
    public let note: String?
    public let installed: Bool
    public let active: Bool
    public let recommended: Bool
    public let fitsMemory: Bool
    public let custom: Bool?
    public let download: DownloadStatus?
    /// Whisper's speech → English translation works well with this model.
    public let translates: Bool?

    enum CodingKeys: String, CodingKey {
        case id, title, family, repo, quantization, note, installed, active, recommended, custom, download, translates
        case downloadGB = "download_gb"
        case ramGB = "ram_gb"
        case minMemoryGB = "min_memory_gb"
        case fitsMemory = "fits_memory"
    }

    public init(
        id: String, title: String, family: String? = nil, repo: String? = nil,
        quantization: String? = nil, downloadGB: Double? = nil, ramGB: Double? = nil,
        minMemoryGB: Double? = nil, note: String? = nil, installed: Bool, active: Bool,
        recommended: Bool, fitsMemory: Bool, custom: Bool? = nil, download: DownloadStatus? = nil,
        translates: Bool? = nil
    ) {
        self.id = id
        self.title = title
        self.family = family
        self.repo = repo
        self.quantization = quantization
        self.downloadGB = downloadGB
        self.ramGB = ramGB
        self.minMemoryGB = minMemoryGB
        self.note = note
        self.installed = installed
        self.active = active
        self.recommended = recommended
        self.fitsMemory = fitsMemory
        self.custom = custom
        self.download = download
        self.translates = translates
    }
}

public struct DownloadStatus: Codable, Equatable, Sendable {
    public let model: String
    public let state: String  // idle | queued | downloading | done | error
    public let bytesDone: Int?
    public let bytesTotal: Int?
    public let progress: Double?
    public let error: String?

    enum CodingKeys: String, CodingKey {
        case model, state, progress, error
        case bytesDone = "bytes_done"
        case bytesTotal = "bytes_total"
    }

    public var isRunning: Bool { state == "queued" || state == "downloading" }
}

public struct ModelList: Codable, Equatable, Sendable {
    public let data: [ModelInfo]
    public let systemMemoryGB: Double?
    public let recommended: String?
    public let active: String?

    enum CodingKeys: String, CodingKey {
        case data, recommended, active
        case systemMemoryGB = "system_memory_gb"
    }

    public var activeModel: ModelInfo? { data.first { $0.active } }
}

public enum ModelsClientError: Error, Equatable, Sendable {
    case server(status: Int, code: String?, message: String)
    case transport(String)

    public var userMessage: String {
        switch self {
        case .transport: return "Сервер распознавания не отвечает"
        case .server(_, let code, let message):
            switch code {
            case "model_not_installed": return "Модель ещё не скачана"
            case "model_downloading": return "Модель ещё скачивается"
            case "model_active": return "Это текущая модель"
            case "model_not_found": return "Модель не найдена на Hugging Face"
            case "unsupported_model": return "Нужна MLX-модель Whisper или Qwen3-ASR"
            case "model_load_failed": return "Модель не загрузилась; осталась прежняя"
            case "busy": return "Сервер занят, попробуйте через минуту"
            case "invalid_request": return "Нужен адрес вида org/name"
            default: return message.isEmpty ? "Ошибка сервера" : String(message.prefix(160))
            }
        }
    }
}

/// Client for the model picker endpoints of the local STT server.
public struct ModelsClient: Sendable {
    public let config: AppConfig
    private let session: URLSession

    public init(config: AppConfig, session: URLSession? = nil) {
        self.config = config
        if let session {
            self.session = session
        } else {
            let sessionConfig = URLSessionConfiguration.ephemeral
            // Activation loads a model; give it the same budget as a transcription.
            sessionConfig.timeoutIntervalForRequest = config.timeoutSeconds
            self.session = URLSession(configuration: sessionConfig)
        }
    }

    public func list() async throws -> ModelList {
        try await send("GET", "v1/models", as: ModelList.self)
    }

    public func startDownload(_ id: String) async throws -> DownloadStatus {
        try await send("POST", "v1/models/\(id)/download", as: DownloadStatus.self)
    }

    public func downloadStatus(_ id: String) async throws -> DownloadStatus {
        try await send("GET", "v1/models/\(id)/download", as: DownloadStatus.self)
    }

    public func activate(_ id: String) async throws {
        _ = try await send("POST", "v1/models/\(id)/activate", as: [String: AnyCodableValue].self)
    }

    public func addCustom(repo: String) async throws -> ModelInfo {
        let body = try JSONSerialization.data(withJSONObject: ["repo": repo])
        return try await send("POST", "v1/models/custom", body: body, as: ModelInfo.self)
    }

    private func send<T: Decodable>(
        _ method: String, _ path: String, body: Data? = nil, as type: T.Type
    ) async throws -> T {
        let url = path.split(separator: "/").reduce(config.baseURL) { $0.appendingPathComponent(String($1)) }
        var request = URLRequest(url: url)
        request.httpMethod = method
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw ModelsClientError.transport(error.localizedDescription)
        }
        guard let http = response as? HTTPURLResponse else {
            throw ModelsClientError.transport("no HTTP response")
        }
        guard (200..<300).contains(http.statusCode) else {
            let (code, message) = RetryPolicy.parseError(data)
            throw ModelsClientError.server(status: http.statusCode, code: code, message: message)
        }
        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw ModelsClientError.transport("unexpected response: \(error.localizedDescription)")
        }
    }
}

/// Loose JSON value, for responses whose fields the client doesn't need.
public enum AnyCodableValue: Codable, Equatable, Sendable {
    case string(String), number(Double), bool(Bool), null

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() { self = .null }
        else if let value = try? container.decode(Bool.self) { self = .bool(value) }
        else if let value = try? container.decode(Double.self) { self = .number(value) }
        else if let value = try? container.decode(String.self) { self = .string(value) }
        else { self = .null }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value): try container.encode(value)
        case .number(let value): try container.encode(value)
        case .bool(let value): try container.encode(value)
        case .null: try container.encodeNil()
        }
    }
}

/// Menu text for the «Модель ▸» submenu.
public enum ModelMenu {
    public static func size(_ gigabytes: Double?) -> String {
        guard let gigabytes else { return "" }
        let text = gigabytes >= 1 ? String(format: "%.1f", gigabytes) : String(format: "%.2f", gigabytes)
        return text.replacingOccurrences(of: ".", with: ",") + " ГБ"
    }

    public static func title(_ model: ModelInfo) -> String {
        var parts = [(model.active ? "✓ " : "") + model.title]
        if model.recommended { parts[0] += " ★" }
        if let download = model.download, download.isRunning {
            let percent = download.progress.map { " \(Int(($0 * 100).rounded()))%" } ?? "…"
            parts.append("скачивается\(percent)")
        } else if !model.installed {
            parts.append("скачать \(size(model.downloadGB))")
        } else if let ram = model.ramGB {
            parts.append("~\(size(ram)) памяти")
        }
        if !model.fitsMemory, let need = model.minMemoryGB {
            parts.append("нужно ≥\(Int(need)) ГБ")
        }
        return parts.joined(separator: " — ")
    }

    /// Short name for the status line ("Готов · Qwen3-ASR 1.7B · 8-bit").
    public static func shortTitle(_ model: ModelInfo?) -> String {
        model?.title ?? "модель не выбрана"
    }
}
