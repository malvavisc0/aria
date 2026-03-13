"""YouTube-specific functionality for transcript extraction.

This module contains YouTube-related helper functions.
"""

import re
from typing import Optional

from loguru import logger
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)
from youtube_transcript_api.formatters import TextFormatter

from aria.tools import tool_error_response, tool_success_response
from aria.tools.search._download_internals import (
    _save_content_to_file,
    _validate_url,
)
from aria.tools.search.constants import DOWNLOADS_DIR


def _extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL.

    Args:
        url: YouTube URL

    Returns:
        Video ID or None if not found
    """
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    if match:
        return match.group(1)
    return None


def _get_youtube_transcript(video_id: str) -> tuple[str, list, float]:
    """Fetch and format YouTube transcript.

    Args:
        video_id: YouTube video ID

    Returns:
        Tuple of (transcript_text, snippets, estimated_duration)

    Raises:
        NoTranscriptFound: If no transcripts are available
        TranscriptsDisabled: If transcripts are disabled
    """
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)

    formatter = TextFormatter()
    transcript_text = formatter.format_transcript(transcript)

    return (
        transcript_text,
        transcript.snippets,
        sum(snippet.duration for snippet in transcript.snippets),
    )


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
    from aria.tools.search.download import URLDownloadError

    try:
        validated_url = _validate_url(url)
    except URLDownloadError as exc:
        logger.error(f"Invalid URL for YouTube transcription: {exc}")
        return tool_error_response(
            "get_youtube_video_transcription", intent, exc
        )

    video_id = _extract_video_id(validated_url)
    if not video_id:
        error_msg = "Could not extract YouTube video ID from URL"
        logger.error(error_msg)
        return tool_error_response(
            "get_youtube_video_transcription", intent, RuntimeError(error_msg)
        )

    logger.debug(f"Extracted video ID: {video_id} from {validated_url}")

    try:
        transcript_text, snippets, duration = _get_youtube_transcript(video_id)

        file_path, metadata = _save_content_to_file(
            transcript_text,
            validated_url,
            "text/plain",
            "text",
            original_filename=f"{video_id}_transcript.txt",
            download_path=(
                str(DOWNLOADS_DIR) if not download_path else download_path
            ),
        )

        metadata["video_id"] = video_id
        metadata["transcript_segments"] = len(snippets)
        metadata["estimated_duration"] = duration

        return tool_success_response(
            "get_youtube_video_transcription",
            intent,
            {"file_path": file_path, "metadata": metadata},
        )

    except NoTranscriptFound:
        error_msg = f"No transcripts found for video {video_id}. Video may lack captions."
        logger.warning(error_msg)
        return tool_error_response(
            "get_youtube_video_transcription", intent, RuntimeError(error_msg)
        )
    except TranscriptsDisabled:
        error_msg = f"Transcripts disabled for video {video_id} by uploader."
        logger.warning(error_msg)
        return tool_error_response(
            "get_youtube_video_transcription", intent, RuntimeError(error_msg)
        )
    except Exception as exc:
        error_msg = f"Failed to get YouTube transcription from {url}: {exc}"
        logger.error(error_msg)
        return tool_error_response(
            "get_youtube_video_transcription", intent, RuntimeError(error_msg)
        )
