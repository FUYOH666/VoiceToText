import Foundation

func runGlossaryTests() {
    expect(Glossary.prompt(from: Glossary.template) == nil, "template alone sends no prompt")
    expect(Glossary.prompt(from: "") == nil, "empty file sends no prompt")
    let text = """
    # comment
    Claude Code
      MLX  
    Hugging Face
    mlx
    """
    expect(Glossary.prompt(from: text) == "Claude Code, MLX, Hugging Face.", "terms joined, trimmed, deduped: \(Glossary.prompt(from: text) ?? "nil")")

    let many = (1...400).map { "Термин номер \($0)" }.joined(separator: "\n")
    let capped = Glossary.prompt(from: many) ?? ""
    expect(capped.count <= Glossary.maxCharacters + 1, "prompt capped, got \(capped.count)")
    expect(capped.hasSuffix(".") && !capped.contains(", ."), "capped at a whole term")

    let dir = testDirectory.appendingPathComponent("glossary-\(UUID().uuidString)", isDirectory: true)
    let url = try? Glossary.ensureFile(directory: dir)
    expect(url.map { FileManager.default.fileExists(atPath: $0.path) } == true, "ensureFile creates the template")
    expect(Glossary.load(directory: dir) == nil, "fresh template loads as no prompt")
    try? "Qwen\nGitHub\n".write(to: Glossary.fileURL(in: dir), atomically: true, encoding: .utf8)
    _ = try? Glossary.ensureFile(directory: dir)  // must not overwrite user edits
    expect(Glossary.load(directory: dir) == "Qwen, GitHub.", "user terms kept and loaded")

    // The prompt goes out as its own multipart field before the file.
    let client = STTClient(config: .loopbackDefault)
    let url2 = URL(string: "http://127.0.0.1:8765/v1/audio/transcriptions")!
    if let request = try? client.multipartRequest(url: url2, wav: Data([1, 2]), prompt: "Claude Code."),
       let body = request.httpBody.flatMap({ String(data: $0, encoding: .isoLatin1) })
    {
        expect(body.contains("name=\"prompt\"\r\n\r\nClaude Code.\r\n"), "prompt field in multipart")
        expect(body.contains("name=\"file\"; filename=\"audio.wav\""), "file field still there")
    } else {
        expect(false, "multipart request with prompt")
    }
    if let plain = try? client.multipartRequest(url: url2, wav: Data([1]), prompt: nil),
       let body = plain.httpBody.flatMap({ String(data: $0, encoding: .isoLatin1) })
    {
        expect(!body.contains("name=\"prompt\""), "no prompt field without a glossary")
    }
}
