#if canImport(VoiceToTextCore)
import VoiceToTextCore
#endif
import SwiftUI

@main
struct VoiceToTextApp: App {
    @StateObject private var state = AppState()

    var body: some Scene {
        MenuBarExtra {
            Text("Статус: \(state.statusLine)")
            Divider()
            Button(state.engineButtonTitle(.whisper)) { state.selectEngine(.whisper) }
                .disabled(state.isSwitching || state.isBusy)
            Button(state.engineButtonTitle(.qwen)) { state.selectEngine(.qwen) }
                .disabled(state.isSwitching || state.isBusy)
            Divider()
            Button(state.recordButtonTitle) { state.toggle() }
            if state.phase == .recording {
                Button("Отменить запись (Esc)") { state.cancel() }
            }
            Button("Повторить последнюю запись") { state.retryLast() }
                .disabled(state.isBusy)
            Menu("История") {
                if state.history.isEmpty {
                    Text("Пока пусто")
                } else {
                    ForEach(state.history, id: \.id) { entry in
                        Button(AppState.historyTitle(entry)) { state.historyItemSelected(entry) }
                    }
                }
            }
            Divider()
            Button("Копировать текст") { state.copyLastText() }
            Button("Показать текст") { state.showLastText() }
            Divider()
            Toggle("Звуки", isOn: $state.soundsEnabled)
            Button("Проверить сервер") { state.showHealth() }
            Button("Разрешения…") { state.requestPermissions() }
            Button("О программе") { state.showAbout() }
            Divider()
            Button("Выход") { state.quit() }
        } label: {
            Image(systemName: state.menuSymbol)
        }
        .menuBarExtraStyle(.menu)
    }
}
