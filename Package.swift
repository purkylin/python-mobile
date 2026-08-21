// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PythonMobile",
    platforms: [
        .iOS(.v18),
        .macOS(.v15)
    ],
    products: [
        .library(
            name: "PythonMobile",
            targets: ["PythonMobile"]
        ),
    ],
    targets: [
        .binaryTarget(
            name: "Python",
            url: "https://cdn.9228.eu/python/Python-3.14.xcframework.zip",
            checksum: "8e8ca477adab72cf08d7c7ccdca63df129d534ef7920747acc2e8000a2e05ff5"
        ),
        .target(
            name: "PythonMobile",
            dependencies: ["Python"],
            resources: [
                .copy("Resources/lib")
            ]
        ),
        .testTarget(
            name: "PythonMobileTests",
            dependencies: ["PythonMobile"]
        ),
    ]
)
