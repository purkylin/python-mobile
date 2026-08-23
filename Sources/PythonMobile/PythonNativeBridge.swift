import Foundation
import Python

public final class PythonCacheStore: @unchecked Sendable {
    public static let shared = PythonCacheStore()

    public var proxyURLProvider: (@Sendable (_ site: String) -> String)?

    private let lock = NSLock()
    private var memoryCache: [String: (value: String, expiresAt: Double?)] = [:]
    private let cacheDirectory: URL

    private init() {
        let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory())
        self.cacheDirectory = base.appendingPathComponent("tvbox_spider_cache", isDirectory: true)
        try? FileManager.default.createDirectory(at: cacheDirectory, withIntermediateDirectories: true)
    }

    public func set(key: String, value: String) {
        guard !key.isEmpty else { return }
        lock.lock()
        defer { lock.unlock() }

        var expiresAt: Double? = nil
        if let data = value.data(using: .utf8),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let exp = json["expiresAt"] {
            if let num = exp as? NSNumber {
                var val = num.doubleValue
                if val > 1_000_000_000_000 { val /= 1000.0 }
                expiresAt = val
            } else if let str = exp as? String, let val = Double(str) {
                var v = val
                if v > 1_000_000_000_000 { v /= 1000.0 }
                expiresAt = v
            }
        }

        memoryCache[key] = (value, expiresAt)

        let fileURL = cacheFileURL(for: key)
        try? value.write(to: fileURL, atomically: true, encoding: .utf8)
    }

    public func get(key: String) -> String? {
        guard !key.isEmpty else { return nil }
        lock.lock()
        defer { lock.unlock() }

        let now = Date().timeIntervalSince1970

        if let entry = memoryCache[key] {
            if let exp = entry.expiresAt, now > exp {
                memoryCache.removeValue(forKey: key)
                try? FileManager.default.removeItem(at: cacheFileURL(for: key))
                return nil
            }
            return entry.value
        }

        let fileURL = cacheFileURL(for: key)
        guard let data = try? Data(contentsOf: fileURL),
              let string = String(data: data, encoding: .utf8) else {
            return nil
        }

        var expiresAt: Double? = nil
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let exp = json["expiresAt"] {
            if let num = exp as? NSNumber {
                var val = num.doubleValue
                if val > 1_000_000_000_000 { val /= 1000.0 }
                expiresAt = val
            } else if let str = exp as? String, let val = Double(str) {
                var v = val
                if v > 1_000_000_000_000 { v /= 1000.0 }
                expiresAt = v
            }
        }

        if let exp = expiresAt, now > exp {
            try? FileManager.default.removeItem(at: fileURL)
            return nil
        }

        memoryCache[key] = (string, expiresAt)
        return string
    }

    public func delete(key: String) {
        guard !key.isEmpty else { return }
        lock.lock()
        defer { lock.unlock() }

        memoryCache.removeValue(forKey: key)
        try? FileManager.default.removeItem(at: cacheFileURL(for: key))
    }

    public func clear() {
        lock.lock()
        defer { lock.unlock() }

        memoryCache.removeAll()
        try? FileManager.default.removeItem(at: cacheDirectory)
        try? FileManager.default.createDirectory(at: cacheDirectory, withIntermediateDirectories: true)
    }

    public func getProxyURL(site: String) -> String {
        if let provider = proxyURLProvider {
            return provider(site)
        }
        return "http://127.0.0.1:9978/proxy?do=py&site=\(site)"
    }

    private func cacheFileURL(for key: String) -> URL {
        let safeName = key.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? key
        return cacheDirectory.appendingPathComponent("\(safeName).json")
    }
}

private func tvboxNativeCacheSet(
    _ module: UnsafeMutablePointer<PyObject>?,
    _ args: UnsafeMutablePointer<PyObject>?
) -> UnsafeMutablePointer<PyObject>? {
    guard let args,
          PyTuple_Size(args) >= 2,
          let keyObj = PyTuple_GetItem(args, 0),
          let valObj = PyTuple_GetItem(args, 1),
          let keyPtr = PyUnicode_AsUTF8(keyObj),
          let valPtr = PyUnicode_AsUTF8(valObj) else {
        return PyBool_FromLong(0)
    }
    let key = String(cString: keyPtr)
    let value = String(cString: valPtr)
    PythonCacheStore.shared.set(key: key, value: value)
    return PyBool_FromLong(1)
}

private func tvboxNativeCacheGet(
    _ module: UnsafeMutablePointer<PyObject>?,
    _ args: UnsafeMutablePointer<PyObject>?
) -> UnsafeMutablePointer<PyObject>? {
    guard let args,
          PyTuple_Size(args) >= 1,
          let keyObj = PyTuple_GetItem(args, 0),
          let keyPtr = PyUnicode_AsUTF8(keyObj) else {
        return PyUnicode_FromString("")
    }
    let key = String(cString: keyPtr)
    if let result = PythonCacheStore.shared.get(key: key) {
        return PyUnicode_FromString(result)
    }
    return PyUnicode_FromString("")
}

private func tvboxNativeCacheDel(
    _ module: UnsafeMutablePointer<PyObject>?,
    _ args: UnsafeMutablePointer<PyObject>?
) -> UnsafeMutablePointer<PyObject>? {
    guard let args,
          PyTuple_Size(args) >= 1,
          let keyObj = PyTuple_GetItem(args, 0),
          let keyPtr = PyUnicode_AsUTF8(keyObj) else {
        return PyBool_FromLong(0)
    }
    let key = String(cString: keyPtr)
    PythonCacheStore.shared.delete(key: key)
    return PyBool_FromLong(1)
}

private func tvboxNativeCacheClear(
    _ module: UnsafeMutablePointer<PyObject>?,
    _ args: UnsafeMutablePointer<PyObject>?
) -> UnsafeMutablePointer<PyObject>? {
    PythonCacheStore.shared.clear()
    return PyBool_FromLong(1)
}

private func tvboxNativeGetProxyURL(
    _ module: UnsafeMutablePointer<PyObject>?,
    _ args: UnsafeMutablePointer<PyObject>?
) -> UnsafeMutablePointer<PyObject>? {
    var site = "spider"
    if let args, PyTuple_Size(args) >= 1,
       let siteObj = PyTuple_GetItem(args, 0),
       let sitePtr = PyUnicode_AsUTF8(siteObj) {
        site = String(cString: sitePtr)
    }
    let url = PythonCacheStore.shared.getProxyURL(site: site)
    return PyUnicode_FromString(url)
}

nonisolated(unsafe) private let tvboxCacheSetName: UnsafeMutablePointer<CChar> = {
    let name = "cache_set"
    let ptr = UnsafeMutablePointer<CChar>.allocate(capacity: name.utf8.count + 1)
    ptr.initialize(from: Array(name.utf8CString), count: name.utf8.count + 1)
    return ptr
}()

nonisolated(unsafe) private let tvboxCacheGetName: UnsafeMutablePointer<CChar> = {
    let name = "cache_get"
    let ptr = UnsafeMutablePointer<CChar>.allocate(capacity: name.utf8.count + 1)
    ptr.initialize(from: Array(name.utf8CString), count: name.utf8.count + 1)
    return ptr
}()

nonisolated(unsafe) private let tvboxCacheDelName: UnsafeMutablePointer<CChar> = {
    let name = "cache_del"
    let ptr = UnsafeMutablePointer<CChar>.allocate(capacity: name.utf8.count + 1)
    ptr.initialize(from: Array(name.utf8CString), count: name.utf8.count + 1)
    return ptr
}()

nonisolated(unsafe) private let tvboxCacheClearName: UnsafeMutablePointer<CChar> = {
    let name = "cache_clear"
    let ptr = UnsafeMutablePointer<CChar>.allocate(capacity: name.utf8.count + 1)
    ptr.initialize(from: Array(name.utf8CString), count: name.utf8.count + 1)
    return ptr
}()

nonisolated(unsafe) private let tvboxGetProxyURLName: UnsafeMutablePointer<CChar> = {
    let name = "get_proxy_url"
    let ptr = UnsafeMutablePointer<CChar>.allocate(capacity: name.utf8.count + 1)
    ptr.initialize(from: Array(name.utf8CString), count: name.utf8.count + 1)
    return ptr
}()

nonisolated(unsafe) private var tvboxCacheSetMethod = PyMethodDef(
    ml_name: UnsafePointer(tvboxCacheSetName),
    ml_meth: tvboxNativeCacheSet,
    ml_flags: Int32(METH_VARARGS),
    ml_doc: nil
)

nonisolated(unsafe) private var tvboxCacheGetMethod = PyMethodDef(
    ml_name: UnsafePointer(tvboxCacheGetName),
    ml_meth: tvboxNativeCacheGet,
    ml_flags: Int32(METH_VARARGS),
    ml_doc: nil
)

nonisolated(unsafe) private var tvboxCacheDelMethod = PyMethodDef(
    ml_name: UnsafePointer(tvboxCacheDelName),
    ml_meth: tvboxNativeCacheDel,
    ml_flags: Int32(METH_VARARGS),
    ml_doc: nil
)

nonisolated(unsafe) private var tvboxCacheClearMethod = PyMethodDef(
    ml_name: UnsafePointer(tvboxCacheClearName),
    ml_meth: tvboxNativeCacheClear,
    ml_flags: Int32(METH_VARARGS),
    ml_doc: nil
)

nonisolated(unsafe) private var tvboxGetProxyURLMethod = PyMethodDef(
    ml_name: UnsafePointer(tvboxGetProxyURLName),
    ml_meth: tvboxNativeGetProxyURL,
    ml_flags: Int32(METH_VARARGS),
    ml_doc: nil
)

public enum TVBoxNativeBridge {
    public static func install() {
        guard let module = PyModule_New("_tvbox_native") else { return }

        if let function = PyCFunction_NewEx(&tvboxCacheSetMethod, module, nil) {
            _ = PyObject_SetAttrString(module, "cache_set", function)
            Py_DecRef(function)
        }
        if let function = PyCFunction_NewEx(&tvboxCacheGetMethod, module, nil) {
            _ = PyObject_SetAttrString(module, "cache_get", function)
            Py_DecRef(function)
        }
        if let function = PyCFunction_NewEx(&tvboxCacheDelMethod, module, nil) {
            _ = PyObject_SetAttrString(module, "cache_del", function)
            Py_DecRef(function)
        }
        if let function = PyCFunction_NewEx(&tvboxCacheClearMethod, module, nil) {
            _ = PyObject_SetAttrString(module, "cache_clear", function)
            Py_DecRef(function)
        }
        if let function = PyCFunction_NewEx(&tvboxGetProxyURLMethod, module, nil) {
            _ = PyObject_SetAttrString(module, "get_proxy_url", function)
            Py_DecRef(function)
        }

        guard let modules = PyImport_GetModuleDict() else {
            Py_DecRef(module)
            return
        }
        _ = PyDict_SetItemString(modules, "_tvbox_native", module)
        Py_DecRef(module)
    }
}
