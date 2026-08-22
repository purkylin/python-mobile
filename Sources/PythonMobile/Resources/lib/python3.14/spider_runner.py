# spider_runner.py
import sys
import json
import types
import traceback
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning)

_spiders = {}

def sanitize_script(script):
    return script

def init_spider(site_key, script_content, ext_param=""):
    try:
        module_name = f"spider_{site_key}"
        mod = types.ModuleType(module_name)
        mod.__file__ = f"<{module_name}>"

        clean_content = sanitize_script(script_content)
        exec(compile(clean_content, mod.__file__, "exec"), mod.__dict__)
        sys.modules[module_name] = mod

        spider_cls = getattr(mod, "Spider", None)
        if spider_cls is None:
            return json.dumps({"success": False, "error": f"Module {module_name} has no Spider class"})

        spider = spider_cls()
        if hasattr(spider, "init"):
            spider.init(ext_param or "")

        _spiders[site_key] = spider
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })

def call_spider(site_key, method, args=None):
    try:
        spider = _spiders.get(site_key)
        if spider is None:
            return json.dumps({"error": f"Spider for site '{site_key}' is not initialized"})

        func = getattr(spider, method, None)
        if func is None or not callable(func):
            return json.dumps({"error": f"Method '{method}' not found on spider '{site_key}'"})

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = [args]
        elif args is None:
            args = []

        if isinstance(args, dict):
            res = func(**args)
        elif isinstance(args, list):
            res = func(*args)
        else:
            res = func(args)

        if isinstance(res, str):
            return res
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "traceback": traceback.format_exc()
        })
