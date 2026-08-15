import Foundation

/// File logger under ~/Library/Logs/vtt2/voicetotext.log (no print in product paths).
public enum AppLog {
    private static let lock = NSLock()
    private static var fileHandle: FileHandle?

    public static var logDirectory: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/vtt2", isDirectory: true)
    }

    public static var logFile: URL {
        logDirectory.appendingPathComponent("voicetotext.log", isDirectory: false)
    }

    public static func info(_ message: String) {
        write(level: "INFO", message)
    }

    public static func warning(_ message: String) {
        write(level: "WARNING", message)
    }

    public static func error(_ message: String) {
        write(level: "ERROR", message)
    }

    public static func debug(_ message: String) {
        write(level: "DEBUG", message)
    }

    private static func write(level: String, _ message: String) {
        let stamp = ISO8601DateFormatter().string(from: Date())
        let line = "\(stamp) \(level) voicetotext \(message)\n"
        lock.lock()
        defer { lock.unlock() }
        do {
            try FileManager.default.createDirectory(
                at: logDirectory,
                withIntermediateDirectories: true
            )
            if fileHandle == nil {
                if !FileManager.default.fileExists(atPath: logFile.path) {
                    FileManager.default.createFile(atPath: logFile.path, contents: nil)
                }
                fileHandle = try FileHandle(forWritingTo: logFile)
                try fileHandle?.seekToEnd()
            }
            if let data = line.data(using: .utf8) {
                try fileHandle?.write(contentsOf: data)
            }
        } catch {
            // Last resort: stderr only if the log file cannot be opened.
            fputs(line, stderr)
        }
    }
}
