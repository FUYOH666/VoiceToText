import SwiftUI

@main
struct VoiceToTextApp: App {
    @StateObject private var state = AppState()

    var body: some Scene {
        MenuBarExtra(state.icon) {
            Text("Статус: \(state.status)")
            Divider()
            Button("Начать / остановить запись") { state.toggle() }
            Divider()
            Button("Копировать текст") { state.copyLastText() }
            Button("Показать текст") { state.showLastText() }
            Divider()
            Button("Health Check") { state.showHealth() }
            Button("О программе") { state.showAbout() }
            Divider()
            Button("Выход") { state.quit() }
        }
        .menuBarExtraStyle(.menu)
    }
}
