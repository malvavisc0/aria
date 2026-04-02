"""Vision tool exceptions."""

from aria.tools.errors import ToolError


class VisionError(ToolError):
    """Base exception for vision operations."""

    code = "VISION_ERROR"
    recoverable = False
    how_to_fix = "Check the file and try again."


class VisionFileNotFoundError(VisionError):
    """File not found for vision processing."""

    code = "FILE_NOT_FOUND"
    recoverable = False
    how_to_fix = "Verify the file path exists and check permissions."


class UnsupportedFormatError(VisionError):
    """Unsupported file format."""

    code = "UNSUPPORTED_FORMAT"
    recoverable = False
    how_to_fix = (
        "Provide a PDF or image file. Supported image formats: "
        "PNG, JPEG, WebP, GIF, BMP, TIFF."
    )


class VLModelError(VisionError):
    """Vision-language model request failed."""

    code = "VL_MODEL_ERROR"
    recoverable = True
    how_to_fix = "The VL model failed. Text-based fallback will be attempted automatically."
