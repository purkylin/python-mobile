import base64
import json as json_module
import ssl
import urllib.error
import urllib.parse
import urllib.request

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
_last_transport_error = None


def _begin_request_scope():
    global _last_transport_error
    _last_transport_error = None


def _consume_transport_error():
    global _last_transport_error
    error = _last_transport_error
    _last_transport_error = None
    return error


def _response_error_message(response):
    code = response.status_code
    if 200 <= code < 300:
        return None
    if code == 403:
        return f"Auth Failed (HTTP 403) for url: {response.url}"
    if code == 404:
        return f"Not Found (HTTP 404) for url: {response.url}"
    if code == 429:
        return f"Access Limit Exceeded (HTTP 429) for url: {response.url}"

    message = None
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            message = payload.get("message") or payload.get("msg")
            if not message and isinstance(error, dict):
                message = error.get("message")
            elif not message and isinstance(error, str):
                message = error
    except Exception:
        pass

    suffix = f": {str(message).strip()}" if message else ""
    return f"Server Error (HTTP {code}){suffix} for url: {response.url}"


class RequestsCookieJar(dict):
    def get_dict(self):
        return dict(self)

    def set(self, key, value, domain=None, path="/"):
        self[str(key)] = str(value)


def _extract_cookies(headers):
    cookies = {}
    values = headers.get("Set-Cookie") or headers.get("set-cookie") or ""
    for value in values.split(","):
        pair = value.split(";", 1)[0].strip()
        if "=" in pair:
            key, item = pair.split("=", 1)
            cookies[key.strip()] = item.strip()
    return cookies


class Response:
    def __init__(self, content_bytes, status_code, headers, url=""):
        self.content = content_bytes or b""
        self.status_code = status_code
        self.status = status_code
        self.headers = headers or {}
        self.url = url
        self.encoding = "utf-8"
        self.cookies = _extract_cookies(self.headers)
        self.reason = self.headers.get("Reason", "")

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    @property
    def text(self):
        try:
            return self.content.decode(self.encoding or "utf-8")
        except Exception:
            return self.content.decode("utf-8", errors="ignore")

    @property
    def apparent_encoding(self):
        content_type = ""
        for key, value in self.headers.items():
            if str(key).lower() == "content-type":
                content_type = str(value)
                break

        marker = "charset="
        lowered = content_type.lower()
        if marker in lowered:
            value = content_type[lowered.index(marker) + len(marker):]
            return value.split(";", 1)[0].strip().strip('"\'') or "utf-8"

        try:
            self.content.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            return "gb18030"

    def json(self, **kwargs):
        return json_module.loads(self.text, **kwargs)

    def raise_for_status(self):
        message = _response_error_message(self)
        if message:
            global _last_transport_error
            _last_transport_error = message
            raise exceptions.HTTPError(message, response=self)


class Session:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15"
        }
        self.cookies = RequestsCookieJar()
        self.verify = True
        self.adapters = {}

    def mount(self, prefix, adapter):
        self.adapters[prefix] = adapter

    def close(self):
        pass

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
        request_headers = dict(self.headers)
        if headers:
            request_headers.update({key: str(value) for key, value in headers.items()})

        if params:
            query = urllib.parse.urlencode(params, doseq=True) if not isinstance(params, str) else params
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{query}"

        all_cookies = dict(self.cookies)
        if cookies:
            all_cookies.update(cookies)
        if all_cookies:
            request_headers["Cookie"] = "; ".join(
                f"{key}={value}" for key, value in all_cookies.items()
            )

        body = None
        if json is not None:
            body = json_module.dumps(json, ensure_ascii=False).encode("utf-8")
            if not any(key.lower() == "content-type" for key in request_headers):
                request_headers["Content-Type"] = "application/json"
        elif data is not None:
            if isinstance(data, dict):
                body = urllib.parse.urlencode(data, doseq=True).encode("utf-8")
                if not any(key.lower() == "content-type" for key in request_headers):
                    request_headers["Content-Type"] = "application/x-www-form-urlencoded"
            elif isinstance(data, str):
                body = data.encode("utf-8")
            else:
                body = data

        try:
            request_timeout = 15 if timeout is None else float(timeout)
        except (TypeError, ValueError):
            request_timeout = 15
        request_timeout = max(0.1, min(request_timeout, 15))

        verify = kwargs.get("verify", self.verify)
        context = ssl.create_default_context()
        if verify is False:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        native_request = None
        try:
            from _tvbox_http import request as native_request
        except ImportError:
            pass

        if native_request is not None and verify is not False:
            payload = {
                "method": method.upper(),
                "url": url,
                "headers": request_headers,
                "body": base64.b64encode(body or b"").decode("ascii"),
                "timeout": timeout
            }
            native_response = json_module.loads(
                native_request(json_module.dumps(payload, ensure_ascii=False))
            )
            if not native_response.get("ok"):
                message = native_response.get("error", "HTTP request failed")
                global _last_transport_error
                _last_transport_error = message
                raise exceptions.RequestException(message)

            result = Response(
                base64.b64decode(native_response.get("body", "")),
                native_response.get("status_code", 0),
                native_response.get("headers", {}),
                url=native_response.get("url", url)
            )
            _last_transport_error = _response_error_message(result)
            if _last_transport_error:
                raise exceptions.HTTPError(_last_transport_error, response=result)
            self.cookies.update(result.cookies)
            return result

        request = urllib.request.Request(
            url,
            data=body,
            headers=request_headers,
            method=method.upper()
        )

        try:
            with urllib.request.urlopen(request, timeout=request_timeout, context=context) as response:
                result = Response(
                    response.read(),
                    response.status,
                    dict(response.headers),
                    url=response.geturl()
                )
        except urllib.error.HTTPError as error:
            result = Response(
                error.read(),
                error.code,
                dict(error.headers),
                url=url
            )
        except Exception as error:
            _last_transport_error = str(error)
            raise exceptions.RequestException(str(error))

        _last_transport_error = _response_error_message(result)
        if _last_transport_error:
            raise exceptions.HTTPError(_last_transport_error, response=result)
        self.cookies.update(result.cookies)
        return result


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
