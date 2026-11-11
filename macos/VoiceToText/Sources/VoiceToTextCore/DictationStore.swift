import Foundation

/// One dictation: the saved audio and what became of it.
public struct DictationEntry: Codable, Equatable, Sendable {
    public enum Status: String, Codable, Sendable {
        case pending, done, failed, cancelled
    }

    public let id: String
    public let createdAt: Date
    public var audioFile: String?
    public var durationSeconds: Double
    public var status: Status
    public var text: String?
    public var error: String?

    public var canRetry: Bool { audioFile != nil }
}

/// Keeps every dictation on disk *before* it is sent, so a server crash, a
/// timeout or a cancel never loses what was said.
///
/// Layout under `~/Library/Application Support/VoiceToText/`:
/// `recordings/<id>.wav` and `history.jsonl` (one entry per line, oldest first).
/// Only the last `maxEntries` within `maxAge` are kept; older audio is deleted.
public final class DictationStore: @unchecked Sendable {
    public static let maxEntries = 50
    public static let maxAge: TimeInterval = 7 * 24 * 3600

    public static var defaultDirectory: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/VoiceToText", isDirectory: true)
    }

    public let directory: URL
    private let lock = NSLock()
    private let now: @Sendable () -> Date

    public init(
        directory: URL = DictationStore.defaultDirectory,
        now: @escaping @Sendable () -> Date = { Date() }
    ) {
        self.directory = directory
        self.now = now
    }

    var recordingsDirectory: URL { directory.appendingPathComponent("recordings", isDirectory: true) }
    var historyFile: URL { directory.appendingPathComponent("history.jsonl", isDirectory: false) }

    /// Save the WAV and a `pending` entry. Call before uploading.
    public func begin(wav: Data, durationSeconds: Double) throws -> DictationEntry {
        try lock.withLock {
            try FileManager.default.createDirectory(at: recordingsDirectory, withIntermediateDirectories: true)
            let created = now()
            let id = Self.makeID(created)
            let file = "\(id).wav"
            try wav.write(to: recordingsDirectory.appendingPathComponent(file), options: .atomic)
            let entry = DictationEntry(
                id: id, createdAt: created, audioFile: file,
                durationSeconds: durationSeconds, status: .pending, text: nil, error: nil
            )
            var all = loadUnlocked()
            all.append(entry)
            try saveUnlocked(prunedUnlocked(all))
            return entry
        }
    }

    public func finish(_ id: String, text: String) {
        update(id) { entry in
            entry.status = .done
            entry.text = text
            entry.error = nil
        }
    }

    public func fail(_ id: String, error: String, cancelled: Bool = false) {
        update(id) { entry in
            entry.status = cancelled ? .cancelled : .failed
            entry.error = error
        }
    }

    /// Oldest first.
    public func entries() -> [DictationEntry] {
        lock.withLock { loadUnlocked() }
    }

    /// The entry "Повторить последнюю" should use: the newest one that still has audio.
    public func latestRetryable() -> DictationEntry? {
        entries().last { $0.canRetry }
    }

    public func audio(for entry: DictationEntry) -> Data? {
        guard let file = entry.audioFile else { return nil }
        return try? Data(contentsOf: recordingsDirectory.appendingPathComponent(file))
    }

    // MARK: - Internals (call with lock held)

    private func update(_ id: String, _ change: (inout DictationEntry) -> Void) {
        lock.withLock {
            var all = loadUnlocked()
            guard let index = all.firstIndex(where: { $0.id == id }) else { return }
            change(&all[index])
            do {
                try saveUnlocked(all)
            } catch {
                AppLog.error("history save failed: \(error.localizedDescription)")
            }
        }
    }

    private func loadUnlocked() -> [DictationEntry] {
        guard let text = try? String(contentsOf: historyFile, encoding: .utf8) else { return [] }
        let decoder = Self.decoder
        return text.split(separator: "\n").compactMap { line in
            try? decoder.decode(DictationEntry.self, from: Data(line.utf8))
        }
    }

    private func saveUnlocked(_ entries: [DictationEntry]) throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let encoder = Self.encoder
        let lines = try entries.map { String(decoding: try encoder.encode($0), as: UTF8.self) }
        let body = lines.joined(separator: "\n") + (lines.isEmpty ? "" : "\n")
        try body.write(to: historyFile, atomically: true, encoding: .utf8)
    }

    /// Drop entries beyond the count/age limits and delete their audio.
    private func prunedUnlocked(_ entries: [DictationEntry]) -> [DictationEntry] {
        let cutoff = now().addingTimeInterval(-Self.maxAge)
        var kept = entries.filter { $0.createdAt >= cutoff }
        if kept.count > Self.maxEntries {
            kept.removeFirst(kept.count - Self.maxEntries)
        }
        let keptIDs = Set(kept.map(\.id))
        for entry in entries where !keptIDs.contains(entry.id) {
            if let file = entry.audioFile {
                try? FileManager.default.removeItem(at: recordingsDirectory.appendingPathComponent(file))
            }
        }
        return kept
    }

    private static func makeID(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        return "\(formatter.string(from: date))-\(UUID().uuidString.prefix(8).lowercased())"
    }

    private static var encoder: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return encoder
    }

    private static var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}
