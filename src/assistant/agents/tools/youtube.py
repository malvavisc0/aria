from agno.tools.toolkit import Toolkit

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    raise ImportError(
        "`youtube-transcript-api` not installed. Please install using `pip install youtube_transcript_api`"
    )
import json
import re
from urllib.parse import urlencode
from urllib.request import urlopen


class YouTubeTools(Toolkit):
    """
    A toolkit class specifically designed for interacting with YouTube services.
    This class provides methods to retrieve metadata and transcripts of YouTube videos.
    """

    def __init__(self):
        """
        Initializes the YouTubeTools with the name 'youtube_tools' and registers
        the methods 'retrieve_youtube_video_metadata' and 'retrieve_youtube_video_transcript'.
        """
        super().__init__(name="youtube_tools")
        self.register(self.retrieve_youtube_video_metadata)
        self.register(self.retrieve_youtube_video_transcript)

    def extract_youtube_video_id(self, youtube_url: str) -> str:
        """
        Extracts the video ID from a given YouTube URL.

        Parameters:
         youtube_url (str): The URL of the YouTube video.

        Returns:
         str: The video ID if found, otherwise None.
        """
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, youtube_url)
        if not match:
            raise ValueError("Error getting video ID from URL")
        return match.group(1)

    def retrieve_youtube_video_metadata(self, video_url: str) -> str:
        """
        Retrieves metadata for a YouTube video given its URL.

        Parameters:
         video_url (str): The URL of the YouTube video.

        Returns:
         metadata (str): A JSON string containing the video metadata.

        Raises:
         ValueError: If the video ID cannot be extracted from the URL.
         Exception: If an error occurs while retrieving the video data.
        """
        video_id = self.extract_youtube_video_id(youtube_url=video_url)
        try:
            params = {
                "format": "json",
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
            url = "https://www.youtube.com/oembed"
            query_string = urlencode(params)
            url = url + "?" + query_string
            with urlopen(url) as response:
                response_text = response.read()
                video_data = json.loads(response_text.decode())
                clean_data = {
                    "title": video_data.get("title"),
                    "author_name": video_data.get("author_name"),
                    "author_url": video_data.get("author_url"),
                    "thumbnail_url": video_data.get("thumbnail_url"),
                }
                metadata = json.dumps(clean_data, indent=4)
                return metadata
        except Exception as e:
            raise Exception(f"Error getting video data: {e}")

    def retrieve_youtube_video_transcript(self, video_url: str) -> str:
        """
        Retrieves the transcript of a YouTube video given its URL.

        Parameters:
         video_url (str): The URL of the YouTube video.

        Returns:
         str: The transcript of the video as a single string.
        """
        video_id = self.extract_youtube_video_id(youtube_url=video_url)
        transcript = YouTubeTranscriptApi().fetch(video_id=video_id)
        return " ".join([snippet.text for snippet in transcript.snippets])
