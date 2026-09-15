"""Optional neutral HITL rendering; use the same overlay for all formal conditions.

Run from repository root with PYTHONPATH containing the repository root and
DJANGO_SETTINGS_MODULE=evaluation.baselines.common.presentation_settings.
Database location/handling remain the existing Layer 3 defaults.
"""
import copy
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAYER3 = ROOT / 'layer3'
sys.path.insert(0, str(LAYER3))
sys.path.insert(0, str(LAYER3 / 'dashboard'))
spec = importlib.util.spec_from_file_location('_baseline_original_django_settings', LAYER3 / 'dashboard/settings.py')
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
for name in dir(original):
    if name.isupper():
        globals()[name] = copy.deepcopy(getattr(original, name))
TEMPLATES[0]['DIRS'] = [str(Path(__file__).parent / 'templates')] + list(TEMPLATES[0]['DIRS'])
