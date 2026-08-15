import SwiftUI

@main
struct VoiceToTextApp: App {
    @StateObject private var state = AppState()

    var body: some Scene {
        MenuBarExtra {
            Text("Статус: \(state.status)")
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
