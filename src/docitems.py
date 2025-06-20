from __future__ import annotations

import sys
from pathlib import Path


def directive_md(directive, argument, options, contents, **kwargs):
    if argument:
        print(f":::{{{directive}}} {argument}", **kwargs)
    else:
        print(f":::{{{directive}}}", **kwargs)
    for opt in options:
        print(f"{opt}", **kwargs)
        print(**kwargs)
    for line in contents:
        print(line, **kwargs)
    print(":::\n", **kwargs)


def title_md(title, **kwargs):
    print(f"# {title}\n", **kwargs)


def directive_rst(directive, argument, options, contents, **kwargs):
    if argument:
        print(f".. {directive}:: {argument}", **kwargs)
    else:
        print(f".. {directive}::", **kwargs)
    for opt in options:
        print(f"   {opt}", **kwargs)
    print(**kwargs)
    for line in contents:
        print("  ", line, **kwargs)
    print(**kwargs)


def title_rst(title, **kwargs):
    print(title, **kwargs)
    print("=" * len(title), **kwargs)
    print(**kwargs)


def table_rst(role, rows, **kwargs):
    print(".. list-table::\n", **kwargs)
    for (name, descr) in rows:
        print(f"   * - {role}`{name}`", **kwargs)
        print(f"     - {descr}", **kwargs)
    print(**kwargs)


def _label(name, **kwargs):
    print(f".. _{name}:\n", **kwargs)


def make_label(name):
    return f"{name.replace(' ', '-').lower()}_module"

_directive = directive_rst
_title = title_rst
_table = table_rst

class DocItem:
    @staticmethod
    def make_name(rootpath, pth):
        relpath=pth.relative_to(rootpath)
        return '.'.join(relpath.parts)


class PackageItem(DocItem):
    def __init__(self, pth: Path, rootpath: Path | None = None):
        if rootpath is None:
            rootpath = pth.parent
        packs = []
        funcs = []
        self.id = self.make_name(rootpath, pth)
        self.name = pth.stem
        self.descr = pth.name.upper()
        for f in pth.iterdir():
            if f.is_dir():
                packs.append(PackageItem(pth / f, rootpath))
            elif f.is_file() and f.suffix == '.m':
                item = FunctionItem(pth / f)
                if f.name == 'Contents.m':
                    self.descr = item.descr
                else:
                    funcs.append(item)
        self.subpackages = packs
        self.functions = funcs

    def generate(self, dest=None, recursive: bool = None):
        def gen(file):
            _label(make_label(self.name), file=file)
            _title(self.name, file=file)

            if self.subpackages:
                tocitems = [f"{p.id}" for p in self.subpackages]
                _directive("toctree","", [":hidden:"], tocitems, file=file)
                _directive("rubric", "Modules", [], [], file=file)
                tbl = ((make_label(p.name), p.descr) for p in self.subpackages)
                _table(":ref:", tbl, file=file)

            if self.functions:
                _directive("rubric", "Functions", [], [], file=file)
                _table(":func:", ((f.name, f.descr) for f in self.functions), file=file)
                for f in self.functions:
                    contents = ("".join(("| ", line)) for line in f.contents)
                    _directive("py:function", f.name, [], contents, file=file)

        if dest is None:
            gen(sys.stdout)
        else:
            fn = Path(dest) / "api" / ".".join((self.id, "rst"))
            with fn.open("wt") as f:
                gen(f)

        if recursive:
            for p in self.subpackages:
                p.generate(dest, recursive=recursive)


class FunctionItem(DocItem):
    def __init__(self, pth: Path):

        def get_lines(f):
            for line in f:
                if not line.startswith('%'):
                    break
                yield line[1:-1]

        self.name = pth.stem
        with pth.open("rt") as f:
            line = next(f)
            if not line.startswith('%'):
                line = next(f)
            self.descr=line[1:].strip()
            self.contents = list(get_lines(f))

    def h1(self, line: str):
        return line[1:].strip()


def make_docitems(rootpath: Path):
    return PackageItem(Path(rootpath))
