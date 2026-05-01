#!/usr/bin/env python3
"""
Backward-compatible entry point.
Delegates to src.cli for the legacy email digest workflow.
"""

from src.cli import main

if __name__ == "__main__":
    main()
