import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("MMT_DATA_DIR", tempfile.mkdtemp(prefix="mmt_test_"))
os.environ.setdefault("MMT_WORKER", "0")
os.environ.setdefault("MMT_SAUVEGARDE_AUTO", "0")
