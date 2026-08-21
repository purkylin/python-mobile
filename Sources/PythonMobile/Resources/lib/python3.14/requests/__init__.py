# requests/__init__.py
import urllib.request
import urllib.parse
import json
import ssl
from . import exceptions
from .exceptions import *

class _Codes:
    ok = 200
    created = 201
    accepted = 202
    no_content = 204
    bad_request = 400
    unauthorized = 401
    forbidden = 403
    not_found = 404
    internal_server_error = 500

codes = _Codes()

class Response:
    def __init__(self, content_bytes, status_code, headers, url=""):
        self.content = content_bytes or b""
        self.status_code = status_code
        self.headers = headers or {}
        self.url = url
        self.encoding = "utf-8"
        self.cookies = {}

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    @property
    def text(self):
        try:
            return self.content.decode(self.encoding or "utf-8")
        except Exception:
            return self.content.decode("utf-8", errors="ignore")

    def json(self, **kwargs):
        return json.loads(self.text, **kwargs)

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise exceptions.HTTPError(f"HTTP {self.status_code} Error for url: {self.url}", response=self)

class Session:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15"
        }
        self.cookies = {}

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def head(self, url, **kwargs):
        return self.request("HEAD", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)

    def request(self, method, url, params=None, data=None, json=None, headers=None, cookies=None, timeout=15, **kwargs):
        req_headers = dict(self.headers)
        if headers:
            for k, v in headers.items():
                req_headers[k] = str(v)

        if params:
            if isinstance(params, dict):
                query = urllib.parse.urlencode(params)
            else:
                query = str(params)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{query}"

        all_cookies = dict(self.cookies)
        if cookies:
            all_cookies.update(cookies)
        if all_cookies:
            req_headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in all_cookies.items())

        body = None
        if json is not None:
            body = json.dumps(json).encode("utf-8")
            if "Content-Type" not in req_headers and "content-type" not in req_headers:
                req_headers["Content-Type"] = "application/json"
        elif data is not None:
            if isinstance(data, dict):
                body = urllib.parse.urlencode(data).encode("utf-8")
                if "Content-Type" not in req_headers and "content-type" not in req_headers:
                    req_headers["Content-Type"] = "application/x-www-form-urlencoded"
            elif isinstance(data, str):
                body = data.encode("utf-8")
            else:
                body = data

        req = urllib.request.Request(url, data=body, headers=req_headers, method=method.upper())
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                resp_headers = dict(resp.headers)
                return Response(resp.read(), resp.status, resp_headers, url=url)
        except urllib.error.HTTPError as e:
            return Response(e.read(), e.code, dict(e.headers), url=url)
        except Exception as e:
            raise exceptions.RequestException(str(e))

_default_session = Session()

def get(url, **kwargs):
    return _default_session.get(url, **kwargs)

def post(url, **kwargs):
    return _default_session.post(url, **kwargs)

def head(url, **kwargs):
    return _default_session.head(url, **kwargs)

def put(url, **kwargs):
    return _default_session.put(url, **kwargs)

def delete(url, **kwargs):
    return _default_session.delete(url, **kwargs)

def request(method, url, **kwargs):
    return _default_session.request(method, url, **kwargs)
