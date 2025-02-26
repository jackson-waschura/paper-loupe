"""Paper Loupe - A CLI-based application to manage and prioritize your research paper backlog."""

import os.path

# Read version from VERSION file
with open(os.path.join(os.path.dirname(__file__), "VERSION")) as f:
    __version__ = f.read().strip()
