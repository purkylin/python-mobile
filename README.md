# PythonMobile 🐍📱

A lightweight, modern, Swift 6 native **CPython 3.15 embedded runtime** for **iOS 18+** and **macOS 15+**.

## Features

- 🚀 **CPython 3.15 Isolation**: Uses official `PyConfig` isolated configuration inside the iOS Sandbox.
- 📦 **Remote Binary Target**: Automatically downloads and links `Python.xcframework` via Swift Package Manager.
- 🛡️ **Thread Safety & Crash Protection**: Built-in mutex locking and error stack trace capture.
- 🔒 **Zero String Escaping Issues**: Base64 encoded IPC eliminates syntax warnings and escaping errors.
- 📚 **Bundled Standard Library**: Full Python standard library (`json`, `urllib`, `encodings`, `math`, `ctypes`, etc.).

---

## Installation

### Swift Package Manager

Add the package dependency to your `Package.swift`:

```swift
dependencies: [
    .package(url: "https://github.com/your-username/python-mobile.git", from: "1.0.0")
],
targets: [
    .target(
        name: "YourApp",
        dependencies: [
            .product(name: "PythonMobile", package: "python-mobile")
        ]
    )
]
```

Or in Xcode: **File** -> **Add Package Dependencies...** -> Enter repository URL.

---

## Quick Start

### 1. Evaluate Python Expressions

```swift
import PythonMobile

let answer = try PythonEngine.shared.eval("21 * 2")
print(answer) // "42"
```

### 2. Execute Python Scripts

```swift
try PythonEngine.shared.runCode("""
import math
print("Square root of 256:", math.sqrt(256))
""")
```

### 3. Load Dynamic Modules and Call Functions

```swift
let script = """
def process_user(name, age):
    return {
        "status": "ok",
        "greeting": f"Hello {name}, you are {age} years old!"
    }
"""

// Load module dynamically
try PythonEngine.shared.loadModule(name: "user_service", code: script)

// Call Python function with Swift parameters
let result = try PythonEngine.shared.call(
    module: "user_service",
    function: "process_user",
    args: ["Alice", 28]
)

print(result) // ["status": "ok", "greeting": "Hello Alice, you are 28 years old!"]
```

---

## License

MIT License. Includes CPython 3.15 licensed under the Python Software Foundation License.
