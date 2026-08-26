import re
import json
import html
import requests

try:
    import _tvbox_native
except ImportError:
    _tvbox_native = None

Response = requests.Response


class Spider:
    def __init__(self):
        self.header = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15"
        }
        self.session = requests.Session()
        self.session.headers.update(self.header)
        self.site_key = ""
        self._local_cache = {}

    def init(self, extend=""):
        pass

    def getName(self):
        return getattr(self, "name", "") or self.__class__.__name__

    def log(self, *args, **kwargs):
        print(*args, **kwargs, flush=True)

    def isVideoFormat(self, url):
        if not url or not isinstance(url, str):
            return False
        clean_url = url.split("?")[0].lower()
        video_exts = (
            ".m3u8", ".mp4", ".flv", ".ts", ".mkv", ".avi",
            ".mov", ".wmv", ".rmvb", ".mpd", ".webm", ".m4v"
        )
        return clean_url.endswith(video_exts) or ".m3u8" in clean_url or ".mp4" in clean_url

    def is_video_format(self, url):
        return self.isVideoFormat(url)

    def manualVideoCheck(self):
        return False

    def manual_video_check(self):
        return self.manualVideoCheck()

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    # ==================== Cache Methods ====================

    def setCache(self, key, value):
        if not key:
            return
        key_str = str(key)
        val_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value

        if _tvbox_native and hasattr(_tvbox_native, "cache_set"):
            _tvbox_native.cache_set(key_str, val_str)
        else:
            self._local_cache[key_str] = value

    def set_cache(self, key, value):
        return self.setCache(key, value)

    def getCache(self, key, default=""):
        if not key:
            return default
        key_str = str(key)

        if _tvbox_native and hasattr(_tvbox_native, "cache_get"):
            raw = _tvbox_native.cache_get(key_str)
            if not raw:
                return default
            try:
                return json.loads(raw)
            except Exception:
                return raw

        return self._local_cache.get(key_str, default)

    def get_cache(self, key, default=""):
        return self.getCache(key, default)

    def delCache(self, key):
        if not key:
            return
        key_str = str(key)
        if _tvbox_native and hasattr(_tvbox_native, "cache_del"):
            _tvbox_native.cache_del(key_str)
        else:
            self._local_cache.pop(key_str, None)

    def del_cache(self, key):
        return self.delCache(key)

    def clearCache(self):
        if _tvbox_native and hasattr(_tvbox_native, "cache_clear"):
            _tvbox_native.cache_clear()
        else:
            self._local_cache.clear()

    def clear_cache(self):
        return self.clearCache()

    # ==================== Proxy Methods ====================

    def getProxyUrl(self, local=True):
        site_name = self.getName() or "spider"
        if _tvbox_native and hasattr(_tvbox_native, "get_proxy_url"):
            return _tvbox_native.get_proxy_url(site_name)
        return f"http://127.0.0.1:9978/proxy?do=py&site={site_name}"

    def get_proxy_url(self, local=True):
        return self.getProxyUrl(local)

    def localProxy(self, param):
        return [200, "video/MP2T", b""]

    def local_proxy(self, param):
        return self.localProxy(param)

    # ==================== String & Utility Methods ====================

    def cleanText(self, text):
        if not text or not isinstance(text, str):
            return ""
        cleaned = re.sub(r"<[^>]+>", "", text)
        cleaned = html.unescape(cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def clean_text(self, text):
        return self.cleanText(text)

    def regStr(self, reg, src, group=1, default=""):
        if not src or not reg:
            return default
        match = re.search(reg, src)
        if match:
            try:
                return match.group(group)
            except Exception:
                return match.group(0)
        return default

    def reg_str(self, reg, src, group=1, default=""):
        return self.regStr(reg, src, group, default)

    def stringify(self, value):
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)

    def loads(self, value):
        return json.loads(value)

    def dumps(self, value, **kwargs):
        ensure_ascii = kwargs.pop("ensure_ascii", False)
        return json.dumps(value, ensure_ascii=ensure_ascii, **kwargs)

    def json(self, value):
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return {}

    # ==================== Content Methods ====================

    def homeContent(self, filter=True):
        return "{}"

    def home_content(self, filter=True):
        return self.homeContent(filter)

    def homeVideoContent(self):
        return "{}"

    def home_video_content(self):
        return self.homeVideoContent()

    def categoryContent(self, tid, pg="1", filter=True, extend=None):
        return "{}"

    def category_content(self, tid, pg="1", filter=True, extend=None):
        return self.categoryContent(tid, pg, filter, extend)

    def detailContent(self, ids):
        return "{}"

    def detail_content(self, ids):
        return self.detailContent(ids)

    def searchContent(self, key, quick=False, pg="1"):
        return "{}"

    def search_content(self, key, quick=False, pg="1"):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags=None):
        return "{}"

    def player_content(self, flag, id, vipFlags=None):
        return self.playerContent(flag, id, vipFlags)

    def liveContent(self, url):
        return "{}"

    def live_content(self, url):
        return self.liveContent(url)

    def action(self, action, *args, **kwargs):
        return "{}"

    # ==================== HTTP Request Methods ====================

    def getCookie(self, name=None):
        cookies = self.session.cookies.get_dict()
        if name:
            return cookies.get(name, "")
        return "; ".join([f"{k}={v}" for k, v in cookies.items()])

    def get_cookie(self, name=None):
        return self.getCookie(name)

    def setCookie(self, key, value, domain=""):
        if isinstance(key, dict):
            for k, v in key.items():
                self.session.cookies.set(k, str(v), domain=domain or None)
        elif key:
            self.session.cookies.set(str(key), str(value), domain=domain or None)

    def set_cookie(self, key, value, domain=""):
        return self.setCookie(key, value, domain)

    def fetch(self, url, params=None, headers=None, timeout=15, cookies=None, **kwargs):
        return self.get(url, params=params, headers=headers, timeout=timeout, cookies=cookies, **kwargs)

    def get(self, url, params=None, headers=None, timeout=15, cookies=None, **kwargs):
        request_headers = dict(self.header)
        if headers:
            request_headers.update(headers)
        return self.session.get(
            url,
            params=params,
            headers=request_headers,
            cookies=cookies,
            timeout=timeout,
            **kwargs
        )

    def post(self, url, data=None, json=None, json_data=None, params=None, headers=None, timeout=15, cookies=None, **kwargs):
        request_headers = dict(self.header)
        if headers:
            request_headers.update(headers)
        payload = json if json is not None else json_data
        return self.session.post(
            url,
            data=data,
            json=payload,
            params=params,
            headers=request_headers,
            cookies=cookies,
            timeout=timeout,
            **kwargs
        )

    def head(self, url, params=None, headers=None, timeout=15, cookies=None, **kwargs):
        request_headers = dict(self.header)
        if headers:
            request_headers.update(headers)
        return self.session.head(
            url,
            params=params,
            headers=request_headers,
            cookies=cookies,
            timeout=timeout,
            **kwargs
        )

    def put(self, url, data=None, json=None, params=None, headers=None, timeout=15, cookies=None, **kwargs):
        request_headers = dict(self.header)
        if headers:
            request_headers.update(headers)
        return self.session.put(
            url,
            data=data,
            json=json,
            params=params,
            headers=request_headers,
            cookies=cookies,
            timeout=timeout,
            **kwargs
        )

    def delete(self, url, params=None, headers=None, timeout=15, cookies=None, **kwargs):
        request_headers = dict(self.header)
        if headers:
            request_headers.update(headers)
        return self.session.delete(
            url,
            params=params,
            headers=request_headers,
            cookies=cookies,
            timeout=timeout,
            **kwargs
        )



