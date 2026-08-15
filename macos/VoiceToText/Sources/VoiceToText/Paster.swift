#if canImport(VoiceToTextCore)
import VoiceToTextCore
#endif
import AppKit
import CoreGraphics
import Foundation

/// Save frontmost app → clipboard → Cmd+V. Failures are logged, not alerted.
enum Paster {
    private static var savedBundleID: String?

    static func saveFrontmost() {
        savedBundleID = NSWorkspace.shared.frontmostApplication?.bundleIdentifier
        if let savedBundleID {
            AppLog.info("saved frontmost app: \(savedBundleID)")
        } else {
            AppLog.warning("could not save frontmost app")
        }
    }

    @discardableResult
    static func paste(_ text: String) -> Bool {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            AppLog.warning("empty text; skip paste")
            return false
        }

        restoreFrontmost()
        Thread.sleep(forTimeInterval: 0.15)

        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        guard pasteboard.setString(trimmed, forType: .string) else {
            AppLog.error("NSPasteboard setString failed")
            return false
        }

        Thread.sleep(forTimeInterval: 0.1)
        let ok = postCommandV()
        if ok {
            AppLog.info("pasted \(trimmed.count) characters via Cmd+V")
        } else {
            AppLog.error("CGEvent Cmd+V failed; text left on clipboard")
        }
        return ok
    }

    private static func restoreFrontmost() {
        guard let savedBundleID else { return }
        let match = NSWorkspace.shared.runningApplications.first {
            $0.bundleIdentifier == savedBundleID
        }
        guard let match else {
            AppLog.warning("saved app \(savedBundleID) is not running; paste into current frontmost")
            return
        }
        match.activate()
    }

    private static func postCommandV() -> Bool {
        let source = CGEventSource(stateID: .hidSystemState)
        let keyV: CGKeyCode = 0x09
        guard
            let down = CGEvent(keyboardEventSource: source, virtualKey: keyV, keyDown: true),
            let up = CGEvent(keyboardEventSource: source, virtualKey: keyV, keyDown: false)
        else {
            return false
        }
        down.flags = .maskCommand
        up.flags = .maskCommand
        down.post(tap: .cghidEventTap)
        up.post(tap: .cghidEventTap)
        return true
    }
}
