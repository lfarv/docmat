from __future__ import annotations

import sys
from collections.abc import Iterable
from itertools import chain
from pathlib import Path
import re


def directive_md(directive, argument, options, contents, **kwargs):
    """Myst directive"""
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
    """Myst title"""
    print(f"# {title}\n", **kwargs)


def directive_rst(directive, argument, options, contents, **kwargs):
    """RST directive"""
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
    """RST title"""
    print(title, **kwargs)
    print("=" * len(title), **kwargs)
    print(**kwargs)


def table_rst(role, rows, **kwargs):
    """RST table"""
    print(".. list-table::\n", **kwargs)
    for (name, descr) in rows:
        print(f"   * - {role}`{name}`", **kwargs)
        print(f"     - {descr}", **kwargs)
    print(**kwargs)


def _label(name, **kwargs):
    """RST label"""
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
    """Representation of a Matlab directory"""
    @staticmethod
    def get_lines(f: Iterable[str]) -> Iterable[str]:
        for line in f:
            if not line.startswith('%'):
                break
            yield line[1:].rstrip()

    def __init__(self, pth: Path, rootpath: Path | None = None, recursive: bool = True) -> None:

        def store(container, cls, name, contents):
            try:
                item = cls(name, contents)
            except TypeError:
                pass
            else:
                container.append(item)

        if rootpath is None:
            rootpath = pth.parent
        packs = []
        funcs = []
        cls = []
        self.id = self.make_name(rootpath, pth)
        self.name = pth.stem
        self.descr = pth.name.upper()
        for f in pth.iterdir():
            fpath = pth / f
            name = fpath.stem
            if recursive and f.is_dir():
                if not (name == "private" or name.endswith("@")):
                    packs.append(PackageItem(fpath, rootpath))
            elif f.is_file() and f.suffix == '.m':
                with f.open("rt") as ff:
                    line = next(ff).rstrip()
                    lines = self.get_lines(ff)
                    if line.startswith('%'):
                        try:
                            item = ScriptItem(name, chain([line[1:]], lines))
                        except TypeError:
                            break
                        if f.name == 'Contents.m':
                            self.descr = item.descr
                    elif "function" in line:
                        store(funcs, FunctionItem, name, lines)
                    elif "classdef" in line:
                        store(cls, ClassItem, name, lines)

        self.subpackages = sorted(packs, key=lambda p: p.name)
        self.functions = sorted(funcs, key=lambda f: f.name)
        self.classes = sorted(cls, key=lambda c: c.name)

    def gen(self, file=sys.stdout, recursive: bool = False):
        _label(make_label(self.name), file=file)
        _title(self.name, file=file)

        if recursive and self.subpackages:
            tocitems = [f"{p.id}" for p in self.subpackages]
            _directive("toctree", "", [":hidden:"], tocitems, file=file)
            _directive("rubric", "Modules", [], [], file=file)
            tbl = ((make_label(p.name), p.descr) for p in self.subpackages)
            _table(":ref:", tbl, file=file)

        if self.classes:
            _directive("rubric", "Classes", [], [], file=file)
            _table(":class:", ((c.name, c.descr) for c in self.classes), file=file)

        if self.functions:
            _directive("rubric", "Functions", [], [], file=file)
            _table(":func:", ((f.name, f.descr) for f in self.functions), file=file)

        for c in self.classes:
            c.gen(file=file)

        for f in self.functions:
            f.gen(file=file)

    def generate(self, dest=None, recursive: bool = None):

        if not (self.subpackages or self.functions or self.classes):
            return

        if dest is None:
            self.gen(sys.stdout, recursive=recursive)
        else:
            fn = Path(dest) / "api" / ".".join((self.id, "rst"))
            with fn.open("wt") as f:
                self.gen(f, recursive=recursive)

        if recursive:
            for p in self.subpackages:
                p.generate(dest, recursive=recursive)


class FileItem(DocItem):
    """Representation of a Matlab file (function, script, class)"""
    def __init__(self, name: str, contents: Iterable[str]):
        self.name = name
        self.arguments = ""
        self.descr = ""
        self.contents = list(self.scan(contents))

    def scan(self, src: Iterable[str]):

        def emph(m: re.Match):
            if m.group(2) and not self.arguments:
                self.arguments = m.group(2).lower()
            return "".join(("**", m.group(0).lower(), "**"))

        pattern = f"(?<!\w)(?:(\w+|\[.*?\])\s*=\s*)?(?:{self.name})(\(.*\))?(?!\w)"
        # group(0):  full match
        # group(1):  return value
        # group(2):  arguments
        try:
            line = next(src)
        except StopIteration:
            return

        if "private" in line.lower():
            raise TypeError("private files are excluded")
        self.descr = line.replace(self.name.upper(), "").strip()
        yield self.descr

        for line in src:
            yield re.sub(pattern, emph, line, flags=re.I)


    def gen(self, file=sys.stdout):
        contents = ("".join(("| ", line)) for line in self.contents)
        signature = "".join((self.name, self.arguments))
        _directive("py:function", signature, [], contents, file=file)


class ScriptItem(FileItem):
    """Representation of a Matlab script"""
    pass


class ClassItem(FileItem):
    """Representation of a Matlab class"""
    pass


class FunctionItem(FileItem):
    """Representation of a Matlab function"""
    pass
