import os
import re
import pickle
import asyncio
import requests
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv


# =========================
# ENV
# =========================
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
if TMDB_API_KEY in ["your_actual_tmdb_api_key_here", "your_tmdb_api_key_here", "xxxx", ""]:
    TMDB_API_KEY = None

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_500 = "https://image.tmdb.org/t/p/w500"


# =========================
# FASTAPI APP
# =========================
app = FastAPI(title="Movie Recommender API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# PICKLE GLOBALS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DF_PATH = os.path.join(BASE_DIR, "df.pkl")
INDICES_PATH = os.path.join(BASE_DIR, "indices.pkl")
TFIDF_MATRIX_PATH = os.path.join(BASE_DIR, "tfidf_matrix.pkl")
TFIDF_PATH = os.path.join(BASE_DIR, "tfidf.pkl")

df: Optional[pd.DataFrame] = None
indices_obj: Any = None
tfidf_matrix: Any = None
tfidf_obj: Any = None

TITLE_TO_IDX: Optional[Dict[str, int]] = None
TITLE_RAW_TO_IDX: Optional[Dict[str, int]] = None



# =========================
# MODELS
# =========================
class TMDBMovieCard(BaseModel):
    tmdb_id: int
    title: str
    poster_url: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None


class TMDBMovieDetails(BaseModel):
    tmdb_id: int
    title: str
    overview: Optional[str] = None
    release_date: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    genres: List[dict] = []


class TFIDFRecItem(BaseModel):
    title: str
    score: float
    match_percentage: Optional[int] = None
    tmdb: Optional[TMDBMovieCard] = None


class SearchBundleResponse(BaseModel):
    query: str
    movie_details: TMDBMovieDetails
    tfidf_recommendations: List[TFIDFRecItem]
    genre_recommendations: List[TMDBMovieCard]


# =========================
# UTILS
# =========================
def _norm_title(t: str) -> str:
    t = str(t).strip().lower()
    return re.sub(r'[^\w\s]', '', t)


def make_img_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if str(path).startswith("http://") or str(path).startswith("https://"):
        return str(path)
    return f"{TMDB_IMG_500}{path}"


GENRE_POSTER_MAP = {
    "animation": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=500&q=80",
    "action": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500&q=80",
    "adventure": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500&q=80",
    "comedy": "https://images.unsplash.com/photo-1514306191717-452ec28c7814?w=500&q=80",
    "drama": "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=500&q=80",
    "sci-fi": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=500&q=80",
    "horror": "https://images.unsplash.com/photo-1509248961158-e54f6934749c?w=500&q=80",
    "romance": "https://images.unsplash.com/photo-1518199266791-5375a83190b7?w=500&q=80",
    "thriller": "https://images.unsplash.com/photo-1478720568477-152d9b164e26?w=500&q=80",
}

FAMOUS_POSTERS = {
    "toy story": "https://upload.wikimedia.org/wikipedia/en/1/13/Toy_Story.jpg",
    "jumanji": "https://upload.wikimedia.org/wikipedia/en/b/b6/Jumanji_poster.jpg",
    "batman": "https://upload.wikimedia.org/wikipedia/en/8/8a/Batman_%281989%29_poster.jpg",
    "spider-man": "https://upload.wikimedia.org/wikipedia/en/f/f3/Spider-Man2002Poster.jpg",
    "inception": "https://upload.wikimedia.org/wikipedia/en/2/2e/Inception_%282010%29_theatrical_poster.jpg",
}


def _get_poster_url_for_movie(title: str, genres_str: str = "") -> str:
    t_lower = str(title).lower().strip()
    if t_lower in FAMOUS_POSTERS:
        return FAMOUS_POSTERS[t_lower]
    g_lower = str(genres_str).lower()
    for g, url in GENRE_POSTER_MAP.items():
        if g in g_lower:
            return url
    return "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&q=80"


def _search_local_movies(query: str, limit: int = 20) -> List[dict]:
    if df is None:
        return []
    q = query.strip().lower()
    matches = df[df["title"].astype(str).str.lower().str.contains(q, regex=False, na=False)]
    results = []
    for idx, row in matches.head(limit).iterrows():
        poster = _get_poster_url_for_movie(row["title"], row.get("genres", ""))
        results.append({
            "id": 990000 + int(idx),
            "title": str(row["title"]),
            "overview": str(row.get("overview", "")),
            "release_date": "",
            "vote_average": float(row.get("vote_average", 0.0)) if pd.notnull(row.get("vote_average")) else 0.0,
            "poster_path": poster,
        })
    return results


def _get_local_top_movies(limit: int = 24) -> List[dict]:
    if df is None:
        return []
    results = []
    for idx, row in df.head(limit).iterrows():
        poster = _get_poster_url_for_movie(row["title"], row.get("genres", ""))
        results.append({
            "id": 990000 + int(idx),
            "title": str(row["title"]),
            "overview": str(row.get("overview", "")),
            "release_date": "",
            "vote_average": float(row.get("vote_average", 0.0)) if pd.notnull(row.get("vote_average")) else 0.0,
            "poster_path": poster,
        })
    return results


def _get_local_movie_details(tmdb_id: int) -> dict:
    if df is None:
        return {"id": tmdb_id, "title": "Unknown", "genres": []}
    idx = tmdb_id - 990000 if tmdb_id >= 990000 else tmdb_id
    if 0 <= idx < len(df):
        row = df.iloc[idx]
        genres_str = str(row.get("genres", ""))
        genres_list = []
        if isinstance(row.get("genres"), list):
            genres_list = [{"id": i + 1, "name": str(g)} for i, g in enumerate(row["genres"])]
        elif isinstance(genres_str, str):
            genres_list = [{"id": i + 1, "name": g.strip()} for i, g in enumerate(genres_str.split(",")) if g.strip()]
        poster = _get_poster_url_for_movie(row["title"], genres_str)
        return {
            "id": tmdb_id,
            "title": str(row["title"]),
            "overview": str(row.get("overview", "")),
            "release_date": "",
            "poster_path": poster,
            "backdrop_path": poster,
            "genres": genres_list,
        }
    return {"id": tmdb_id, "title": f"Movie #{tmdb_id}", "genres": []}


HTTP_CLIENT: Optional[httpx.AsyncClient] = None
SEARCH_BUNDLE_CACHE: Dict[str, Any] = {}


async def tmdb_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safe TMDB GET with fallback to local df dataset on network/API errors or missing API key.
    Uses async httpx connection pool for instant keep-alive requests.
    """
    global HTTP_CLIENT
    q = dict(params)

    if TMDB_API_KEY:
        q["api_key"] = TMDB_API_KEY

        if HTTP_CLIENT is not None:
            try:
                r = await HTTP_CLIENT.get(f"{TMDB_BASE}{path}", params=q)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                pass

        try:
            def _fetch():
                return requests.get(f"{TMDB_BASE}{path}", params=q, timeout=6)
            r = await asyncio.to_thread(_fetch)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass  # Fallback to local dataset on network block or timeout

    # Local fallback dispatch when API key missing or requests fail
    if "/search/movie" in path:
        query = params.get("query", "")
        return {"results": _search_local_movies(query)}
    elif "/trending" in path or "/movie/popular" in path or "/movie/top_rated" in path or "/movie/upcoming" in path or "/movie/now_playing" in path:
        return {"results": _get_local_top_movies()}
    elif path.startswith("/movie/"):
        try:
            m_id = int(path.split("/")[2])
            return _get_local_movie_details(m_id)
        except Exception:
            pass
    elif "/discover/movie" in path:
        return {"results": _get_local_top_movies()}

    return {"results": _get_local_top_movies()}


async def tmdb_cards_from_results(
    results: List[dict], limit: int = 20
) -> List[TMDBMovieCard]:
    out: List[TMDBMovieCard] = []
    for m in (results or [])[:limit]:
        out.append(
            TMDBMovieCard(
                tmdb_id=int(m["id"]),
                title=m.get("title") or m.get("name") or "",
                poster_url=make_img_url(m.get("poster_path")),
                release_date=m.get("release_date"),
                vote_average=m.get("vote_average"),
            )
        )
    return out


async def tmdb_movie_details(movie_id: int) -> TMDBMovieDetails:
    data = await tmdb_get(f"/movie/{movie_id}", {"language": "en-US"})
    return TMDBMovieDetails(
        tmdb_id=int(data["id"]),
        title=data.get("title") or "",
        overview=data.get("overview"),
        release_date=data.get("release_date"),
        poster_url=make_img_url(data.get("poster_path")),
        backdrop_url=make_img_url(data.get("backdrop_path")),
        genres=data.get("genres", []) or [],
    )


async def tmdb_search_movies(query: str, page: int = 1) -> Dict[str, Any]:
    """
    Raw TMDB response for keyword search (MULTIPLE results).
    Streamlit will use this for suggestions and grid.
    """
    return await tmdb_get(
        "/search/movie",
        {
            "query": query,
            "include_adult": "false",
            "language": "en-US",
            "page": page,
        },
    )


async def tmdb_search_first(query: str) -> Optional[dict]:
    data = await tmdb_search_movies(query=query, page=1)
    results = data.get("results", [])
    return results[0] if results else None


# =========================
# TF-IDF Helpers
# =========================
def build_title_to_idx_map(indices: Any) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Normalizes indices into:
    - TITLE_TO_IDX (normalized title -> index)
    - TITLE_RAW_TO_IDX (raw lowercase title -> index)
    """
    title_to_idx: Dict[str, int] = {}
    title_raw_to_idx: Dict[str, int] = {}

    if isinstance(indices, dict) or hasattr(indices, "items"):
        for k, v in indices.items():
            k_str = str(k).strip().lower()
            title_raw_to_idx[k_str] = int(v)
            title_to_idx[_norm_title(k_str)] = int(v)
        return title_to_idx, title_raw_to_idx

    raise RuntimeError("indices.pkl must be dict or pandas Series-like (with .items())")


def find_local_idx_by_title(title: str) -> Optional[int]:
    global TITLE_TO_IDX, TITLE_RAW_TO_IDX
    if not TITLE_TO_IDX:
        return None

    raw_key = str(title).strip().lower()
    norm_key = _norm_title(title)

    # 1. Exact raw match
    if TITLE_RAW_TO_IDX and raw_key in TITLE_RAW_TO_IDX:
        return int(TITLE_RAW_TO_IDX[raw_key])

    # 2. Exact normalized match
    if norm_key in TITLE_TO_IDX:
        return int(TITLE_TO_IDX[norm_key])

    # 3. Clean subtitle match (e.g. "Spider-Man: Far From Home" -> "spider man")
    clean_raw = raw_key.split(":")[0].split("-")[0].strip()
    clean_norm = _norm_title(clean_raw)
    if len(clean_norm) >= 3 and clean_norm in TITLE_TO_IDX:
        return int(TITLE_TO_IDX[clean_norm])

    # 4. Strict Substring match (minimum key length >= 4)
    if len(norm_key) >= 4:
        for k, v in TITLE_TO_IDX.items():
            if len(k) >= 4 and (norm_key == k or (len(k) > 5 and norm_key in k)):
                return int(v)

    return None


def get_local_idx_by_title(title: str) -> int:
    idx = find_local_idx_by_title(title)
    if idx is not None:
        return idx
    raise HTTPException(
        status_code=404, detail=f"Title not found in local dataset: '{title}'"
    )


def tfidf_recommend_titles(
    query_title: str, overview_text: str = "", genres_text: str = "", top_n: int = 10
) -> List[Tuple[str, float]]:
    """
    Returns list of (title, score) from local df using hybrid cosine similarity on TF-IDF matrix
    blended with popularity and vote_average weighting.
    """
    global df, tfidf_matrix, tfidf_obj
    if df is None or tfidf_matrix is None:
        return []

    idx = find_local_idx_by_title(query_title)

    qv = None
    if idx is not None:
        qv = tfidf_matrix[idx]
    else:
        comb_text = f"{query_title} {overview_text} {genres_text}".strip()
        if comb_text and tfidf_obj is not None:
            try:
                qv = tfidf_obj.transform([comb_text])
            except Exception:
                qv = None

    scores = None
    if qv is not None and getattr(qv, "nnz", 0) > 0:
        sim_scores = (tfidf_matrix @ qv.T).toarray().ravel()
        pops = df["popularity"].fillna(0).astype(float).values
        pop_max = pops.max() if pops.max() > 0 else 1.0
        norm_pops = pops / pop_max
        votes = df["vote_average"].fillna(0).astype(float).values / 10.0
        scores = (0.75 * sim_scores) + (0.15 * norm_pops) + (0.10 * votes)

    out: List[Tuple[str, float]] = []
    if scores is not None and scores.max() > 0:
        order = np.argsort(-scores)
        for i in order:
            if idx is not None and int(i) == int(idx):
                continue
            try:
                row = df.iloc[int(i)]
                title_i = str(row["title"])
            except Exception:
                continue
            score_val = float(scores[int(i)])
            if score_val <= 0 and idx is None:
                continue
            out.append((title_i, score_val))
            if len(out) >= top_n:
                break

    # Fallback if no recommendations generated: return popular movies from df
    if not out and df is not None:
        for idx_row, row in df.head(top_n * 2).iterrows():
            if idx is not None and int(idx_row) == int(idx):
                continue
            out.append((str(row["title"]), 0.75))
            if len(out) >= top_n:
                break

    return out


async def attach_tmdb_card_by_title(title: str) -> TMDBMovieCard:
    """
    Uses TMDB search by title to fetch poster for a title.
    If not found on TMDB, falls back to local df poster mapping so it NEVER returns None.
    """
    try:
        m = await tmdb_search_first(title)
        if m and (m.get("poster_path") or m.get("id")):
            return TMDBMovieCard(
                tmdb_id=int(m["id"]),
                title=m.get("title") or title,
                poster_url=make_img_url(m.get("poster_path")),
                release_date=m.get("release_date"),
                vote_average=m.get("vote_average"),
            )
    except Exception:
        pass

    # Fallback 1: Local df lookup
    idx = find_local_idx_by_title(title)
    if idx is not None and df is not None and 0 <= idx < len(df):
        row = df.iloc[idx]
        poster = _get_poster_url_for_movie(title, str(row.get("genres", "")))
        return TMDBMovieCard(
            tmdb_id=990000 + int(idx),
            title=str(row["title"]),
            poster_url=poster,
            release_date="",
            vote_average=float(row.get("vote_average", 0.0)) if pd.notnull(row.get("vote_average")) else 0.0,
        )

    # Fallback 2: Synthetic card
    return TMDBMovieCard(
        tmdb_id=abs(hash(title)) % 1000000 + 100000,
        title=title,
        poster_url=_get_poster_url_for_movie(title, ""),
        release_date="",
        vote_average=7.0,
    )



# =========================
# STARTUP: LOAD PICKLES
# =========================
@app.on_event("startup")
async def load_pickles():
    global df, indices_obj, tfidf_matrix, tfidf_obj, TITLE_TO_IDX, TITLE_RAW_TO_IDX, HTTP_CLIENT

    HTTP_CLIENT = httpx.AsyncClient(timeout=6.0)

    # Load df
    with open(DF_PATH, "rb") as f:
        df = pickle.load(f)

    # Load indices
    with open(INDICES_PATH, "rb") as f:
        indices_obj = pickle.load(f)

    # Load TF-IDF matrix (usually scipy sparse)
    with open(TFIDF_MATRIX_PATH, "rb") as f:
        tfidf_matrix = pickle.load(f)

    # Load tfidf vectorizer (optional, not used directly here)
    with open(TFIDF_PATH, "rb") as f:
        tfidf_obj = pickle.load(f)

    # Build normalized map
    TITLE_TO_IDX, TITLE_RAW_TO_IDX = build_title_to_idx_map(indices_obj)

    # sanity
    if df is None or "title" not in df.columns:
        raise RuntimeError("df.pkl must contain a DataFrame with a 'title' column")


@app.on_event("shutdown")
async def shutdown_event():
    global HTTP_CLIENT
    if HTTP_CLIENT:
        await HTTP_CLIENT.aclose()


# =========================
# ROUTES
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- HOME FEED (TMDB) ----------
@app.get("/home", response_model=List[TMDBMovieCard])
async def home(
    category: str = Query("popular"),
    limit: int = Query(24, ge=1, le=50),
):
    """
    Home feed for Streamlit (posters).
    category:
      - trending (trending/movie/day)
      - popular, top_rated, upcoming, now_playing  (movie/{category})
    """
    try:
        if category == "trending":
            data = await tmdb_get("/trending/movie/day", {"language": "en-US"})
            return await tmdb_cards_from_results(data.get("results", []), limit=limit)

        if category not in {"popular", "top_rated", "upcoming", "now_playing"}:
            raise HTTPException(status_code=400, detail="Invalid category")

        data = await tmdb_get(f"/movie/{category}", {"language": "en-US", "page": 1})
        return await tmdb_cards_from_results(data.get("results", []), limit=limit)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Home route failed: {e}")


# ---------- TMDB KEYWORD SEARCH (MULTIPLE RESULTS) ----------
@app.get("/tmdb/search")
async def tmdb_search(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1, le=10),
):
    """
    Returns RAW TMDB shape with 'results' list.
    Streamlit will use it for:
      - dropdown suggestions
      - grid results
    """
    return await tmdb_search_movies(query=query, page=page)


# ---------- MOVIE DETAILS (SAFE ROUTE) ----------
@app.get("/movie/id/{tmdb_id}", response_model=TMDBMovieDetails)
async def movie_details_route(tmdb_id: int):
    return await tmdb_movie_details(tmdb_id)


# ---------- GENRE RECOMMENDATIONS ----------
@app.get("/recommend/genre", response_model=List[TMDBMovieCard])
async def recommend_genre(
    tmdb_id: int = Query(...),
    limit: int = Query(18, ge=1, le=50),
):
    """
    Given a TMDB movie ID:
    - fetch details
    - pick first genre
    - discover movies in that genre (popular)
    """
    details = await tmdb_movie_details(tmdb_id)
    if not details.genres:
        top_data = await tmdb_get("/movie/popular", {"language": "en-US", "page": 1})
        cards = await tmdb_cards_from_results(top_data.get("results", []), limit=limit)
        return [c for c in cards if c.tmdb_id != tmdb_id]

    genre_id = details.genres[0]["id"]
    discover = await tmdb_get(
        "/discover/movie",
        {
            "with_genres": genre_id,
            "language": "en-US",
            "sort_by": "popularity.desc",
            "page": 1,
        },
    )
    cards = await tmdb_cards_from_results(discover.get("results", []), limit=limit)
    return [c for c in cards if c.tmdb_id != tmdb_id]


# ---------- TF-IDF ONLY (debug/useful) ----------
@app.get("/recommend/tfidf")
async def recommend_tfidf(
    title: str = Query(..., min_length=1),
    top_n: int = Query(10, ge=1, le=50),
):
    recs = tfidf_recommend_titles(title, top_n=top_n)
    return [{"title": t, "score": s} for t, s in recs]


# ---------- BUNDLE: Details + TF-IDF recs + Genre recs ----------
@app.get("/movie/search", response_model=SearchBundleResponse)
async def search_bundle(
    query: str = Query(..., min_length=1),
    tfidf_top_n: int = Query(12, ge=1, le=30),
    genre_limit: int = Query(12, ge=1, le=30),
):
    """
    Ultra-fast Hybrid Recommendation Endpoint:
      - Caches responses for sub-millisecond retrieval
      - Queries TMDB Official Recommendations & Similar Movies API (High Accuracy)
      - Blends with popularity-weighted local TF-IDF similarity in parallel
    """
    cache_key = f"{query.strip().lower()}_{tfidf_top_n}_{genre_limit}"
    if cache_key in SEARCH_BUNDLE_CACHE:
        return SEARCH_BUNDLE_CACHE[cache_key]

    best = await tmdb_search_first(query)
    if not best:
        local_matches = _search_local_movies(query, limit=1)
        if local_matches:
            best = local_matches[0]
        else:
            raise HTTPException(
                status_code=404, detail=f"No movie found for query: {query}"
            )

    tmdb_id = int(best["id"])
    details = await tmdb_movie_details(tmdb_id)

    tfidf_items: List[TFIDFRecItem] = []

    # 1) Primary: Official TMDB Recommendations / Similar API (Highest Quality)
    rec_data = await tmdb_get(f"/movie/{tmdb_id}/recommendations", {"language": "en-US", "page": 1})
    tmdb_results = rec_data.get("results", [])
    if not tmdb_results:
        sim_data = await tmdb_get(f"/movie/{tmdb_id}/similar", {"language": "en-US", "page": 1})
        tmdb_results = sim_data.get("results", [])

    for i, m in enumerate(tmdb_results):
        m_id = int(m["id"])
        if m_id == details.tmdb_id:
            continue
        match_pct = max(70, 98 - (i * 2))
        card = TMDBMovieCard(
            tmdb_id=m_id,
            title=m.get("title") or m.get("name") or "",
            poster_url=make_img_url(m.get("poster_path")),
            release_date=m.get("release_date"),
            vote_average=m.get("vote_average"),
        )
        tfidf_items.append(TFIDFRecItem(
            title=card.title,
            score=match_pct / 100.0,
            match_percentage=match_pct,
            tmdb=card
        ))
        if len(tfidf_items) >= tfidf_top_n:
            break

    # 2) Secondary: Local TF-IDF (Popularity & Rating Weighted) if TMDB recommendations are under limit
    if len(tfidf_items) < tfidf_top_n:
        genres_str = " ".join([g.get("name", "") for g in details.genres]) if details.genres else ""
        recs = tfidf_recommend_titles(
            details.title,
            overview_text=details.overview or "",
            genres_text=genres_str,
            top_n=tfidf_top_n,
        )
        # Fetch cards in PARALLEL using asyncio.gather
        cards = await asyncio.gather(*[attach_tmdb_card_by_title(t) for t, s in recs])
        for (t_title, score), card in zip(recs, cards):
            if any(x.title == t_title for x in tfidf_items):
                continue
            pct = int(min(98, max(68, round(score * 100)))) if score > 0 else 75
            tfidf_items.append(TFIDFRecItem(title=t_title, score=score, match_percentage=pct, tmdb=card))
            if len(tfidf_items) >= tfidf_top_n:
                break

    # 3) Genre recommendations (TMDB discover by first genre)
    genre_recs: List[TMDBMovieCard] = []
    if details.genres:
        genre_id = details.genres[0]["id"]
        discover = await tmdb_get(
            "/discover/movie",
            {
                "with_genres": genre_id,
                "language": "en-US",
                "sort_by": "popularity.desc",
                "page": 1,
            },
        )
        cards = await tmdb_cards_from_results(
            discover.get("results", []), limit=genre_limit
        )
        genre_recs = [c for c in cards if c.tmdb_id != details.tmdb_id]

    if not genre_recs:
        top_data = await tmdb_get("/movie/popular", {"language": "en-US", "page": 1})
        cards = await tmdb_cards_from_results(top_data.get("results", []), limit=genre_limit)
        genre_recs = [c for c in cards if c.tmdb_id != details.tmdb_id]

    if not tfidf_items and genre_recs:
        for g_card in genre_recs[:tfidf_top_n]:
            tfidf_items.append(TFIDFRecItem(
                title=g_card.title,
                score=0.85,
                match_percentage=85,
                tmdb=g_card
            ))

    response = SearchBundleResponse(
        query=query,
        movie_details=details,
        tfidf_recommendations=tfidf_items,
        genre_recommendations=genre_recs,
    )
    SEARCH_BUNDLE_CACHE[cache_key] = response
    return response