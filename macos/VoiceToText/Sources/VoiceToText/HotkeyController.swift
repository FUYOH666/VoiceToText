#if canImport(VoiceToTextCore)
import VoiceToTextCore
#endif
import Carbon
import Foundation

/// Global Option+Space via Carbon (no extra SPM dependency).
final class HotkeyController: @unchecked Sendable {
    var onPressed: (() -> Void)?
    private var hotKeyRef: EventHotKeyRef?
    private var handlerRef: EventHandlerRef?

    func start() {
        stop()
        let hotKeyID = EventHotKeyID(signature: OSType(0x56545431), id: 1)
        let status = RegisterEventHotKey(
            UInt32(kVK_Space),
            UInt32(optionKey),
            hotKeyID,
            GetEventDispatcherTarget(),
            0,
            &hotKeyRef
        )
        if status != noErr {
            AppLog.error("RegisterEventHotKey failed: \(status)")
            return
        }

        var spec = EventTypeSpec(
            eventClass: OSType(kEventClassKeyboard),
            eventKind: UInt32(kEventHotKeyPressed)
        )
        let userData = Unmanaged.passUnretained(self).toOpaque()
        let installed = InstallEventHandler(
            GetEventDispatcherTarget(),
            hotKeyEventHandler,
            1,
            &spec,
            userData,
            &handlerRef
        )
        if installed != noErr {
            AppLog.error("InstallEventHandler failed: \(installed)")
        } else {
            AppLog.info("Hotkey registered: option+space")
        }
    }

    func stop() {
        if let hotKeyRef {
            UnregisterEventHotKey(hotKeyRef)
            self.hotKeyRef = nil
        }
        if let handlerRef {
            RemoveEventHandler(handlerRef)
            self.handlerRef = nil
        }
    }

    deinit {
        stop()
    }
}

private func hotKeyEventHandler(
    _: EventHandlerCallRef?,
    _: EventRef?,
    userData: UnsafeMutableRawPointer?
) -> OSStatus {
    guard let userData else { return noErr }
    let controller = Unmanaged<HotkeyController>.fromOpaque(userData).takeUnretainedValue()
    DispatchQueue.main.async {
        controller.onPressed?()
    }
    return noErr
}
