import Foundation

/// 16 kHz mono 16-bit PCM WAV (OpenAI-compatible upload).
public enum WAVEncoder {
    public static let sampleRate = 16_000

    public static func pcm16kMono(floats: [Float]) -> Data {
        var samples = [Int16](repeating: 0, count: floats.count)
        for (index, value) in floats.enumerated() {
            let clipped = max(-1.0, min(1.0, value))
            samples[index] = Int16((clipped * Float(Int16.max)).rounded())
        }
        let dataSize = samples.count * MemoryLayout<Int16>.size
        var data = Data()
        data.append(ascii("RIFF"))
        data.append(le32(UInt32(36 + dataSize)))
        data.append(ascii("WAVE"))
        data.append(ascii("fmt "))
        data.append(le32(16))
        data.append(le16(1))
        data.append(le16(1))
        data.append(le32(UInt32(sampleRate)))
        data.append(le32(UInt32(sampleRate * 2)))
        data.append(le16(2))
        data.append(le16(16))
        data.append(ascii("data"))
        data.append(le32(UInt32(dataSize)))
        samples.withUnsafeBytes { data.append(contentsOf: $0) }
        return data
    }

    private static func ascii(_ value: String) -> Data {
        Data(value.utf8)
    }

    private static func le16(_ value: UInt16) -> Data {
        var little = value.littleEndian
        return Data(bytes: &little, count: 2)
    }

    private static func le32(_ value: UInt32) -> Data {
        var little = value.littleEndian
        return Data(bytes: &little, count: 4)
    }
}
