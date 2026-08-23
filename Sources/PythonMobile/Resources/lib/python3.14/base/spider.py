import re
import requests


Response = requests.Response


class Spider:
    def __init__(self):
        self.header = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15"
        }
        self.session = requests.Session()
        self.session.headers.update(self.header)

    def init(self, extend=""):
        pass

    def getName(self):
        return ""

    def log(self, *args, **kwargs):
        print(*args, **kwargs, flush=True)

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

    def regStr(self, reg, src, group=1):
        match = re.search(reg, src)
        return match.group(group) if match else ""

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


