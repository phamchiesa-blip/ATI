"""
data_pipeline.py
-----------------
Step 1 of the Data & Feature Engineering task: load the two raw TMDB 5000
CSV files, merge them, and clean/parse them into a single tidy DataFrame
that the rest of the pipeline (feature_engineering.py) can consume.

Expected input files (download from Kaggle: "TMDB 5000 Movie Dataset"):
    tmdb_5000_movies.csv
    tmdb_5000_credits.csv
"""

import ast
import pandas as pd


def _safe_literal_eval(value):
    """The genres/keywords/cast/crew columns are stored as strings that look
    like Python/JSON lists of dicts, e.g. '[{"id": 28, "name": "Action"}, ...]'.
    This turns that string back into a real Python list, or [] if it's empty
    or malformed."""
    if pd.isna(value):
        return []
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return []


def _extract_names(list_of_dicts, key="name", limit=None):
    """Pulls out the 'name' field from a list of dicts, e.g. turns
    [{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}]
    into ["Action", "Adventure"]. `limit` keeps only the first N names,
    useful for cast (we usually only care about the main/top-billed cast)."""
    names = [d.get(key) for d in list_of_dicts if isinstance(d, dict) and d.get(key)]
    if limit is not None:
        names = names[:limit]
    return names


def _extract_director(crew_list):
    """The crew column mixes every job (editor, composer, director, ...).
    We only want the director's name."""
    for member in crew_list:
        if isinstance(member, dict) and member.get("job") == "Director":
            return member.get("name")
    return None


def load_raw(movies_csv_path: str, credits_csv_path: str) -> pd.DataFrame:
    """Load the two CSV files and merge them into one DataFrame, one row
    per movie."""
    movies = pd.read_csv(movies_csv_path)
    credits = pd.read_csv(credits_csv_path)

    # Both files identify the movie, but under different column names
    # (movies.id vs credits.movie_id). Standardize to `movie_id`.
    movies = movies.rename(columns={"id": "movie_id"})
    credits = credits.rename(columns={"movie_id": "movie_id"})[["movie_id", "cast", "crew"]]

    df = movies.merge(credits, on="movie_id", how="inner")
    return df


def clean_and_parse(df: pd.DataFrame, top_cast_n: int = 5) -> pd.DataFrame:
    """Clean missing/invalid rows and turn the raw JSON-like text columns
    into simple Python lists/strings that are easy to work with later.

    Adds these new columns:
        genres_list    -> list[str]
        keywords_list  -> list[str]
        cast_list      -> list[str]   (top `top_cast_n` billed actors only)
        director       -> str or None
        release_year   -> int or None
    """
    df = df.copy()

    # Drop movies with no title or no overview -- there is nothing useful
    # to build a content-based feature vector from in that case.
    df = df.dropna(subset=["title", "overview"])
    df = df.drop_duplicates(subset=["movie_id"])

    # Fill in reasonable defaults for the numeric fields we will normalize
    # later, instead of dropping the movie entirely.
    df["popularity"] = df["popularity"].fillna(0.0)
    df["vote_average"] = df["vote_average"].fillna(0.0)
    df["vote_count"] = df["vote_count"].fillna(0)
    df["overview"] = df["overview"].fillna("")

    # Parse the JSON-like text columns.
    df["genres_list"] = df["genres"].apply(_safe_literal_eval).apply(_extract_names)
    df["keywords_list"] = df["keywords"].apply(_safe_literal_eval).apply(_extract_names)
    cast_parsed = df["cast"].apply(_safe_literal_eval)
    df["cast_list"] = cast_parsed.apply(lambda lst: _extract_names(lst, limit=top_cast_n))
    crew_parsed = df["crew"].apply(_safe_literal_eval)
    df["director"] = crew_parsed.apply(_extract_director)

    # release_date -> release_year (used for the "Newness" signal later).
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["release_year"] = df["release_date"].dt.year

    # A movie with no genre at all and no director is almost always a data
    # error in this dataset, not a real movie -- drop those too.
    df = df[df["genres_list"].apply(len) > 0]

    return df.reset_index(drop=True)


if __name__ == "__main__":
    # Quick manual check: `python data_pipeline.py <movies.csv> <credits.csv>`
    import sys

    movies_path, credits_path = sys.argv[1], sys.argv[2]
    raw = load_raw(movies_path, credits_path)
    clean = clean_and_parse(raw)
    print(f"Loaded {len(raw)} raw rows -> {len(clean)} clean rows")
    print(clean[["movie_id", "title", "genres_list", "director", "cast_list", "release_year"]].head())
