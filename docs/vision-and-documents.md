# Vision & Document Upload Processing

How Aria handles images and documents uploaded through the chat UI.

## Overview

When a user attaches files to a chat message, Aria processes them in a
pre-processing step **before** the agent sees the prompt. The goal is to
convert uploads into plain text that flows naturally through the existing
agent pipeline (memory, compression, fact extraction) without any
changes to the core workflow.

There are two processing paths:

| Upload type | Processing | Result in prompt |
|---|---|---|
| **Images** (png, jpg, webp, gif, bmp, tiff) | Vision API → text description | `[Image 1 (photo.jpg)]: A red car on a highway…` |
| **Documents** (pdf, docx, xlsx, pptx, csv, html) | MarkItDown → markdown file in workspace | `report.pdf → Converted to markdown: ~/.aria/workspace/uploads/report.md (247 lines)` |
| **Text files** (txt, md, json, xml, yaml, toml, py, js, ts, sh, log, ini, cfg, rst) | MarkItDown → markdown file in workspace | `script.py → Converted to markdown: ~/.aria/workspace/uploads/script.md (42 lines)` |
| **Other files** | Copied to uploads dir, path passed as-is | `- /path/to/file.bin` |

## Architecture

```
User uploads files in Chainlit UI
         │
         ▼
┌─────────────────────────────────┐
│  message_pipeline._handle_message()
│                                 │
│  1. extract_file_paths(msg)     │ ← Non-image files → copy to ~/.aria/uploads/
│  2. extract_image_data(msg)     │ ← Images → base64 encoded
│  3. convert_documents_to_markdown(paths) │ ← MarkItDown conversion
│  4. _describe_image() per image │ ← Vision API call
│  5. Assemble prompt with metadata│
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  AgentWorkflow.run(prompt)      │ ← Text-only, unchanged
│  (memory, compression, tools)   │
└─────────────────────────────────┘
```

## Image Processing (Vision)

### How it works

1. `extract_image_data()` in `session.py` detects image elements by MIME
   type or file extension, reads them, and returns base64-encoded data.

2. For each image, `_describe_image()` in `message_pipeline.py` sends a
   request to the vLLM chat completions endpoint with the image as a
   `data:` URL. The prompt asks for a concise 2–3 sentence description.

3. The description text is injected into the user prompt:
   ```
   [Attached images]:
   [Image 1 (chart.png)]: A bar chart showing quarterly revenue growth…
   [Image 2 (photo.jpg)]: A group photo in front of a building…
   ```

### Why text descriptions, not multimodal passthrough

Passing raw images through the agent pipeline would break:
- **Memory** — images can't be embedded or fact-extracted
- **Context compression** — base64 blobs are incompressible
- **Token counting** — `len(str(content)) // 4` would massively undercount
- **Session restore** — images aren't persisted in the database

Text descriptions (~200–500 tokens each) flow through all these systems
unchanged.

### Configuration

Set the environment variable to enable vision:

```bash
ARIA_VLLM_VISION_ENABLED=true
```

When disabled, images are still detected but the prompt shows:
```
[Image 1 (photo.jpg)]: <vision disabled — enable ARIA_VLLM_VISION_ENABLED>
```

The model must support vision (e.g., Qwen-VL, LLaVA). If the vision API
call fails (timeout, model error), the prompt falls back to
`<description unavailable>` and the user's text message still goes through.

### Token budget

| Item | Tokens |
|---|---|
| Vision API call (per image) | ~300–2000 input, ~100–256 output |
| Description stored in prompt | ~100–256 per image |
| Max 5 images worst case | ~1,280 tokens total |

Fits comfortably in both 32K and 256K context windows.

## Document Processing (MarkItDown)

### How it works

1. `extract_file_paths()` in `session.py` copies non-image uploads to
   `~/.aria/uploads/` with unique filenames (thread ID + UUID).

2. `convert_documents_to_markdown()` checks each file's extension against
   supported types and converts using MarkItDown. The resulting `.md`
   file is saved to **`~/.aria/workspace/uploads/`** — inside the
   agent's workspace so it's accessible via file tools.

3. The prompt includes rich metadata:
   ```
   [Uploaded files]:
   - report.pdf (original: ~/.aria/uploads/t1_abc123_report.pdf)
     Converted to markdown: ~/.aria/workspace/uploads/report.md (247 lines, 12,450 chars)
   ```

4. The agent can then use its file read tools to inspect the converted
   markdown, search within it, or answer questions about its content.

### Supported formats

| Format | Extensions | MIME types |
|---|---|---|
| PDF | `.pdf` | `application/pdf` |
| Word | `.doc`, `.docx` | `application/msword`, `application/vnd.openxmlformats-…` |
| Excel | `.xls`, `.xlsx` | `application/vnd.ms-excel`, `application/vnd.openxmlformats-…` |
| PowerPoint | `.ppt`, `.pptx` | `application/vnd.ms-powerpoint`, `application/vnd.openxmlformats-…` |
| CSV | `.csv` | `text/csv` |
| HTML | `.html`, `.htm` | `text/html` |
| JSON | `.json` | `application/json` |
| XML | `.xml` | `text/xml`, `application/xml` |
| YAML | `.yaml`, `.yml` | `text/yaml`, `text/x-yaml`, `application/x-yaml` |
| TOML | `.toml` | `application/toml` |
| Plain text | `.txt`, `.log`, `.ini`, `.cfg` | `text/plain` |
| Markdown | `.md` | `text/markdown`, `text/plain` |
| reStructuredText | `.rst` | `text/plain`, `text/x-rst` |
| Python | `.py` | `text/x-python`, `text/plain` |
| JavaScript/TypeScript | `.js`, `.ts` | `text/plain` |
| Shell | `.sh` | `text/x-script`, `text/plain` |

### Why convert to workspace files, not inject content into prompt

- Large documents can be thousands of tokens — too much for the prompt
- The agent can selectively read sections with file tools
- The converted file persists across the conversation
- The agent can grep/search within it
- No impact on context compression or memory

### Error handling

If conversion fails (corrupt file, unsupported content, MarkItDown not
installed), the metadata reports the error and the original file path
is still available:

```
[Uploaded files]:
- broken.pdf: ~/.aria/uploads/t1_abc_broken.pdf (conversion failed: …)
```

Unrecognised file types (e.g., `.bin`, `.exe`, `.zip`) are passed through
as plain file paths without conversion attempted.

## File locations

| Directory | Purpose |
|---|---|
| `~/.aria/uploads/` | Raw uploaded files (all types except images) |
| `~/.aria/workspace/uploads/` | Converted markdown files (agent-accessible) |

## Source files

| File | Responsibility |
|---|---|
| `src/aria/web/session.py` | `extract_image_data()`, `extract_file_paths()`, `convert_documents_to_markdown()` |
| `src/aria/web/message_pipeline.py` | `_describe_image()`, `_handle_message()` prompt assembly |
| `src/aria/config/api.py` | `Vllm.vision_enabled` configuration |
| `src/aria/.chainlit/config.toml` | File upload UI settings (`spontaneous_file_upload`) |
