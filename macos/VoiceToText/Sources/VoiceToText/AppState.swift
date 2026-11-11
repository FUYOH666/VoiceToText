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

    /// Menu bar mark. Stays `waveform` while recording: macOS already shows its orange
    /// microphone indicator then, and a second recording mark looked like a duplicate.
    /// It changes only for processing and errors, which the system does not show.
    @Published var menuSymbol: String = AppState.idleSymbol
    @Published var status: String = "Готов"
    @Published var lastText: String = ""
    @Published private(set) var models: [ModelInfo] = []
    @Published private(set) var memoryGB: Double?
    @Published private(set) var modelsUnavailable = false
    @Published var isSwitching = false
    @Published private(set) var phase: Phase = .idle
    @Published private(set) var history: [DictationEntry] = []
    @Published var soundsEnabled: Bool {
        didSet { UserDefaults.standard.set(soundsEnabled, forKey: Self.soundsKey) }
    }

    static let idleSymbol = "waveform"
    static let processingSymbol = "hourglass"
    static let errorSymbol = "exclamationmark.triangle"
    /// A forgotten recording stops itself here instead of growing past the server limit.
    static let maxRecordingSeconds: TimeInterval = 15 * 60
    static let warnBeforeLimitSeconds: TimeInterval = 60
    private static let soundsKey = "soundsEnabled"

    var statusLine: String {
        if phase == .idle, status == "Готов", let title = activeModel?.title {
            return "\(status) · \(title)"
        }
        return status
    }

    var activeModel: ModelInfo? { models.first { $0.active } }

    var modelMenuTitle: String {
        "Модель: \(ModelMenu.shortTitle(activeModel))"
    }

    var isBusy: Bool { phase != .idle }

    var recordButtonTitle: String {
        switch phase {
        case .idle: return "Начать запись"
        case .recording: return "Остановить и распознать"
        case .processing: return "Отменить распознавание"
        }
    }

    private let recorder = Recorder()
    private let hotkey = HotkeyController()
    private let client: STTClient
    private let modelsClient: ModelsClient
    private let store = DictationStore()
    private var transcribeTask: Task<Void, Never>?
    private var downloadTask: Task<Void, Never>?
    private var limitTimers: [Timer] = []
    private var modelsTimer: Timer?
    private var errorReset: Task<Void, Never>?
    /// Option+Space is physically down (guards against key repeat).
    private var hotkeyDown = false
    /// Set when a press started the recording; a long hold ends it on release.
    private var holdStartedAt: Date?
    /// Held at least this long = push-to-talk (release stops). Shorter = tap to toggle.
    static let pushToTalkThreshold: TimeInterval = 0.5

    init(config: AppConfig = AppConfig.load()) {
        client = STTClient(config: config)
        modelsClient = ModelsClient(config: config)
        soundsEnabled = UserDefaults.standard.object(forKey: Self.soundsKey) as? Bool ?? true
        hotkey.onReleased = { [weak self] in
            Task { @MainActor in self?.hotkeyReleased() }
        }
        hotkey.onPressed = { [weak self] in
            Task { @MainActor in self?.hotkeyPressed() }
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
        Task { await self.refreshModels() }
        // The list is cheap (local HTTP); keep the menu fresh without a menu-open hook.
        modelsTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            Task { @MainActor in await self?.refreshModels() }
        }
    }

    // MARK: - Dictation

    /// Hotkey: start → stop and transcribe → (while processing) cancel. Never ignored.
    /// Two ways to dictate with one hotkey:
    /// hold Option+Space while speaking and let go (push-to-talk), or tap it
    /// once to start and once more to stop.
    func hotkeyPressed() {
        guard !hotkeyDown else { return }
        hotkeyDown = true
        if phase == .idle {
            startRecording()
            holdStartedAt = phase == .recording ? Date() : nil
        } else {
            holdStartedAt = nil
            toggle()
        }
    }

    func hotkeyReleased() {
        hotkeyDown = false
        guard let started = holdStartedAt else { return }
        holdStartedAt = nil
        if phase == .recording, Date().timeIntervalSince(started) >= Self.pushToTalkThreshold {
            AppLog.info("push-to-talk: released after \(String(format: "%.1f", Date().timeIntervalSince(started)))s")
            stopAndTranscribe()
        }
    }

    func openGlossary() {
        do {
            let url = try Glossary.ensureFile()
            NSWorkspace.shared.open(url)
        } catch {
            presentAlert(title: "Словарь", message: "Не удалось создать файл словаря: \(error.localizedDescription)")
        }
    }

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
        menuSymbol = Self.idleSymbol
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
                let text = try await client.transcribe(wav: wav, prompt: Glossary.load())
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

    // MARK: - Models

    func refreshModels() async {
        do {
            let list = try await modelsClient.list()
            models = list.data
            memoryGB = list.systemMemoryGB
            modelsUnavailable = false
        } catch {
            modelsUnavailable = true
            AppLog.warning("model list unavailable: \(error)")
        }
    }

    /// Menu click on a model: switch to it, or offer to download it first.
    func selectModel(_ model: ModelInfo) {
        guard !isSwitching, downloadTask == nil else {
            presentAlert(title: "Модель", message: "Дождитесь окончания текущей операции с моделью.")
            return
        }
        if isBusy {
            presentAlert(title: "Модель", message: "Сначала закончите диктовку.")
            return
        }
        if model.active { return }
        if !model.fitsMemory {
            let need = model.minMemoryGB.map { "\(Int($0)) ГБ" } ?? "больше"
            presentAlert(title: model.title, message: "Этой модели нужно не меньше \(need) памяти.")
            return
        }
        if model.installed {
            Task { await activate(model) }
            return
        }
        let details = [
            "Скачать \(ModelMenu.size(model.downloadGB)), в работе ~\(ModelMenu.size(model.ramGB)) памяти.",
            model.note ?? "",
            "Диктовка продолжит работать на текущей модели, пока идёт загрузка.",
        ].filter { !$0.isEmpty }.joined(separator: "\n\n")
        guard confirm(title: model.title, message: details, ok: "Скачать и включить") else { return }
        download(model)
    }

    func addCustomModel() {
        guard !isBusy, !isSwitching, downloadTask == nil else { return }
        guard let repo = askText(
            title: "Своя модель с Hugging Face",
            message: "Адрес репозитория, например mlx-community/whisper-large-v3-turbo.\nПодходят MLX-модели Whisper и Qwen3-ASR.",
            placeholder: "org/name"
        ) else { return }
        status = "Проверяю \(repo)…"
        Task {
            do {
                let model = try await modelsClient.addCustom(repo: repo)
                await refreshModels()
                status = "Готов"
                selectModel(models.first { $0.id == model.id } ?? model)
            } catch let error as ModelsClientError {
                showError(error.userMessage)
            } catch {
                showError("Не удалось проверить модель")
            }
        }
    }

    private func download(_ model: ModelInfo) {
        downloadTask = Task { [weak self] in
            guard let self else { return }
            do {
                var progress = try await modelsClient.startDownload(model.id)
                while progress.isRunning {
                    let percent = progress.progress.map { " \(Int(($0 * 100).rounded()))%" } ?? "…"
                    if phase == .idle { status = "Скачиваю \(model.title)\(percent)" }
                    await refreshModels()
                    try await Task.sleep(nanoseconds: 1_000_000_000)
                    progress = try await modelsClient.downloadStatus(model.id)
                }
                downloadTask = nil
                guard progress.state == "done" else {
                    showError("Не удалось скачать: \(progress.error ?? "ошибка сети")")
                    await refreshModels()
                    return
                }
                await refreshModels()
                await activate(models.first { $0.id == model.id } ?? model)
            } catch let error as ModelsClientError {
                downloadTask = nil
                showError(error.userMessage)
            } catch {
                downloadTask = nil
            }
        }
    }

    private func activate(_ model: ModelInfo) async {
        if isBusy {
            // A dictation started meanwhile; switch after it instead of under it.
            status = "Модель скачана — выберите её в меню"
            return
        }
        isSwitching = true
        status = "Включаю \(model.title)…"
        menuSymbol = Self.processingSymbol
        defer { isSwitching = false }
        do {
            try await modelsClient.activate(model.id)
            await refreshModels()
            AppLog.info("model switched to \(model.id)")
            setIdle("Готов")
        } catch let error as ModelsClientError {
            await refreshModels()
            showError(error.userMessage)
        } catch {
            showError("Не удалось переключить модель")
        }
    }

    private func confirm(title: String, message: String, ok: String) -> Bool {
        NSApplication.shared.activate(ignoringOtherApps: true)
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.addButton(withTitle: ok)
        alert.addButton(withTitle: "Отмена")
        return alert.runModal() == .alertFirstButtonReturn
    }

    private func askText(title: String, message: String, placeholder: String) -> String? {
        NSApplication.shared.activate(ignoringOtherApps: true)
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        let field = NSTextField(frame: NSRect(x: 0, y: 0, width: 320, height: 24))
        field.placeholderString = placeholder
        alert.accessoryView = field
        alert.addButton(withTitle: "Проверить")
        alert.addButton(withTitle: "Отмена")
        alert.window.initialFirstResponder = field
        guard alert.runModal() == .alertFirstButtonReturn else { return nil }
        let value = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        return value.isEmpty ? nil : value
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
