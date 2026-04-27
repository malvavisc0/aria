"""
Constants for IMDB tools.

Constants, enums, and error messages for IMDB tools.
"""

# Valid title type strings for filtering searches
# These map to imdbinfo.TitleType enum values
VALID_TITLE_TYPES = {
    "movie": "Movies",
    "movies": "Movies",
    "series": "Series",
    "tv": "Series",
    "tv_series": "Series",
    "episode": "Episodes",
    "episodes": "Episodes",
    "short": "Shorts",
    "shorts": "Shorts",
    "tv_movie": "TvMovie",
    "video": "Video",
    "videos": "Video",
}

# Error messages - clean and agent-friendly
ERROR_INVALID_TITLE_TYPE = "Invalid title_type '{value}'. Valid types: {valid_types}"
ERROR_EMPTY_QUERY = "Search query is required."
ERROR_EMPTY_IMDB_ID = "IMDb ID is required."
ERROR_NO_RESULTS = "No results found for '{query}'. Try a different search term."
ERROR_MOVIE_NOT_FOUND = (
    "No movie/series found with IMDb ID '{imdb_id}'. Verify the ID is correct."
)
ERROR_PERSON_NOT_FOUND = (
    "No person found with IMDb ID '{person_id}'. Verify the ID is correct."
)
ERROR_EPISODES_NOT_FOUND = (
    "No episodes found for series '{imdb_id}'. This may not be a TV series."
)
ERROR_REVIEWS_NOT_FOUND = "No reviews available for '{imdb_id}'."
ERROR_TRIVIA_NOT_FOUND = "No trivia available for '{imdb_id}'."
ERROR_FILMOGRAPHY_NOT_FOUND = "No filmography found for person '{person_id}'."
ERROR_NETWORK = "Network error: Unable to connect to IMDb. Please try again later."
ERROR_TIMEOUT = "Request timed out. IMDb may be slow to respond. Please try again."
ERROR_RATE_LIMIT = "Rate limited by IMDb. Please wait a moment before trying again."
ERROR_UNKNOWN = "An unexpected error occurred: {error}"
