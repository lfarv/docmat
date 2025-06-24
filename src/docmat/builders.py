from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TextIO


class Builder(ABC):
    """
    Abstract base class for documentation builders.

    This class defines the interface for all documentation builders.
    Subclasses must implement all abstract methods to provide
    format-specific rendering of documentation elements.
    """

    suffix = ""

    @staticmethod
    @abstractmethod
    def directive(
        directive: str,
        argument: str,
        options: Iterable[str],
        contents: Iterable[str],
        file: TextIO | None = None,
    ) -> None:
        """
        Generate a directive in the target format.

        Args:
            directive: The directive name
            argument: The directive argument
            options: List of directive options
            contents: List of content lines
            file: File-like object to write to (defaults to sys.stdout)
        """
        ...

    @staticmethod
    @abstractmethod
    def role(role_name: str, value: str) -> str:
        """
        Generate a role reference in the target format.

        Args:
            role_name: The name of the role
            value: The value for the role

        Returns:
            A formatted string representing the role
        """
        ...

    @staticmethod
    @abstractmethod
    def title(title: str, file: TextIO | None = None) -> None:
        """
        Generate a title in the target format.

        Args:
            title: The title text
            file: File-like object to write to (defaults to sys.stdout)
        """
        ...

    @staticmethod
    @abstractmethod
    def table(rows: Iterable[tuple[str, str]], file: TextIO | None = None) -> None:
        """
        Generate a table in the target format.

        Args:
            rows: Iterable of (name, description) tuples
            file: File-like object to write to (defaults to sys.stdout)
        """
        ...

    @staticmethod
    @abstractmethod
    def label(name: str, file: TextIO | None = None) -> None:
        """
        Generate a label in the target format.

        Args:
            name: The label name
            file: File-like object to write to (defaults to sys.stdout)
        """
        ...

    @staticmethod
    @abstractmethod
    def line_block(inpt: Iterable[str]) -> Iterable[str]:
        """
        Generate a line block in the target format.

        Args:
            inpt: Iterable of strings representing lines of text

        Returns:
            Iterable of strings representing the formatted line block
        """
        ...


class RstBuilder(Builder):
    """
    reStructuredText (RST) builder for documentation.

    Generates documentation in the reStructuredText format used by Sphinx.
    """

    suffix = ".rst"

    @staticmethod
    def directive(
        directive: str,
        argument: str,
        options: Iterable[str],
        contents: Iterable[str],
        file: TextIO | None = None,
    ) -> None:
        """
        Generate an RST directive.

        Args:
            directive: The directive name
            argument: The directive argument
            options: List of directive options
            contents: List of content lines
            file: File-like object to write to (defaults to sys.stdout)
        """
        if argument:
            print(f".. {directive}:: {argument}", file=file)
        else:
            print(f".. {directive}::", file=file)
        for opt in options:
            print(f"   {opt}", file=file)
        print(file=file)
        for line in contents:
            print("  ", line, file=file)
        print(file=file)

    @staticmethod
    def role(role_name: str, value: str) -> str:
        """
        Generate an RST role reference.

        Args:
            role_name: The name of the role
            value: The value for the role

        Returns:
            A formatted string representing the role
        """
        return f":{role_name}:`{value}`"

    @staticmethod
    def title(title: str, file: TextIO | None = None) -> None:
        """
        Generate an RST title.

        Args:
            title: The title text
            file: File-like object to write to (defaults to sys.stdout)
        """
        print(title, file=file)
        print("=" * len(title), file=file)
        print(file=file)

    @staticmethod
    def table(rows: Iterable[tuple[str, str]], file: TextIO | None = None) -> None:
        """
        Generate an RST table.

        Args:
            rows: Iterable of (name, description) tuples
            file: File-like object to write to (defaults to sys.stdout)
        """
        print(".. list-table::\n", file=file)
        for name, descr in rows:
            print(f"   * - {name}", file=file)
            print(f"     - {descr}", file=file)
        print(file=file)

    @staticmethod
    def label(name: str, file: TextIO | None = None) -> None:
        """
        Generate an RST label.

        Args:
            name: The label name
            file: File-like object to write to (defaults to sys.stdout)
        """
        print(f".. _{name}:\n", file=file)

    @staticmethod
    def line_block(inpt: Iterable[str]) -> Iterable[str]:
        """
        Generate an RST line block.

        Args:
            inpt: Iterable of strings representing lines of text

        Returns:
            Iterable of strings representing the formatted line block
        """
        for line in inpt:
            if line:
                yield "| " + line
            else:
                yield line


class MystBuilder(Builder):
    """
    MyST Markdown builder for documentation.

    Generates documentation in the MyST Markdown format, which is a superset of
    CommonMark Markdown with added support for Sphinx directives and roles.
    """

    suffix = ".md"

    @staticmethod
    def directive(
        directive: str,
        argument: str,
        options: Iterable[str],
        contents: Iterable[str],
        file: TextIO | None = None,
    ) -> None:
        """
        Generate a MyST directive.

        Args:
            directive: The directive name
            argument: The directive argument
            options: List of directive options
            contents: List of content lines
            file: File-like object to write to (defaults to sys.stdout)
        """
        if argument:
            print(f":::{{{directive}}} {argument}", file=file)
        else:
            print(f":::{{{directive}}}", file=file)
        for opt in options:
            print(f"{opt}", file=file)
            print(file=file)
        for line in contents:
            print(line, file=file)
        print(":::\n", file=file)

    @staticmethod
    def role(role_name: str, value: str) -> str:
        """
        Generate a MyST role reference.

        Args:
            role_name: The name of the role
            value: The value for the role

        Returns:
            A formatted string representing the role
        """

        return f"{{{role_name}}}`{value}`"

    @staticmethod
    def title(title: str, file: TextIO | None = None) -> None:
        """
        Generate a MyST title.

        Args:
            title: The title text
            file: File-like object to write to (defaults to sys.stdout)
        """
        print(f"# {title}\n", file=file)

    @staticmethod
    def table(rows: Iterable[tuple[str, str]], file: TextIO | None = None) -> None:
        """
        Generate a MyST table.

        Args:
            rows: Iterable of (name, description) tuples
            file: File-like object to write to (defaults to sys.stdout)
        """
        if rows:
            print("| Name | Description |", file=file)
            print("| ---- | ----------- |", file=file)
            for name, descr in rows:
                print(f"| {name} | {descr} |", file=file)
            print(file=file)

    @staticmethod
    def label(name: str, file: TextIO | None = None) -> None:
        """
        Generate a MyST label.

        Args:
            name: The label name
            file: File-like object to write to (defaults to sys.stdout)
        """
        print(f"({name})=", file=file)

    @staticmethod
    def line_block(inpt: Iterable[str]) -> Iterable[str]:
        """
        Generate a MyST line block.

        Args:
            inpt: Iterable of strings representing lines of text

        Returns:
            Iterable of strings representing the formatted line block
        """
        yield ":::{line-block}"
        yield from inpt
        yield ":::\n"
