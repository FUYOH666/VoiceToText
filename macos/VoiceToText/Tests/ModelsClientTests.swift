import Foundation

/// Shape of a real `GET /v1/models` answer (trimmed to three models).
let sampleModelList = #"""
{"object":"list","system_memory_gb":16.0,"recommended":"qwen3-asr-1.7b-8bit","active":"whisper-large-v3",
 "data":[
  {"id":"qwen3-asr-1.7b-8bit","object":"model","title":"Qwen3-ASR 1.7B · 8-bit","family":"qwen3_asr",
   "repo":"moona3k/mlx-qwen3-asr-1.7b-8bit","quantization":"8bit","download_gb":2.17,"ram_gb":2.7,
   "min_memory_gb":8,"languages":"30","note":"n","verified_revision":"x","custom":false,
   "installed":true,"active":false,"recommended":true,"fits_memory":true},
  {"id":"whisper-large-v3-turbo-8bit","object":"model","title":"Whisper large-v3 turbo · 8-bit",
   "family":"mlx_whisper","repo":"r","quantization":"8bit","download_gb":0.86,"ram_gb":1.3,
   "min_memory_gb":8,"installed":false,"active":false,"recommended":false,"fits_memory":true,
   "download":{"model":"whisper-large-v3-turbo-8bit","state":"downloading","bytes_done":430,
               "bytes_total":860,"progress":0.5,"error":null}},
  {"id":"whisper-large-v3","object":"model","title":"Whisper large-v3","family":"mlx_whisper","repo":"r2",
   "quantization":"fp16","download_gb":3.08,"ram_gb":3.6,"min_memory_gb":32,
   "installed":true,"active":true,"recommended":false,"fits_memory":false}
 ]}
"""#

func runModelsClientTests() async {
    // Decoding the list.
    MockURLProtocol.reset()
    MockURLProtocol.handler = { request in
        expect(request.url?.path == "/v1/models", "list path, got \(request.url?.path ?? "")")
        return (200, Data(sampleModelList.utf8))
    }
    do {
        let list = try await makeModelsClient().list()
        expect(list.data.count == 3, "three models decoded")
        expect(list.systemMemoryGB == 16 && list.recommended == "qwen3-asr-1.7b-8bit", "list header")
        expect(list.activeModel?.id == "whisper-large-v3", "active model")
        expect(list.data[1].download?.isRunning == true, "running download decoded")
    } catch {
        expect(false, "list threw \(error)")
    }

    // Activation that the server refuses maps to a readable message.
    MockURLProtocol.reset()
    MockURLProtocol.handler = { request in
        expect(request.httpMethod == "POST", "activate is POST")
        return (409, Data(#"{"error":{"message":"x is not downloaded yet","code":"model_not_installed"}}"#.utf8))
    }
    do {
        try await makeModelsClient().activate("x")
        expect(false, "activate 409 should throw")
    } catch let error as ModelsClientError {
        expect(error == .server(status: 409, code: "model_not_installed", message: "x is not downloaded yet"), "409 mapped")
        expect(error.userMessage == "Модель ещё не скачана", "409 message: \(error.userMessage)")
    } catch {
        expect(false, "activate unexpected \(error)")
    }

    // Success.
    MockURLProtocol.reset()
    MockURLProtocol.handler = { _ in (200, Data(#"{"active":"x","changed":true}"#.utf8)) }
    do {
        try await makeModelsClient().activate("x")
        expect(true, "activate ok")
    } catch {
        expect(false, "activate ok threw \(error)")
    }

    // Custom repo goes out as JSON.
    MockURLProtocol.reset()
    MockURLProtocol.handler = { request in
        expect(request.url?.path == "/v1/models/custom", "custom path")
        expect(request.value(forHTTPHeaderField: "Content-Type") == "application/json", "custom is JSON")
        return (200, Data(#"{"id":"custom-a","title":"a","installed":false,"active":false,"recommended":false,"fits_memory":true}"#.utf8))
    }
    do {
        let model = try await makeModelsClient().addCustom(repo: "org/a")
        expect(model.id == "custom-a", "custom decoded")
    } catch {
        expect(false, "custom threw \(error)")
    }

    runModelMenuTests()
}

func runModelMenuTests() {
    expect(ModelMenu.size(0.86) == "0,86 ГБ", "size <1 GB: \(ModelMenu.size(0.86))")
    expect(ModelMenu.size(2.17) == "2,2 ГБ", "size >=1 GB: \(ModelMenu.size(2.17))")
    guard let list = try? JSONDecoder().decode(ModelList.self, from: Data(sampleModelList.utf8)) else {
        expect(false, "sample decodes")
        return
    }
    let qwen = ModelMenu.title(list.data[0])
    expect(qwen == "Qwen3-ASR 1.7B · 8-bit ★ — ~2,7 ГБ памяти", "installed recommended: \(qwen)")
    let turbo = ModelMenu.title(list.data[1])
    expect(turbo == "Whisper large-v3 turbo · 8-bit — скачивается 50%", "downloading: \(turbo)")
    let large = ModelMenu.title(list.data[2])
    expect(large == "✓ Whisper large-v3 — ~3,6 ГБ памяти — нужно ≥32 ГБ", "active, does not fit: \(large)")
    let notInstalled = ModelInfo(
        id: "s", title: "Whisper small", downloadGB: 0.48, installed: false, active: false,
        recommended: false, fitsMemory: true
    )
    expect(ModelMenu.title(notInstalled) == "Whisper small — скачать 0,48 ГБ", "not installed: \(ModelMenu.title(notInstalled))")
}

func makeModelsClient() -> ModelsClient {
    let configuration = URLSessionConfiguration.ephemeral
    configuration.protocolClasses = [MockURLProtocol.self]
    configuration.timeoutIntervalForRequest = 2
    return ModelsClient(config: .loopbackDefault, session: URLSession(configuration: configuration))
}
