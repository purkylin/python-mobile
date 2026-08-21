# base/spider.py
import urllib.request
import urllib.parse
import json
import ssl

class Response:
    def __init__(self, content_bytes, status_code, headers):
        self._content = content_bytes
        self.status_code = status_code
        self.headers = headers

    @property
    def content(self):
        return self._content

    @property
    def text(self):
        try:
            return self._content.decode("utf-8")
        except Exception:
            return self._content.decode("utf-8", errors="ignore")

    def json(self):
        return json.loads(self.text)

class Spider:
    def __init__(self):
        pass

    def init(self, extend=""):
        pass

    def getName(self):
        return ""

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def homeContent(self, filter=True):
        return "{}"

    def homeVideoContent(self):
        return "{}"

    def categoryContent(self, tid, pg="1", filter=True, extend=None):
        return "{}"

    def detailContent(self, ids):
        return "{}"

    def searchContent(self, key, quick=False, pg="1"):
        return "{}"

    def playerContent(self, flag, id, vipFlags=None):
        return "{}"

    def localProxy(self, param):
        return []

    def fetch(self, url, params=None, headers=None, timeout=15, cookies=None):
        return self.get(url, params=params, headers=headers, timeout=timeout, cookies=cookies)

    def get(self, url, params=None, headers=None, timeout=15, cookies=None):
        if params:
            query = urllib.parse.urlencode(params)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{query}"

        req = urllib.request.Request(url)
        if headers:
            for k, v in headers.items():
                req.add_header(k, str(v))
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            req.add_header("Cookie", cookie_str)
        if not req.has_header("User-Agent"):
            req.add_header("User-Agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)")

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return Response(resp.read(), resp.status, dict(resp.headers))

    def post(self, url, data=None, json_data=None, params=None, headers=None, timeout=15, cookies=None):
        if params:
            query = urllib.parse.urlencode(params)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{query}"

        body = None
        req = urllib.request.Request(url, method="POST")
        if headers:
            for k, v in headers.items():
                req.add_header(k, str(v))
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            req.add_header("Cookie", cookie_str)
        if not req.has_header("User-Agent"):
            req.add_header("User-Agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)")

        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            req.add_header("Content-Type", "application/json")
        elif data is not None:
            if isinstance(data, dict):
                body = urllib.parse.urlencode(data).encode("utf-8")
                req.add_header("Content-Type", "application/x-www-form-urlencoded")
            elif isinstance(data, str):
                body = data.encode("utf-8")
            else:
                body = data

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, data=body, timeout=timeout, context=ctx) as resp:
            return Response(resp.read(), resp.status, dict(resp.headers))
