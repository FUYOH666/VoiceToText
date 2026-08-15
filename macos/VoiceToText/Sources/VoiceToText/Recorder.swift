#if canImport(VoiceToTextCore)
import VoiceToTextCore
#endif
import AVFoundation
import Foundation

enum RecorderError: Error {
    case alreadyRecording
    case notRecording
    case engine(String)
}

/// AVAudioEngine capture converted to 16 kHz mono float, then WAV.
final class Recorder: @unchecked Sendable {
    private let engine = AVAudioEngine()
    private let lock = NSLock()
    private var floats: [Float] = []
    private var converter: AVAudioConverter?
    private(set) var isRecording = false

    func requestPermission() async -> Bool {
        await withCheckedContinuation { continuation in
            AVCaptureDevice.requestAccess(for: .audio) { granted in
                continuation.resume(returning: granted)
            }
        }
    }

    func start() throws {
        lock.lock()
        defer { lock.unlock() }
        if isRecording { throw RecorderError.alreadyRecording }

        floats = []
        let input = engine.inputNode
        let inputFormat = input.inputFormat(forBus: 0)
        guard
            let target = AVAudioFormat(
                commonFormat: .pcmFormatFloat32,
                sampleRate: Double(WAVEncoder.sampleRate),
                channels: 1,
                interleaved: false
            )
        else {
            throw RecorderError.engine("cannot create 16 kHz mono format")
        }
        converter = AVAudioConverter(from: inputFormat, to: target)
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, _ in
            self?.append(buffer: buffer, target: target)
        }
        do {
            try engine.start()
        } catch {
            input.removeTap(onBus: 0)
            throw RecorderError.engine(error.localizedDescription)
        }
        isRecording = true
        AppLog.info("recording started (in=\(inputFormat.sampleRate)Hz → 16000Hz mono)")
    }

    func stop() throws -> Data {
        lock.lock()
        let wasRecording = isRecording
        isRecording = false
        let captured = floats
        floats = []
        lock.unlock()

        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        converter = nil
        guard wasRecording else { throw RecorderError.notRecording }
        AppLog.info("recording stopped: \(captured.count) samples")
        return WAVEncoder.pcm16kMono(floats: captured)
    }

    private func append(buffer: AVAudioPCMBuffer, target: AVAudioFormat) {
        guard let converter else {
            appendFloats(from: buffer)
            return
        }
        let ratio = target.sampleRate / buffer.format.sampleRate
        let capacity = AVAudioFrameCount((Double(buffer.frameLength) * ratio).rounded(.up) + 16)
        guard
            let converted = AVAudioPCMBuffer(pcmFormat: target, frameCapacity: capacity)
        else { return }
        var error: NSError?
        var consumed = false
        let status = converter.convert(to: converted, error: &error) { _, outStatus in
            if consumed {
                outStatus.pointee = .noDataNow
                return nil
            }
            consumed = true
            outStatus.pointee = .haveData
            return buffer
        }
        if status == .error {
            AppLog.warning("audio convert: \(error?.localizedDescription ?? "unknown")")
            return
        }
        appendFloats(from: converted)
    }

    private func appendFloats(from buffer: AVAudioPCMBuffer) {
        guard let channel = buffer.floatChannelData?.pointee else { return }
        let count = Int(buffer.frameLength)
        lock.lock()
        floats.append(contentsOf: UnsafeBufferPointer(start: channel, count: count))
        lock.unlock()
    }
}
