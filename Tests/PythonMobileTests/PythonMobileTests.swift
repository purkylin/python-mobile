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
