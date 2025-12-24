# Prevent import filename collisions when a similarly-named module exists inside
# the package source. Some test modules share basenames with helper modules in
# `src/` during development; that can cause an import-file mismatch error during
# pytest collection. Remove any existing module object so pytest can import the
# test file by its path.
import sys

if "test_panns_device_selection" in sys.modules:
    del sys.modules["test_panns_device_selection"]
