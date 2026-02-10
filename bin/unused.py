#!/usr/bin/env python

"""Find unused files."""

from pathlib import Path
import re
import sys


DATA_INC = re.compile(r'data-inc="(.+?)"')
SUFFIXES = {".py", ".sh", ".sql", ".txt"}


def main():
    for filename in sys.argv[1:]:
        filename = Path(filename)
        dirname = filename.parent
        actual = {str(p) for p in dirname.iterdir() if interesting(p)}
        expected = set(DATA_INC.findall(filename.read_text()))
        unused = actual - expected
        if unused:
            if len(sys.argv) > 2:
                print(filename)
                for name in sorted(unused):
                    print("-", name)
            else:
                for name in sorted(unused):
                    print(name)


def interesting(p):
    return p.suffix in SUFFIXES


if __name__ == "__main__":
    main()
