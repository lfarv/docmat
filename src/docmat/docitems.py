from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from itertools import chain
from pathlib import Path
from typing import TextIO

from .builders import Builder, RstBuilder


class DocItem:
    """Base class for documentation items"""

    node: dict[str, PackageItem] = {}
    leaf: dict[str, FileItem] = {}


class PackageItem(DocItem):
    """Representation of a Matlab directory"""

    MATLAB_EXTENSION = ".m"
    PRIVATE_DIR = "private"
    CONTENTS_FILE = "Contents.m"

    @staticmethod
    def make_name(rootpath: Path, pth: Path) -> str:
        relpath = pth.relative_to(rootpath)
        return ".".join(relpath.parts)

    @staticmethod
    def make_label(name: str) -> str:
        return f"{name.replace(' ', '-').casefold()}_module"

    @staticmethod
    def get_lines(f: Iterable[str]) -> Iterator[str]:
        # Skip initial lines not starting with % (continuation of function signature)
        for line in f:
            if line.startswith("%"):
                yield line[1:].strip()
                break
        # Stop at the end of the docstring
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
        if rootpath is None:
            rootpath = pth.parent

        self.id = self.make_name(rootpath, pth)
        self.name = pth.stem
        self.descr = pth.name.upper()

        self.subpackages: list = []
        self.functions: list = []
        self.classes: list = []

        self._process_directory(pth, rootpath, recursive)
        self._sort_items()

    def _process_directory(self, pth: Path, rootpath: Path, recursive: bool) -> None:
        for file_path in pth.iterdir():
            if recursive and file_path.is_dir():
                self._handle_subdirectory(file_path, rootpath)
            elif file_path.is_file() and file_path.suffix == self.MATLAB_EXTENSION:
                self._process_matlab_file(file_path)

    def _handle_subdirectory(self, dir_path: Path, rootpath: Path) -> None:
        name = dir_path.stem
        if not (name == self.PRIVATE_DIR or name.endswith("@")):
            item = PackageItem(dir_path, rootpath)
            if item.sz > 0:
                self.node[name.casefold()] = item
                self.subpackages.append(item)

    def _process_matlab_file(self, file_path: Path) -> None:
        name = file_path.stem
        with file_path.open("rt") as ff:
            first_line = next(ff).rstrip()
            lines = self.get_lines(ff)

            if first_line.startswith("%"):
                self._handle_script_file(name, first_line, lines, file_path)
            elif "function" in first_line:
                self._store_item(self.functions, FunctionItem, name, lines)
            elif "classdef" in first_line:
                self._store_item(self.classes, ClassItem, name, lines)

    def _handle_script_file(
        self, name: str, first_line: str, lines: Iterable[str], file_path: Path
    ) -> None:
        try:
            item = ScriptItem(name, chain([first_line[1:]], lines))
            if file_path.name == self.CONTENTS_FILE:
                self.descr = item.descr
        except TypeError:
            return

    def _store_item(
        self, container: list, cls: type, name: str, contents: Iterator[str]
    ) -> None:
        try:
            item = cls(name, contents)
        except TypeError:
            return
        self.leaf[name.casefold()] = item
        container.append(item)

    def _sort_items(self) -> None:
        self.subpackages.sort(key=lambda p: p.name)
        self.functions.sort(key=lambda f: f.name)
        self.classes.sort(key=lambda c: c.name)

    @property
    def sz(self) -> int:
        return len(self.subpackages) + len(self.functions) + len(self.classes)

    def gen(
        self,
        file: TextIO | None = None,
        recursive: bool = True,
        builder: type[Builder] = RstBuilder,
    ) -> None:
        self._generate_header(file, builder)
        self._generate_package_section(file, recursive, builder)
        self._generate_class_section(file, builder)
        self._generate_function_section(file, builder)
        self._generate_items(file, builder)

    def _generate_header(self, file: TextIO | None, builder: type[Builder]) -> None:
        builder.label(self.make_label(self.name), file=file)
        builder.title(self.name, file=file)

    def _generate_package_section(
        self, file: TextIO | None, recursive: bool, builder: type[Builder]
    ) -> None:
        if recursive and self.subpackages:
            tocitems = [f"{p.id}" for p in self.subpackages]
            builder.directive("toctree", "", [":hidden:"], tocitems, file=file)
            builder.directive("rubric", "Modules", [], [], file=file)
            tbl = (
                (builder.role("ref", self.make_label(p.name)), p.descr)
                for p in self.subpackages
            )
            builder.table(tbl, file=file)

    def _generate_class_section(
        self, file: TextIO | None, builder: type[Builder]
    ) -> None:
        if self.classes:
            tbl = ((builder.role("class", c.name), c.descr) for c in self.classes)
            builder.directive("rubric", "Classes", [], [], file=file)
            builder.table(tbl, file=file)

    def _generate_function_section(
        self, file: TextIO | None, builder: type[Builder]
    ) -> None:
        if self.functions:
            tbl = ((builder.role("func", f.name), f.descr) for f in self.functions)
            builder.directive("rubric", "Functions", [], [], file=file)
            builder.table(tbl, file=file)

    def _generate_items(self, file: TextIO | None, builder: type[Builder]) -> None:
        for c in self.classes:
            c.gen(file=file, builder=builder)
        for f in self.functions:
            f.gen(file=file, builder=builder)

    def generate(
        self, dest=None, recursive: bool = True, builder: type[Builder] = RstBuilder
    ) -> None:
        if dest is None:
            self.gen(recursive=recursive, builder=builder)
        else:
            fn = Path(dest) / "api" / "".join((self.id, builder.suffix))
            with fn.open("wt") as f:
                self.gen(file=f, recursive=recursive, builder=builder)

        if recursive:
            for p in self.subpackages:
                p.generate(dest, recursive=recursive, builder=builder)


class FileItem(DocItem):
    """Representation of a Matlab file (function, script, class)."""

    role = "obj"
    defn = "py:function"

    def __init__(self, name: str, contents: Iterator[str]):
        """Initialize FileItem with name and contents.

        Args:
            name: Name of the Matlab file
            contents: Iterable of strings containing file contents
        """
        self.name = name
        self.arguments = ""
        self.descr = ""
        self.see_also: list[str] = []
        self.contents = list(self.scan(contents))

    def target(self, name, builder):
        try:
            target = self.leaf[name]
        except KeyError:
            print(f"Undefined name in {self.name}: {name}")
            return builder.role("func", name)
        else:
            return builder.role(target.role, target.name)

    def _process_h1(self, line: str) -> str:
        """Process the first line of content."""
        if "private" in line.casefold():
            raise TypeError("private files are excluded")
        return line.replace(self.name.upper(), "").strip()

    def _process_see_also(self, line: str, start_idx: int) -> None:
        """Extract 'see also' references from line."""
        self.see_also = [
            v.casefold() for v in re.findall(r"\w+", line[start_idx + 9 :])
        ]

    def scan(self, src: Iterator[str]) -> Iterator[str]:
        """Scan contents to extract documentation elements."""

        def make_strong(match: re.Match) -> str:
            if match.group(2) and not self.arguments:
                self.arguments = match.group(2).casefold()
            item = match.group(0).casefold().replace(self.name.casefold(), self.name)
            return f"**{item}**"

        # regex pattern for matching function declarations.
        pattern = rf"(?<!\w)(?:(\w+|\[.*?\])\s*=\s*)?{self.name}(\(.*\))?(?!\w)"
        # group(0):  full match
        # group(1):  return value
        # group(2):  arguments

        try:
            first_line = next(src)
        except StopIteration:
            return

        self.descr = self._process_h1(first_line)
        yield self.descr

        for line in src:
            idx = line.find("See also")
            if idx >= 0:
                self._process_see_also(line, idx)
            else:
                yield re.sub(pattern, make_strong, line, flags=re.I)

    def gen(
        self, file: TextIO | None = None, builder: type[Builder] = RstBuilder
    ) -> None:
        """Generate documentation output."""
        contents = self.contents
        if self.see_also:
            sa = [self.target(v, builder) for v in self.see_also]
            contents.append(f"See also {', '.join(sa)}")
        body = builder.line_block(contents) if contents else ()
        signature = f"{self.name}{self.arguments}"
        builder.directive(self.defn, signature, [], body, file=file)


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
