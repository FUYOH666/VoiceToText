import Darwin
import Foundation

/// Engine the STT process loads. The menubar stays a client.
public enum STTEngineChoice: String, Equatable, Sendable {
    case whisper = "mlx_whisper"
    case qwen = "qwen3_asr"

    public var title: String {
        switch self {
        case .whisper: return "Whisper"
        case .qwen: return "Qwen"
        }
    }
}

public struct ProcessResult: Equatable, Sendable {
    public var status: Int32
    public var stderr: String

    public init(status: Int32, stderr: String) {
        self.status = status
        self.stderr = stderr
    }
}

public enum EngineSwitchError: Error, Equatable {
    case configNotFound
    case missingSTTServer
    case qwenExtraMissing
    case restartFailed

    public var message: String {
        switch self {
        case .configNotFound:
            return "Не найден config.yaml."
        case .missingSTTServer:
            return "В config.yaml нет блока stt_server."
        case .qwenExtraMissing:
            return "Qwen не установлен. В каталоге проекта выполните:\nuv sync --extra qwen"
        case .restartFailed:
            return "STT не перезапустился. Конфиг возвращён на прежний движок."
        }
    }
}

/// Read and edit `stt_server.engine` without rewriting the rest of the file.
public enum EngineConfig {
    public static func read(from yaml: String) -> STTEngineChoice? {
        let lines = splitLines(yaml).lines
        guard let range = blockRange(key: "stt_server", in: lines),
              let raw = engineToken(in: lines, range: range)
        else { return nil }
        return STTEngineChoice(rawValue: raw)
    }

    public static func write(_ engine: STTEngineChoice, into yaml: String) throws -> String {
        var parts = splitLines(yaml)
        guard let range = blockRange(key: "stt_server", in: parts.lines) else {
            throw EngineSwitchError.missingSTTServer
        }
        guard let index = engineLineIndex(in: parts.lines, range: range) else {
            throw EngineSwitchError.missingSTTServer
        }
        parts.lines[index] = replacingEngine(parts.lines[index], with: engine)
        if engine == .qwen {
            parts.lines = insertingQwenBlock(into: parts.lines)
        }
        return joinLines(parts)
    }

    private static func replacingEngine(_ line: String, with engine: STTEngineChoice) -> String {
        let indent = line.prefix { $0 == " " || $0 == "\t" }
        let trimmed = line.trimmingCharacters(in: .whitespaces)
        let comment: String
        if let hash = trimmed.firstIndex(of: "#") {
            comment = "  " + trimmed[hash...]
        } else {
            comment = ""
        }
        return "\(indent)engine: \(engine.rawValue)\(comment)"
    }

    private static func insertingQwenBlock(into lines: [String]) -> [String] {
        guard let range = blockRange(key: "transcription", in: lines) else {
            return lines
        }
        let parent = lines[range.lowerBound - 1]
        let parentIndent = parent.prefix { $0 == " " }.count
        if qwenBlockExists(in: lines, range: range, parentIndent: parentIndent) {
            return lines
        }
        let childIndent = firstChildIndent(in: lines, range: range, parentIndent: parentIndent)
        let pad = String(repeating: " ", count: childIndent)
        let nested = String(repeating: " ", count: childIndent + 2)
        let block = [
            "\(pad)qwen3_asr:",
            "\(nested)model_name: \"moona3k/mlx-qwen3-asr-1.7b-8bit\"",
            "\(nested)quantization_bits: null",
            "\(nested)group_size: 64",
            "\(nested)language: \"ru\"",
        ]
        var updated = lines
        let at = qwenInsertIndex(in: lines, range: range, childIndent: childIndent)
        updated.insert(contentsOf: block, at: at)
        return updated
    }

    private static func qwenBlockExists(in lines: [String], range: Range<Int>, parentIndent: Int) -> Bool {
        for index in range {
            let line = lines[index]
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.isEmpty || trimmed.hasPrefix("#") { continue }
            let indent = line.prefix { $0 == " " }.count
            if indent > parentIndent && trimmed.hasPrefix("qwen3_asr:") {
                return true
            }
        }
        return false
    }

    private static func qwenInsertIndex(in lines: [String], range: Range<Int>, childIndent: Int) -> Int {
        for index in range {
            let line = lines[index]
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            let indent = line.prefix { $0 == " " }.count
            if indent == childIndent && trimmed.hasPrefix("mlx_whisper:") {
                return index
            }
        }
        return range.upperBound
    }

    private static func firstChildIndent(in lines: [String], range: Range<Int>, parentIndent: Int) -> Int {
        for index in range {
            let line = lines[index]
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.isEmpty || trimmed.hasPrefix("#") { continue }
            let indent = line.prefix { $0 == " " }.count
            if indent > parentIndent { return indent }
        }
        return parentIndent + 2
    }

    private static func engineToken(in lines: [String], range: Range<Int>) -> String? {
        guard let index = engineLineIndex(in: lines, range: range) else { return nil }
        let trimmed = lines[index].trimmingCharacters(in: .whitespaces)
        let value = trimmed.dropFirst("engine:".count).trimmingCharacters(in: .whitespaces)
        let token = value.split(separator: "#", maxSplits: 1).first.map(String.init) ?? String(value)
        return token.trimmingCharacters(in: .whitespaces).trimmingCharacters(in: CharacterSet(charactersIn: "\"'"))
    }

    private static func engineLineIndex(in lines: [String], range: Range<Int>) -> Int? {
        for index in range {
            let trimmed = lines[index].trimmingCharacters(in: .whitespaces)
            if trimmed.hasPrefix("#") { continue }
            if trimmed.hasPrefix("engine:") { return index }
        }
        return nil
    }

    private static func blockRange(key: String, in lines: [String]) -> Range<Int>? {
        guard let start = lines.firstIndex(where: { line in
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            return !line.hasPrefix(" ") && !line.hasPrefix("\t") && !trimmed.hasPrefix("#")
                && trimmed.hasPrefix("\(key):")
        }) else { return nil }
        var end = start + 1
        while end < lines.count {
            let line = lines[end]
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.isEmpty || trimmed.hasPrefix("#") {
                end += 1
                continue
            }
            if !line.hasPrefix(" ") && !line.hasPrefix("\t") { break }
            end += 1
        }
        return (start + 1)..<end
    }

    private struct Parts {
        var lines: [String]
        var trailingNewline: Bool
    }

    private static func splitLines(_ yaml: String) -> Parts {
        var lines = yaml.components(separatedBy: "\n")
        let trailing = lines.last == ""
        if trailing { lines.removeLast() }
        return Parts(lines: lines, trailingNewline: trailing)
    }

    private static func joinLines(_ parts: Parts) -> String {
        var text = parts.lines.joined(separator: "\n")
        if parts.trailingNewline { text += "\n" }
        return text
    }
}

public struct EngineController: Sendable {
    public var configURL: URL
    public var uvExecutable: String
    public var run: @Sendable (String, [String], URL) -> ProcessResult

    public init(
        configURL: URL,
        uvExecutable: String,
        run: @escaping @Sendable (String, [String], URL) -> ProcessResult
    ) {
        self.configURL = configURL
        self.uvExecutable = uvExecutable
        self.run = run
    }

    /// Switch the on-disk engine and restart `ai.vtt2.stt`. Same engine is a no-op.
    public func select(_ target: STTEngineChoice) throws {
        let original = try String(contentsOf: configURL, encoding: .utf8)
        if EngineConfig.read(from: original) == target { return }
        if target == .qwen {
            let probe = run(
                uvExecutable,
                ["run", "python", "-c", "import mlx_qwen3_asr"],
                configURL.deletingLastPathComponent()
            )
            if probe.status != 0 {
                throw EngineSwitchError.qwenExtraMissing
            }
        }
        let updated = try EngineConfig.write(target, into: original)
        try updated.write(to: configURL, atomically: true, encoding: .utf8)
        let kick = run(
            "/bin/launchctl",
            ["kickstart", "-k", "gui/\(getuid())/ai.vtt2.stt"],
            configURL.deletingLastPathComponent()
        )
        if kick.status != 0 {
            try original.write(to: configURL, atomically: true, encoding: .utf8)
            throw EngineSwitchError.restartFailed
        }
    }
}

public enum EngineProcesses {
    public static func uvExecutable() -> String {
        if let fromAgent = uvFromSTTAgent(), FileManager.default.isExecutableFile(atPath: fromAgent) {
            return fromAgent
        }
        let local = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".local/bin/uv").path
        if FileManager.default.isExecutableFile(atPath: local) { return local }
        let brew = "/opt/homebrew/bin/uv"
        if FileManager.default.isExecutableFile(atPath: brew) { return brew }
        return local
    }

    public static func run(executable: String, arguments: [String], cwd: URL) -> ProcessResult {
        runLimited(executable: executable, arguments: arguments, cwd: cwd, timeoutSeconds: 45)
    }

    private static func runLimited(
        executable: String,
        arguments: [String],
        cwd: URL,
        timeoutSeconds: TimeInterval
    ) -> ProcessResult {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: executable)
        process.arguments = arguments
        process.currentDirectoryURL = cwd
        let errPipe = Pipe()
        let outPipe = Pipe()
        process.standardError = errPipe
        process.standardOutput = outPipe
        do {
            try process.run()
        } catch {
            return ProcessResult(status: 127, stderr: error.localizedDescription)
        }
        let deadline = Date().addingTimeInterval(timeoutSeconds)
        while process.isRunning && Date() < deadline {
            Thread.sleep(forTimeInterval: 0.05)
        }
        if process.isRunning {
            process.terminate()
            return ProcessResult(status: 124, stderr: "timeout")
        }
        let data = errPipe.fileHandleForReading.readDataToEndOfFile()
        let text = String(data: data, encoding: .utf8) ?? ""
        return ProcessResult(status: process.terminationStatus, stderr: text)
    }

    private static func uvFromSTTAgent() -> String? {
        let plist = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/LaunchAgents/ai.vtt2.stt.plist")
        guard let data = try? Data(contentsOf: plist),
              let obj = try? PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any],
              let args = obj["ProgramArguments"] as? [String],
              let first = args.first,
              first == "uv" || first.hasSuffix("/uv")
        else { return nil }
        return first
    }
}
