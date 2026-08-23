import Foundation
import Python

private typealias TVBoxPythonFunction = @convention(c) (
    UnsafeMutablePointer<PyObject>?,
    UnsafeMutablePointer<PyObject>?
) -> UnsafeMutablePointer<PyObject>?

private final class TVBoxHTTPResultBox: @unchecked Sendable {
    var data: Data?
    var response: HTTPURLResponse?
    var error: Error?
}

private enum TVBoxHTTPTransport {
    static func request(_ payload: String) -> String {
        guard let payloadData = payload.data(using: .utf8),
              let jsonObject = try? JSONSerialization.jsonObject(with: payloadData),
              let values = jsonObject as? [String: Any],
              let urlString = values["url"] as? String,
              let url = URL(string: urlString) else {
            return failure("Invalid HTTP request payload")
        }

        var request = URLRequest(url: url)
        request.httpMethod = (values["method"] as? String ?? "GET").uppercased()
        request.timeoutInterval = timeout(from: values["timeout"])

        if let headers = values["headers"] as? [String: String] {
            for (key, value) in headers {
                request.setValue(value, forHTTPHeaderField: key)
            }
        }
        if let body = values["body"] as? String {
            request.httpBody = Data(base64Encoded: body)
        }

        let requestID = String(UUID().uuidString.prefix(8))
        let method = request.httpMethod ?? "GET"
        let start = Date()
        print("[TVBox HTTP] \(requestID) -> \(method) \(urlString) timeout=\(Int(request.timeoutInterval))s")
        let result = TVBoxHTTPResultBox()
        let semaphore = DispatchSemaphore(value: 0)
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            result.data = data
            result.response = response as? HTTPURLResponse
            result.error = error
            let elapsed = Int(Date().timeIntervalSince(start))
            if let error {
                print("[TVBox HTTP] \(requestID) !! failed after \(elapsed)s: \(error.localizedDescription)")
            } else {
                print("[TVBox HTTP] \(requestID) <- status=\(result.response?.statusCode ?? 0) elapsed=\(elapsed)s")
            }
            semaphore.signal()
        }
        task.resume()

        let waitResult = semaphore.wait(timeout: .now() + request.timeoutInterval)
        guard waitResult == .success else {
            task.cancel()
            print("[TVBox HTTP] \(requestID) !! timeout after \(Int(Date().timeIntervalSince(start)))s")
            return failure("HTTP request timed out")
        }
        if let error = result.error {
            print("[TVBox HTTP] \(requestID) !! failed: \(error.localizedDescription)")
            return failure(error.localizedDescription)
        }
        guard let response = result.response, let data = result.data else {
            print("[TVBox HTTP] \(requestID) !! empty response")
            return failure("HTTP response was empty")
        }

        let headers = response.allHeaderFields.reduce(into: [String: String]()) { output, item in
            output[String(describing: item.key)] = String(describing: item.value)
        }
        let value: [String: Any] = [
            "ok": true,
            "status_code": response.statusCode,
            "url": response.url?.absoluteString ?? urlString,
            "headers": headers,
            "body": data.base64EncodedString()
        ]
        guard let encoded = try? JSONSerialization.data(withJSONObject: value),
              let resultString = String(data: encoded, encoding: .utf8) else {
            return failure("Failed to encode HTTP response")
        }
        return resultString
    }

    private static func timeout(from value: Any?) -> TimeInterval {
        let seconds = (value as? NSNumber)?.doubleValue ?? 15
        return max(0.1, min(seconds, 15))
    }

    private static func failure(_ message: String) -> String {
        let value: [String: Any] = ["ok": false, "error": message]
        guard let data = try? JSONSerialization.data(withJSONObject: value),
              let result = String(data: data, encoding: .utf8) else {
            return "{\"ok\":false,\"error\":\"HTTP request failed\"}"
        }
        return result
    }
}

private func tvboxHTTPRequest(
    _ module: UnsafeMutablePointer<PyObject>?,
    _ args: UnsafeMutablePointer<PyObject>?
) -> UnsafeMutablePointer<PyObject>? {
    guard let args,
          let payloadObject = PyTuple_GetItem(args, 0),
          let payloadPointer = PyUnicode_AsUTF8(payloadObject) else {
        return nil
    }
    let payload = String(cString: payloadPointer)
    return PyUnicode_FromString(TVBoxHTTPTransport.request(payload))
}

nonisolated(unsafe) private let tvboxHTTPMethodName: UnsafeMutablePointer<CChar> = {
    let pointer = UnsafeMutablePointer<CChar>.allocate(capacity: 19)
    pointer.initialize(from: Array("_tvbox_http_request".utf8CString), count: 19)
    return pointer
}()

nonisolated(unsafe) private var tvboxHTTPMethod = PyMethodDef(
    ml_name: UnsafePointer(tvboxHTTPMethodName),
    ml_meth: tvboxHTTPRequest,
    ml_flags: Int32(METH_VARARGS),
    ml_doc: nil
)

enum TVBoxHTTPBridge {
    static func install() {
        guard let module = PyModule_New("_tvbox_http"),
              let function = PyCFunction_NewEx(&tvboxHTTPMethod, module, nil) else {
            return
        }
        _ = PyObject_SetAttrString(module, "request", function)
        Py_DecRef(function)

        guard let modules = PyImport_GetModuleDict() else {
            Py_DecRef(module)
            return
        }
        _ = PyDict_SetItemString(modules, "_tvbox_http", module)
        Py_DecRef(module)
    }
}
