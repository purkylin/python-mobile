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
            url: "https://cdn.9228.eu/python/Python-3.15.0rc1.zip",
            checksum: "2ea949a624230de7f2c1ab99454e412d042792d7df06912ad02602abd6dac6b4"
        ),
        .target(
            name: "PythonMobile",
            dependencies: ["Python"],
            resources: [
                .copy("Resources/site-packages")
            ]
        ),
        .testTarget(
            name: "PythonMobileTests",
            dependencies: ["PythonMobile"]
        ),
    ]
)
