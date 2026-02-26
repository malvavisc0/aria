"""Download and convert content from a URL."""

import inspect
import json
import mimetypes
import os
import random
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union
from urllib.parse import urlparse

import httpx
from loguru import logger
from markitdown import MarkItDown
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)
from youtube_transcript_api.formatters import TextFormatter

from aria.tools.search.constants import (
    BINARY_CONTENT_TYPES,
    DOWNLOADS_DIR,
    HTML_CONTENT_TYPES,
    MAX_FILE_SIZE,
    MAX_RETRIES,
    SUPPORTED_FORMATS,
    TIMEOUT,
    USER_AGENTS,
)


class URLDownloadError(Exception):
    """
    Custom exception for URL download errors.

    Raised when there are issues with downloading content from a URL,
    such as invalid URLs, network timeouts, or HTTP errors.
    """


class AntiBotDetectedError(Exception):
    """
    Custom exception for anti-bot detection.

    Raised when the target server detects automated access and blocks the
    request.
    """


class UnknownOutputError(Exception):
    """
    Custom exception when the output is not supported.

    Raised when an unsupported output format is specified for content
    conversion.
    """


class ContentParsingError(Exception):
    """
    Custom exception for content parsing errors.

    Raised when there are issues processing or converting content after
    downloading.
    """


def get_file_from_url(
    intent: str,
    url: str,
    output: Optional[str] = "auto",
    custom_headers: Optional[Dict[str, str]] = None,
    max_size: Optional[int] = MAX_FILE_SIZE,
    download_path: Optional[str] = str(DOWNLOADS_DIR),
) -> str:
    """
    Download URL content to disk and optionally convert it
    (markdown/text/binary).

    Args:
        intent: Why you're downloading (e.g., "Reading article")
        url: URL to download
        output: Format - auto/markdown/text/binary (default: auto)
        custom_headers: Optional HTTP headers
        max_size: Max bytes (default: 50MB)
        download_path: Save directory (default: DOWNLOADS_DIR)

    Returns:
        JSON with file_path, content (if text), mime_type, size_bytes.
        Supports HTML, PDF, DOCX, images, YouTube transcripts.
    """
    logger.info(
        f"get_file_from_url called with url='{url}', "
        f"output='{output}', download_path='{download_path}'"
    )

    try:
        # Validate inputs
        validated_url = _validate_url(url)
        output_value = output or "auto"
        validated_format = _validate_format(output_value)
        max_size_value = MAX_FILE_SIZE if max_size is None else max_size
        # Treat empty string like None so downloads go under DOWNLOADS_DIR.
        if not download_path:
            download_path_value = str(DOWNLOADS_DIR)
        else:
            download_path_value = download_path
        logger.debug(f"URL validated: {validated_url}, format: {validated_format}")

        frame = inspect.currentframe()
        if frame:
            func_name = frame.f_code.co_name
            logger.debug(f"Calling {func_name} to achieve: {intent}")

        # Download the file
        logger.debug(f"Fetching file from {validated_url}")
        response_data, content_type, filename = _fetch_file(
            validated_url,
            custom_headers=custom_headers,
            max_size=max_size_value,
        )
        logger.debug(
            f"File fetched: content_type={content_type}, "
            f"filename={filename}, size={len(response_data)} bytes"
        )

        # Save content to disk and get metadata
        file_path, metadata = _save_content_to_file(
            response_data,
            validated_url,
            content_type or "application/octet-stream",
            validated_format,
            original_filename=filename,
            download_path=download_path_value,
        )

        logger.info(f"Successfully downloaded file to: {file_path}")
        # Return success JSON response
        return _create_response(file_path, metadata)

    except URLDownloadError as exc:
        logger.error(f"URL download error for {url}: {exc}")
        return _create_error_response(str(exc))
    except ContentParsingError as exc:
        logger.error(f"Content parsing error for {url}: {exc}")
        return _create_error_response(str(exc))
    except Exception as exc:
        error_msg = f"Failed to download file from {url}: {exc}"
        logger.error(f"Unexpected error downloading {url}: {exc}")
        return _create_error_response(error_msg)


def get_youtube_video_transcription(
    intent: str, url: str, download_path: Optional[str] = str(DOWNLOADS_DIR)
) -> str:
    """
    Save a YouTube video's full captions/transcript as a text file using
    youtube-transcript-api.
    """
    try:
        validated_url = _validate_url(url)
    except URLDownloadError as exc:
        logger.error(f"Invalid URL for YouTube transcription: {exc}")
        return _create_error_response(str(exc))

    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    # Extract video ID
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", validated_url)
    if not video_id_match:
        error_msg = "Could not extract YouTube video ID from URL"
        logger.error(error_msg)
        return _create_error_response(error_msg)
    video_id = video_id_match.group(1)

    logger.debug(f"Extracted video ID: {video_id} from {validated_url}")

    try:
        # Fetch transcript
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)

        # Format transcript text
        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript)

        # Save content to disk and get metadata
        file_path, metadata = _save_content_to_file(
            transcript_text,
            validated_url,
            "text/plain",
            "text",
            original_filename=f"{video_id}_transcript.txt",
            download_path=(str(DOWNLOADS_DIR) if not download_path else download_path),
        )

        # Add transcript-specific metadata
        metadata["video_id"] = video_id
        metadata["transcript_segments"] = len(transcript.snippets)
        metadata["estimated_duration"] = sum(
            snippet.duration for snippet in transcript.snippets
        )

        # Return success JSON response
        return _create_response(file_path, metadata)

    except NoTranscriptFound:
        error_msg = (
            f"No transcripts found for video {video_id}. " "Video may lack captions."
        )
        logger.warning(error_msg)
        return _create_error_response(error_msg)
    except TranscriptsDisabled:
        error_msg = f"Transcripts disabled for video {video_id} " "by uploader."
        logger.warning(error_msg)
        return _create_error_response(error_msg)
    except Exception as exc:
        error_msg = f"Failed to get YouTube transcription from {url}: {exc}"
        logger.error(error_msg)
        return _create_error_response(error_msg)


def _validate_url(url: str) -> str:
    """
    Validate that a URL is well-formed and uses HTTP or HTTPS protocol.

    Args:
        url (str): The URL to validate

    Returns:
        str: The validated URL

    Raises:
        URLDownloadError: If the URL is empty, malformed, or uses an
            unsupported protocol
    """
    if not url:
        raise URLDownloadError("URL cannot be empty")
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise URLDownloadError("Invalid URL format")
        if parsed.scheme not in ["http", "https"]:
            raise URLDownloadError("Only HTTP and HTTPS URLs are supported")
    except Exception as exc:
        raise URLDownloadError(f"URL validation failed: {exc}") from exc

    return url


def _validate_format(output_format: str) -> str:
    """
    Validate that the requested output format is supported.

    Args:
        output_format (str): The desired output format

    Returns:
        str: The validated output format

    Raises:
        ContentParsingError: If the output format is not supported
    """
    if output_format in SUPPORTED_FORMATS:
        return output_format
    supported = ", ".join(SUPPORTED_FORMATS)
    error = f"Unsupported format '{output_format}'. Supported formats: {supported}"
    raise ContentParsingError(error)


def _is_html_content(content_type: str) -> bool:
    """
    Check if a content type represents HTML content.

    Args:
        content_type (str): The content type to check

    Returns:
        bool: True if the content type represents HTML, False otherwise
    """
    return any(html_type in content_type for html_type in HTML_CONTENT_TYPES)


def _is_binary_content(content_type: str) -> bool:
    """
    Check if a content type represents binary content.

    Args:
        content_type (str): The content type to check

    Returns:
        bool: True if the content type represents binary data, False otherwise
    """
    return any(binary_type in content_type for binary_type in BINARY_CONTENT_TYPES)


def _get_default_headers() -> Dict[str, str]:
    """
    Generate default HTTP headers to mimic a real browser.

    Returns:
        Dict[str, str]: A dictionary of default HTTP headers
    """
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def _get_antibot_headers() -> Dict[str, str]:
    """
    Generate HTTP headers designed to avoid anti-bot detection.

    Returns:
        Dict[str, str]: A dictionary of anti-bot evasion headers
    """
    headers = _get_default_headers()

    # Add random referer
    referers = [
        "https://www.google.com/",
        "https://www.bing.com/",
        "https://duckduckgo.com/",
        "https://www.reddit.com/",
        "https://news.ycombinator.com/",
    ]
    headers["Referer"] = random.choice(referers)

    return headers


def _detect_antibot_response(response: httpx.Response) -> bool:
    """
    Detect if a server response indicates anti-bot protection.

    Args:
        response (httpx.Response): The HTTP response to check

    Returns:
        bool: True if anti-bot indicators are detected, False otherwise
    """
    content = response.text.lower()
    antibot_indicators = [
        "cloudflare",
        "captcha",
        "bot detection",
        "access denied",
        "blocked",
        "security check",
        "ddos protection",
    ]

    return any(indicator in content for indicator in antibot_indicators)


def _extract_filename_from_response(
    response: httpx.Response, url: str
) -> Optional[str]:
    """
    Extract filename from HTTP response headers or URL.

    Args:
        response (httpx.Response): The HTTP response
        url (str): The original URL

    Returns:
        Optional[str]: The extracted filename or None
    """
    # Try Content-Disposition header first
    content_disp = response.headers.get("content-disposition", "")
    if content_disp:
        # Parse filename from Content-Disposition
        # Example: attachment; filename="document.pdf"
        match = re.search(r'filename[*]?=(["\']?)(.+?)\1', content_disp)
        if match:
            filename = match.group(2)
            # Remove any path components
            return os.path.basename(filename)

    # Fallback to URL path
    parsed_url = urlparse(url)
    if parsed_url.path:
        filename = os.path.basename(parsed_url.path)
        if filename and "." in filename:
            return filename

    return None


def _fetch_file(
    url: str,
    custom_headers: Optional[Dict[str, str]] = None,
    max_size: int = MAX_FILE_SIZE,
) -> tuple[Union[str, bytes], str, Optional[str]]:
    """
    Download a file from a URL with retry logic and anti-bot evasion.

    Args:
        url (str): The URL to fetch
        custom_headers (Dict[str, str]): Optional custom headers to add
        max_size (int): Maximum file size in bytes (default: 100MB)

    Returns:
        tuple[Union[str, bytes], str, str]: A tuple containing:
            - content (as str or bytes)
            - content type
            - original filename (or None)

    Raises:
        URLDownloadError: If the file cannot be downloaded after all
                         retry attempts or exceeds size limit
    """
    last_error = ""

    # Merge custom headers with default anti-bot headers
    headers = _get_antibot_headers()
    if custom_headers:
        headers.update(custom_headers)

    client = httpx.Client(
        timeout=httpx.Timeout(TIMEOUT),
        follow_redirects=True,
        headers=headers,
        verify=False,
    )

    for attempt in range(MAX_RETRIES):
        try:
            # Add random delay between attempts
            if attempt > 0:
                delay = min(2**attempt, 10) + random.uniform(0, 1)
                time.sleep(delay)

            response = client.get(url)
            response.raise_for_status()

            # Check file size limit
            content_length = response.headers.get("content-length")
            if content_length:
                size = int(content_length)
                if size > max_size:
                    raise URLDownloadError(
                        f"File size ({size} bytes) exceeds maximum "
                        f"allowed size ({max_size} bytes)"
                    )

            content_type = response.headers.get("content-type", "").lower()
            # Strip parameters (e.g. "; charset=utf-8") to improve detection +
            # extension guessing.
            content_type = content_type.split(";", 1)[0].strip()

            # Extract filename from response
            filename = _extract_filename_from_response(response, url)

            # Check for anti-bot indicators only for HTML content
            if _is_html_content(content_type):
                if _detect_antibot_response(response):
                    raise AntiBotDetectedError("Anti-bot system detected")
                # Check actual text size
                text_content = response.text
                if len(text_content.encode("utf-8")) > max_size:
                    raise URLDownloadError(
                        (
                            "File size (%s bytes) exceeds maximum allowed "
                            "size "
                            "(%s bytes)" % (len(text_content.encode("utf-8")), max_size)
                        )
                    )
                return text_content, content_type, filename

            # For binary content, check actual size and return bytes
            content = response.content
            if len(content) > max_size:
                raise URLDownloadError(
                    f"File size ({len(content)} bytes) exceeds maximum "
                    f"allowed size ({max_size} bytes)"
                )

            return content, content_type, filename

        except httpx.TimeoutException:
            last_error = f"Request timeout (attempt {attempt + 1}/{MAX_RETRIES})"
        except httpx.HTTPStatusError as exc:
            last_error = f"HTTP error {exc.response.status_code}"
            if exc.response.status_code in [403, 429]:  # Likely anti-bot
                continue
            break  # Don't retry other HTTP errors
        except AntiBotDetectedError:
            last_error = f"Anti-bot detected (attempt {attempt + 1}/{MAX_RETRIES})"
            # If anti-bot is detected, don't continue retrying
            break
        except URLDownloadError:
            # Re-raise size limit errors
            raise
        except Exception as exc:
            last_error = f"Request failed: {exc}"
            break

    raise URLDownloadError(
        f"Failed to fetch file after {MAX_RETRIES} attempts: {last_error}"
    )


def _is_markitdown_supported(content_type: str) -> bool:
    """
    Check if a content type is supported by MarkItDown for conversion.

    Args:
        content_type (str): The content type to check

    Returns:
        bool: True if the content type is supported by MarkItDown, False
        otherwise
    """
    supported_types = [
        "application/pdf",
        "application/msword",
        ("application/vnd.openxmlformats-" "officedocument.wordprocessingml.document"),
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        (
            "application/vnd.openxmlformats-"
            "officedocument.presentationml.presentation"
        ),
        "text/csv",
        "application/json",
        "text/xml",
        "application/xml",
    ]
    return any(supported_type in content_type for supported_type in supported_types)


def _auto_detect_format(content_type: str) -> str:
    """
    Auto-detect the appropriate output format based on content type.

    Args:
        content_type (str): The content type to analyze

    Returns:
        str: The auto-detected output format
    """
    if _is_html_content(content_type) or _is_markitdown_supported(content_type):
        return "markdown"
    if _is_binary_content(content_type):
        return "binary"

    return "text"


def _get_file_extension(url: str, content_type: str) -> str:
    """
    Get the file extension from URL or content type.

    Args:
        url (str): The URL to extract extension from
        content_type (str): The content type to fallback to

    Returns:
        str: The file extension
    """
    parsed_url = urlparse(url)  # Try to get extension from URL
    if parsed_url.path:
        _, ext = os.path.splitext(parsed_url.path)
        if ext:
            return ext

    # Fallback to content type mapping (strip parameters if present)
    content_type = (content_type or "").split(";", 1)[0].strip()
    ext = mimetypes.guess_extension(content_type)
    return ext or ".bin"


def _clean_text(text: str) -> str:
    """
    Clean and normalize text content.

    Args:
        text (str): The text to clean

    Returns:
        str: The cleaned text
    """
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text.strip())

    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")

    return text


def _markitdown(content: Union[str, bytes], content_type: str, url: str) -> str:
    """
    Convert content to markdown using MarkItDown.

    Args:
        content (Union[str, bytes]): The content to convert
        content_type (str): The content type
        url (str): The URL used for extension detection

    Returns:
        str: The markdown-formatted content
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    file_ext = _get_file_extension(url, content_type)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = os.path.join(temp_dir, f"content{file_ext}")
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(content)
        # Convert inside the with block before temp_dir is deleted
        result = MarkItDown().convert(temp_file_path).text_content

    return _clean_text(result)


def _create_response(file_path: str, metadata: Dict) -> str:
    """
    Create a success JSON response.

    Args:
        file_path (str): Path to the downloaded file
        metadata (Dict): File metadata

    Returns:
        str: JSON string with success response
    """
    response = {
        "success": True,
        "file_path": file_path,
        "metadata": metadata,
        "error": None,
    }
    return json.dumps(response, indent=2)


def _create_error_response(error_message: str) -> str:
    """
    Create an error JSON response.

    Args:
        error_message (str): Error message to include

    Returns:
        str: JSON string with error response
    """
    response = {
        "success": False,
        "file_path": None,
        "metadata": None,
        "error": error_message,
    }
    return json.dumps(response, indent=2)


def _save_content_to_file(
    content: Union[str, bytes],
    url: str,
    content_type: str,
    output_format: str = "auto",
    original_filename: Optional[str] = None,
    download_path: Optional[str] = None,
) -> tuple[str, Dict]:
    """
    Save content to a file on disk and return the file path and metadata.

    Args:
        content (Union[str, bytes]): The content to save
        url (str): The original URL
        content_type (str): The content type
        output_format (str): The desired output format
        original_filename (Optional[str]): Original filename from headers/URL
        download_path (Optional[str]): Absolute Path or None for temp directory

    Returns:
        tuple[str, Dict]: A tuple containing the file path and metadata
    """
    # Determine download directory
    if download_path:
        # Use specified path (can be absolute or relative)
        resolved_path = Path(download_path).expanduser().resolve()

        # Check if it's a directory or a file path
        if resolved_path.is_dir() or (
            not resolved_path.suffix and not resolved_path.exists()
        ):
            # It's a directory - use original filename from URL/headers
            download_dir = resolved_path
            download_dir.mkdir(parents=True, exist_ok=True)
            # Use original filename if available, otherwise use URL-based name
            if original_filename:
                base_filename = Path(original_filename).stem
                file_ext = Path(original_filename).suffix or _get_file_extension(
                    url, content_type
                )
            else:
                # Extract filename from URL
                url_path = urlparse(url).path
                url_filename = os.path.basename(url_path) if url_path else "content"
                base_filename = Path(url_filename).stem or "content"
                file_ext = Path(url_filename).suffix or _get_file_extension(
                    url, content_type
                )
        else:
            # It's a file path - use the specified filename
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            download_dir = resolved_path.parent
            base_filename = resolved_path.stem
            file_ext = resolved_path.suffix or _get_file_extension(url, content_type)
    else:
        # Use temporary directory (original behavior)
        download_dir = Path(tempfile.mkdtemp(prefix="aria2_download_"))
        base_filename = "content"
        file_ext = _get_file_extension(url, content_type)

    # Auto-detect format if "auto" is specified
    if output_format == "auto":
        output_format = _auto_detect_format(content_type)

    # Determine if this is a MarkItDown-supported binary file
    is_markitdown_binary = _is_binary_content(
        content_type
    ) and _is_markitdown_supported(content_type)

    # For MarkItDown-supported binary files, save both original and parsed
    if is_markitdown_binary:
        # Save original binary file
        original_file_name = f"{base_filename}{file_ext}"
        original_file_path = download_dir / original_file_name

        if isinstance(content, str):
            content = content.encode("utf-8")

        with open(original_file_path, "wb") as f:
            f.write(content)

        # Parse with MarkItDown and save to text file
        try:
            parsed_text = _markitdown(content, content_type, url)
            parsed_file_name = f"{base_filename}_parsed.txt"
            parsed_file_path = download_dir / parsed_file_name

            with open(parsed_file_path, "w", encoding="utf-8") as f:
                f.write(parsed_text)

            # Create metadata with both file paths
            file_size = original_file_path.stat().st_size
            parsed_file_size = parsed_file_path.stat().st_size
            metadata = {
                "url": url,
                "content_type": content_type,
                "file_size": file_size,
                "file_extension": file_ext,
                "format": "binary",
                "parsed": True,
                "parsed_file_path": str(parsed_file_path),
                "parsed_file_size": parsed_file_size,
                "original_filename": original_filename,
                "timestamp": datetime.now().isoformat(),
            }
            return str(original_file_path), metadata
        except Exception as e:
            # If parsing fails, just return the original file
            file_size = original_file_path.stat().st_size
            metadata = {
                "url": url,
                "content_type": content_type,
                "file_size": file_size,
                "file_extension": file_ext,
                "format": "binary",
                "parsed": False,
                "parse_error": str(e),
                "original_filename": original_filename,
                "timestamp": datetime.now().isoformat(),
            }
            return str(original_file_path), metadata

    # For unsupported binary content, save as-is
    elif _is_binary_content(content_type):
        file_name = f"{base_filename}{file_ext}"
        file_path = download_dir / file_name

        if isinstance(content, str):
            content = content.encode("utf-8")

        with open(file_path, "wb") as f:
            f.write(content)

        # Create metadata
        file_size = file_path.stat().st_size
        metadata = {
            "url": url,
            "content_type": content_type,
            "file_size": file_size,
            "file_extension": file_ext,
            "format": "binary",
            "parsed": False,
            "original_filename": original_filename,
            "timestamp": datetime.now().isoformat(),
        }
        return str(file_path), metadata

    # For text/HTML content
    elif isinstance(content, str):
        # Special handling for HTML with markdown output - save both files
        if _is_html_content(content_type) and output_format == "markdown":
            # Save original HTML file
            html_file_name = f"{base_filename}{file_ext}"
            html_file_path = download_dir / html_file_name

            with open(html_file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Convert to markdown and save
            try:
                logger.debug(f"Converting HTML to markdown for {url}")
                markdown_content = _markitdown(content, content_type, url)
                logger.debug("HTML to markdown conversion successful")

                markdown_file_name = f"{base_filename}.md"
                markdown_file_path = download_dir / markdown_file_name

                with open(markdown_file_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)

                # Create metadata with both file paths
                html_file_size = html_file_path.stat().st_size
                markdown_file_size = markdown_file_path.stat().st_size
                metadata = {
                    "url": url,
                    "content_type": content_type,
                    "file_size": html_file_size,
                    "file_extension": file_ext,
                    "format": "html",
                    "parsed": True,
                    "parsed_file_path": str(markdown_file_path),
                    "parsed_file_size": markdown_file_size,
                    "original_filename": original_filename,
                    "timestamp": datetime.now().isoformat(),
                }
                return str(html_file_path), metadata

            except Exception as e:
                logger.error(f"Failed to convert HTML to markdown: {e}")
                # If conversion fails, just return the HTML file
                html_file_size = html_file_path.stat().st_size
                metadata = {
                    "url": url,
                    "content_type": content_type,
                    "file_size": html_file_size,
                    "file_extension": file_ext,
                    "format": "html",
                    "parsed": False,
                    "parse_error": str(e),
                    "original_filename": original_filename,
                    "timestamp": datetime.now().isoformat(),
                }
                return str(html_file_path), metadata

        # For other cases, save single file
        elif _is_html_content(content_type):
            # Save as HTML without conversion
            format_type = "html"
            file_name = f"{base_filename}{file_ext}"
        elif output_format == "markdown":
            # Non-HTML content requested as markdown
            format_type = "markdown"
            file_name = f"{base_filename}.md"
            try:
                content = _markitdown(content, content_type, url)
            except Exception:
                # If conversion fails for non-HTML, save as-is
                pass
        else:
            # Plain text
            format_type = "text"
            file_name = f"{base_filename}{file_ext}"

        file_path = download_dir / file_name
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Create metadata
        file_size = file_path.stat().st_size
        metadata = {
            "url": url,
            "content_type": content_type,
            "file_size": file_size,
            "file_extension": file_ext,
            "format": format_type,
            "parsed": False,
            "original_filename": original_filename,
            "timestamp": datetime.now().isoformat(),
        }
        return str(file_path), metadata

    # For binary content that came as bytes
    else:
        file_name = f"{base_filename}{file_ext}"
        file_path = download_dir / file_name

        with open(file_path, "wb") as f:
            f.write(content)

        # Create metadata
        file_size = file_path.stat().st_size
        metadata = {
            "url": url,
            "content_type": content_type,
            "file_size": file_size,
            "file_extension": file_ext,
            "format": "binary",
            "parsed": False,
            "original_filename": original_filename,
            "timestamp": datetime.now().isoformat(),
        }
        return str(file_path), metadata
