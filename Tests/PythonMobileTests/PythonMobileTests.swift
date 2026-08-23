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

    @Test("typing_extensions presence")
    func testTypingExtensions() throws {
        try PythonEngine.shared.runCode("""
        import typing_extensions
        from typing_extensions import override, Self
        """)
    }

    @Test("bs4 BeautifulSoup with lxml and html.parser features")
    func testBeautifulSoupWithVariousFeatures() throws {
        try PythonEngine.shared.runCode("""
        from bs4 import BeautifulSoup

        html_doc = "<html><body><div class='title'>Hello TVBox</div></body></html>"

        # 1. Specified 'lxml' (automatically routed to html.parser)
        s1 = BeautifulSoup(html_doc, 'lxml')
        assert s1.find('div', class_='title').text == "Hello TVBox"

        # 2. Specified 'html.parser'
        s2 = BeautifulSoup(html_doc, 'html.parser')
        assert s2.find('div', class_='title').text == "Hello TVBox"

        # 3. Default (no feature argument)
        s3 = BeautifulSoup(html_doc)
        assert s3.find('div', class_='title').text == "Hello TVBox"
        """)
    }

    @Test("requests module compatibility")
    func testRequests() throws {
        try PythonEngine.shared.runCode("""
        import requests
        assert requests.codes.ok == 200
        assert hasattr(requests, "get")
        assert hasattr(requests, "post")
        assert hasattr(requests, "Session")
        """)
    }

    @Test("Crypto AES and PKCS7 Padding")
    func testCryptoAES() throws {
        try PythonEngine.shared.runCode("""
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad, unpad

        key = b"1234567890123456"
        iv = b"6543210987654321"
        plaintext = b"TVBox Secret Token"

        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        ciphertext = cipher.encrypt(pad(plaintext, 16))

        decipher = AES.new(key, AES.MODE_CBC, iv=iv)
        decrypted = unpad(decipher.decrypt(ciphertext), 16)

        assert decrypted == plaintext
        """)
    }

    @Test("urllib3 HTTP library")
    func testUrllib3() throws {
        try PythonEngine.shared.runCode("""
        import urllib3
        assert hasattr(urllib3, "PoolManager")
        """)
    }

    @Test("Dynamic module loading and calling")
    func testModuleLoadingAndCall() throws {
        let pythonCode = """
        from bs4 import BeautifulSoup
        from base.spider import Spider

        class MySpider(Spider):
            def homeContent(self, filter):
                soup = BeautifulSoup("<div class='item'>Title via BS4</div>", "lxml")
                title = soup.find(class_='item').text
                return {"title": title, "status": "ok"}

        spider_instance = MySpider()

        def fetch_home(filter):
            return spider_instance.homeContent(filter)
        """

        try PythonEngine.shared.loadModule(name: "test_spider_bs4", code: pythonCode)
        let response = try PythonEngine.shared.call(module: "test_spider_bs4", function: "fetch_home", args: [true])

        guard let dict = response as? [String: Any] else {
            Issue.record("Expected dictionary response")
            return
        }

        #expect(dict["title"] as? String == "Title via BS4")
        #expect(dict["status"] as? String == "ok")
    }

    @Test("Spider runner envelope")
    func testSpiderRunnerEnvelope() throws {
        let key = "python_mobile_runner_test"
        let source = """
        from base.spider import Spider as BaseSpider

        class Spider(BaseSpider):
            def homeContent(self, filter=True):
                return {"ok": True, "items": [1, 2, 3]}
        """

        let initialized = try PythonEngine.shared.call(
            module: "spider_runner",
            function: "init_spider",
            args: [key, source, ""]
        ) as? [String: Any]

        #expect(initialized?["ok"] as? Bool == true)

        let response = try PythonEngine.shared.call(
            module: "spider_runner",
            function: "call_spider",
            args: [key, "homeContent", [true]]
        ) as? [String: Any]

        #expect(response?["ok"] as? Bool == true)
        let value = response?["value"] as? [String: Any]
        #expect(value?["ok"] as? Bool == true)
        #expect(value?["items"] as? [Int] == [1, 2, 3])
    }

    @Test("Requests response JSON decoding")
    func testRequestsResponseJSONDecoding() throws {
        let source = """
        import requests

        def decode_response():
            response = requests.Response(b'{"status": "ok"}', 200, {})
            return response.json()
        """

        try PythonEngine.shared.loadModule(name: "python_mobile_requests_test", code: source)
        let response = try PythonEngine.shared.call(
            module: "python_mobile_requests_test",
            function: "decode_response"
        ) as? [String: Any]

        #expect(response?["status"] as? String == "ok")
    }
}
