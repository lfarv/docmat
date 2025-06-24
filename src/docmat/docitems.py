from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from itertools import chain
from pathlib import Path

from .builders import Builder, RstBuilder


class DocItem:
    """Base class for documentation items"""

    role = "obj"
    defn = "py:function"
    node = {}
    leaf = {}

    def target(self, name, builder):
        try:
            target = self.leaf[name]
        except KeyError:
            print(f"Undefined name in {self.name}: {name}")
            return builder.role("func", name)
        else:
            return builder.role(target.role, target.name)


class PackageItem(DocItem):
    """Representation of a Matlab directory"""

    @staticmethod
    def make_name(rootpath, pth):
        relpath = pth.relative_to(rootpath)
        return ".".join(relpath.parts)

    @staticmethod
    def make_label(name):
        return f"{name.replace(' ', '-').casefold()}_module"

    @staticmethod
    def get_lines(f: Iterable[str]) -> Iterable[str]:
        for line in f:
            if not line.startswith("%"):
                break
            yield line[1:].rstrip()

    def __init__(
        self,
        pth: Path,
        rootpath: Path | None = None,
        recursive: bool = True,
    ) -> None:
        def store(container, cls, name, contents):
            try:
                item = cls(name, contents)
            except TypeError:
                pass
            else:
                self.leaf[name.casefold()] = item
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
            name = f.stem
            if recursive and f.is_dir():
                if not (name == "private" or name.endswith("@")):
                    item = PackageItem(f, rootpath)
                    if item.sz > 0:
                        self.node[name.casefold()] = item
                        packs.append(item)
            elif f.is_file() and f.suffix == ".m":
                with f.open("rt") as ff:
                    line = next(ff).rstrip()
                    lines = self.get_lines(ff)
                    if line.startswith("%"):
                        try:
                            item = ScriptItem(name, chain([line[1:]], lines))
                        except TypeError:
                            break
                        if f.name == "Contents.m":
                            self.descr = item.descr
                    elif "function" in line:
                        store(funcs, FunctionItem, name, lines)
                    elif "classdef" in line:
                        store(cls, ClassItem, name, lines)

        self.subpackages = sorted(packs, key=lambda p: p.name)
        self.functions = sorted(funcs, key=lambda f: f.name)
        self.classes = sorted(cls, key=lambda c: c.name)

    @property
    def sz(self):
        return len(self.subpackages) + len(self.functions) + len(self.classes)

    def gen(
        self,
        file=sys.stdout,
        recursive: bool = False,
        builder: type[Builder] = RstBuilder,
    ):
        builder.label(self.make_label(self.name), file=file)
        builder.title(self.name, file=file)

        if recursive and self.subpackages:
            tocitems = [f"{p.id}" for p in self.subpackages]
            builder.directive("toctree", "", [":hidden:"], tocitems, file=file)
            builder.directive("rubric", "Modules", [], [], file=file)
            tbl = (
                (builder.role("ref", self.make_label(p.name)), p.descr)
                for p in self.subpackages
            )
            builder.table(tbl, file=file)

        if self.classes:
            tbl = ((builder.role("class", c.name), c.descr) for c in self.classes)
            builder.directive("rubric", "Classes", [], [], file=file)
            builder.table(tbl, file=file)

        if self.functions:
            tbl = ((builder.role("func", f.name), f.descr) for f in self.functions)
            builder.directive("rubric", "Functions", [], [], file=file)
            builder.table(tbl, file=file)

        for c in self.classes:
            c.gen(file=file, builder=builder)

        for f in self.functions:
            f.gen(file=file, builder=builder)

    def generate(
        self, dest=None, recursive: bool = None, builder: type[Builder] = RstBuilder
    ):
        if dest is None:
            self.gen(sys.stdout, recursive=recursive, builder=builder)
        else:
            fn = Path(dest) / "api" / "".join((self.id, builder.suffix))
            with fn.open("wt") as f:
                self.gen(f, recursive=recursive, builder=builder)

        if recursive:
            for p in self.subpackages:
                p.generate(dest, recursive=recursive, builder=builder)


class FileItem(DocItem):
    """Representation of a Matlab file (function, script, class)"""

    role = "obj"

    def __init__(self, name: str, contents: Iterable[str]):
        self.name = name
        self.arguments = ""
        self.descr = ""
        self.see_also = []
        self.contents = list(self.scan(contents))

    def scan(self, src: Iterable[str]):
        def strong(m: re.Match):
            if m.group(2) and not self.arguments:
                self.arguments = m.group(2).casefold()
            nm = self.name
            item = m.group(0).casefold().replace(nm.casefold(), nm)
            return "".join(("**", item, "**"))

        pattern = rf"(?<!\w)(?:(\w+|\[.*?\])\s*=\s*)?{self.name}(\(.*\))?(?!\w)"
        # group(0):  full match
        # group(1):  return value
        # group(2):  arguments
        try:
            line = next(src)
        except StopIteration:
            return

        if "private" in line.casefold():
            raise TypeError("private files are excluded")
        self.descr = line.replace(self.name.upper(), "").strip()
        yield self.descr

        for line in src:
            idx = line.find("See also")
            if idx >= 0:
                self.see_also = [
                    v.casefold() for v in re.findall(r"\w+", line[idx + 9 :])
                ]
            else:
                yield re.sub(pattern, strong, line, flags=re.I)

    def gen(self, file=sys.stdout, builder: type[Builder] = RstBuilder):
        contents = self.contents
        if self.see_also:
            sa = [self.target(v, builder) for v in self.see_also]
            contents.append("See also " + ", ".join(sa))
        contents = builder.line_block(contents) if contents else ()
        signature = "".join((self.name, self.arguments))
        builder.directive(self.defn, signature, [], contents, file=file)


class ScriptItem(FileItem):
    """Representation of a Matlab script"""

    pass


class ClassItem(FileItem):
    """Representation of a Matlab class"""

    role = "class"
    defn = "py:class"


class FunctionItem(FileItem):
    """Representation of a Matlab function"""

    role = "func"
    defn = "py:function"
