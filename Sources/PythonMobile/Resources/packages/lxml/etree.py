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

    def getchildren(self):
        return list(self._children)

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
    if not expr or node is None:
        return []

    union_parts = _split_xpath(expr, "|")
    if len(union_parts) > 1:
        results = []
        for part in union_parts:
            for element in _evaluate_xpath(node, part):
                if element not in results:
                    results.append(element)
        return results

    if expr in ("text()", "./text()"):
        return [node.text] if node.text else []
    if expr.startswith("@") or expr.startswith("./@"):
        value = node.get(expr.split("@", 1)[1])
        return [value] if value is not None else []

    current_nodes = [node]
    for step in _split_xpath(expr, "/"):
        if not step:
            continue
        axis, node_test, predicates = _parse_step(step)
        next_nodes = []
        for context in current_nodes:
            candidates = _axis_candidates(context, axis)
            base_predicates = [
                predicate for predicate in predicates
                if not _is_position_predicate(predicate)
            ]
            matched = [
                candidate for candidate in candidates
                if _match_step(candidate, node_test, base_predicates)
            ]
            for position, candidate in enumerate(matched, 1):
                if _match_step(candidate, node_test, predicates, position, len(matched)):
                    if candidate not in next_nodes:
                        next_nodes.append(candidate)
        current_nodes = next_nodes
    return current_nodes

def _get_all_descendants(node):
    nodes = [node]
    for child in node._children:
        nodes.extend(_get_all_descendants(child))
    return nodes

def _split_xpath(expression, separator):
    parts = []
    start = 0
    bracket_depth = 0
    paren_depth = 0
    quote = None
    for index, character in enumerate(expression):
        if quote:
            if character == quote:
                quote = None
            continue
        if character in "'\"":
            quote = character
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth -= 1
        elif character == "(":
            paren_depth += 1
        elif character == ")":
            paren_depth -= 1
        elif character == separator and bracket_depth == 0 and paren_depth == 0:
            parts.append(expression[start:index].strip())
            start = index + 1
    parts.append(expression[start:].strip())
    return parts


def _parse_step(step):
    axis = "child"
    if "::" in step:
        axis, step = step.split("::", 1)
    node_test_end = step.find("[")
    if node_test_end < 0:
        return axis.strip(), step.strip(), []

    node_test = step[:node_test_end].strip()
    predicates = []
    remainder = step[node_test_end:]
    while remainder.startswith("["):
        depth = 0
        quote = None
        end = None
        for index, character in enumerate(remainder):
            if quote:
                if character == quote:
                    quote = None
                continue
            if character in "'\"":
                quote = character
            elif character == "[":
                depth += 1
            elif character == "]":
                depth -= 1
                if depth == 0:
                    end = index
                    break
        if end is None:
            break
        predicates.append(remainder[1:end].strip())
        remainder = remainder[end + 1:].strip()
    return axis.strip(), node_test, predicates


def _axis_candidates(node, axis):
    if axis == "descendant-or-self":
        return _get_all_descendants(node)
    if axis == "descendant":
        return _get_all_descendants(node)[1:]
    if axis == "self":
        return [node]
    if axis == "parent":
        return [node.parent] if node.parent else []
    if axis == "following-sibling":
        if not node.parent:
            return []
        try:
            index = node.parent._children.index(node)
        except ValueError:
            return []
        return node.parent._children[index + 1:]
    return list(node._children)


def _match_step(elem, node_test, predicates, position=1, total=1):
    if elem is None or (node_test != "*" and elem.tag != node_test.lower()):
        return False
    return all(_match_predicate(elem, predicate, position, total) for predicate in predicates)


def _match_predicate(elem, predicate, position, total):
    predicate = _strip_outer_parens(predicate.strip())
    for operator in (" or ", " and "):
        parts = _split_text_operator(predicate, operator)
        if len(parts) > 1:
            if operator.strip() == "or":
                return any(_match_predicate(elem, part, position, total) for part in parts)
            return all(_match_predicate(elem, part, position, total) for part in parts)

    not_match = re.fullmatch(r"not\((.*)\)", predicate, re.S)
    if not_match:
        return not _match_predicate(elem, not_match.group(1), position, total)
    if predicate in ("", "true()"):
        return True

    if predicate.startswith("position()"):
        if " mod " in predicate:
            match = re.search(r"position\(\)\s+mod\s+(\d+)\s*=\s*(\d+)", predicate)
            return bool(match and position % int(match.group(1)) == int(match.group(2)))
        match = re.search(r"position\(\)\s*=\s*(last\(\)|(\d+))", predicate)
        if match:
            return position == total if match.group(1) == "last()" else position == int(match.group(2))

    sibling_match = re.fullmatch(r"count\(preceding-sibling::\*\)\s*=\s*(\d+)", predicate)
    if sibling_match:
        if not elem.parent:
            return False
        return len(elem.parent._children[:elem.parent._children.index(elem)]) == int(sibling_match.group(1))

    self_match = re.fullmatch(r"self::([\w*-]+)", predicate)
    if self_match:
        return self_match.group(1) == "*" or elem.tag == self_match.group(1).lower()

    name_match = re.fullmatch(r"name\(\.\)\s*=\s*['\"]([^'\"]+)['\"]", predicate)
    if name_match:
        return elem.tag == name_match.group(1).lower()

    class_matches = re.findall(
        r"contains\(concat\('\s*',\s*normalize-space\(@class\),\s*'\s*'\),\s*['\"]\s*([^'\"]*?)\s*['\"]\)",
        predicate
    )
    if class_matches:
        classes = set((elem.get("class") or "").split())
        return all(value in classes for value in class_matches)

    contains_match = re.fullmatch(
        r"contains\(\s*@([\w-]+)\s*,\s*['\"]([^'\"]*)['\"]\s*\)", predicate
    )
    if contains_match:
        return contains_match.group(2) in (elem.get(contains_match.group(1)) or "")

    text_contains = re.fullmatch(r"contains\(\.\s*,\s*['\"]([^'\"]*)['\"]\s*\)", predicate)
    if text_contains:
        return text_contains.group(1) in _element_text(elem)

    attr_match = re.fullmatch(r"@([\w-]+)\s*(=|!=)\s*['\"]([^'\"]*)['\"]", predicate)
    if attr_match:
        value = elem.get(attr_match.group(1))
        expected = attr_match.group(3)
        return value == expected if attr_match.group(2) == "=" else value is not None and value != expected

    attr_exists = re.fullmatch(r"@([\w-]+)", predicate)
    if attr_exists:
        return elem.get(attr_exists.group(1)) is not None
    return True


def _is_position_predicate(predicate):
    predicate = _strip_outer_parens(predicate.strip())
    return (
        predicate.startswith("position()")
        or predicate == "last()"
        or predicate.startswith("count(preceding-sibling::")
    )


def _element_text(element):
    return "".join(element.itertext())


def _split_text_operator(expression, operator):
    parts = []
    start = 0
    bracket_depth = 0
    paren_depth = 0
    quote = None
    index = 0
    while index <= len(expression) - len(operator):
        character = expression[index]
        if quote:
            if character == quote:
                quote = None
            index += 1
            continue
        if character in "'\"":
            quote = character
            index += 1
            continue
        if character == "(":
            paren_depth += 1
        elif character == ")":
            paren_depth -= 1
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth -= 1
        if expression.startswith(operator, index) and bracket_depth == 0 and paren_depth == 0:
            parts.append(expression[start:index].strip())
            start = index + len(operator)
            index = start
            continue
        index += 1
    if parts:
        parts.append(expression[start:].strip())
    return parts or [expression]


def _strip_outer_parens(expression):
    while expression.startswith("(") and expression.endswith(")"):
        depth = 0
        quote = None
        balanced = True
        for index, character in enumerate(expression):
            if quote:
                if character == quote:
                    quote = None
                continue
            if character in "'\"":
                quote = character
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0 and index != len(expression) - 1:
                    balanced = False
                    break
        if not balanced or depth != 0:
            break
        expression = expression[1:-1].strip()
    return expression
