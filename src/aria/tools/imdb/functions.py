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

import inspect
from functools import wraps
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

from aria.tools import tool_error_response, tool_success_response
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
            ERROR_INVALID_TITLE_TYPE.format(
                value=title_type, valid_types=valid_types
            )
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


def _imdb_tool(
    error_not_found_msg_template: str, *, id_param: str = "imdb_id"
):
    """Decorator for IMDB tool functions.

    Handles ID validation and standardized error handling.

    Args:
        error_not_found_msg_template: Message template for not-found cases.
        id_param: Name of the ID parameter to validate and normalize.
    """

    def _format_not_found_msg(id_value: str) -> str:
        return error_not_found_msg_template.format(**{id_param: id_value})

    def decorator(func):
        signature = inspect.signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs) -> str:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()

            intent = str(bound.arguments.get("intent", "unknown"))
            raw_id = bound.arguments.get(id_param)

            if not isinstance(raw_id, str) or not raw_id.strip():
                return tool_error_response(
                    func.__name__, intent, ValueError(ERROR_EMPTY_IMDB_ID)
                )

            normalized_id = raw_id.strip()
            bound.arguments[id_param] = normalized_id

            try:
                return func(*bound.args, **bound.kwargs)
            except ValueError as e:
                expected_not_found = _format_not_found_msg(normalized_id)
                if "not found" in str(e).lower() or expected_not_found in str(
                    e
                ):
                    return tool_error_response(
                        func.__name__, intent, ValueError(expected_not_found)
                    )
                logger.error(f"{func.__name__} validation error: {e}")
                return tool_error_response(func.__name__, intent, e)
            except Exception as e:
                logger.error(f"{func.__name__} failed: {e}")
                return tool_error_response(
                    func.__name__, intent, RuntimeError(_classify_error(e))
                )

        return wrapper

    return decorator


def search_imdb_titles(
    intent: str, query: str, title_type: Optional[str] = None
) -> str:
    """
    Search for movies, TV series, and other titles on IMDb.

    Args:
        intent: Why you're searching (e.g., "Finding Matrix movie")
        query: The title to search for
        title_type: Optional filter - movie, series, episode, short,
            tv_movie, video

    Returns:
        JSON with titles[{imdbId, title, year, kind, rating}],
        names[{imdbId, name, job}]. Use when IMDb ID unknown.
    """
    logger.info(f"search_imdb_titles called with query='{query}'")

    if not query or not query.strip():
        return tool_error_response(
            "search_imdb_titles", intent, ValueError(ERROR_EMPTY_QUERY)
        )

    try:
        imdb_title_type = _get_title_type(title_type)
        logger.debug(f"Title type filter: {imdb_title_type}")

        result = search_title(query.strip(), title_type=imdb_title_type)

        if result is None or (
            (not result.titles or len(result.titles) == 0)
            and (not result.names or len(result.names) == 0)
        ):
            return tool_error_response(
                "search_imdb_titles",
                intent,
                ValueError(ERROR_NO_RESULTS.format(query=query)),
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
        return tool_success_response("search_imdb_titles", intent, response)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return tool_error_response("search_imdb_titles", intent, e)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return tool_error_response(
            "search_imdb_titles", intent, RuntimeError(_classify_error(e))
        )


@_imdb_tool(ERROR_MOVIE_NOT_FOUND.format(imdb_id="{imdb_id}"))
def get_movie_details(intent: str, imdb_id: str) -> str:
    """Get comprehensive details for a movie or TV series."""
    logger.info(f"get_movie_details called with imdb_id='{imdb_id}'")

    movie = get_movie(imdb_id)

    if movie is None:
        raise ValueError(ERROR_MOVIE_NOT_FOUND.format(imdb_id=imdb_id))

    # Directors: prefer movie.directors, fall back to categories
    directors = [
        {"imdbId": d.imdbId, "name": d.name} for d in (movie.directors or [])
    ]
    if not directors:
        cat_directors = (movie.categories or {}).get("director", [])
        directors = [
            {"imdbId": d.imdbId, "name": d.name} for d in cat_directors
        ]

    # Writers: extracted from categories
    cat_writers = (movie.categories or {}).get("writer", [])
    writers = [{"imdbId": w.imdbId, "name": w.name} for w in cat_writers]

    # Producers: extracted from categories
    cat_producers = (movie.categories or {}).get("producer", [])
    producers = [{"imdbId": p.imdbId, "name": p.name} for p in cat_producers]

    # Cast with characters: extracted from categories
    cat_cast = (movie.categories or {}).get("cast", [])
    cast = [
        {
            "imdbId": c.imdbId,
            "name": c.name,
            "characters": getattr(c, "characters", []),
        }
        for c in cat_cast
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
        "writers": writers,
        "producers": producers,
        "cast": cast,
        "stars": stars,
        "release_date": movie.release_date,
        "cover_url": movie.cover_url,
        "worldwide_gross": movie.worldwide_gross,
        "production_budget": movie.production_budget,
        "awards": awards,
    }

    logger.info(f"Retrieved details for '{movie.title}' ({movie.year})")
    return tool_success_response("get_movie_details", intent, result)


@_imdb_tool(
    ERROR_PERSON_NOT_FOUND.format(person_id="{person_id}"),
    id_param="person_id",
)
def get_person_details(intent: str, person_id: str) -> str:
    """
    Get details about an actor, director, or other film industry person.

    Args:
        intent: Why you're fetching (e.g., "Getting Keanu Reeves info")
        person_id: IMDb person ID with/without 'nm' prefix (e.g., nm0000206)

    Returns:
        JSON with imdbId, name, bio, image_url, birth_date, birth_place,
        knownfor[], primary_profession[], height.
    """
    logger.info(f"get_person_details called with person_id='{person_id}'")

    person = get_name(person_id)

    if person is None:
        raise ValueError(ERROR_PERSON_NOT_FOUND.format(person_id=person_id))

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
    return tool_success_response("get_person_details", intent, result)


@_imdb_tool(
    ERROR_FILMOGRAPHY_NOT_FOUND.format(person_id="{person_id}"),
    id_param="person_id",
)
def get_person_filmography(intent: str, person_id: str) -> str:
    """
    Get the complete filmography for an actor or director.

    Args:
        intent: Why you're fetching (e.g., "Getting Nolan filmography")
        person_id: IMDb person ID with/without 'nm' prefix

    Returns:
        JSON with filmography{director[], actor[], producer[], writer[]}.
        Each entry has imdbId, title, year, kind, rating.
    """
    logger.info(f"get_person_filmography called with person_id='{person_id}'")

    filmography = get_filmography(person_id)

    if not filmography:
        raise ValueError(
            ERROR_FILMOGRAPHY_NOT_FOUND.format(person_id=person_id)
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
    return tool_success_response("get_person_filmography", intent, result)


@_imdb_tool(ERROR_EPISODES_NOT_FOUND.format(imdb_id="{imdb_id}"))
def get_all_series_episodes(intent: str, imdb_id: str) -> str:
    """
    Get all episodes for a TV series.

    Args:
        intent: Why you're fetching (e.g., "Getting Breaking Bad episodes")
        imdb_id: IMDb series ID with/without 'tt' prefix

    Returns:
        JSON with series_id, episode_count, episodes[{imdbId, title,
        year, rating, votes, plot, release_date, duration, genres}].
        Note: No season/episode numbers in this endpoint.
    """
    logger.info(f"get_all_series_episodes called with imdb_id='{imdb_id}'")

    episodes = get_all_episodes(imdb_id)

    if not episodes:
        raise ValueError(ERROR_EPISODES_NOT_FOUND.format(imdb_id=imdb_id))

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
    return tool_success_response("get_all_series_episodes", intent, result)


@_imdb_tool(ERROR_REVIEWS_NOT_FOUND.format(imdb_id="{imdb_id}"))
def get_movie_reviews(intent: str, imdb_id: str) -> str:
    """
    Get user reviews for a movie or TV series.

    Args:
        intent: Why you're fetching (e.g., "Checking Godfather reviews")
        imdb_id: IMDb ID with/without 'tt' prefix

    Returns:
        JSON with imdb_id, review_count, reviews[{spoiler, summary,
        text, authorRating, upVotes, downVotes}].
    """
    logger.info(f"get_movie_reviews called with imdb_id='{imdb_id}'")

    reviews = get_reviews(imdb_id)

    if not reviews:
        raise ValueError(ERROR_REVIEWS_NOT_FOUND.format(imdb_id=imdb_id))

    result = {
        "imdb_id": imdb_id,
        "review_count": len(reviews),
        "reviews": reviews if isinstance(reviews, list) else [],
    }

    logger.info(f"Retrieved {len(reviews)} reviews for '{imdb_id}'")
    return tool_success_response("get_movie_reviews", intent, result)


@_imdb_tool(ERROR_TRIVIA_NOT_FOUND.format(imdb_id="{imdb_id}"))
def get_movie_trivia(intent: str, imdb_id: str) -> str:
    """
    Get trivia and interesting facts about a movie or TV series.

    Args:
        intent: Why you're fetching (e.g., "Getting Pulp Fiction trivia")
        imdb_id: IMDb ID with/without 'tt' prefix

    Returns:
        JSON with imdb_id, trivia_count, trivia[{text, related_titles}].
        Behind-the-scenes facts and production details.
    """
    logger.info(f"get_movie_trivia called with imdb_id='{imdb_id}'")

    trivia = get_trivia(imdb_id)

    if not trivia:
        raise ValueError(ERROR_TRIVIA_NOT_FOUND.format(imdb_id=imdb_id))

    result = {
        "imdb_id": imdb_id,
        "trivia_count": len(trivia),
        "trivia": trivia if isinstance(trivia, list) else [],
    }

    logger.info(f"Retrieved {len(trivia)} trivia items for '{imdb_id}'")
    return tool_success_response("get_movie_trivia", intent, result)
