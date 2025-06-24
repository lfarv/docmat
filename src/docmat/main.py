#! env python
import sys
from pathlib import Path

from .docitems import PackageItem
from .builders import MystBuilder


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "."
    source = Path(source).expanduser().resolve()
    rootpath = source / "atmat"
    dest = source / "docs" / "m"
    doc = PackageItem(rootpath, rootpath, recursive=True)
    doc.subpackages.append(PackageItem(rootpath, recursive=False))
    package = {p.name: p for p in doc.subpackages}
    for module in [
        "atphysics",
        "atplot",
        "attrack",
        "atutils",
        "lattice",
        "atmat",
        "atmatch",
    ]:
        package[module].generate(dest, recursive=True)


# Press the green button in the gutter to run the script.
if __name__ == "__main__":
    main()


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
