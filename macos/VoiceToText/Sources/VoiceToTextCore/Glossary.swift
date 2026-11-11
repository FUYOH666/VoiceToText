import Foundation

/// The user's glossary: names and terms the model should spell right
/// ("Claude Code, MLX, Hugging Face, Qwen"). Sent with every dictation as the
/// `prompt` field (Whisper initial prompt / Qwen context).
///
/// File: `~/Library/Application Support/VoiceToText/glossary.txt`, one term or
/// short phrase per line, `#` starts a comment. Empty file = no prompt.
public enum Glossary {
    /// The server rejects prompts over 1000 characters; leave room.
    public static let maxCharacters = 800

    public static func fileURL(in directory: URL = DictationStore.defaultDirectory) -> URL {
        directory.appendingPathComponent("glossary.txt", isDirectory: false)
    }

    public static let template = """
    # Словарь терминов VoiceToText.
    # По одному слову или короткой фразе в строке. Модель будет писать их именно так.
    # Строки с # не учитываются. Пустой файл — словарь выключен.
    #
    # Например:
    # Claude Code
    # Hugging Face
    # MLX
    # GitHub
    """

    /// Prompt text built from the file, or nil when there is nothing to send.
    public static func prompt(from text: String) -> String? {
        var terms: [String] = []
        var seen = Set<String>()
        for raw in text.split(whereSeparator: \.isNewline) {
            let line = raw.trimmingCharacters(in: .whitespaces)
            guard !line.isEmpty, !line.hasPrefix("#") else { continue }
            let key = line.lowercased()
            guard !seen.contains(key) else { continue }
            seen.insert(key)
            terms.append(line)
        }
        guard !terms.isEmpty else { return nil }
        var result = ""
        for term in terms {
            let next = result.isEmpty ? term : "\(result), \(term)"
            if next.count > maxCharacters { break }
            result = next
        }
        return result.isEmpty ? nil : result + "."
    }

    public static func load(directory: URL = DictationStore.defaultDirectory) -> String? {
        guard let text = try? String(contentsOf: fileURL(in: directory), encoding: .utf8) else { return nil }
        return prompt(from: text)
    }

    /// Create the file with the commented template if it doesn't exist; return its URL.
    @discardableResult
    public static func ensureFile(directory: URL = DictationStore.defaultDirectory) throws -> URL {
        let url = fileURL(in: directory)
        if !FileManager.default.fileExists(atPath: url.path) {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            try (template + "\n").write(to: url, atomically: true, encoding: .utf8)
        }
        return url
    }
}
