#if canImport(VoiceToTextCore)
import VoiceToTextCore
#endif
import AppKit
import ApplicationServices
import CoreGraphics
import Foundation

/// Save frontmost app → clipboard → Cmd+V.
/// Same event order as the working Python injector (annotated/session tap + Cmd down/up).
enum Paster {
    private static var savedBundleID: String?

    /// Log only. Prompting on every paste fights a stale TCC row after ad-hoc rebuilds.
    static func logPermissions() {
        let accessibility = AXIsProcessTrusted()
        let monitoring = CGPreflightListenEventAccess()
        AppLog.info("permissions Accessibility=\(accessibility) InputMonitoring=\(monitoring)")
        if !accessibility || !monitoring {
            AppLog.warning(
                "VoiceToText is not trusted yet. Remove the old row in Privacy, add this .app, enable Accessibility and Input Monitoring."
            )
        }
    }

    /// Explicit menu action only — shows the system sheet once.
    static func promptPermissions() {
        let prompt = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(prompt)
        if !CGPreflightListenEventAccess() {
            _ = CGRequestListenEventAccess()
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

    @discardableResult
    static func paste(_ text: String) -> Bool {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            AppLog.warning("empty text; skip paste")
            return false
        }

        logPermissions()
        restoreFrontmost()
        Thread.sleep(forTimeInterval: 0.3)

        let front = NSWorkspace.shared.frontmostApplication?.bundleIdentifier ?? "unknown"
        AppLog.info("frontmost before Cmd+V: \(front)")

        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        guard pasteboard.setString(trimmed, forType: .string) else {
            AppLog.error("NSPasteboard setString failed")
            return false
        }
        Thread.sleep(forTimeInterval: 0.2)

        let tap = preferredTap()
        let posted = postCommandV(tap: tap)
        if posted {
            AppLog.info("Cmd+V posted via \(tapName(tap)) (\(trimmed.count) chars); text also on clipboard")
        } else {
            AppLog.error("Cmd+V post failed; text left on clipboard. Enable Accessibility + Input Monitoring for VoiceToText")
        }
        return posted
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
        if #available(macOS 14.0, *) {
            match.activate()
        } else {
            match.activate(options: [.activateIgnoringOtherApps])
        }
        Thread.sleep(forTimeInterval: 0.2)
    }

    private static func preferredTap() -> CGEventTapLocation {
        // Python: AnnotatedSession first (Sequoia+), then session. hidEventTap is often dropped.
        if AXIsProcessTrusted() || CGPreflightListenEventAccess() {
            return .cgAnnotatedSessionEventTap
        }
        return .cgSessionEventTap
    }

    private static func tapName(_ tap: CGEventTapLocation) -> String {
        switch tap {
        case .cghidEventTap: return "hid"
        case .cgSessionEventTap: return "session"
        case .cgAnnotatedSessionEventTap: return "annotated"
        @unknown default: return "unknown"
        }
    }

    private static func postCommandV(tap: CGEventTapLocation) -> Bool {
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
        Thread.sleep(forTimeInterval: 0.05)
        vDown.post(tap: tap)
        Thread.sleep(forTimeInterval: 0.15)
        vUp.post(tap: tap)
        Thread.sleep(forTimeInterval: 0.05)
        cmdUp.post(tap: tap)
        Thread.sleep(forTimeInterval: 0.2)
        return true
    }
}
