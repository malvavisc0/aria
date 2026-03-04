"""Constants for vision tools output paths."""

from aria.tools.constants import BASE_DIR

VISION_OUTPUT_DIR = BASE_DIR / "vision"
VISION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
