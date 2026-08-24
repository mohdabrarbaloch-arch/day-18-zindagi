"""Conftest — ensure the temp DB env is set before app import in tests."""

import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp.name}")
