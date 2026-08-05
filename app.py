import os
import random
import urllib.parse
import requests
import streamlit as st

# ==============================================================================
# CONFIG & PAGE SETUP
# ==============================================================================
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(
    page_title="MovieVerse",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# MODERN DARK ORANGE & BLACK GLASSMORPHISM STYLES
# ==============================================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Outfit', 'Inter', sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at top left, #261103 0%, #0d0d12 45%, #050507 100%);
        color: #f8fafc;
    }

    /* Hide Streamlit Top Header Bar & Toolbar */
    header[data-testid="stHeader"] {
        display: none !important;
    }

    #MainMenu, footer {
        visibility: hidden;
    }

    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 3rem;
        max-width: 1440px;
    }

    .navbar-bar {
        background: rgba(26, 18, 14, 0.75);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(249, 115, 22, 0.2);
        border-radius: 20px;
        padding: 12px 24px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
    }

    /* Glassmorphism Card Base */
    .glass-card {
        background: rgba(22, 22, 30, 0.75);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(249, 115, 22, 0.15);
        border-radius: 20px;
        padding: 18px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.6);
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease;
    }

    .glass-card:hover {
        transform: translateY(-6px);
        border-color: rgba(249, 115, 22, 0.45);
        box-shadow: 0 20px 40px -15px rgba(249, 115, 22, 0.3);
    }

    /* Hero Banner */
    .hero-container {
        position: relative;
        border-radius: 24px;
        overflow: hidden;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, rgba(45, 18, 4, 0.92), rgba(15, 12, 16, 0.96));
        border: 1px solid rgba(249, 115, 22, 0.25);
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7);
        padding: 35px;
    }

    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #ffedd5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    .hero-overview {
        color: #94a3b8;
        font-size: 1.02rem;
        line-height: 1.6;
        max-width: 800px;
        margin-bottom: 1.2rem;
    }

    /* Movie Poster Wrap & Badges */
    .poster-wrap {
        position: relative;
        border-radius: 16px;
        overflow: hidden;
        margin-bottom: 10px;
        aspect-ratio: 2/3;
        background: #181820;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }

    .poster-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.4s ease;
    }

    .poster-wrap:hover .poster-img {
        transform: scale(1.05);
    }

    /* Floating Badges */
    .badge-rating {
        position: absolute;
        top: 10px;
        right: 10px;
        background: rgba(12, 12, 16, 0.85);
        backdrop-filter: blur(8px);
        color: #f59e0b;
        font-weight: 700;
        font-size: 0.82rem;
        padding: 4px 9px;
        border-radius: 10px;
        border: 1px solid rgba(245, 158, 11, 0.35);
        z-index: 10;
    }

    .badge-match {
        position: absolute;
        top: 10px;
        left: 10px;
        background: linear-gradient(135deg, #ea580c, #c2410c);
        color: #ffffff;
        font-weight: 800;
        font-size: 0.78rem;
        padding: 4px 9px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.45);
        z-index: 10;
    }

    /* Gradient Poster Fallback */
    .fallback-poster {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 15px;
        background: linear-gradient(135deg, #431407 0%, #1c0a03 50%, #0a0a0d 100%);
        color: #ffedd5;
    }

    .fallback-title {
        font-size: 0.95rem;
        font-weight: 700;
        margin-top: 10px;
        line-height: 1.25;
    }

    /* Movie Titles */
    .movie-card-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #f1f5f9;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-top: 6px;
        margin-bottom: 2px;
    }

    .movie-card-subtitle {
        font-size: 0.8rem;
        color: #64748b;
        margin-bottom: 8px;
    }

    /* Genre Pill */
    .genre-pill {
        display: inline-block;
        background: rgba(249, 115, 22, 0.15);
        color: #fed7aa;
        border: 1px solid rgba(249, 115, 22, 0.35);
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 500;
        margin-right: 6px;
        margin-bottom: 6px;
    }

    /* Custom Streamlit Button Styling */
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        font-weight: 600;
        background: linear-gradient(135deg, #ea580c 0%, #9a3412 100%);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.15);
        transition: all 0.2s ease;
        padding: 6px 14px;
    }

    div.stButton > button:hover {
        background: linear-gradient(135deg, #f97316 0%, #c2410c 100%);
        box-shadow: 0 6px 20px rgba(249, 115, 22, 0.45);
        border-color: rgba(255, 255, 255, 0.3);
        transform: translateY(-2px);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# STATE & ROUTING MANAGEMENT
# ==============================================================================
if "view" not in st.session_state:
    st.session_state.view = "home"  # home | details | watchlist
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None
if "watchlist" not in st.session_state:
    st.session_state.watchlist = {}
if "recently_viewed" not in st.session_state:
    st.session_state.recently_viewed = []

qp_view = st.query_params.get("view")
qp_id = st.query_params.get("id")
if qp_view in ("home", "details", "watchlist"):
    st.session_state.view = qp_view
if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except Exception:
        pass


def goto_home():
    st.session_state.view = "home"
    st.query_params["view"] = "home"
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()


def goto_details(tmdb_id: int):
    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.query_params["view"] = "details"
    st.query_params["id"] = str(int(tmdb_id))
    st.rerun()


def goto_watchlist():
    st.session_state.view = "watchlist"
    st.query_params["view"] = "watchlist"
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()


def toggle_watchlist(movie: dict):
    m_id = movie.get("tmdb_id") or movie.get("id")
    if not m_id:
        return
    m_id = int(m_id)
    if m_id in st.session_state.watchlist:
        del st.session_state.watchlist[m_id]
        st.toast(f"Removed '{movie.get('title')}' from Watchlist", icon="🗑️")
    else:
        st.session_state.watchlist[m_id] = movie
        st.toast(f"Saved '{movie.get('title')}' to Watchlist!", icon="❤️")


# ==============================================================================
# API HELPERS
# ==============================================================================
@st.cache_data(ttl=600, show_spinner=False)
def api_get_json(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=20)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:250]}"
        return r.json(), None
    except Exception as e:
        return None, f"Connection issue: {e}"


# ==============================================================================
# UI COMPONENTS
# ==============================================================================
def render_header():
    col1, col2 = st.columns([3, 2], vertical_alignment="center")
    with col1:
        st.markdown(
            "<h1 style='margin:0 0 10px 0; font-size: 2.3rem; font-weight:800; background: linear-gradient(135deg, #ffedd5, #ea580c); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>🎬 MovieVerse</h1>",
            unsafe_allow_html=True,
        )
    with col2:
        nav_c1, nav_c2, nav_c3 = st.columns([1, 1, 1])
        with nav_c1:
            if st.button("🏠 Home", use_container_width=True):
                goto_home()
        with nav_c2:
            wl_count = len(st.session_state.watchlist)
            if st.button(f"❤️ Watchlist ({wl_count})", use_container_width=True):
                goto_watchlist()
        with nav_c3:
            if st.button("🎲 Pick Random!", use_container_width=True):
                # Fetch trending and select random
                data, _ = api_get_json("/home", {"category": "popular", "limit": 30})
                if data:
                    random_movie = random.choice(data)
                    goto_details(random_movie["tmdb_id"])


def render_poster_card(movie: dict, match_pct: int | None = None, key_prefix: str = "card"):
    tmdb_id = movie.get("tmdb_id") or movie.get("id")
    title = movie.get("title", "Untitled")
    poster_url = movie.get("poster_url") or movie.get("poster_path")
    vote_avg = movie.get("vote_average")
    release_date = movie.get("release_date") or ""
    year = release_date.split("-")[0] if release_date and "-" in release_date else ""

    # Rating badge
    rating_html = f"<div class='badge-rating'>⭐ {vote_avg:.1f}</div>" if vote_avg and vote_avg > 0 else ""
    # Match badge
    match_html = f"<div class='badge-match'>🔥 {match_pct}% Match</div>" if match_pct else ""

    # Poster image or Fallback
    if poster_url:
        poster_html = f"<div class='poster-wrap'>{match_html}{rating_html}<img src='{poster_url}' class='poster-img' alt='{title}'/></div>"
    else:
        poster_html = (
            f"<div class='poster-wrap'>{match_html}{rating_html}"
            f"<div class='fallback-poster'>"
            f"<div style='font-size: 2.2rem;'>🎬</div>"
            f"<div class='fallback-title'>{title}</div>"
            f"</div></div>"
        )

    st.markdown(poster_html, unsafe_allow_html=True)
    st.markdown(f"<div class='movie-card-title'>{title}</div>", unsafe_allow_html=True)
    if year:
        st.markdown(f"<div class='movie-card-subtitle'>{year}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='movie-card-subtitle'>Movie</div>", unsafe_allow_html=True)

    btn_c1, btn_c2 = st.columns([2.5, 1])
    with btn_c1:
        if st.button("Details", key=f"{key_prefix}_det_{tmdb_id}"):
            if tmdb_id:
                goto_details(tmdb_id)
    with btn_c2:
        is_saved = int(tmdb_id) in st.session_state.watchlist if tmdb_id else False
        btn_label = "❤️" if is_saved else "🤍"
        if st.button(btn_label, key=f"{key_prefix}_wl_{tmdb_id}"):
            toggle_watchlist(movie)
            st.rerun()


def render_poster_grid(movies: list, cols: int = 6, key_prefix: str = "grid"):
    if not movies:
        st.info("No movies found matching your criteria.")
        return

    rows = (len(movies) + cols - 1) // cols
    idx = 0
    for r in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(movies):
                break
            m = movies[idx]
            match_pct = m.get("match_percentage")
            with colset[c]:
                render_poster_card(m, match_pct=match_pct, key_prefix=f"{key_prefix}_{r}_{c}_{idx}")
            idx += 1


# ==============================================================================
# VIEWS
# ==============================================================================
def view_home():
    render_header()

    # Search & Filter Controls
    search_col, filter_col, rating_col = st.columns([3, 1.5, 1.5])

    with search_col:
        query = st.text_input(
            "🔍 Search Movie",
            placeholder="Type movie name (e.g. Inception, Avengers, Batman...)",
        )

    with filter_col:
        category = st.selectbox(
            "🏷️ Feed Category",
            ["trending", "popular", "top_rated", "upcoming", "now_playing"],
            format_func=lambda x: x.replace("_", " ").title(),
        )

    with rating_col:
        min_rating = st.slider("⭐ Minimum Rating", 0.0, 9.0, 0.0, step=0.5)

    # Search mode vs Feed mode
    if query and len(query.strip()) >= 2:
        st.markdown(f"### 🔎 Search Results for *'{query}'*")
        data, err = api_get_json("/tmdb/search", {"query": query.strip()})
        if err or not data:
            st.warning(f"Could not retrieve search results: {err}")
        else:
            raw_results = data.get("results", [])
            cards = []
            for item in raw_results:
                v_avg = item.get("vote_average", 0.0)
                if min_rating > 0 and v_avg < min_rating:
                    continue
                cards.append({
                    "tmdb_id": item.get("id"),
                    "title": item.get("title") or item.get("name") or "Untitled",
                    "poster_url": f"{TMDB_IMG}{item.get('poster_path')}" if item.get("poster_path") else None,
                    "vote_average": v_avg,
                    "release_date": item.get("release_date"),
                })
            render_poster_grid(cards, cols=6, key_prefix="search_grid")

    else:
        # Featured Hero Banner
        data, err = api_get_json("/home", {"category": category, "limit": 30})

        if data and len(data) > 0:
            hero_movie = data[0]
            hero_id = hero_movie.get("tmdb_id")
            hero_title = hero_movie.get("title", "")
            hero_rating = hero_movie.get("vote_average", 0.0)

            hero_html = f"""
            <div class='hero-container'>
                <div style='display:flex; gap:30px; align-items:center; flex-wrap:wrap;'>
                    <div style='flex:1; min-width: 280px;'>
                        <span class='genre-pill'>🔥 Top Recommendation</span>
                        <h2 class='hero-title'>{hero_title}</h2>
                        <p class='hero-overview'>Explore detailed recommendations and content-based similarity matches for {hero_title}.</p>
                        <div style='display:flex; gap:15px; align-items:center;'>
                            <div style='font-size: 1.1rem; font-weight:700; color:#f59e0b;'>⭐ {hero_rating:.1f} / 10</div>
                        </div>
                    </div>
                </div>
            </div>
            """
            st.markdown(hero_html, unsafe_allow_html=True)
            if st.button(f"✨ Explore Details for '{hero_title}'", key="hero_btn"):
                if hero_id:
                    goto_details(hero_id)

            st.markdown(f"### 🍿 {category.replace('_', ' ').title()} Movies")

            # Apply rating filter
            filtered_data = [m for m in data if (m.get("vote_average") or 0.0) >= min_rating]
            render_poster_grid(filtered_data, cols=6, key_prefix="home_grid")
        else:
            st.info("Loading movie feed...")


def view_details():
    render_header()

    tmdb_id = st.session_state.selected_tmdb_id
    if not tmdb_id:
        st.error("No movie selected.")
        if st.button("⬅️ Back to Home"):
            goto_home()
        return

    # Fetch movie details
    data, err = api_get_json(f"/movie/id/{tmdb_id}")
    if err or not data:
        st.error(f"Could not load details for movie #{tmdb_id}: {err}")
        if st.button("⬅️ Back to Home"):
            goto_home()
        return

    # Record in recently viewed
    if not any(m.get("tmdb_id") == tmdb_id for m in st.session_state.recently_viewed):
        st.session_state.recently_viewed.insert(0, {
            "tmdb_id": tmdb_id,
            "title": data.get("title"),
            "poster_url": data.get("poster_url"),
            "vote_average": data.get("vote_average"),
        })
        st.session_state.recently_viewed = st.session_state.recently_viewed[:8]

    # Top Bar
    if st.button("⬅️ Back to Home"):
        goto_home()

    # Detail Header Layout
    left, right = st.columns([1, 2.5], gap="large")

    with left:
        poster_url = data.get("poster_url")
        if poster_url:
            st.image(poster_url, width="stretch")
        else:
            st.markdown(
                f"<div class='fallback-poster' style='height: 400px; border-radius:16px;'>"
                f"<div style='font-size: 3rem;'>🎬</div>"
                f"<div class='fallback-title'>{data.get('title')}</div></div>",
                unsafe_allow_html=True,
            )

        # Watchlist Toggle Button
        is_saved = int(tmdb_id) in st.session_state.watchlist
        wl_btn_text = "💔 Remove from Watchlist" if is_saved else "❤️ Add to Watchlist"
        if st.button(wl_btn_text, use_container_width=True):
            toggle_watchlist(data)
            st.rerun()

    with right:
        title = data.get("title", "")
        release_date = data.get("release_date") or "-"
        genres = data.get("genres", [])
        overview = data.get("overview") or "No overview available."

        st.markdown(f"# {title}")

        # Meta pills
        genre_pills_html = "".join([f"<span class='genre-pill'>{g.get('name')}</span>" for g in genres])
        st.markdown(
            f"<div style='margin-bottom: 12px;'>{genre_pills_html}</div>"
            f"<p style='color:#94a3b8;'>📅 Release Date: <b>{release_date}</b></p>",
            unsafe_allow_html=True,
        )

        st.markdown("### 📖 Overview")
        st.write(overview)

        # Trailer Search Link Button
        yt_query = urllib.parse.quote(f"{title} official trailer")
        yt_url = f"https://www.youtube.com/results?search_query={yt_query}"
        st.markdown(
            f"<a href='{yt_url}' target='_blank' style='text-decoration:none;'>"
            f"<div style='display:inline-block; background:linear-gradient(135deg, #ef4444, #dc2626); color:white; font-weight:700; padding:10px 20px; border-radius:12px;'>▶️ Watch Trailer on YouTube</div>"
            f"</a>",
            unsafe_allow_html=True,
        )

    st.divider()

    # Recommendations Bundle
    st.markdown(f"## 🤖 AI Recommended Movies for *'{title}'*")

    bundle, err_b = api_get_json("/movie/search", {"query": title, "tfidf_top_n": 12})
    cards = []
    if bundle:
        tfidf_items = bundle.get("tfidf_recommendations", [])
        for x in tfidf_items or []:
            tmdb = x.get("tmdb") or {}
            rec_title = tmdb.get("title") or x.get("title") or "Untitled"
            rec_id = tmdb.get("tmdb_id") or (abs(hash(rec_title)) % 1000000 + 100000)
            cards.append({
                "tmdb_id": rec_id,
                "title": rec_title,
                "poster_url": tmdb.get("poster_url"),
                "vote_average": tmdb.get("vote_average"),
                "release_date": tmdb.get("release_date"),
                "match_percentage": x.get("match_percentage") or 80,
            })
        
        if not cards:
            genre_recs = bundle.get("genre_recommendations", [])
            for g in genre_recs or []:
                cards.append({
                    "tmdb_id": g.get("tmdb_id") or (abs(hash(g.get("title", ""))) % 1000000 + 100000),
                    "title": g.get("title") or "Untitled",
                    "poster_url": g.get("poster_url"),
                    "vote_average": g.get("vote_average"),
                    "release_date": g.get("release_date"),
                    "match_percentage": 85,
                })

    if not cards:
        # Fallback to genre discovery directly
        genre_cards, _ = api_get_json("/recommend/genre", {"tmdb_id": tmdb_id, "limit": 12})
        if genre_cards:
            for g in genre_cards:
                cards.append({
                    "tmdb_id": g.get("tmdb_id") or (abs(hash(g.get("title", ""))) % 1000000 + 100000),
                    "title": g.get("title") or "Untitled",
                    "poster_url": g.get("poster_url"),
                    "vote_average": g.get("vote_average"),
                    "release_date": g.get("release_date"),
                    "match_percentage": 82,
                })

    if not cards:
        # Fallback to popular home feed
        home_cards, _ = api_get_json("/home", {"category": "popular", "limit": 12})
        if home_cards:
            for h in home_cards:
                cards.append({
                    "tmdb_id": h.get("tmdb_id"),
                    "title": h.get("title") or "Untitled",
                    "poster_url": h.get("poster_url"),
                    "vote_average": h.get("vote_average"),
                    "release_date": h.get("release_date"),
                    "match_percentage": 78,
                })

    if cards:
        render_poster_grid(cards, cols=6, key_prefix="rec_grid")
    else:
        st.info("No recommendations available at the moment.")

    # Recently Viewed Section
    if len(st.session_state.recently_viewed) > 1:
        st.divider()
        st.markdown("### 🕒 Recently Viewed")
        recent_cards = [m for m in st.session_state.recently_viewed if m.get("tmdb_id") != tmdb_id]
        render_poster_grid(recent_cards, cols=6, key_prefix="recent_grid")


def view_watchlist():
    render_header()
    st.markdown("## ❤️ My Watchlist")

    wl = list(st.session_state.watchlist.values())
    if not wl:
        st.info("Your Watchlist is empty! Click '❤️' on any movie poster to save it here.")
        if st.button("🍿 Browse Movies"):
            goto_home()
        return

    render_poster_grid(wl, cols=6, key_prefix="wl_grid")


# ==============================================================================
# MAIN ROUTER
# ==============================================================================
def main():
    if st.session_state.view == "details":
        view_details()
    elif st.session_state.view == "watchlist":
        view_watchlist()
    else:
        view_home()


if __name__ == "__main__":
    main()