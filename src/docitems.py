from __future__ import annotations

import sys
from collections.abc import Iterable
from itertools import chain
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

    @staticmethod
    def get_lines(f: Iterable[str]) -> Iterable[str]:
        for line in f:
            if not line.startswith('%'):
                break
            yield line[1:-1].rstrip()

    def __init__(self, pth: Path, rootpath: Path | None = None) -> None:
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
            if f.is_dir():
                packs.append(PackageItem(fpath, rootpath))
            elif f.is_file() and f.suffix == '.m':
                with f.open("rt") as ff:
                    line = next(ff)
                    lines = self.get_lines(ff)
                    if line.startswith('%'):
                        item = ScriptItem(fpath.stem, chain([line[1:]], lines))
                        if f.name == 'Contents.m':
                            self.descr = item.descr
                    elif "function" in line:
                        funcs.append(FunctionItem(fpath.stem, lines))
                    elif "class" in line:
                        cls.append(ClassItem(fpath.stem, lines))

        self.subpackages = packs
        self.functions = funcs
        self.classes = cls

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

            if self.classes:
                _directive("rubric", "Classes", [], [], file=file)
                _table(":class:", ((f.name, f.descr) for f in self.functions), file=file)
                for f in self.classes:
                    contents = ("".join(("| ", line)) for line in f.contents)
                    _directive("py:class", f.name, [], contents, file=file)

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


class FileItem(DocItem):
    def __init__(self, name: str, contents: Iterable[str]):
        self.name = name
        self.contents = list(contents)
        try:
            descr=self.contents[0]
        except IndexError:
            descr = ""
        self.descr = descr


class ScriptItem(FileItem):
    pass


class ClassItem(FileItem):
    pass


class FunctionItem(FileItem):
    pass
