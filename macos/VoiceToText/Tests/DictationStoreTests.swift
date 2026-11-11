import AppKit
import Foundation

final class FakeClock: @unchecked Sendable {
    private let lock = NSLock()
    private var current = Date(timeIntervalSince1970: 1_800_000_000)
    var now: Date { lock.withLock { current } }
    func advance(_ seconds: TimeInterval) { lock.withLock { current += seconds } }
}

func runDictationStoreTests() {
    let dir = testDirectory.appendingPathComponent("store-\(UUID().uuidString)", isDirectory: true)
    let clock = FakeClock()
    let store = DictationStore(directory: dir, now: { clock.now })

    // Audio is on disk before upload, and survives a failure.
    let wav = WAVEncoder.pcm16kMono(floats: [0, 0.1, -0.1])
    guard let entry = try? store.begin(wav: wav, durationSeconds: 1.5) else {
        expect(false, "begin should save")
        return
    }
    expect(entry.status == .pending, "new entry is pending")
    expect(store.audio(for: entry) == wav, "audio saved before upload")
    store.fail(entry.id, error: "Сервер не ответил")
    let failed = store.entries().last
    expect(failed?.status == .failed && failed?.error == "Сервер не ответил", "failure recorded")
    expect(store.latestRetryable()?.id == entry.id, "failed entry is retryable")

    store.finish(entry.id, text: "привет")
    expect(store.entries().last?.status == .done && store.entries().last?.text == "привет", "finish after retry")

    store.fail(entry.id, error: "Отменено", cancelled: true)
    expect(store.entries().last?.status == .cancelled, "cancel recorded")

    // A fresh store over the same folder reads the same history.
    let reopened = DictationStore(directory: dir, now: { clock.now })
    expect(reopened.entries().map(\.id) == [entry.id], "history persists across launches")

    // Count limit: oldest entries and their audio are deleted.
    var ids: [String] = [entry.id]
    for index in 0..<DictationStore.maxEntries {
        clock.advance(1)
        if let next = try? store.begin(wav: wav, durationSeconds: Double(index)) { ids.append(next.id) }
    }
    let afterCount = store.entries()
    expect(afterCount.count == DictationStore.maxEntries, "keeps \(DictationStore.maxEntries), got \(afterCount.count)")
    expect(!afterCount.contains { $0.id == entry.id }, "oldest entry dropped")
    expect(store.audio(for: entry) == nil, "oldest audio deleted")

    // Age limit.
    clock.advance(DictationStore.maxAge + 10)
    _ = try? store.begin(wav: wav, durationSeconds: 1)
    expect(store.entries().count == 1, "entries older than 7 days dropped, got \(store.entries().count)")
    let leftover = (try? FileManager.default.contentsOfDirectory(atPath: dir.appendingPathComponent("recordings").path)) ?? []
    expect(leftover.count == 1, "old audio files deleted, \(leftover.count) left")
}

func runClipboardTests() {
    let pasteboard = NSPasteboard(name: NSPasteboard.Name("vtt-test-\(UUID().uuidString)"))
    defer { pasteboard.releaseGlobally() }

    pasteboard.clearContents()
    pasteboard.setString("мой буфер", forType: .string)
    let snapshot = ClipboardSnapshot.capture(pasteboard)
    expect(!snapshot.isEmpty, "snapshot captured")

    let change = ClipboardSnapshot.writeTransient("диктовка", to: pasteboard)
    expect(change != nil, "transient write")
    expect(pasteboard.string(forType: .string) == "диктовка", "dictation on clipboard")
    expect(pasteboard.types?.contains(ClipboardSnapshot.transientType) == true, "marked transient")
    expect(pasteboard.types?.contains(ClipboardSnapshot.concealedType) == true, "marked concealed")

    if let change {
        expect(ClipboardSnapshot.shouldRestore(changeCountAfterWrite: change, currentChangeCount: pasteboard.changeCount),
               "restore when untouched")
        expect(!ClipboardSnapshot.shouldRestore(changeCountAfterWrite: change, currentChangeCount: change + 1),
               "no restore after user copied something")
    }
    snapshot.restore(to: pasteboard)
    expect(pasteboard.string(forType: .string) == "мой буфер", "user clipboard restored")
}
