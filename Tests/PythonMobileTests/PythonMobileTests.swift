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

    @Test("lxml etree and XPath parsing")
    func testLxmlXPath() throws {
        try PythonEngine.shared.runCode("""
        from lxml import etree

        html_content = '''
        <div class="video-list">
            <div class="item" id="v1"><a href="/play/1">Movie One</a></div>
            <div class="item" id="v2"><a href="/play/2">Movie Two</a></div>
        </div>
        '''

        tree = etree.HTML(html_content)
        items = tree.xpath('//div[@class="item"]')
        assert len(items) == 2

        titles = tree.xpath('//div[@class="item"]/a/text()')
        assert titles == ["Movie One", "Movie Two"]

        hrefs = tree.xpath('//div[@class="item"]/a/@href')
        assert hrefs == ["/play/1", "/play/2"]
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

    @Test("bs4 (BeautifulSoup4) HTML parsing")
    func testBeautifulSoup() throws {
        try PythonEngine.shared.runCode("""
        from bs4 import BeautifulSoup

        html_doc = "<html><body><div class='title'>Hello TVBox</div></body></html>"
        soup = BeautifulSoup(html_doc, 'html.parser')
        assert soup.find('div', class_='title').text == "Hello TVBox"
        """)
    }

    @Test("pyquery CSS selector parsing")
    func testPyQuery() throws {
        try PythonEngine.shared.runCode("""
        from pyquery import PyQuery as pq

        doc = pq("<div class='container'><span id='msg'>Testing PyQuery</span></div>")
        assert doc("#msg").text() == "Testing PyQuery"
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
        from lxml import etree
        from base.spider import Spider

        class MySpider(Spider):
            def homeContent(self, filter):
                tree = etree.HTML("<div class='item'>Title</div>")
                title = tree.xpath("//div[@class='item']/text()")[0]
                return {"title": title, "status": "ok"}

        spider_instance = MySpider()

        def fetch_home(filter):
            return spider_instance.homeContent(filter)
        """

        try PythonEngine.shared.loadModule(name: "test_spider", code: pythonCode)
        let response = try PythonEngine.shared.call(module: "test_spider", function: "fetch_home", args: [true])

        guard let dict = response as? [String: Any] else {
            Issue.record("Expected dictionary response")
            return
        }

        #expect(dict["title"] as? String == "Title")
        #expect(dict["status"] as? String == "ok")
    }
}
