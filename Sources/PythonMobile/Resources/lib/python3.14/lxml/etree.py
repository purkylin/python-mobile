# lxml/etree.py
import re
from html.parser import HTMLParser as _StdHTMLParser

class LxmlError(Exception): pass
class ParserError(LxmlError): pass
class XMLSyntaxError(LxmlError): pass

class _Element:
    def __init__(self, tag, attrib=None):
        self.tag = tag.lower() if tag else ""
        self.attrib = {k.lower(): v for k, v in (attrib or {}).items()}
        self._text_parts = []
        self._children = []
        self.parent = None
        self.tail = ""

    @property
    def text(self):
        return "".join(self._text_parts) if self._text_parts else None

    @text.setter
    def text(self, val):
        self._text_parts = [val] if val is not None else []

    def append(self, elem):
        elem.parent = self
        self._children.append(elem)

    def insert(self, index, elem):
        elem.parent = self
        self._children.insert(index, elem)

    def remove(self, elem):
        if elem in self._children:
            self._children.remove(elem)
            elem.parent = None

    def get(self, key, default=None):
        return self.attrib.get(key.lower(), default)

    def set(self, key, value):
        self.attrib[key.lower()] = value

    def items(self):
        return list(self.attrib.items())

    def keys(self):
        return list(self.attrib.keys())

    def values(self):
        return list(self.attrib.values())

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)

    def __getitem__(self, idx):
        return self._children[idx]

    def itertext(self):
        if self.text:
            yield self.text
        for child in self._children:
            yield from child.itertext()
            if child.tail:
                yield child.tail

    def xpath(self, expr, namespaces=None, **kwargs):
        return _evaluate_xpath(self, str(expr).strip())

    def cssselect(self, expr):
        import cssselect
        tr = cssselect.GenericTranslator()
        xpath_expr = tr.css_to_xpath(expr)
        return self.xpath(xpath_expr)

Element = _Element

class _ElementTree:
    def __init__(self, element=None, file=None, parser=None):
        self._root = element

    def getroot(self):
        return self._root

    def xpath(self, expr, namespaces=None, **kwargs):
        return self._root.xpath(expr, namespaces=namespaces, **kwargs) if self._root else []

ElementTree = _ElementTree

def SubElement(parent, tag, attrib=None, **extra):
    attrs = dict(attrib or {})
    attrs.update(extra)
    elem = _Element(tag, attrs)
    parent.append(elem)
    return elem

def Comment(text=None):
    elem = _Element("!--")
    elem.text = text or ""
    return elem

def ProcessingInstruction(target, text=None):
    elem = _Element(f"?{target}")
    elem.text = text or ""
    return elem

PI = ProcessingInstruction

class XMLParser:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

class HTMLParser(_StdHTMLParser):
    def __init__(self, **kwargs):
        super().__init__(convert_charrefs=True)
        self.root = None
        self.stack = []
        self.kwargs = kwargs

    def handle_starttag(self, tag, attrs):
        elem = _Element(tag, dict(attrs))
        if self.root is None:
            self.root = elem
        if self.stack:
            self.stack[-1].append(elem)
        self.stack.append(elem)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        if self.stack:
            self.stack[-1]._text_parts.append(data)

def HTML(text, parser=None):
    if not isinstance(text, str):
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        else:
            text = str(text or "")
    if isinstance(parser, type):
        p = parser()
    elif isinstance(parser, HTMLParser):
        p = parser
    else:
        p = HTMLParser()
    p.feed(text)
    return p.root or _Element("html")

def XML(text, parser=None):
    return HTML(text, parser=parser)

def fromstring(text, parser=None):
    return HTML(text, parser=parser)

def tostring(element, encoding="utf-8", pretty_print=False, method="html"):
    if isinstance(element, _ElementTree):
        element = element.getroot()
    if element is None:
        return b"" if encoding else ""
    def _render(elem):
        attrs = " ".join(f'{k}="{v}"' for k, v in elem.attrib.items())
        attr_str = f" {attrs}" if attrs else ""
        inner = (elem.text or "") + "".join(_render(c) for c in elem._children)
        return f"<{elem.tag}{attr_str}>{inner}</{elem.tag}>{elem.tail or ''}"
    rendered = _render(element)
    return rendered.encode(encoding) if encoding else rendered

class XPath:
    def __init__(self, path):
        self.path = path

    def __call__(self, element):
        return element.xpath(self.path)

# --- XPath Engine ---

def _evaluate_xpath(node, expr):
    if not expr or not node:
        return []

    if expr == "text()" or expr == "./text()":
        return [node.text] if node.text else []
    if expr.startswith("@") or expr.startswith("./@"):
        attr = expr.split("@", 1)[1]
        val = node.get(attr)
        return [val] if val is not None else []

    is_descendant = expr.startswith("//") or expr.startswith(".//") or "descendant-or-self::" in expr
    clean_expr = re.sub(r"^(?:\.?//|descendant-or-self::\*/?)", "", expr)
    steps = [s for s in re.split(r"/(?![\w\s]*\])", clean_expr) if s]

    current_nodes = _get_all_descendants(node) if is_descendant else [node]

    for step in steps:
        if step == "text()":
            results = []
            for n in current_nodes:
                if n.text:
                    results.append(n.text)
            return results
        if step.startswith("@"):
            attr = step[1:]
            results = []
            for n in current_nodes:
                val = n.get(attr)
                if val is not None:
                    results.append(val)
            return results

        next_nodes = []
        for n in current_nodes:
            candidates = [n] if is_descendant else n._children
            for candidate in candidates:
                if _match_step(candidate, step):
                    if candidate not in next_nodes:
                        next_nodes.append(candidate)
        current_nodes = next_nodes
        is_descendant = False

    return current_nodes

def _get_all_descendants(node):
    nodes = [node]
    for child in node._children:
        nodes.extend(_get_all_descendants(child))
    return nodes

def _match_step(elem, step):
    m = re.match(r"^([\w\*\-]+)(?:\[(.*)\])?$", step)
    if not m:
        return False
    tag, pred = m.groups()
    if tag != "*" and elem.tag != tag.lower():
        return False
    if not pred:
        return True

    attr_match = re.match(r"@([\w\-]+)\s*=\s*['\"]([^'\"]*)['\"]", pred)
    if attr_match:
        attr_name, attr_val = attr_match.groups()
        return elem.get(attr_name) == attr_val

    contains_match = re.match(r"contains\(\s*@([\w\-]+)\s*,\s*['\"]([^'\"]*)['\"]\s*\)", pred)
    if contains_match:
        attr_name, substr = contains_match.groups()
        val = elem.get(attr_name) or ""
        return substr in val

    if pred.startswith("@"):
        return elem.get(pred[1:]) is not None

    if pred.isdigit():
        idx = int(pred)
        if elem.parent:
            siblings = [c for c in elem.parent._children if c.tag == elem.tag]
            return siblings.index(elem) + 1 == idx if elem in siblings else False

    return True
