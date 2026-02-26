# IMDB Tools (`aria.tools.imdb.functions`)

This file documents the tools implemented in
[`aria.tools.imdb.functions`](src/aria/tools/imdb/functions.py:1).

---

## Title Search

### `search_imdb_titles(intent: str, query: str, title_type: str | None = None)`

Search for movies, TV series, and other titles on IMDb.

**When to use:** Find titles when you don't know the exact IMDb ID.

**Parameters:**
- `intent`: Your intended outcome with this tool call.
- `query`: The title to search for.
- `title_type`: Optional filter - one of: `movie`, `series`, `episode`,
  `short`, `tv_movie`, `video`.

**Returns:**
- JSON with `titles` array (imdbId, title, year, kind, rating)
- JSON with `names` array (imdbId, name, job)

**Example:**
```python
search_imdb_titles("Find The Matrix movie", "The Matrix", title_type="movie")
```

---

## Title Details

### `get_movie_details(intent: str, imdb_id: str)`

Get comprehensive details for a movie or TV series.

**When to use:** You have an IMDb ID and need full information including
cast, crew, ratings, plot, and more.

**Parameters:**
- `intent`: Your intended outcome with this tool call.
- `imdb_id`: IMDb ID (with or without 'tt' prefix), e.g., `tt0133093`.

**Returns:**
- JSON with: imdbId, title, year, kind, duration, rating, votes,
  metacritic_rating, mpaa, plot, genres, languages_text, countries,
  directors, stars, release_date, cover_url, worldwide_gross,
  production_budget, awards.

**Example:**
```python
get_movie_details("Get full details for The Matrix", "tt0133093")
```

---

## Person Tools

### `get_person_details(intent: str, person_id: str)`

Get details about an actor, director, or other film industry person.

**When to use:** You have a person's IMDb ID and need their biography,
known works, and other information.

**Parameters:**
- `intent`: Your intended outcome with this tool call.
- `person_id`: IMDb person ID (with or without 'nm' prefix),
  e.g., `nm0000206`.

**Returns:**
- JSON with: imdbId, name, bio, image_url, birth_date, birth_place,
  death_date, death_place, knownfor, primary_profession, height.

**Example:**
```python
get_person_details("Get info about Keanu Reeves", "nm0000206")
```

---

### `get_person_filmography(intent: str, person_id: str)`

Get the complete filmography for an actor or director.

**When to use:** See all movies and shows a person has worked on,
organized by category (actor, director, etc.).

**Parameters:**
- `intent`: Your intended outcome with this tool call.
- `person_id`: IMDb person ID (with or without 'nm' prefix).

**Returns:**
- JSON with `person_id` and `filmography` dict where keys are categories
  (director, actor, producer, etc.) and values are arrays of titles
  with imdbId, title, year, kind, rating.

**Example:**
```python
get_person_filmography("Get all films directed by Nolan", "nm0634240")
```

---

## TV Series Tools

### `get_all_series_episodes(intent: str, imdb_id: str)`

Get all episodes for a TV series.

**When to use:** Get a complete list of all episodes for a TV series.

**Parameters:**
- `intent`: Your intended outcome with this tool call.
- `imdb_id`: IMDb ID for the TV series, e.g., `tt0903747` for Breaking Bad.

**Returns:**
- JSON with `series_id`, `episode_count`, and `episodes` array.
  Each episode has: imdbId, title, year, rating, votes, plot,
  release_date, duration, genres.

**Note:** Does not include season/episode numbers.

**Example:**
```python
get_all_series_episodes("Get all Breaking Bad episodes", "tt0903747")
```

---

## Reviews and Trivia

### `get_movie_reviews(intent: str, imdb_id: str)`

Get user reviews for a movie or TV series.

**When to use:** See what viewers think about a title.

**Parameters:**
- `intent`: Your intended outcome with this tool call.
- `imdb_id`: IMDb ID (with or without 'tt' prefix).

**Returns:**
- JSON with `imdb_id`, `review_count`, and `reviews` array.
  Each review has: spoiler, summary, text, authorRating, upVotes, downVotes.

**Example:**
```python
get_movie_reviews("Get reviews for The Godfather", "tt0068646")
```

---

### `get_movie_trivia(intent: str, imdb_id: str)`

Get trivia and interesting facts about a movie or TV series.

**When to use:** Find behind-the-scenes facts, production details,
and interesting tidbits.

**Parameters:**
- `intent`: Your intended outcome with this tool call.
- `imdb_id`: IMDb ID (with or without 'tt' prefix).

**Returns:**
- JSON with `imdb_id`, `trivia_count`, and `trivia` array.
  Each item has: body (may contain HTML), interestScore.

**Example:**
```python
get_movie_trivia("Get trivia for Pulp Fiction", "tt0110912")
```

---

## Error Handling

All functions return a JSON object with an `error` key when something
goes wrong. Common errors:

- Empty query/ID: `"Search query is required."` or `"IMDb ID is required."`
- Not found: `"No movie/series found with IMDb ID '...'"`
- Network issues: `"Network error: Unable to connect to IMDb..."`
- Rate limiting: `"Rate limited by IMDb. Please wait..."`
