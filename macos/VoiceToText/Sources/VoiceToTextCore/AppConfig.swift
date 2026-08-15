import Foundation

/// Loopback STT settings. Reads `transcription.local_stt` from config.yaml when found.
public struct AppConfig: Sendable, Equatable {
    public var baseURL: URL
    public var path: String
    public var timeoutSeconds: TimeInterval
    public var warmupWaitSeconds: TimeInterval

    public static let loopbackDefault = AppConfig(
        baseURL: URL(string: "http://127.0.0.1:8765")!,
        path: "/v1/audio/transcriptions",
        timeoutSeconds: 600,
        warmupWaitSeconds: 180
    )

    public init(
        baseURL: URL,
        path: String,
        timeoutSeconds: TimeInterval,
        warmupWaitSeconds: TimeInterval
    ) {
        self.baseURL = baseURL
        self.path = path
        self.timeoutSeconds = timeoutSeconds
        self.warmupWaitSeconds = warmupWaitSeconds
    }

    /// Parse a YAML document; unknown/missing keys keep loopback defaults.
    public static func parseYAML(_ text: String) -> AppConfig {
        var config = loopbackDefault
        let block = extractLocalSTTBlock(from: text) ?? text
        if let raw = scalar(named: "base_url", in: block),
           let url = URL(string: raw.trimmingCharacters(in: CharacterSet(charactersIn: "\"'")))
        {
            config.baseURL = url
        }
        if let raw = scalar(named: "path", in: block) {
            config.path = raw.trimmingCharacters(in: CharacterSet(charactersIn: "\"'"))
        }
        if let raw = scalar(named: "timeout_seconds", in: block), let value = TimeInterval(raw) {
            config.timeoutSeconds = value
        }
        if let raw = scalar(named: "warmup_wait_seconds", in: block), let value = TimeInterval(raw) {
            config.warmupWaitSeconds = value
        }
        return config
    }

    /// Search env `VTT2_CONFIG`, then walk up from `start` / cwd for `config.yaml`.
    public static func load(searchingFrom start: URL? = nil) -> AppConfig {
        if let env = ProcessInfo.processInfo.environment["VTT2_CONFIG"], !env.isEmpty {
            let url = URL(fileURLWithPath: env)
            if let text = try? String(contentsOf: url, encoding: .utf8) {
                AppLog.info("config from VTT2_CONFIG")
                return parseYAML(text)
            }
        }

        var directories: [URL] = []
        if let start {
            directories.append(start)
        }
        directories.append(URL(fileURLWithPath: FileManager.default.currentDirectoryPath))
        if let bundle = Bundle.main.bundleURL as URL? {
            directories.append(bundle.deletingLastPathComponent())
            directories.append(bundle.deletingLastPathComponent().deletingLastPathComponent())
        }

        for root in directories {
            var dir = root
            for _ in 0..<6 {
                let candidate = dir.appendingPathComponent("config.yaml")
                if FileManager.default.isReadableFile(atPath: candidate.path),
                   let text = try? String(contentsOf: candidate, encoding: .utf8)
                {
                    AppLog.info("config from \(candidate.path)")
                    return parseYAML(text)
                }
                let parent = dir.deletingLastPathComponent()
                if parent.path == dir.path { break }
                dir = parent
            }
        }

        AppLog.info("config.yaml not found; using loopback default")
        return loopbackDefault
    }

    private static func extractLocalSTTBlock(from text: String) -> String? {
        let lines = text.split(separator: "\n", omittingEmptySubsequences: false).map(String.init)
        guard let start = lines.firstIndex(where: { $0.trimmingCharacters(in: .whitespaces).hasPrefix("local_stt:") })
        else { return nil }
        var block: [String] = []
        let startIndent = lines[start].prefix { $0 == " " }.count
        for line in lines.dropFirst(start + 1) {
            if line.trimmingCharacters(in: .whitespaces).isEmpty {
                block.append(line)
                continue
            }
            let indent = line.prefix { $0 == " " }.count
            if indent <= startIndent { break }
            block.append(line)
        }
        return block.joined(separator: "\n")
    }

    private static func scalar(named key: String, in text: String) -> String? {
        for line in text.split(separator: "\n") {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            guard trimmed.hasPrefix("\(key):") else { continue }
            let value = trimmed.dropFirst(key.count + 1).trimmingCharacters(in: .whitespaces)
            if !value.isEmpty { return value }
        }
        return nil
    }
}
