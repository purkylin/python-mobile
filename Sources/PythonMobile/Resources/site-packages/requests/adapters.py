class HTTPAdapter:
    def __init__(self, *args, max_retries=0, **kwargs):
        self.max_retries = 0

    def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
        return None

    def proxy_manager_for(self, proxy, **kwargs):
        return None

    def close(self):
        pass
