import Foundation

// Hand-rolled checks: test.sh compiles the core sources and every file in Tests/
// into one binary with plain swiftc, so there is no XCTest or `swift test` here.

var failed = 0
var checks = 0

func expect(_ cond: Bool, _ message: String) {
    checks += 1
    if !cond {
        fputs("FAIL: \(message)\n", stderr)
        failed += 1
    }
}

/// Fresh per run and removed at exit. Tests write config files and logs here,
/// never the repo config.yaml or ~/Library/Logs/vtt2.
let testDirectory: URL = {
    let dir = FileManager.default.temporaryDirectory
        .appendingPathComponent("vtt-core-tests-\(UUID().uuidString)", isDirectory: true)
    try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    return dir
}()

func writeTempConfig(_ name: String, _ text: String) -> URL {
    let dir = testDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
    try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    let file = dir.appendingPathComponent(name)
    do {
        try text.write(to: file, atomically: true, encoding: .utf8)
    } catch {
        expect(false, "write temp config \(name): \(error)")
    }
    return file
}

func readText(_ url: URL) -> String {
    (try? String(contentsOf: url, encoding: .utf8)) ?? ""
}

final class CallLog: @unchecked Sendable {
    private let lock = NSLock()
    private var items: [String] = []
    func add(_ item: String) { lock.withLock { items.append(item) } }
    func reset() { lock.withLock { items.removeAll() } }
    var values: [String] { lock.withLock { items } }
}

final class LockBox: @unchecked Sendable {
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
