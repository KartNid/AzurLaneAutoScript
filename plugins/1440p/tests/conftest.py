import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
UPSTREAM = Path(os.environ.get('ALAS_PLUGIN_TEST_ROOT', os.getcwd())).resolve()
sys.path.insert(0, str(UPSTREAM))
os.chdir(str(UPSTREAM))

import alas_1440p
alas_1440p.activate(UPSTREAM)

# Keep the existing probe tests against the independently packaged diagnostic.
import alas_1440p.probe as probe
probe.ROOT = UPSTREAM
sys.modules['dev_tools.resolution_probe'] = probe
