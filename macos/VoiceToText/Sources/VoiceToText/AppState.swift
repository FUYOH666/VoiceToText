#if canImport(VoiceToTextCore)
import VoiceToTextCore
#endif
import AppKit
import Foundation
import SwiftUI

@MainActor
final class AppState: ObservableObject {
    @Published var icon: String = "🎤"
    @Published var status: String = "Готов"
    @Published var lastText: String = ""

    private let recorder = Recorder()
    private let hotkey = HotkeyController()
    private let client: STTClient
    private var isRecording = false
    private var isProcessing = false

    init(config: AppConfig = AppConfig.load()) {
        client = STTClient(config: config)
        hotkey.onPressed = { [weak self] in
            Task { @MainActor in
                self?.toggle()
            }
        }
        hotkey.start()
        NSApplication.shared.setActivationPolicy(.accessory)
        AppLog.info("VoiceToText UI started; STT \(config.baseURL.absoluteString)")
        Task { await self.warmupPermission() }
    }

    func toggle() {
        if isProcessing { return }
        if isRecording {
            stopAndTranscribe()
        } else {
            startRecording()
        }
    }

    func showHealth() {
        Task {
            do {
                _ = try await client.healthOK()
                presentAlert(title: "Health Check", message: "local_stt: OK\n\(client.config.baseURL.absoluteString)")
            } catch {
                presentAlert(title: "Health Check", message: "local_stt: \(error.localizedDescription)")
            }
        }
    }

    func showAbout() {
        presentAlert(
            title: "VoiceToText",
            message: "Private local STT. Option+Space → paste.\nSTT: \(client.config.baseURL.absoluteString)\nprivate@scanovich.ai"
        )
    }

    func showLastText() {
        if lastText.isEmpty {
            presentAlert(title: "Нет текста", message: "Нет текста для отображения")
        } else {
            presentAlert(title: "Последний текст", message: String(lastText.prefix(2000)))
        }
    }

    func copyLastText() {
        guard !lastText.isEmpty else {
            presentAlert(title: "Нет текста", message: "Нет текста для копирования")
            return
        }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(lastText, forType: .string)
    }

    func quit() {
        hotkey.stop()
        NSApplication.shared.terminate(nil)
    }

    private func startRecording() {
        Paster.saveFrontmost()
        do {
            try recorder.start()
            isRecording = true
            icon = "🔴"
            status = "ЗАПИСЬ"
            AppLog.info("recording")
        } catch {
            isRecording = false
            icon = "🎤"
            status = "Ошибка"
            AppLog.error("start recording: \(error.localizedDescription)")
        }
    }

    private func stopAndTranscribe() {
        isRecording = false
        isProcessing = true
        icon = "🎤"
        status = "Обработка..."
        let wav: Data
        do {
            wav = try recorder.stop()
        } catch {
            isProcessing = false
            status = "Ошибка"
            AppLog.error("stop recording: \(error.localizedDescription)")
            return
        }

        Task {
            do {
                let text = try await client.transcribe(wav: wav)
                lastText = text
                if text.isEmpty {
                    status = "Готов"
                    AppLog.info("empty transcription")
                } else {
                    status = "Готов"
                    Paster.paste(text)
                }
            } catch {
                status = "Ошибка"
                AppLog.error("transcribe: \(error.localizedDescription)")
            }
            isProcessing = false
            icon = "🎤"
        }
    }

    private func warmupPermission() async {
        let granted = await recorder.requestPermission()
        if !granted {
            status = "Нет микрофона"
            AppLog.warning("microphone permission denied")
        }
    }

    private func presentAlert(title: String, message: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.alertStyle = .informational
        alert.runModal()
    }
}
