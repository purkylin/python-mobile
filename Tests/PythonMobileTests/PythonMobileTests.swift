import Testing
@testable import PythonMobile

@Suite("PythonMobile Tests", .serialized)
struct PythonMobileTests {

    @Test("Python evaluation")
    func testEvaluation() throws {
        let result = try PythonEngine.shared.eval("21 * 2")
        #expect(result == "42")
    }

    @Test("Standard library imports")
    func testStandardLibrary() throws {
        try PythonEngine.shared.runCode("""
        import json
        import math
        import urllib.parse
        import encodings
        assert math.sqrt(16) == 4.0
        """)
    }

    @Test("Dynamic module loading and calling")
    func testModuleLoadingAndCall() throws {
        let pythonCode = """
        def multiply(a, b):
            return {"result": a * b, "operation": "multiply"}
        """

        try PythonEngine.shared.loadModule(name: "calc", code: pythonCode)
        let response = try PythonEngine.shared.call(module: "calc", function: "multiply", args: [6, 7])

        guard let dict = response as? [String: Any] else {
            Issue.record("Expected dictionary response")
            return
        }

        #expect(dict["result"] as? Int == 42)
        #expect(dict["operation"] as? String == "multiply")
    }
}
