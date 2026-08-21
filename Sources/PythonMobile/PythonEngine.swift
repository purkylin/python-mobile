import Foundation
import Python

public final class PythonEngine: @unchecked Sendable {
    public static let shared = PythonEngine()

    private let lock = NSLock()
    private var isInitialized = false

    private init() {}

    /// Initializes the embedded Python runtime inside the sandbox.
    public func ensureInitialized() throws {
        lock.lock()
        defer { lock.unlock() }

        guard !isInitialized else { return }

        guard let libPath = resolveStandardLibraryPath() else {
            throw PythonError.runtimeUnavailable("Missing Python standard library resources in Bundle")
        }

        var preconfig = PyPreConfig()
        PyPreConfig_InitIsolatedConfig(&preconfig)
        preconfig.utf8_mode = 1
        _ = Py_PreInitialize(&preconfig)

        var config = PyConfig()
        PyConfig_InitIsolatedConfig(&config)

        let pythonHome = (libPath as NSString).deletingLastPathComponent
        if let wHome = Py_DecodeLocale(pythonHome, nil) {
            withUnsafeMutablePointer(to: &config) { ptr in
                _ = PyConfig_SetString(ptr, &ptr.pointee.home, wHome)
            }
            PyMem_RawFree(wHome)
        }

        let stdlibPath = "\(libPath)/python3.14"
        let dynloadPath = "\(libPath)/python3.14/lib-dynload"

        config.module_search_paths_set = 1
        for path in [stdlibPath, dynloadPath, pythonHome] {
            if let wPath = Py_DecodeLocale(path, nil) {
                _ = withUnsafeMutablePointer(to: &config.module_search_paths) { listPtr in
                    PyWideStringList_Append(listPtr, wPath)
                }
                PyMem_RawFree(wPath)
            }
        }

        let status = Py_InitializeFromConfig(&config)
        if PyStatus_Exception(status) != 0 {
            let errorMsg = status.err_msg.map { String(cString: $0) } ?? "Unknown error"
            PyConfig_Clear(&config)
            throw PythonError.initializationFailed(errorMsg)
        }
        PyConfig_Clear(&config)

        // Setup warning filters and base utilities
        _ = PyRun_SimpleString("""
        import warnings, sys
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        """)

        isInitialized = true
    }

    /// Executes raw Python statements.
    public func runCode(_ code: String) throws {
        try ensureInitialized()

        lock.lock()
        defer { lock.unlock() }

        let gstate = PyGILState_Ensure()
        defer { PyGILState_Release(gstate) }

        guard PyRun_SimpleString(code) == 0 else {
            throw PythonError.executionFailed("Failed to execute Python statement")
        }
    }

    /// Evaluates a Python expression and returns its string result.
    public func eval(_ expression: String) throws -> String {
        try ensureInitialized()

        lock.lock()
        defer { lock.unlock() }

        let gstate = PyGILState_Ensure()
        defer { PyGILState_Release(gstate) }

        let exprB64 = Data(expression.utf8).base64EncodedString()
        let script = """
        import base64
        __expr = base64.b64decode('\(exprB64)').decode('utf-8')
        __result__ = str(eval(__expr))
        """

        return try executeStatementAndGetResult(script)
    }

    /// Dynamically loads a Python module from source code into sys.modules.
    public func loadModule(name: String, code: String) throws {
        try ensureInitialized()

        lock.lock()
        defer { lock.unlock() }

        let gstate = PyGILState_Ensure()
        defer { PyGILState_Release(gstate) }

        let nameB64 = Data(name.utf8).base64EncodedString()
        let codeB64 = Data(code.utf8).base64EncodedString()

        let script = """
        import sys, types, base64, traceback
        __mod_name = base64.b64decode('\(nameB64)').decode('utf-8')
        __mod_code = base64.b64decode('\(codeB64)').decode('utf-8')

        __mod = types.ModuleType(__mod_name)
        __mod.__file__ = f"<module_{__mod_name}>"
        exec(compile(__mod_code, __mod.__file__, "exec"), __mod.__dict__)
        sys.modules[__mod_name] = __mod
        """

        guard PyRun_SimpleString(script) == 0 else {
            throw PythonError.executionFailed("Failed to load module '\(name)'")
        }
    }

    /// Calls a function in a loaded module with Base64 encoded JSON parameters.
    public func call(module: String, function: String, args: [Any] = []) throws -> Any? {
        try ensureInitialized()

        lock.lock()
        defer { lock.unlock() }

        let gstate = PyGILState_Ensure()
        defer { PyGILState_Release(gstate) }

        let argsData = (try? JSONSerialization.data(withJSONObject: args)) ?? Data("[]".utf8)
        let modB64 = Data(module.utf8).base64EncodedString()
        let funcB64 = Data(function.utf8).base64EncodedString()
        let argsB64 = argsData.base64EncodedString()

        let script = """
        import sys, json, base64, traceback
        __m_name = base64.b64decode('\(modB64)').decode('utf-8')
        __f_name = base64.b64decode('\(funcB64)').decode('utf-8')
        __a_json = base64.b64decode('\(argsB64)').decode('utf-8')

        __mod = sys.modules.get(__m_name)
        if __mod is None:
            try:
                import importlib
                __mod = importlib.import_module(__m_name)
            except Exception:
                __mod = None

        if __mod is None:
            __result__ = json.dumps({"__error__": f"Module '{__m_name}' could not be loaded"})
        else:
            __fn = getattr(__mod, __f_name, None)
            if __fn is None or not callable(__fn):
                __result__ = json.dumps({"__error__": f"Function '{__f_name}' not found in module '{__m_name}'"})
            else:
                try:
                    __args = json.loads(__a_json)
                    if isinstance(__args, list):
                        __res = __fn(*__args)
                    elif isinstance(__args, dict):
                        __res = __fn(**__args)
                    else:
                        __res = __fn(__args)

                    if isinstance(__res, str):
                        __result__ = __res
                    else:
                        __result__ = json.dumps(__res, ensure_ascii=False)
                except Exception as e:
                    __result__ = json.dumps({"__error__": str(e), "__traceback__": traceback.format_exc()})
        """

        let resultString = try executeStatementAndGetResult(script)
        if let data = resultString.data(using: .utf8),
           let json = try? JSONSerialization.jsonObject(with: data) {
            if let dict = json as? [String: Any], let error = dict["__error__"] as? String {
                throw PythonError.executionFailed(error)
            }
            return json
        }

        return resultString
    }

    /// Appends a custom directory to sys.path.
    public func addModulePath(_ path: String) throws {
        try ensureInitialized()

        lock.lock()
        defer { lock.unlock() }

        let pathB64 = Data(path.utf8).base64EncodedString()
        let script = """
        import sys, base64
        __p = base64.b64decode('\(pathB64)').decode('utf-8')
        if __p not in sys.path:
            sys.path.insert(0, __p)
        """
        guard PyRun_SimpleString(script) == 0 else {
            throw PythonError.executionFailed("Failed to append module path: \(path)")
        }
    }

    // MARK: - Private Helpers

    private func executeStatementAndGetResult(_ code: String) throws -> String {
        guard PyRun_SimpleString(code) == 0 else {
            throw PythonError.executionFailed("Failed to execute Python script")
        }

        guard let mainMod = PyImport_AddModule("__main__"),
              let mainDict = PyModule_GetDict(mainMod),
              let resultObj = PyDict_GetItemString(mainDict, "__result__") else {
            throw PythonError.invalidResponse("Failed to read __result__ from Python runtime")
        }

        guard let utf8 = PyUnicode_AsUTF8(resultObj) else {
            throw PythonError.invalidResponse("Python __result__ is not a valid UTF8 string")
        }

        return String(cString: utf8)
    }

    private func resolveStandardLibraryPath() -> String? {
        #if SWIFT_PACKAGE
        if let modulePath = Bundle.module.path(forResource: "lib", ofType: nil) {
            return modulePath
        }
        if let resPath = Bundle.module.resourcePath {
            let direct = "\(resPath)/lib"
            if FileManager.default.fileExists(atPath: direct) {
                return direct
            }
        }
        #endif

        if let mainPath = Bundle.main.path(forResource: "lib", ofType: nil) {
            return mainPath
        }

        if let pythonHome = Bundle.main.path(forResource: "python", ofType: nil) {
            return "\(pythonHome)/lib"
        }

        return nil
    }
}
