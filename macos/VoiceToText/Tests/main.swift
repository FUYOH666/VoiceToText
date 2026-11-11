import Foundation

// Runner for macos/scripts/test.sh. Add new suites here.

AppLog.directoryOverride = testDirectory
expect(AppLog.logFile.path.hasPrefix(testDirectory.path), "test log stays in the temp dir")

runAppConfigTests()
runWAVEncoderTests()
runEngineSwitchTests()
runLiveShapedSwitchTests()
runDictationStoreTests()
runClipboardTests()
let sem = DispatchSemaphore(value: 0)
Task {
    await runSTTClientTests()
    sem.signal()
}
sem.wait()

try? FileManager.default.removeItem(at: testDirectory)

if failed > 0 {
    fputs("\(failed) of \(checks) checks failed\n", stderr)
    exit(1)
}
print("All VoiceToTextCore tests passed (\(checks) checks)")
