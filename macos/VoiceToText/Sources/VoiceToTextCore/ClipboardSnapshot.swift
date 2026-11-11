import AppKit
import Foundation

/// Copy of everything on a pasteboard, so dictation can borrow the clipboard
/// for Cmd+V and then give the user's own clipboard back.
public struct ClipboardSnapshot {
    private let items: [[(NSPasteboard.PasteboardType, Data)]]

    /// nspasteboard.org markers: clipboard managers skip our temporary item and
    /// don't keep dictated text in their history.
    public static let transientType = NSPasteboard.PasteboardType("org.nspasteboard.TransientType")
    public static let concealedType = NSPasteboard.PasteboardType("org.nspasteboard.ConcealedType")

    public static func capture(_ pasteboard: NSPasteboard) -> ClipboardSnapshot {
        let items = (pasteboard.pasteboardItems ?? []).map { item in
            item.types.compactMap { type in item.data(forType: type).map { (type, $0) } }
        }
        return ClipboardSnapshot(items: items)
    }

    public var isEmpty: Bool { items.isEmpty }

    /// Put the dictated text on the pasteboard, marked transient. Returns the
    /// change count right after the write.
    @discardableResult
    public static func writeTransient(_ text: String, to pasteboard: NSPasteboard) -> Int? {
        pasteboard.clearContents()
        let item = NSPasteboardItem()
        guard item.setString(text, forType: .string) else { return nil }
        item.setData(Data(), forType: transientType)
        item.setData(Data(), forType: concealedType)
        guard pasteboard.writeObjects([item]) else { return nil }
        return pasteboard.changeCount
    }

    /// Restore only if nobody wrote to the pasteboard since our own write.
    public static func shouldRestore(changeCountAfterWrite: Int, currentChangeCount: Int) -> Bool {
        changeCountAfterWrite == currentChangeCount
    }

    public func restore(to pasteboard: NSPasteboard) {
        pasteboard.clearContents()
        guard !items.isEmpty else { return }
        let restored = items.map { pairs -> NSPasteboardItem in
            let item = NSPasteboardItem()
            for (type, data) in pairs {
                item.setData(data, forType: type)
            }
            return item
        }
        pasteboard.writeObjects(restored)
    }
}
