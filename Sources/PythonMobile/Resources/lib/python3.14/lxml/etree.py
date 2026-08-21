# lxml/etree.py
import re
from html.parser import HTMLParser

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

    def get(self, key, default=None):
        return self.attrib.get(key.lower(), default)

    def set(self, key, value):
        self.attrib[key.lower()] = value

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

    def xpath(self, expr):
        return _evaluate_xpath(self, expr.strip())

class _HTMLTreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = None
        self.stack = []

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

def HTML(text):
    if not isinstance(text, str):
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        else:
            text = str(text or "")
    parser = _HTMLTreeBuilder()
    parser.feed(text)
    return parser.root or _Element("html")

def fromstring(text):
    return HTML(text)

def tostring(element, encoding="utf-8"):
    def _render(elem):
        attrs = " ".join(f'{k}="{v}"' for k, v in elem.attrib.items())
        attr_str = f" {attrs}" if attrs else ""
        inner = (elem.text or "") + "".join(_render(c) for c in elem._children)
        return f"<{elem.tag}{attr_str}>{inner}</{elem.tag}>{elem.tail or ''}"
    rendered = _render(element)
    return rendered.encode(encoding) if encoding else rendered

# --- XPath Engine ---

def _evaluate_xpath(node, expr):
    if not expr or not node:
        return []

    # Handle attribute or text extraction on current node
    if expr == "text()" or expr == "./text()":
        return [node.text] if node.text else []
    if expr.startswith("@") or expr.startswith("./@"):
        attr = expr.split("@", 1)[1]
        val = node.get(attr)
        return [val] if val is not None else []

    # Tokenize steps: //div[@class='item'] -> search all descendants
    is_descendant = expr.startswith("//") or expr.startswith(".//")
    clean_expr = re.sub(r"^\.?//", "", expr)
    steps = re.split(r"/(?![\w\s]*\])", clean_expr)

    current_nodes = _get_all_descendants(node) if is_descendant else [node]

    for step in steps:
        if not step:
            continue
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
            candidates = n._children if not is_descendant else [n]
            for child in candidates:
                if _match_step(child, step):
                    next_nodes.append(child)
        current_nodes = next_nodes
        is_descendant = False

    return current_nodes

def _get_all_descendants(node):
    nodes = []
    for child in node._children:
        nodes.append(child)
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

    # [@class='foo'] or [@class="foo"]
    attr_match = re.match(r"@([\w\-]+)\s*=\s*['\"]([^'\"]*)['\"]", pred)
    if attr_match:
        attr_name, attr_val = attr_match.groups()
        return elem.get(attr_name) == attr_val

    # [contains(@class, 'foo')]
    contains_match = re.match(r"contains\(\s*@([\w\-]+)\s*,\s*['\"]([^'\"]*)['\"]\s*\)", pred)
    if contains_match:
        attr_name, substr = contains_match.groups()
        val = elem.get(attr_name) or ""
        return substr in val

    # [@id]
    if pred.startswith("@"):
        return elem.get(pred[1:]) is not None

    # [1] (1-based index)
    if pred.isdigit():
        idx = int(pred)
        if elem.parent:
            siblings = [c for c in elem.parent._children if c.tag == elem.tag]
            return siblings.index(elem) + 1 == idx if elem in siblings else False

    return True
