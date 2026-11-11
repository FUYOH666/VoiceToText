#if canImport(VoiceToTextCore)
import VoiceToTextCore
#endif
import AppKit
import Carbon
import CoreGraphics
import Foundation

enum PasteResult: Equatable {
    case pasted
    /// A password field has secure input on; nothing was pasted or left on the clipboard.
    case secureInput
    /// No Accessibility grant: the text is left on the clipboard for a manual Cmd+V.
    case noAccessibility
    case failed
}

/// Save frontmost app → borrow the clipboard → Cmd+V → give the clipboard back.
@MainActor
enum Paster {
    private static var savedBundleID: String?
    /// How long the target app gets to read the clipboard before it is restored.
    private static let restoreDelay: UInt64 = 1_000_000_000

    /// Log only. Posting Cmd+V needs Accessibility; the Carbon hotkey needs no
    /// permission, and the app never listens to other apps' keystrokes.
    static func logPermissions() {
        let postEvents = CGPreflightPostEventAccess()
        AppLog.info("permissions Accessibility=\(postEvents)")
        if !postEvents {
            AppLog.warning(
                "VoiceToText is not trusted yet. Remove the old row in Privacy, add this .app, enable Accessibility."
            )
        }
    }

    /// Explicit menu action only — shows the system sheet once.
    static func promptPermissions() {
        if !CGPreflightPostEventAccess() {
            _ = CGRequestPostEventAccess()
        }
        logPermissions()
    }

    static func saveFrontmost() {
        savedBundleID = NSWorkspace.shared.frontmostApplication?.bundleIdentifier
        if let savedBundleID {
            AppLog.info("saved frontmost app: \(savedBundleID)")
        } else {
            AppLog.warning("could not save frontmost app")
        }
    }

    static func paste(_ text: String) async -> PasteResult {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return .failed }

        await restoreFrontmost()
        try? await Task.sleep(nanoseconds: 300_000_000)

        if IsSecureEventInputEnabled() {
            AppLog.warning("secure input is on (password field); not pasting")
            return .secureInput
        }

        let pasteboard = NSPasteboard.general
        guard CGPreflightPostEventAccess() else {
            pasteboard.clearContents()
            pasteboard.setString(trimmed, forType: .string)
            AppLog.error("no Accessibility; text left on clipboard for manual Cmd+V")
            return .noAccessibility
        }

        let front = NSWorkspace.shared.frontmostApplication?.bundleIdentifier ?? "unknown"
        AppLog.info("frontmost before Cmd+V: \(front)")

        let snapshot = ClipboardSnapshot.capture(pasteboard)
        guard let ourChange = ClipboardSnapshot.writeTransient(trimmed, to: pasteboard) else {
            AppLog.error("NSPasteboard write failed")
            return .failed
        }
        try? await Task.sleep(nanoseconds: 100_000_000)

        guard await postCommandV(tap: .cgAnnotatedSessionEventTap) else {
            AppLog.error("Cmd+V events could not be created; text left on clipboard")
            return .failed
        }
        AppLog.info("Cmd+V posted (\(trimmed.count) chars)")

        try? await Task.sleep(nanoseconds: restoreDelay)
        if ClipboardSnapshot.shouldRestore(
            changeCountAfterWrite: ourChange,
            currentChangeCount: pasteboard.changeCount
        ) {
            snapshot.restore(to: pasteboard)
            AppLog.info("clipboard restored")
        } else {
            AppLog.info("clipboard changed by someone else; not restoring")
        }
        return .pasted
    }

    private static func restoreFrontmost() async {
        guard let savedBundleID else { return }
        let match = NSWorkspace.shared.runningApplications.first {
            $0.bundleIdentifier == savedBundleID
        }
        guard let match else {
            AppLog.warning("saved app \(savedBundleID) is not running; paste into current frontmost")
            return
        }
        if #available(macOS 14.0, *) {
            match.activate()
        } else {
            match.activate(options: [.activateIgnoringOtherApps])
        }
        try? await Task.sleep(nanoseconds: 200_000_000)
    }

    private static func postCommandV(tap: CGEventTapLocation) async -> Bool {
        let source = CGEventSource(stateID: .hidSystemState)
        let cmd: CGKeyCode = 0x37
        let keyV: CGKeyCode = 0x09
        guard
            let cmdDown = CGEvent(keyboardEventSource: source, virtualKey: cmd, keyDown: true),
            let vDown = CGEvent(keyboardEventSource: source, virtualKey: keyV, keyDown: true),
            let vUp = CGEvent(keyboardEventSource: source, virtualKey: keyV, keyDown: false),
            let cmdUp = CGEvent(keyboardEventSource: source, virtualKey: cmd, keyDown: false)
        else {
            return false
        }
        cmdDown.flags = .maskCommand
        vDown.flags = .maskCommand
        vUp.flags = .maskCommand
        cmdUp.flags = []

        cmdDown.post(tap: tap)
        try? await Task.sleep(nanoseconds: 50_000_000)
        vDown.post(tap: tap)
        try? await Task.sleep(nanoseconds: 150_000_000)
        vUp.post(tap: tap)
        try? await Task.sleep(nanoseconds: 50_000_000)
        cmdUp.post(tap: tap)
        return true
    }
}
