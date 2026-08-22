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
}
