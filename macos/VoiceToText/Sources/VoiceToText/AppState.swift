#if canImport(VoiceToTextCore)
import VoiceToTextCore
#endif
import AppKit
import Foundation
import SwiftUI

/// Short system sounds for start / stop / error. Off switch lives in the menu.
enum Sounds {
    enum Cue: String {
        case start = "Tink"
        case stop = "Pop"
        case warn = "Purr"
        case error = "Basso"
    }

    static func play(_ cue: Cue, enabled: Bool) {
        guard enabled else { return }
        NSSound(named: NSSound.Name(cue.rawValue))?.play()
    }
}

@MainActor
final class AppState: ObservableObject {
    enum Phase: Equatable {
        case idle, recording, processing
    }

    /// Menu bar mark. Changes with the phase so recording is visible at a glance.
    @Published var menuSymbol: String = AppState.idleSymbol
    @Published var status: String = "Готов"
    @Published var lastText: String = ""
    @Published var engine: STTEngineChoice?
    @Published var isSwitching = false
    @Published private(set) var phase: Phase = .idle
    @Published private(set) var history: [DictationEntry] = []
    @Published var soundsEnabled: Bool {
        didSet { UserDefaults.standard.set(soundsEnabled, forKey: Self.soundsKey) }
    }

    static let idleSymbol = "waveform"
    static let recordingSymbol = "record.circle"
    static let processingSymbol = "hourglass"
    static let errorSymbol = "exclamationmark.triangle"
    /// A forgotten recording stops itself here instead of growing past the server limit.
    static let maxRecordingSeconds: TimeInterval = 15 * 60
    static let warnBeforeLimitSeconds: TimeInterval = 60
    private static let soundsKey = "soundsEnabled"

    var statusLine: String {
        if phase == .idle, status == "Готов", let title = engine?.title {
            return "\(status) · \(title)"
        }
        return status
    }

    var isBusy: Bool { phase != .idle }

    var recordButtonTitle: String {
        switch phase {
        case .idle: return "Начать запись"
        case .recording: return "Остановить и распознать"
        case .processing: return "Отменить распознавание"
        }
    }

    func engineButtonTitle(_ choice: STTEngineChoice) -> String {
        engine == choice ? "✓ \(choice.title)" : choice.title
    }

    private let recorder = Recorder()
    private let hotkey = HotkeyController()
    private let client: STTClient
    private let store = DictationStore()
    private let engineController: EngineController?
    private var transcribeTask: Task<Void, Never>?
    private var limitTimers: [Timer] = []
    private var errorReset: Task<Void, Never>?

    init(config: AppConfig = AppConfig.load()) {
        client = STTClient(config: config)
        soundsEnabled = UserDefaults.standard.object(forKey: Self.soundsKey) as? Bool ?? true
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
            Task { @MainActor in self?.toggle() }
        }
        hotkey.onEscape = { [weak self] in
            Task { @MainActor in self?.cancel() }
        }
        recorder.onInterrupted = { [weak self] in
            Task { @MainActor in
                guard let self, self.phase == .recording else { return }
                self.stopAndTranscribe()
            }
        }
        hotkey.start()
        NSApplication.shared.setActivationPolicy(.accessory)
        AppLog.info("VoiceToText UI started; STT \(config.baseURL.absoluteString)")
        Paster.logPermissions()
        refreshHistory()
        Task { await self.warmupPermission() }
    }

    // MARK: - Dictation

    /// Hotkey: start → stop and transcribe → (while processing) cancel. Never ignored.
    func toggle() {
        switch phase {
        case .idle: startRecording()
        case .recording: stopAndTranscribe()
        case .processing: cancel()
        }
    }

    /// Esc or the menu: drop a recording, or stop waiting for the server.
    func cancel() {
        switch phase {
        case .idle:
            return
        case .recording:
            clearLimitTimers()
            recorder.discard()
            setIdle("Запись отменена")
        case .processing:
            transcribeTask?.cancel()
        }
    }

    func retryLast() {
        guard phase == .idle else { return }
        guard let entry = store.latestRetryable(), let wav = store.audio(for: entry) else {
            presentAlert(title: "Повтор", message: "Нет сохранённой записи для повтора.")
            return
        }
        retry(entry, wav: wav)
    }

    func historyItemSelected(_ entry: DictationEntry) {
        if entry.status == .done, let text = entry.text, !text.isEmpty {
            NSPasteboard.general.clearContents()
            NSPasteboard.general.setString(text, forType: .string)
            status = "Скопировано из истории"
            return
        }
        guard phase == .idle, let wav = store.audio(for: entry) else { return }
        retry(entry, wav: wav)
    }

    static func historyTitle(_ entry: DictationEntry) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        let time = formatter.string(from: entry.createdAt)
        switch entry.status {
        case .done:
            let text = (entry.text ?? "").replacingOccurrences(of: "\n", with: " ")
            let preview = text.isEmpty ? "(пусто)" : String(text.prefix(48)) + (text.count > 48 ? "…" : "")
            return "\(time) · \(preview)"
        case .failed: return "⚠︎ \(time) · не распознано — повторить"
        case .cancelled: return "⏹ \(time) · отменено — повторить"
        case .pending: return "… \(time) · в работе"
        }
    }

    private func retry(_ entry: DictationEntry, wav: Data) {
        Paster.saveFrontmost()
        AppLog.info("retry dictation \(entry.id)")
        run(entryID: entry.id, wav: wav)
    }

    private func startRecording() {
        errorReset?.cancel()
        Paster.saveFrontmost()
        do {
            try recorder.start()
        } catch RecorderError.microphoneDenied {
            showError("Нет доступа к микрофону")
            presentAlert(
                title: "Микрофон",
                message: "Разрешите VoiceToText доступ к микрофону: Системные настройки → Конфиденциальность и безопасность → Микрофон."
            )
            return
        } catch RecorderError.noInputDevice {
            showError("Микрофон не найден")
            return
        } catch {
            AppLog.error("start recording: \(error.localizedDescription)")
            showError("Не удалось начать запись")
            return
        }
        phase = .recording
        menuSymbol = Self.recordingSymbol
        status = "Запись… (Esc — отмена)"
        hotkey.setEscapeActive(true)
        Sounds.play(.start, enabled: soundsEnabled)
        scheduleLimitTimers()
        AppLog.info("recording")
    }

    private func stopAndTranscribe() {
        clearLimitTimers()
        let wav: Data
        let samples = recorder.samplesCaptured
        do {
            wav = try recorder.stop()
        } catch {
            AppLog.error("stop recording: \(error.localizedDescription)")
            showError("Не удалось остановить запись")
            return
        }
        Sounds.play(.stop, enabled: soundsEnabled)
        let seconds = Double(samples) / Double(WAVEncoder.sampleRate)
        if seconds < 0.3 {
            setIdle("Слишком короткая запись")
            return
        }
        var entryID: String?
        do {
            entryID = try store.begin(wav: wav, durationSeconds: seconds).id
        } catch {
            // Still transcribe; only the safety copy is missing.
            AppLog.error("could not save recording: \(error.localizedDescription)")
        }
        refreshHistory()
        run(entryID: entryID, wav: wav)
    }

    private func run(entryID: String?, wav: Data) {
        phase = .processing
        menuSymbol = Self.processingSymbol
        status = "Распознаю… (Esc — отмена)"
        hotkey.setEscapeActive(true)
        let client = self.client
        transcribeTask = Task { [weak self] in
            do {
                let text = try await client.transcribe(wav: wav)
                await self?.finish(entryID: entryID, text: text)
            } catch let error as STTClientError {
                self?.failed(entryID: entryID, error: error)
            } catch {
                self?.failed(entryID: entryID, error: .unreachable(error.localizedDescription))
            }
        }
    }

    private func finish(entryID: String?, text: String) async {
        transcribeTask = nil
        if let entryID { store.finish(entryID, text: text) }
        refreshHistory()
        guard !text.isEmpty else {
            // Keep the previous text: an empty result must not wipe it.
            setIdle("Речь не распознана")
            AppLog.info("empty transcription")
            return
        }
        lastText = text
        hotkey.setEscapeActive(false)
        status = "Вставляю…"
        switch await Paster.paste(text) {
        case .pasted:
            setIdle("Готов")
        case .secureInput:
            setIdle("Поле пароля: текст не вставлен (есть в истории)")
        case .noAccessibility:
            showError("Нет доступа к вставке: текст в буфере, нажмите ⌘V")
        case .failed:
            showError("Не удалось вставить: текст в истории")
        }
    }

    private func failed(entryID: String?, error: STTClientError) {
        transcribeTask = nil
        let cancelled = error == .cancelled
        if let entryID {
            store.fail(entryID, error: error.userMessage, cancelled: cancelled)
        }
        refreshHistory()
        if cancelled {
            setIdle("Отменено — запись сохранена, можно повторить")
        } else {
            AppLog.error("transcribe: \(error)")
            showError("\(error.userMessage). Запись сохранена — «Повторить»")
        }
    }

    // MARK: - Status

    private func setIdle(_ message: String) {
        phase = .idle
        menuSymbol = Self.idleSymbol
        status = message
        hotkey.setEscapeActive(false)
    }

    private func showError(_ message: String) {
        setIdle(message)
        menuSymbol = Self.errorSymbol
        Sounds.play(.error, enabled: soundsEnabled)
        errorReset?.cancel()
        errorReset = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 8_000_000_000)
            guard let self, !Task.isCancelled, self.phase == .idle else { return }
            self.menuSymbol = Self.idleSymbol
        }
    }

    private func scheduleLimitTimers() {
        clearLimitTimers()
        let warnAt = Self.maxRecordingSeconds - Self.warnBeforeLimitSeconds
        let warn = Timer.scheduledTimer(withTimeInterval: warnAt, repeats: false) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.phase == .recording else { return }
                self.status = "Запись: осталась минута"
                Sounds.play(.warn, enabled: self.soundsEnabled)
            }
        }
        let stop = Timer.scheduledTimer(withTimeInterval: Self.maxRecordingSeconds, repeats: false) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.phase == .recording else { return }
                AppLog.info("max recording length reached; stopping")
                self.stopAndTranscribe()
            }
        }
        limitTimers = [warn, stop]
    }

    private func clearLimitTimers() {
        limitTimers.forEach { $0.invalidate() }
        limitTimers = []
    }

    private func refreshHistory() {
        history = Array(store.entries().suffix(10).reversed())
    }

    // MARK: - Menu actions

    func selectEngine(_ target: STTEngineChoice) {
        if isSwitching { return }
        if isBusy {
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
                status = "Готов"
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
                presentAlert(title: "Сервер распознавания", message: "Работает\n\(client.config.baseURL.absoluteString)")
            } catch let error as STTClientError {
                presentAlert(title: "Сервер распознавания", message: error.userMessage)
            } catch {
                presentAlert(title: "Сервер распознавания", message: error.localizedDescription)
            }
        }
    }

    func requestPermissions() {
        Paster.promptPermissions()
    }

    func showAbout() {
        presentAlert(
            title: "VoiceToText",
            message: "Private local STT. Option+Space → paste, Esc — отмена.\nSTT: \(client.config.baseURL.absoluteString)\nЗаписи и история: ~/Library/Application Support/VoiceToText\nprivate@scanovich.ai"
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

    private func warmupPermission() async {
        let granted = await recorder.requestPermission()
        if !granted {
            status = "Нет микрофона"
            AppLog.warning("microphone permission denied")
        }
    }

    private func presentAlert(title: String, message: String) {
        NSApplication.shared.activate(ignoringOtherApps: true)
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.alertStyle = .informational
        alert.runModal()
    }
}
