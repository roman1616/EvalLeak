"""Module entry point so `python -m evalleak` works."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
