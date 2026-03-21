"""conftest.py: Add src/ and each src/pkg/ to sys.path for all tests.

For top-level packages like `roomba_cleaning_nav`, the import root is `src/`.
For nested ROS2-style packages like `roomba_autonomous_cleaning` which contain
an inner package of the same name (src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/),
we add `src/<pkg>/` as well so that `from roomba_autonomous_cleaning.config import ...` works.
However, for the namespace-qualified form `from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models`,
having only `src/` in sys.path is sufficient.
"""
import sys
import os

repo_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(repo_root, "src")

# Add the src/ directory so all top-level packages are importable
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Also add each sub-package root so inner packages can be imported directly.
# e.g. src/roomba_autonomous_cleaning/ is added so that
#   `from roomba_autonomous_cleaning.models import ...` works.
for pkg in sorted(os.listdir(src_dir)):
    pkg_path = os.path.join(src_dir, pkg)
    if os.path.isdir(pkg_path) and pkg_path not in sys.path:
        sys.path.append(pkg_path)
