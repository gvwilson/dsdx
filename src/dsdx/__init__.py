"""Utilities."""

import random
import sys


def dsdx(func):
    if len(sys.argv) > 1:
        random.seed(int(sys.argv[1]))
    func()
