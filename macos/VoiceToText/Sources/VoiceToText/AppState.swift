#if canImport(VoiceToTextCore)
import VoiceToTextCore
#endif
import AppKit
import Foundation
import SwiftUI

@MainActor
final class AppState: ObservableObject {
    /// App mark in the menu bar. Not `mic` — macOS already shows the orange privacy pill while recording.
    @Published var menuSymbol: String = "waveform"
    @Published var status: String = "Готов"
    @Published var lastText: String = ""
    @Published var engine: STTEngineChoice?
    @Published var isSwitching = false

    var statusLine: String {
        if status == "Готов" || status == "Нет микрофона", let title = engine?.title {
            return "\(status) · \(title)"
        }
        return status
    }

    func engineButtonTitle(_ choice: STTEngineChoice) -> String {
        engine == choice ? "✓ \(choice.title)" : choice.title
    }

    private let recorder = Recorder()
    private let hotkey = HotkeyController()
    private let client: STTClient
    private let engineController: EngineController?
    private var isRecording = false
    private var isProcessing = false

    init(config: AppConfig = AppConfig.load()) {
        client = STTClient(config: config)
        if let url = AppConfig.locateConfigFile() {
            engineController = EngineController(
                configURL: url,
                uvExecutable: EngineProcesses.uvExecutable(),
                run: { executable, arguments, cwd in
                    EngineProcesses.run(executable: executable, arguments: arguments, cwd: cwd)
                }
            )
            if let text = try? String(contentsOf: url, encoding: .utf8) {
                engine = EngineConfig.read(from: text)
            }
        } else {
            engineController = nil
        }
        hotkey.onPressed = { [weak self] in
            Task { @MainActor in
                self?.toggle()
            }
        }
        hotkey.start()
        NSApplication.shared.setActivationPolicy(.accessory)
        AppLog.info("VoiceToText UI started; STT \(config.baseURL.absoluteString)")
        Paster.logPermissions()
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

    func selectEngine(_ target: STTEngineChoice) {
        if isSwitching { return }
        if isRecording || isProcessing {
            presentAlert(title: "Движок", message: "Сначала остановите запись.")
            return
        }
        if engine == target { return }
        guard let engineController else {
            presentAlert(title: "Движок", message: EngineSwitchError.configNotFound.message)
            return
        }
        isSwitching = true
        let previous = status
        status = "Переключение…"
        Task {
            do {
                try await Task.detached {
                    try engineController.select(target)
                }.value
                engine = target
                status = previous == "Нет микрофона" ? previous : "Готов"
                AppLog.info("STT engine switched to \(target.rawValue)")
            } catch let error as EngineSwitchError {
                status = previous == "Переключение…" ? "Готов" : previous
                AppLog.error("engine switch failed: \(error.message)")
                presentAlert(title: "Движок", message: error.message)
            } catch {
                status = previous == "Переключение…" ? "Готов" : previous
                AppLog.error("engine switch failed")
                presentAlert(title: "Движок", message: "Не удалось переключить движок.")
            }
            isSwitching = false
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

    func requestPermissions() {
        Paster.promptPermissions()
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
            menuSymbol = "waveform"
            status = "ЗАПИСЬ"
            AppLog.info("recording")
        } catch {
            isRecording = false
            menuSymbol = "waveform"
            status = "Ошибка"
            AppLog.error("start recording: \(error.localizedDescription)")
        }
    }

    private func stopAndTranscribe() {
        isRecording = false
        isProcessing = true
        menuSymbol = "hourglass"
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
            menuSymbol = "waveform"
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
