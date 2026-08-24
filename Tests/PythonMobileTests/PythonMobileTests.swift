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
        from requests.adapters import HTTPAdapter
        assert requests.codes.ok == 200
        assert hasattr(requests, "get")
        assert hasattr(requests, "post")
        assert hasattr(requests, "Session")
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=2))
        assert session.adapters["https://"].max_retries == 0
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

        standard_key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        standard_plaintext = bytes.fromhex("00112233445566778899aabbccddeeff")
        standard_ciphertext = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
        assert AES.new(standard_key, AES.MODE_ECB).encrypt(standard_plaintext) == standard_ciphertext
        assert AES.new(standard_key, AES.MODE_ECB).decrypt(standard_ciphertext) == standard_plaintext
        """)
    }

    @Test("Crypto ARC4 compatibility")
    func testCryptoARC4() throws {
        try PythonEngine.shared.runCode("""
        from Crypto.Cipher import ARC4

        encrypted = ARC4.new(b"Key").encrypt(b"Plaintext")
        assert encrypted.hex() == "bbf316e8d940af0ad3"
        assert ARC4.new(b"Key").decrypt(encrypted) == b"Plaintext"
        """)
    }

    @Test("Crypto RSA PKCS1 v1.5 compatibility")
    func testCryptoRSA() throws {
        try PythonEngine.shared.runCode("""
        import base64
        from Crypto.Hash import SHA256
        from Crypto.PublicKey import RSA
        from Crypto.Cipher import PKCS1_v1_5
        from Crypto.Signature import pkcs1_15

        public_der = base64.b64decode(
            "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCoYt0BP77U+DM08BiI/QbSRIfxijXo85BTPqIM1Ow8BNwhLETzRIZ+dEwdWDbydG/PspgBAfRpGaYVdJYtvaC2JnoO8+Ik6qMWojfEJxSFLa0Pb0A892tun4gsxoEMjcreZ+YGyaBxAfqX0BSMfdrOgIYaZQjYrw9TRLlUT31QoQIDAQAB"
        )
        key = RSA.import_key(public_der)
        encrypted = PKCS1_v1_5.new(key).encrypt(b"TVBox")
        assert len(encrypted) == key.size_in_bytes()
        assert callable(pkcs1_15.new)
        assert SHA256.new(b"TVBox").oid == "2.16.840.1.101.3.4.2.1"
        """)
    }

    @Test("Legacy Spider receives BaseSpider instance state")
    func testLegacySpiderStateInjection() throws {
        try PythonEngine.shared.runCode("""
        import spider_runner

        script = '''
        class Spider:
            def init(self, extend=''):
                pass

            def categoryContent(self, tid, pg, filter, extend):
                return {'list': [{'vod_id': self.header['User-Agent']}], 'page': pg}
        '''
        initialized = spider_runner.init_spider("legacy-state-test", script)
        assert initialized["ok"]
        response = spider_runner.call_spider(
            "legacy-state-test", "categoryContent", ["tv", "1", False, {}]
        )
        assert response["ok"]
        assert response["value"]["list"][0]["vod_id"]
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

    @Test("Spider Native Cache and utilities")
    func testSpiderNativeCacheAndUtilities() throws {
        let key = "python_mobile_cache_test"
        let source = """
        from base.spider import Spider

        class Spider(Spider):
            def test_cache_and_utils(self):
                self.setCache("test_token", {"token": "abc123xyz", "expiresAt": 9999999999})
                cached = self.getCache("test_token")
                cleaned = self.cleanText(" <div>Hello <b>World</b> &amp; TVBox </div> ")
                is_video = self.isVideoFormat("https://example.com/play/video.m3u8?token=123")
                proxy_url = self.getProxyUrl()
                return {
                    "cached": cached,
                    "cleaned": cleaned,
                    "is_video": is_video,
                    "proxy_url": proxy_url
                }
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
            args: [key, "test_cache_and_utils", []]
        ) as? [String: Any]
        #expect(response?["ok"] as? Bool == true)

        guard let value = response?["value"] as? [String: Any] else {
            Issue.record("Expected dictionary response")
            return
        }

        let cached = value["cached"] as? [String: Any]
        #expect(cached?["token"] as? String == "abc123xyz")
        #expect(value["cleaned"] as? String == "Hello World & TVBox")
        #expect(value["is_video"] as? Bool == true)
        #expect((value["proxy_url"] as? String)?.contains("proxy?do=py") == true)
    }
}
