# Download Tools (`aria2.tools.search.download`)

This file documents the tools implemented in [`aria2.tools.search.download`](src/aria2/tools/search/download.py:1).

### `get_file_from_url(intent: str, url: str, output: str = "auto", custom_headers: dict[str, str] | None = None, max_size: int | None = MAX_FILE_SIZE, download_path: str | None = str(DOWNLOADS_DIR))`

Download URL content to disk and optionally convert it.

When to use: Download and convert web content to local files.

Parameters:
- `intent`: Your intended outcome with this tool call.
- `url`: URL of the content to download.
- `output`: One of `auto`, `markdown`, `text`, `html`, `binary`, `xml`.
- `custom_headers`: Optional extra HTTP headers.
- `max_size`: Maximum allowed download size in bytes.
- `download_path`: Target directory or file path. If empty, defaults to downloads directory.

Returns:
- JSON string with `success`, `file_path`, `metadata`, and `error`.

Example:
```python
get_file_from_url("Download the project README for offline reading", "https://example.com/readme", output="markdown")
```

### `get_youtube_video_transcription(intent: str, url: str, download_path: str | None = str(DOWNLOADS_DIR))`

Save a YouTube video's transcription as a text file.

Parameters:
- `intent`: Your intended outcome with this tool call.
- `url`: YouTube video URL.
- `download_path`: Directory where the transcript will be saved.

Returns:
- JSON string with `success`, `file_path`, `metadata`, and `error`.

Example:
```python
get_youtube_video_transcription("Fetch transcript to quote key claims", "https://www.youtube.com/watch?v=...", download_path=".files")
```

