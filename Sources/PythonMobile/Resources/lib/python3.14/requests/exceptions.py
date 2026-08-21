# requests/exceptions.py
class RequestException(IOError):
    def __init__(self, *args, **kwargs):
        self.response = kwargs.pop('response', None)
        self.request = kwargs.pop('request', None)
        super(RequestException, self).__init__(*args, **kwargs)

class HTTPError(RequestException): pass
class ConnectionError(RequestException): pass
class ProxyError(ConnectionError): pass
class SSLError(ConnectionError): pass
class Timeout(RequestException): pass
class ConnectTimeout(Timeout, ConnectionError): pass
class ReadTimeout(Timeout): pass
class URLRequired(RequestException): pass
class TooManyRedirects(RequestException): pass
class MissingSchema(RequestException, ValueError): pass
class InvalidSchema(RequestException, ValueError): pass
class InvalidURL(RequestException, ValueError): pass
class InvalidHeader(RequestException, ValueError): pass
class ChunkedEncodingError(RequestException): pass
class ContentDecodingError(RequestException, BaseException): pass
