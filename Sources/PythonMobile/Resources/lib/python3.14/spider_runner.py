import sys
import json
import types
import traceback
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning)

_spiders = {}


def _log(message):
    print(message, flush=True)


def _success(value=None):
    return {"ok": True, "value": value}


def _failure(error_type, message):
    return {
        "ok": False,
        "error": {
            "type": error_type,
            "message": message,
            "traceback": traceback.format_exc()
        }
    }


def sanitize_script(script):
    return script


def init_spider(site_key, script_content, ext_param=""):
    _log(f"[spider_runner] init start site={site_key}")
    try:
        module_name = f"spider_{site_key}"
        mod = types.ModuleType(module_name)
        mod.__file__ = f"<{module_name}>"

        clean_content = sanitize_script(script_content)
        exec(compile(clean_content, mod.__file__, "exec"), mod.__dict__)
        _log(f"[spider_runner] exec complete site={site_key}")
        sys.modules[module_name] = mod

        spider_cls = getattr(mod, "Spider", None)
        if spider_cls is None:
            return _failure("ConfigurationError", f"Module {module_name} has no Spider class")

        spider = spider_cls()
        _log(f"[spider_runner] instance created site={site_key}")
        if hasattr(spider, "init"):
            _log(f"[spider_runner] init method start site={site_key}")
            spider.init(ext_param or "")
            _log(f"[spider_runner] init method complete site={site_key}")

        _spiders[site_key] = spider
        _log(f"[spider_runner] init success site={site_key}")
        return _success({"siteKey": site_key})
    except Exception as error:
        return _failure(type(error).__name__, str(error))


def call_spider(site_key, method, args=None):
    _log(f"[spider_runner] call start site={site_key} method={method}")
    try:
        spider = _spiders.get(site_key)
        if spider is None:
            return _failure("SessionError", f"Spider for site '{site_key}' is not initialized")

        func = getattr(spider, method, None)
        if func is None or not callable(func):
            return _failure("MethodError", f"Method '{method}' not found on spider '{site_key}'")

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = [args]
        elif args is None:
            args = []

        if isinstance(args, dict):
            result = func(**args)
        elif isinstance(args, list):
            result = func(*args)
        else:
            result = func(args)

        _log(f"[spider_runner] call complete site={site_key} method={method}")
        return _success(result)
    except Exception as error:
        return _failure(type(error).__name__, str(error))


def destroy_spider(site_key):
    removed = _spiders.pop(site_key, None) is not None
    sys.modules.pop(f"spider_{site_key}", None)
    return _success(removed)


