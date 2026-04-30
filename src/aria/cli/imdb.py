"""Entertainment CLI commands.

Wraps IMDb tools as CLI sub-commands that output JSON.
"""

from typing import Optional

import typer

app = typer.Typer(
    help="Search movies, TV shows, people, and episodes via IMDb.",
)


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Title or name to search for"),
    title_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter: movie, series, episode, short"
    ),
):
    """Search for movies, TV series, and people on IMDb."""
    from aria.tools.imdb.functions import search_imdb_titles

    result = search_imdb_titles(
        reason="CLI IMDb search", query=query, title_type=title_type
    )
    typer.echo(result)


@app.command("movie")
def movie_cmd(
    imdb_id: str = typer.Argument(..., help="IMDb ID (e.g. tt0133093)"),
):
    """Get comprehensive details for a movie or TV series."""
    from aria.tools.imdb.functions import get_movie_details

    result = get_movie_details(
        reason="CLI IMDb movie details", imdb_id=imdb_id
    )
    typer.echo(result)


@app.command("person")
def person_cmd(
    person_id: str = typer.Argument(
        ..., help="IMDb person ID (e.g. nm0000206)"
    ),
):
    """Get details about an actor, director, or crew member."""
    from aria.tools.imdb.functions import get_person_details

    result = get_person_details(
        reason="CLI IMDb person details", person_id=person_id
    )
    typer.echo(result)


@app.command("filmography")
def filmography_cmd(
    person_id: str = typer.Argument(..., help="IMDb person ID"),
):
    """Get complete filmography for a person."""
    from aria.tools.imdb.functions import get_person_filmography

    result = get_person_filmography(
        reason="CLI IMDb filmography", person_id=person_id
    )
    typer.echo(result)


@app.command("episodes")
def episodes_cmd(
    imdb_id: str = typer.Argument(..., help="IMDb series ID"),
):
    """Get all episodes for a TV series."""
    from aria.tools.imdb.functions import get_all_series_episodes

    result = get_all_series_episodes(
        reason="CLI IMDb episodes", imdb_id=imdb_id
    )
    typer.echo(result)


@app.command("reviews")
def reviews_cmd(
    imdb_id: str = typer.Argument(..., help="IMDb title ID"),
):
    """Get user reviews for a movie or TV series."""
    from aria.tools.imdb.functions import get_movie_reviews

    result = get_movie_reviews(reason="CLI IMDb reviews", imdb_id=imdb_id)
    typer.echo(result)


@app.command("trivia")
def trivia_cmd(
    imdb_id: str = typer.Argument(..., help="IMDb title ID"),
):
    """Get trivia and interesting facts about a title."""
    from aria.tools.imdb.functions import get_movie_trivia

    result = get_movie_trivia(reason="CLI IMDb trivia", imdb_id=imdb_id)
    typer.echo(result)
