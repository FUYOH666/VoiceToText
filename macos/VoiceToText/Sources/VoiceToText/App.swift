import SwiftUI

@main
struct VoiceToTextApp: App {
    @StateObject private var state = AppState()

    var body: some Scene {
        MenuBarExtra {
            Text("Статус: \(state.statusLine)")
            Divider()
            Button(state.engineButtonTitle(.whisper)) { state.selectEngine(.whisper) }
                .disabled(state.isSwitching)
            Button(state.engineButtonTitle(.qwen)) { state.selectEngine(.qwen) }
                .disabled(state.isSwitching)
            Divider()
            Button("Начать / остановить запись") { state.toggle() }
            Divider()
            Button("Копировать текст") { state.copyLastText() }
            Button("Показать текст") { state.showLastText() }
            Divider()
            Button("Health Check") { state.showHealth() }
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
