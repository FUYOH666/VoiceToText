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
            Menu(state.modelMenuTitle) {
                if state.modelsUnavailable && state.models.isEmpty {
                    Text("Сервер распознавания не отвечает")
                }
                ForEach(state.models) { model in
                    Button(ModelMenu.title(model)) { state.selectModel(model) }
                        .disabled(state.isBusy || state.isSwitching || (!model.fitsMemory && !model.active))
                }
                Divider()
                Button("Своя модель с Hugging Face…") { state.addCustomModel() }
                    .disabled(state.isBusy || state.isSwitching)
                if let memory = state.memoryGB {
                    Text("Память Mac: \(Int(memory.rounded())) ГБ · ★ рекомендуется")
                }
            }
            Button("Словарь терминов…") { state.openGlossary() }
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
