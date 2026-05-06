"""
IMDB tools for movie and TV series information retrieval.

This module provides tools for the IMDB Expert agent to search
and retrieve information about movies, TV series, and people.
"""

from aria.tools.imdb.functions import (
    get_all_series_episodes,
    get_movie_details,
    get_movie_reviews,
    get_movie_trivia,
    get_person_details,
    get_person_filmography,
    search_imdb_titles,
)

__all__ = [
    "get_all_series_episodes",
    "get_movie_details",
    "get_movie_reviews",
    "get_movie_trivia",
    "get_person_details",
    "get_person_filmography",
    "search_imdb_titles",
]
