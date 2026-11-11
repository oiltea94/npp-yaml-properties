"""Select the target under test using YP_ARCH, defaulting to x64."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_config import TARGETS, architecture, target_dir, pe_machine

ARCH = architecture()
BUILD = target_dir('build', ARCH)
DIST = target_dir('dist', ARCH)
EVIDENCE = target_dir('evidence', ARCH)
EVIDENCE.mkdir(parents=True, exist_ok=True)
RUNTIME = target_dir('.runtime', ARCH)
NPP_DIR = Path(os.environ.get('NPP_TEST_DIR', r'C:\Program Files\Notepad++'))
