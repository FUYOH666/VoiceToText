// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "VoiceToText",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "VoiceToTextCore", targets: ["VoiceToTextCore"]),
        .executable(name: "VoiceToText", targets: ["VoiceToText"]),
    ],
    targets: [
        .target(name: "VoiceToTextCore"),
        .executableTarget(
            name: "VoiceToText",
            dependencies: ["VoiceToTextCore"]
        ),
        .testTarget(
            name: "VoiceToTextCoreTests",
            dependencies: ["VoiceToTextCore"]
        ),
    ]
)
