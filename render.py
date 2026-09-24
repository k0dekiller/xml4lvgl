from typing import overload
from collections.abc import Callable
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element
import os
import re

class path:
    class Path:
        def __init__(self, path: str) -> None:
            self.path = path
        @overload
        def __call__(self) -> str: ...
        @overload
        def __call__(self, path: str) -> str: ...
        def __call__(self, path: str | None = None) -> str:
            return f"{self.path}{f"/{path}" if path is not None else ""}"
    src = Path("main")
    layout = Path(src("layout"))

def escape(s: str) -> str:
    return f"\"{repr(s).strip("'").replace("\"", "\\\"")}\""

@overload
def parse(e: Element) -> str: ...
@overload
def parse(e: Element, p: Element) -> str: ...
def parse(e: Element, p: Element | None = None) -> str:
    s = ""
    def get(e: Element) -> tuple[str, str]:
        return e.tag, e.get("id", e.tag)
    name, id = get(e)
    _, pid = get(p) if p is not None else (None,)*2
    children = True

    class handler:
        class widget:
            @staticmethod
            def label() -> str:
                nonlocal children; children = False
                s = ""
                text = e.text if e.text is not None else ""
                for c in e:
                    cname, _ = get(c)
                    match cname:
                        case "color": text += f"{c.get("hex")} {c.text}#"
                        case _: raise SyntaxError(f"Unknown tag {cname!r}")
                    if c.tail is not None: text += c.tail
                if e.get("recolor", "false") == "true":
                    s += f"lv_label_set_recolor({id}, true);\n"
                s += f"lv_label_set_text({id}, {escape(text)});\n"
                return s
        class attr:
            @staticmethod
            def align(v: str) -> str:
                return f"lv_obj_align({id}, LV_ALIGN_{v.upper().replace(" ", "_")}, 0, 0);\n"
        
    s += f"lv_obj_t *{id} = lv_{name}_{"create" if pid else "active"}({pid if pid else ""});\n"
    for k, v in e.items():
        attr: Callable[[str], str] | None = getattr(handler.attr, k, None)
        if attr is not None: s += attr(v)
    widget: Callable[[], str] | None = getattr(handler.widget, name, None)
    if widget is not None: s += widget()

    if children:
        for child in e:
            s += f"\n{parse(child, e)}"
    
    return s

layouts: dict[str, str] = {}

for file in os.listdir(path.layout()):
    if not file.endswith(".xml"): continue
    tree = ET.parse(path.layout(file))
    file = file.removesuffix(".xml")
    root = tree.getroot()
    layouts[file] = parse(root)
    print(layouts[file])

for file in os.listdir(path.src()):
    if not file.endswith(".cpp"): continue
    with open(path.src(file), "r") as f:
        code = f.read()
    with open(path.src(file), "w") as f:
        for name, src in layouts.items():
            f.write(re.sub(
                r"(?s)( *)(//% [a-z0-9_]+)(.*?)(?=( *)(//% END))",
                f"\\1\\2\n\\1{src.removesuffix("\n").replace("\n", "\n\\1")}\n",
                code
            ))