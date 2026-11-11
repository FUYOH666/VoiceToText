#if canImport(VoiceToTextCore)
import VoiceToTextCore
#endif
import Carbon
import Foundation

/// Global hotkeys via Carbon (no extra dependency, no Input Monitoring).
/// Option+Space is always registered. Esc is registered only while a dictation
/// is recording or processing, so it never steals Esc from other apps otherwise.
final class HotkeyController: @unchecked Sendable {
    var onPressed: (() -> Void)?
    /// Option+Space let go (push-to-talk ends a held dictation).
    var onReleased: (() -> Void)?
    var onEscape: (() -> Void)?

    private static let signature = OSType(0x56545431)  // "VTT1"
    private static let mainID: UInt32 = 1
    private static let escapeID: UInt32 = 2

    private var mainRef: EventHotKeyRef?
    private var escapeRef: EventHotKeyRef?
    private var handlerRef: EventHandlerRef?

    func start() {
        stop()
        var specs = [
            EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed)),
            EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyReleased)),
        ]
        let userData = Unmanaged.passUnretained(self).toOpaque()
        let installed = InstallEventHandler(
            GetEventDispatcherTarget(), hotKeyEventHandler, specs.count, &specs, userData, &handlerRef
        )
        if installed != noErr {
            AppLog.error("InstallEventHandler failed: \(installed)")
            return
        }
        mainRef = register(keyCode: UInt32(kVK_Space), modifiers: UInt32(optionKey), id: Self.mainID)
        if mainRef != nil {
            AppLog.info("Hotkey registered: option+space")
        } else {
            AppLog.error("Option+Space is taken by another app; use the menu to record")
        }
    }

    /// Esc cancels only while active; unregistered the rest of the time.
    func setEscapeActive(_ active: Bool) {
        if active, escapeRef == nil {
            escapeRef = register(keyCode: UInt32(kVK_Escape), modifiers: 0, id: Self.escapeID)
        } else if !active, let ref = escapeRef {
            UnregisterEventHotKey(ref)
            escapeRef = nil
        }
    }

    func stop() {
        setEscapeActive(false)
        if let mainRef {
            UnregisterEventHotKey(mainRef)
            self.mainRef = nil
        }
        if let handlerRef {
            RemoveEventHandler(handlerRef)
            self.handlerRef = nil
        }
    }

    fileprivate func dispatch(id: UInt32, released: Bool) {
        switch (id, released) {
        case (Self.mainID, false): onPressed?()
        case (Self.mainID, true): onReleased?()
        case (Self.escapeID, false): onEscape?()
        default: break
        }
    }

    private func register(keyCode: UInt32, modifiers: UInt32, id: UInt32) -> EventHotKeyRef? {
        var ref: EventHotKeyRef?
        let hotKeyID = EventHotKeyID(signature: Self.signature, id: id)
        let status = RegisterEventHotKey(keyCode, modifiers, hotKeyID, GetEventDispatcherTarget(), 0, &ref)
        if status != noErr {
            AppLog.error("RegisterEventHotKey(id=\(id)) failed: \(status)")
            return nil
        }
        return ref
    }

    deinit {
        stop()
    }
}

private func hotKeyEventHandler(
    _: EventHandlerCallRef?,
    event: EventRef?,
    userData: UnsafeMutableRawPointer?
) -> OSStatus {
    guard let userData, let event else { return noErr }
    var hotKeyID = EventHotKeyID()
    let status = GetEventParameter(
        event,
        EventParamName(kEventParamDirectObject),
        EventParamType(typeEventHotKeyID),
        nil,
        MemoryLayout<EventHotKeyID>.size,
        nil,
        &hotKeyID
    )
    guard status == noErr else { return status }
    let controller = Unmanaged<HotkeyController>.fromOpaque(userData).takeUnretainedValue()
    let id = hotKeyID.id
    let released = GetEventKind(event) == UInt32(kEventHotKeyReleased)
    DispatchQueue.main.async {
        controller.dispatch(id: id, released: released)
    }
    return noErr
}
