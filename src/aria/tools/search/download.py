"""Download and convert content from a URL."""

from typing import Dict, Optional

from aria.tools import (
    log_tool_call,
    tool_error_response,
    tool_success_response,
)
from aria.tools.search._download_internals import (
    _fetch_file,
    _save_content_to_file,
    _validate_format,
    _validate_url,
)
from aria.tools.search._youtube import (
    get_youtube_video_transcription as _get_youtube_transcript,
)
from aria.tools.search.constants import DOWNLOADS_DIR, MAX_FILE_SIZE


class URLDownloadError(Exception):
    """Custom exception for URL download errors.

    Raised when there are issues with downloading content from a URL,
    such as invalid URLs, network timeouts, or HTTP errors.
    """


class UnknownOutputError(Exception):
    """Custom exception when the output is not supported.

    Raised when an unsupported output format is specified for content
    conversion.
    """


class ContentParsingError(Exception):
    """Custom exception for content parsing errors.

    Raised when there are issues processing or converting content after
    downloading.
    """


@log_tool_call
def get_file_from_url(
    intent: str,
    url: str,
    output: Optional[str] = "auto",
    custom_headers: Optional[Dict[str, str]] = None,
    max_size: Optional[int] = None,
    download_path: Optional[str] = None,
) -> str:
    """Download a file from a URL (PDFs, images, archives, etc.).

    This function is for downloading files only:
    - PDFs, DOCX, XLSX
    - Images, videos, audio
    - ZIP, TAR, archives
    - Raw data files (JSON, CSV, XML)
    - Static HTML pages (when explicitly needed)

    Args:
        intent: Why you're downloading (e.g., "Downloading PDF report")
        url: Direct URL to the file
        output: Format - auto/markdown/text/binary (default: auto)
        custom_headers: Optional HTTP headers
        max_size: Max bytes (default: 5MB)
        download_path: Save directory (default: DOWNLOADS_DIR)

    Returns:
        JSON with file_path, mime_type, size_bytes.
    """
    try:
        validated_url = _validate_url(url)
        output_value = output or "auto"
        validated_format = _validate_format(output_value)
        max_size_value = MAX_FILE_SIZE if max_size is None else max_size

        if not download_path:
            download_path_value = str(DOWNLOADS_DIR)
        else:
            download_path_value = download_path

        response_data, content_type, filename = _fetch_file(
            validated_url,
            custom_headers=custom_headers,
            max_size=max_size_value,
        )

        file_path, metadata = _save_content_to_file(
            response_data,
            validated_url,
            content_type or "application/octet-stream",
            validated_format,
            original_filename=filename,
            download_path=download_path_value,
        )

        return tool_success_response(
            "get_file_from_url",
            intent,
            {"file_path": file_path, "metadata": metadata},
        )

    except URLDownloadError as exc:
        return tool_error_response("get_file_from_url", intent, exc)
    except ContentParsingError as exc:
        return tool_error_response("get_file_from_url", intent, exc)
    except Exception as exc:
        return tool_error_response("get_file_from_url", intent, exc)


# Re-export YouTube function for backwards compatibility
def get_youtube_video_transcription(
    intent: str,
    url: str,
    download_path: Optional[str] = None,
) -> str:
    """Save a YouTube video's full captions/transcript as a text file.

    Args:
        intent: Why you're getting the transcript
        url: YouTube video URL
        download_path: Optional path to save the transcript

    Returns:
        JSON string with file path and metadata
    """
    return _get_youtube_transcript(intent, url, download_path)
