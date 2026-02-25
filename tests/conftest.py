"""
conftest.py — shared pytest fixtures and test-environment setup.

Streamlit must be stubbed before any project module is imported, because
data_processing.py and utils.py apply @st.cache_data decorators and call
st.error() at module scope or inside tested functions.

The stub makes @st.cache_data a transparent (no-op) decorator so tested
functions behave identically to their un-decorated originals, and st.error()
is a silent no-op so exception-handling paths can be exercised without a
running Streamlit server.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# ── 1. Ensure project root is on sys.path ────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── 2. Stub streamlit before any project imports ─────────────────────────────
def _transparent_cache_data(*args, **kwargs):
    """
    Returns a no-op decorator so @st.cache_data(ttl=...) and @st.cache_data
    both leave the wrapped function unchanged, avoiding the need for a running
    Streamlit server.
    """
    def decorator(fn):
        return fn
    # Handle @st.cache_data (no args) vs @st.cache_data(ttl=1800) (with args)
    if len(args) == 1 and callable(args[0]):
        return args[0]
    return decorator


_st_stub = MagicMock()
_st_stub.cache_data = _transparent_cache_data

# Force the stub in before streamlit (or anything that imports it) is loaded.
sys.modules["streamlit"] = _st_stub
