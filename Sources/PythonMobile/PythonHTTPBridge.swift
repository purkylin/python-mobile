import Foundation
import Python
#if canImport(WebKit)
import WebKit
#endif

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
        let hasVerifiedWebSession = applyStoredWebSession(to: &request, for: url)
        if let body = values["body"] as? String {
            request.httpBody = Data(base64Encoded: body)
        }

        let requestID = String(UUID().uuidString.prefix(8))
        let method = request.httpMethod ?? "GET"
        let start = Date()
        if shouldUseWebKitDirectly(for: request, url: url, hasSession: hasVerifiedWebSession),
           let directResponse = webKitResponse(for: request) {
            print(
                "[TVBox HTTP] \(requestID) <- WebKit direct status=\(directResponse.response.statusCode) "
                + "bytes=\(directResponse.data.count)"
            )
            return encodeResponse(
                directResponse.response,
                data: directResponse.data,
                urlString: urlString,
                fallbackURL: url,
                request: request
            )
        }
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
                print(
                    "[TVBox HTTP] \(requestID) <- status=\(result.response?.statusCode ?? 0) "
                    + "bytes=\(data?.count ?? 0) elapsed=\(elapsed)s"
                )
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
            if let certificateError = certificateError(from: error) {
                return failure(
                    certificateError.message,
                    errorType: "SSLError",
                    errorCode: certificateError.code
                )
            }
            return failure(error.localizedDescription)
        }
        guard var response = result.response, var data = result.data else {
            print("[TVBox HTTP] \(requestID) !! empty response")
            return failure("HTTP response was empty")
        }

        var blockedPage = blockedPageEvidence(response: response, data: data)
        if blockedPage != nil,
           hasVerifiedWebSession,
           let fallback = webKitResponse(for: request) {
            response = fallback.response
            data = fallback.data
            blockedPage = blockedPageEvidence(response: response, data: data)
            if blockedPage == nil {
                markWebKitPreferred(for: url)
            }
            print(
                "[TVBox HTTP] \(requestID) WebKit fallback status=\(response.statusCode) "
                + "bytes=\(data.count) blocked=\(blockedPage != nil)"
            )
        }
        return encodeResponse(
            response,
            data: data,
            urlString: urlString,
            fallbackURL: url,
            request: request
        )
    }

    private static func blockedPageEvidence(
        response: HTTPURLResponse,
        data: Data
    ) -> String? {
        let body = String(decoding: data, as: UTF8.self).lowercased()
        if body.contains("<title>just a moment...</title>") {
            return "verification page title 'just a moment...'"
        }
        return nil
    }

    private static func timeout(from value: Any?) -> TimeInterval {
        let seconds = (value as? NSNumber)?.doubleValue ?? 15
        return max(0.1, min(seconds, 15))
    }

    private static func applyStoredWebSession(to request: inout URLRequest, for url: URL) -> Bool {
        guard let host = url.host?.lowercased() else { return false }
        let prefix = "tvbox.webSession.\(host)"
        let defaults = UserDefaults.standard
        guard let userAgent = defaults.string(forKey: "\(prefix).userAgent"),
              !userAgent.isEmpty else {
            return false
        }

        request.setValue(userAgent, forHTTPHeaderField: "User-Agent")
        if let cookie = defaults.string(forKey: "\(prefix).cookie"),
           !cookie.isEmpty {
            request.setValue(cookie, forHTTPHeaderField: "Cookie")
            print("[TVBox HTTP] applying verified web session host=\(host)")
            return true
        }
        return false
    }

    private static func shouldUseWebKitDirectly(
        for request: URLRequest,
        url: URL,
        hasSession: Bool
    ) -> Bool {
        guard hasSession,
              request.httpMethod == "GET",
              let host = url.host?.lowercased() else {
            return false
        }
        return UserDefaults.standard.bool(
            forKey: "tvbox.webSession.\(host).prefersWebKit"
        )
    }

    private static func markWebKitPreferred(for url: URL) {
        guard let host = url.host?.lowercased() else { return }
        UserDefaults.standard.set(
            true,
            forKey: "tvbox.webSession.\(host).prefersWebKit"
        )
    }

    private static func webKitResponse(for request: URLRequest) -> TVBoxWebKitResult? {
        #if canImport(WebKit)
        print("[TVBox HTTP] starting WebKit request main=\(Thread.isMainThread)")
        if Thread.isMainThread {
            return MainActor.assumeIsolated {
                webKitResponseOnMain(for: request)
            }
        }
        let resultBox = TVBoxWebKitResultBox()
        let semaphore = DispatchSemaphore(value: 0)
        DispatchQueue.main.async {
            let loader = TVBoxWebKitLoader(request: request) { result in
                resultBox.result = result
                resultBox.isComplete = true
                semaphore.signal()
            }
            resultBox.loader = loader
            loader.start()
        }
        let waitResult = semaphore.wait(timeout: .now() + request.timeoutInterval)
        DispatchQueue.main.async {
            resultBox.loader?.cancel()
            resultBox.loader = nil
        }
        return waitResult == .success ? resultBox.result : nil
        #else
        return nil
        #endif
    }

    #if canImport(WebKit)
    @MainActor
    private static func webKitResponseOnMain(for request: URLRequest) -> TVBoxWebKitResult? {
        let resultBox = TVBoxWebKitResultBox()
        let loader = TVBoxWebKitLoader(request: request) { result in
            resultBox.result = result
            resultBox.isComplete = true
        }
        resultBox.loader = loader
        loader.start()

        let deadline = Date().addingTimeInterval(request.timeoutInterval)
        while !resultBox.isComplete, Date() < deadline {
            RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.02))
        }
        loader.cancel()
        return resultBox.result
    }
    #endif

    private static func encodeResponse(
        _ response: HTTPURLResponse,
        data: Data,
        urlString: String,
        fallbackURL: URL,
        request: URLRequest
    ) -> String {
        if let evidence = blockedPageEvidence(response: response, data: data) {
            postVerificationRequest(
                evidence: evidence,
                url: response.url ?? fallbackURL,
                userAgent: request.value(forHTTPHeaderField: "User-Agent") ?? ""
            )
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
              let result = String(data: encoded, encoding: .utf8) else {
            return failure("Failed to encode HTTP response")
        }
        return result
    }

    private static func postVerificationRequest(
        evidence: String,
        url: URL,
        userAgent: String
    ) {
        print("[TVBox HTTP] verification required reason=\(evidence) url=\(url.absoluteString)")
        DispatchQueue.main.async {
            NotificationCenter.default.post(
                name: Notification.Name("openSafari"),
                object: nil,
                userInfo: [
                    "url": url,
                    "tvboxChallenge": true,
                    "userAgent": userAgent
                ]
            )
        }
    }

    private static func certificateError(from error: Error) -> (code: Int, message: String)? {
        let nsError = error as NSError
        guard nsError.domain == NSURLErrorDomain else {
            return nil
        }
        let code = URLError.Code(rawValue: nsError.code)
        let message = nsError.localizedDescription
        switch code {
        case .serverCertificateHasBadDate,
             .serverCertificateUntrusted,
             .serverCertificateHasUnknownRoot,
             .serverCertificateNotYetValid,
             .secureConnectionFailed:
            break
        default:
            return nil
        }
        return (nsError.code, message)
    }

    private static func failure(
        _ message: String,
        errorType: String? = nil,
        errorCode: Int? = nil
    ) -> String {
        var value: [String: Any] = ["ok": false, "error": message]
        if let errorType {
            value["error_type"] = errorType
        }
        if let errorCode {
            value["error_code"] = errorCode
        }
        guard let data = try? JSONSerialization.data(withJSONObject: value),
              let result = String(data: data, encoding: .utf8) else {
            return "{\"ok\":false,\"error\":\"HTTP request failed\"}"
        }
        return result
    }
}

#if canImport(WebKit)
private struct TVBoxWebKitResult: @unchecked Sendable {
    let data: Data
    let response: HTTPURLResponse
}

private final class TVBoxWebKitResultBox: @unchecked Sendable {
    var result: TVBoxWebKitResult?
    var loader: TVBoxWebKitLoader?
    var isComplete = false
}

@MainActor
private final class TVBoxWebKitLoader: NSObject, WKNavigationDelegate {
    private let request: URLRequest
    private let completion: (TVBoxWebKitResult?) -> Void
    private var webView: WKWebView?
    private var isComplete = false

    init(request: URLRequest, completion: @escaping (TVBoxWebKitResult?) -> Void) {
        self.request = request
        self.completion = completion
    }

    func start() {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.customUserAgent = request.value(forHTTPHeaderField: "User-Agent")
        webView.navigationDelegate = self
        self.webView = webView
        webView.load(request)
    }

    func cancel() {
        webView?.stopLoading()
        finish(nil)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        webView.evaluateJavaScript("document.documentElement.outerHTML") { [weak self] value, error in
            guard let self,
                  let html = value as? String,
                  let data = html.data(using: .utf8),
                  let url = webView.url ?? self.request.url,
                  let response = HTTPURLResponse(
                    url: url,
                    statusCode: 200,
                    httpVersion: nil,
                    headerFields: ["Content-Type": "text/html; charset=utf-8"]
                  ) else {
                print(
                    "[TVBox HTTP] WebKit fallback could not read page HTML: "
                    + (error?.localizedDescription ?? "unknown error")
                )
                self?.finish(nil)
                return
            }
            self.finish(TVBoxWebKitResult(data: data, response: response))
        }
    }

    func webView(
        _ webView: WKWebView,
        didFail navigation: WKNavigation!,
        withError error: Error
    ) {
        print("[TVBox HTTP] WebKit fallback navigation failed: \(error.localizedDescription)")
        finish(nil)
    }

    func webView(
        _ webView: WKWebView,
        didFailProvisionalNavigation navigation: WKNavigation!,
        withError error: Error
    ) {
        print("[TVBox HTTP] WebKit fallback provisional navigation failed: \(error.localizedDescription)")
        finish(nil)
    }

    private func finish(_ result: TVBoxWebKitResult?) {
        guard !isComplete else { return }
        isComplete = true
        webView?.navigationDelegate = nil
        webView = nil
        completion(result)
    }
}
#else
private struct TVBoxWebKitResult: Sendable {
    let data: Data
    let response: HTTPURLResponse
}
#endif

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
