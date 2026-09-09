"""Shared configuration and portable local-result paths for ADM detectors."""

import json
import os
from pathlib import Path
from typing import Any, Dict


LAYER1_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "detector_config.json"


def load_detector_config(detector_name: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Load and validate known settings, retaining safe code defaults."""
    config_path = Path(os.environ.get("LAYER1_DETECTOR_CONFIG", DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        return dict(defaults)
    with config_path.open() as config_file:
        config = json.load(config_file)
    settings = config.get(detector_name, {})
    if not isinstance(settings, dict):
        raise ValueError(f"Detector configuration for {detector_name!r} must be an object")
    resolved = dict(defaults)
    for key, value in settings.items():
        if key not in defaults:
            raise ValueError(f"Unknown {detector_name!r} setting: {key}")
        if isinstance(defaults[key], (int, float)) and not isinstance(value, (int, float)):
            raise ValueError(f"{detector_name!r}.{key} must be numeric")
        resolved[key] = value
    return resolved


def detector_results_path(filename: str) -> Path:
    """Return a portable, overrideable location for local evaluation copies."""
    directory = Path(os.environ.get("LAYER1_RESULTS_DIR", LAYER1_ROOT / "runtime_results"))
    directory.mkdir(parents=True, exist_ok=True)
    return directory / filename
