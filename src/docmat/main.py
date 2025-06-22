#! env python
import sys
from pathlib import Path

from .docitems import PackageItem


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "."
    source = Path(source).expanduser().resolve()
    rootpath = source / "atmat"
    dest = source / "docs" / "m"
    doc = PackageItem(rootpath, recursive=False)
    doc.generate(dest, recursive=False)
    for module in ["atphysics", "atplot", "attrack", "atutils", "lattice"]:
        doc = PackageItem(rootpath / module)
        doc.generate(dest, recursive=True)


# Press the green button in the gutter to run the script.
if __name__ == "__main__":
    main()


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
