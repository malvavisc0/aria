"""
IMDB tool functions for movie and TV series information retrieval.

This module provides tool functions that wrap the imdbinfo package
for use with the IMDB Expert agent.

Each function returns a JSON string with explicitly documented fields.
The imdbinfo package returns Pydantic models (MovieBriefInfo, PersonDetail,
MovieDetail, BulkedEpisode) or plain dicts (reviews, trivia). We extract
a curated subset of fields from each model to keep responses lean and
self-documenting.
"""

import json
from typing import Optional

from imdbinfo import TitleType as ImdbTitleType
from imdbinfo import (
    get_all_episodes,
    get_filmography,
    get_movie,
    get_name,
    get_reviews,
    get_trivia,
    search_title,
)
from loguru import logger

from aria.tools.imdb.constants import (
    ERROR_EMPTY_IMDB_ID,
    ERROR_EMPTY_QUERY,
    ERROR_EPISODES_NOT_FOUND,
    ERROR_FILMOGRAPHY_NOT_FOUND,
    ERROR_INVALID_TITLE_TYPE,
    ERROR_MOVIE_NOT_FOUND,
    ERROR_NETWORK,
    ERROR_NO_RESULTS,
    ERROR_PERSON_NOT_FOUND,
    ERROR_RATE_LIMIT,
    ERROR_REVIEWS_NOT_FOUND,
    ERROR_TIMEOUT,
    ERROR_TRIVIA_NOT_FOUND,
    ERROR_UNKNOWN,
    VALID_TITLE_TYPES,
)


def _get_title_type(title_type: Optional[str]) -> Optional[ImdbTitleType]:
    """
    Convert user-friendly title type string to ImdbTitleType enum.

    Args:
        title_type: User-friendly title type string (e.g., 'movie', 'series')

    Returns:
        ImdbTitleType enum value or None if no filter specified

    Raises:
        ValueError: If title_type is not a valid type
    """
    if title_type is None:
        return None

    title_type_lower = title_type.lower().strip()
    if title_type_lower not in VALID_TITLE_TYPES:
        valid_types = ", ".join(sorted(VALID_TITLE_TYPES.keys()))
        raise ValueError(
            ERROR_INVALID_TITLE_TYPE.format(value=title_type, valid_types=valid_types)
        )

    # Get the imdbinfo TitleType enum value
    enum_name = VALID_TITLE_TYPES[title_type_lower]
    return getattr(ImdbTitleType, enum_name)


def _classify_error(error: Exception) -> str:
    """
    Classify an exception into a user-friendly error message.

    Args:
        error: The exception that occurred

    Returns:
        A clean, agent-friendly error message string
    """
    error_str = str(error).lower()

    # Network/connection errors
    if any(
        term in error_str
        for term in ["connection", "network", "dns", "resolve", "unreachable"]
    ):
        return ERROR_NETWORK

    # Timeout errors
    if any(term in error_str for term in ["timeout", "timed out"]):
        return ERROR_TIMEOUT

    # Rate limiting
    if any(term in error_str for term in ["rate limit", "429", "too many"]):
        return ERROR_RATE_LIMIT

    # Default to unknown error
    return ERROR_UNKNOWN.format(error=str(error))


def search_imdb_titles(
    intent: str, query: str, title_type: Optional[str] = None
) -> str:
    """
    Search for movies, TV series, and other titles on IMDb.

    Use this tool to find titles when you don't know the exact IMDb ID.
    Returns a list of matching titles with basic information.

    Args:
        intent: The goal of this tool call
            (e.g., "Searching for movie titled Matrix")
        query: The title to search for
        title_type: Optional filter - one of: movie, series, episode,
            short, tv_movie, video

    Returns:
        JSON string with structure:
        {
            "titles": [
                {
                    "imdbId": "tt0133093",
                    "title": "The Matrix",
                    "year": 1999,
                    "kind": "movie",
                    "rating": 8.7
                }
            ],
            "names": [
                {
                    "imdbId": "nm0000206",
                    "name": "Keanu Reeves",
                    "job": "actor"
                }
            ]
        }
    """
    logger.info(f"search_imdb_titles called with query='{query}'")

    if not query or not query.strip():
        return json.dumps({"error": ERROR_EMPTY_QUERY})

    try:
        imdb_title_type = _get_title_type(title_type)
        logger.debug(f"Title type filter: {imdb_title_type}")

        result = search_title(query.strip(), title_type=imdb_title_type)

        if result is None or (
            (not result.titles or len(result.titles) == 0)
            and (not result.names or len(result.names) == 0)
        ):
            return json.dumps(
                {
                    "error": ERROR_NO_RESULTS.format(query=query),
                    "titles": [],
                    "names": [],
                }
            )

        titles = [
            {
                "imdbId": t.imdbId,
                "title": t.title,
                "year": t.year,
                "kind": t.kind,
                "rating": t.rating,
            }
            for t in (result.titles or [])
        ]

        names = [
            {
                "imdbId": n.imdbId,
                "name": n.name,
                "job": n.job,
            }
            for n in (result.names or [])
        ]

        response = {"titles": titles, "names": names}

        logger.info(f"Found {len(titles)} titles, {len(names)} names")
        return json.dumps(response, default=str)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return json.dumps({"error": _classify_error(e)})


def get_movie_details(intent: str, imdb_id: str) -> str:
    """
    Get comprehensive details for a movie or TV series.

    Use this tool when you have an IMDb ID and need full information
    including cast, crew, ratings, plot, and more.

    Args:
        intent: The goal of this tool call
            (e.g., "Getting details for The Matrix")
        imdb_id: IMDb ID (with or without 'tt' prefix)
            e.g., 'tt0133093' or '0133093'

    Returns:
        JSON string with structure:
        {
            "imdbId": "tt0133093",
            "title": "The Matrix",
            "year": 1999,
            "kind": "movie",
            "duration": 136.0,
            "rating": 8.7,
            "votes": 2230088,
            "metacritic_rating": 73,
            "mpaa": "R",
            "plot": "When a beautiful stranger...",
            "genres": ["Action", "Sci-Fi"],
            "languages_text": ["English"],
            "countries": ["United States", "Australia"],
            "directors": [{"imdbId": "nm0905154", "name": "Lana Wachowski"}],
            "stars": [{"imdbId": "nm0000206", "name": "Keanu Reeves"}],
            "release_date": "1999-03-31",
            "cover_url": "https://...",
            "worldwide_gross": "463517383 USD",
            "production_budget": "63000000 USD",
            "awards": {"wins": 42, "nominations": 52}
        }
    """
    logger.info(f"get_movie_details called with imdb_id='{imdb_id}'")

    if not imdb_id or not imdb_id.strip():
        return json.dumps({"error": ERROR_EMPTY_IMDB_ID})

    try:
        movie = get_movie(imdb_id.strip())

        if movie is None:
            return json.dumps({"error": ERROR_MOVIE_NOT_FOUND.format(imdb_id=imdb_id)})

        directors = [
            {"imdbId": d.imdbId, "name": d.name} for d in (movie.directors or [])
        ]

        stars = [{"imdbId": s.imdbId, "name": s.name} for s in (movie.stars or [])]

        awards = None
        if movie.awards:
            awards = {
                "wins": movie.awards.wins,
                "nominations": movie.awards.nominations,
                "prestigious_award": movie.awards.prestigious_award,
            }

        result = {
            "imdbId": movie.imdbId,
            "title": movie.title,
            "year": movie.year,
            "kind": movie.kind,
            "duration": movie.duration,
            "rating": movie.rating,
            "votes": movie.votes,
            "metacritic_rating": movie.metacritic_rating,
            "mpaa": movie.mpaa,
            "plot": movie.plot,
            "genres": movie.genres or [],
            "languages_text": movie.languages_text or [],
            "countries": movie.countries or [],
            "directors": directors,
            "stars": stars,
            "release_date": movie.release_date,
            "cover_url": movie.cover_url,
            "worldwide_gross": movie.worldwide_gross,
            "production_budget": movie.production_budget,
            "awards": awards,
        }

        logger.info(f"Retrieved details for '{movie.title}' ({movie.year})")
        return json.dumps(result, default=str)

    except Exception as e:
        logger.error(f"Failed to get movie details: {e}")
        return json.dumps({"error": _classify_error(e)})


def get_person_details(intent: str, person_id: str) -> str:
    """
    Get details about an actor, director, or other film industry person.

    Use this tool when you have a person's IMDb ID and need their
    biography, known works, and other information.

    Args:
        intent: The goal of this tool call
            (e.g., "Getting details for Keanu Reeves")
        person_id: IMDb person ID (with or without 'nm' prefix)
            e.g., 'nm0000206' or '0000206'

    Returns:
        JSON string with structure:
        {
            "imdbId": "nm0000206",
            "name": "Keanu Reeves",
            "bio": "Keanu Charles Reeves...",
            "image_url": "https://...",
            "birth_date": "1964-09-02",
            "birth_place": "Beirut, Lebanon",
            "death_date": null,
            "death_place": null,
            "knownfor": ["Matrix", "Speed", "John Wick"],
            "primary_profession": ["actor", "producer"],
            "height": "6' 1\" (1.86 m)"
        }
    """
    logger.info(f"get_person_details called with person_id='{person_id}'")

    if not person_id or not person_id.strip():
        return json.dumps({"error": ERROR_EMPTY_IMDB_ID})

    try:
        person = get_name(person_id.strip())

        if person is None:
            return json.dumps(
                {"error": ERROR_PERSON_NOT_FOUND.format(person_id=person_id)}
            )

        result = {
            "imdbId": person.imdbId,
            "name": person.name,
            "bio": person.bio,
            "image_url": person.image_url,
            "birth_date": person.birth_date,
            "birth_place": person.birth_place,
            "death_date": person.death_date,
            "death_place": person.death_place,
            "knownfor": person.knownfor or [],
            "primary_profession": person.primary_profession or [],
            "height": person.height,
        }

        logger.info(f"Retrieved details for person '{person.name}'")
        return json.dumps(result, default=str)

    except Exception as e:
        logger.error(f"Failed to get person details: {e}")
        return json.dumps({"error": _classify_error(e)})


def get_person_filmography(intent: str, person_id: str) -> str:
    """
    Get the complete filmography for an actor or director.

    Use this tool to see all the movies and shows a person has
    worked on, organized by category (actor, director, etc.).

    The imdbinfo.get_filmography() function returns
    Dict[str, List[MovieBriefInfo]] where keys are category names
    (e.g., 'director', 'actor', 'producer') and values are lists
    of MovieBriefInfo Pydantic models.

    Args:
        intent: The goal of this tool call
            (e.g., "Getting filmography for Christopher Nolan")
        person_id: IMDb person ID (with or without 'nm' prefix)
            e.g., 'nm0634240' for Christopher Nolan

    Returns:
        JSON string with structure:
        {
            "person_id": "nm0634240",
            "filmography": {
                "director": [
                    {
                        "imdbId": "tt15398776",
                        "title": "Oppenheimer",
                        "year": 2023,
                        "kind": "movie",
                        "rating": 8.2
                    }
                ],
                "producer": [...],
                "writer": [...]
            }
        }
    """
    logger.info(f"get_person_filmography called with person_id='{person_id}'")

    if not person_id or not person_id.strip():
        return json.dumps({"error": ERROR_EMPTY_IMDB_ID})

    try:
        filmography = get_filmography(person_id.strip())

        if not filmography:
            return json.dumps(
                {
                    "error": ERROR_FILMOGRAPHY_NOT_FOUND.format(person_id=person_id),
                    "filmography": {},
                }
            )

        serialized = {}
        if isinstance(filmography, dict):
            for category, credits in filmography.items():
                serialized[category] = [
                    {
                        "imdbId": c.imdbId,
                        "title": c.title,
                        "year": c.year,
                        "kind": c.kind,
                        "rating": c.rating,
                    }
                    for c in credits
                ]

        result = {
            "person_id": person_id,
            "filmography": serialized,
        }

        logger.info(f"Retrieved filmography for person_id='{person_id}'")
        return json.dumps(result, default=str)

    except Exception as e:
        logger.error(f"Failed to get filmography: {e}")
        return json.dumps({"error": _classify_error(e)})


def get_all_series_episodes(intent: str, imdb_id: str) -> str:
    """
    Get all episodes for a TV series.

    Use this tool to get a complete list of all episodes for a
    TV series, sorted by release date.

    The imdbinfo.get_all_episodes() function returns
    List[BulkedEpisode] Pydantic models. Note: BulkedEpisode does
    NOT include season/episode numbers — only title, year, rating,
    and release_date. Use get_season_episodes() if you need
    season/episode numbering.

    Args:
        intent: The goal of this tool call
            (e.g., "Getting all episodes for Breaking Bad")
        imdb_id: IMDb ID for the TV series (with or without 'tt' prefix)
            e.g., 'tt0903747' for Breaking Bad

    Returns:
        JSON string with structure:
        {
            "series_id": "tt0903747",
            "episode_count": 62,
            "episodes": [
                {
                    "imdbId": "tt0959621",
                    "title": "Pilot",
                    "year": 2008,
                    "rating": 9.0,
                    "votes": 76202,
                    "plot": "Facing a life-altering diagnosis...",
                    "release_date": "2010-10-09",
                    "duration": 3480,
                    "genres": ["Crime", "Drama", "Thriller"]
                }
            ]
        }
    """
    logger.info(f"get_all_series_episodes called with imdb_id='{imdb_id}'")

    if not imdb_id or not imdb_id.strip():
        return json.dumps({"error": ERROR_EMPTY_IMDB_ID})

    try:
        episodes = get_all_episodes(imdb_id.strip())

        if not episodes:
            return json.dumps(
                {
                    "error": ERROR_EPISODES_NOT_FOUND.format(imdb_id=imdb_id),
                    "episodes": [],
                }
            )

        serialized_episodes = [
            {
                "imdbId": ep.imdbId,
                "title": ep.title,
                "year": ep.year,
                "rating": ep.rating,
                "votes": ep.votes,
                "plot": ep.plot,
                "release_date": ep.release_date,
                "duration": ep.duration,
                "genres": ep.genres or [],
            }
            for ep in episodes
        ]

        result = {
            "series_id": imdb_id,
            "episode_count": len(episodes),
            "episodes": serialized_episodes,
        }

        logger.info(f"Retrieved {len(episodes)} episodes for series '{imdb_id}'")
        return json.dumps(result, default=str)

    except Exception as e:
        logger.error(f"Failed to get episodes: {e}")
        return json.dumps({"error": _classify_error(e)})


def get_movie_reviews(intent: str, imdb_id: str) -> str:
    """
    Get user reviews for a movie or TV series.

    Use this tool to see what viewers think about a title.
    Reviews include ratings and review text.

    The imdbinfo.get_reviews() function returns List[dict] with
    already-parsed plain dictionaries (not Pydantic models).

    Args:
        intent: The goal of this tool call
            (e.g., "Getting reviews for The Godfather")
        imdb_id: IMDb ID (with or without 'tt' prefix)
            e.g., 'tt0068646' for The Godfather

    Returns:
        JSON string with structure:
        {
            "imdb_id": "tt0068646",
            "review_count": 50,
            "reviews": [
                {
                    "spoiler": false,
                    "summary": "An offer so good...",
                    "text": "<div>Full review HTML...</div>",
                    "authorRating": 10,
                    "upVotes": 536,
                    "downVotes": 63
                }
            ]
        }
    """
    logger.info(f"get_movie_reviews called with imdb_id='{imdb_id}'")

    if not imdb_id or not imdb_id.strip():
        return json.dumps({"error": ERROR_EMPTY_IMDB_ID})

    try:
        reviews = get_reviews(imdb_id.strip())

        if not reviews:
            return json.dumps(
                {
                    "error": ERROR_REVIEWS_NOT_FOUND.format(imdb_id=imdb_id),
                    "reviews": [],
                }
            )

        result = {
            "imdb_id": imdb_id,
            "review_count": len(reviews),
            "reviews": reviews if isinstance(reviews, list) else [],
        }

        logger.info(f"Retrieved {len(reviews)} reviews for '{imdb_id}'")
        return json.dumps(result, default=str)

    except Exception as e:
        logger.error(f"Failed to get reviews: {e}")
        return json.dumps({"error": _classify_error(e)})


def get_movie_trivia(intent: str, imdb_id: str) -> str:
    """
    Get trivia and interesting facts about a movie or TV series.

    Use this tool to find behind-the-scenes facts, production
    details, and interesting tidbits about a title.

    Args:
        intent: The goal of this tool call
            (e.g., "Getting trivia for Pulp Fiction")
        imdb_id: IMDb ID (with or without 'tt' prefix)
            e.g., 'tt0110912' for Pulp Fiction

    Returns:
        JSON string with structure:
        {
            "imdb_id": "tt0110912",
            "trivia_count": 50,
            "trivia": [
                {
                    "body": "The movie cost only $8 million...",
                    "interestScore": {
                        "usersVoted": 1929,
                        "usersInterested": 1903
                    }
                }
            ]
        }
        Note: The "body" field may contain HTML tags and entities.
    """
    logger.info(f"get_movie_trivia called with imdb_id='{imdb_id}'")

    if not imdb_id or not imdb_id.strip():
        return json.dumps({"error": ERROR_EMPTY_IMDB_ID})

    try:
        trivia = get_trivia(imdb_id.strip())

        if not trivia:
            return json.dumps(
                {
                    "error": ERROR_TRIVIA_NOT_FOUND.format(imdb_id=imdb_id),
                    "trivia": [],
                }
            )

        result = {
            "imdb_id": imdb_id,
            "trivia_count": len(trivia),
            "trivia": trivia if isinstance(trivia, list) else [],
        }

        logger.info(f"Retrieved {len(trivia)} trivia items for '{imdb_id}'")
        return json.dumps(result, default=str)

    except Exception as e:
        logger.error(f"Failed to get trivia: {e}")
        return json.dumps({"error": _classify_error(e)})
