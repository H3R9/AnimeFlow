import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime

# --- Configuration ---
st.set_page_config(
    page_title="AnimeFlow",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_URL = "https://animefire.plus"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": BASE_URL
}
HISTORY_FILE = "watch_history.json"

# --- Professional CSS ---
st.markdown("""
<style>
    /* Import Inter Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Global Deep Dark Theme - No Emojis/Playfulness */
    .stApp {
        background-color: #0F0F0F;
        color: #E0E0E0;
    }

    /* Remove Top Padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }

    /* Header Styling */
    .header-logo {
        font-size: 1.5rem;
        font-weight: 800;
        color: #E50914; /* Netflix Red */
        letter-spacing: -0.5px;
        margin-bottom: 0;
        cursor: pointer;
    }
    
    /* Search Bar Styling */
    div[data-testid="stTextInput"] input {
        background-color: #202020;
        color: white;
        border: 1px solid #333;
        border-radius: 4px; /* Sharper corners */
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #E50914;
        box-shadow: none;
    }

    /* Card/Grid Styling */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1a1a1a;
        border: none;
        border-radius: 4px;
        transition: transform 0.2s ease;
        padding: 0 !important;
        overflow: hidden;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: scale(1.02);
        z-index: 5;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }
    
    /* Card Image */
    div[data-testid="stVerticalBlockBorderWrapper"] img {
        width: 100%;
        aspect-ratio: 2/3;
        object-fit: cover;
        border-radius: 4px 4px 0 0;
        margin-bottom: 0;
    }
    
    /* Card Title Overlay */
    .card-title {
        padding: 10px;
        font-size: 0.9rem;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #fff;
    }

    /* Secondary Text for Mobile */
    .caption-text {
        font-size: 0.8rem;
        color: #aaa;
    }

    /* Buttons - Clean & Flat */
    .stButton button {
        background-color: #333;
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 600;
        transition: background 0.2s;
    }
    .stButton button:hover {
        background-color: #444;
        color: white;
    }
    
    /* Primary Action Buttons */
    .stButton button[kind="primary"] {
        background-color: #E50914;
    }
    .stButton button[kind="primary"]:hover {
        background-color: #F40612;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- Backend Logic (Core) ---

def load_history():
    if not os.path.exists(HISTORY_FILE): return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def save_history(anime_data, episode_num):
    history = load_history()
    key = anime_data['title']
    history[key] = {
        'last_episode': episode_num,
        'anime_title': anime_data['title'],
        'cover_image': anime_data['img'],
        'anime_url': anime_data['url'],
        'timestamp': str(datetime.now())
    }
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except: pass

@st.cache_data(ttl=3600)  # Cache for 1 hour to reduce requests
def get_latest_animes():
    """Fetches latest episodes/animes from homepage to populate empty state."""
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        results = []
        # Target the 'Latest Episodes' cards usually on home
        # Adjust selector based on typical structure observed in debug
        cards = soup.select('.divCardUltimosEps') or soup.select('article.imgAnimes')
        
        for card in cards[:12]: # Limit to 12 items
            try:
                title_elem = card.select_one('.animeTitle') or card.select_one('.title')
                link_elem = card.select_one('a')
                img_elem = card.select_one('img')
                
                if title_elem and link_elem and img_elem:
                    title = title_elem.text.strip()
                    link = link_elem['href']
                    # Handle lazy loading attributes
                    img = img_elem.get('data-src') or img_elem.get('src')
                    
                    if link and not link.startswith('http'):
                        link = f"{BASE_URL}{link}" if link.startswith('/') else f"{BASE_URL}/{link}"
                        
                    results.append({'title': title, 'url': link, 'img': img})
            except: continue
        return results
    except Exception as e:
        # Fail silently for UI polish, return empty
        return []

def search_anime(query):
    try:
        # Improved error handling for Search
        query_slug = query.lower().strip().replace(" ", "-") 
        search_url = f"{BASE_URL}/pesquisar/{query_slug}"
        
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        response.raise_for_status() # Will trigger except if 404 or 500
        
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        # Selectors updated to be broad enough
        for card in soup.select('.divCardUltimosEps'):
            title = card.select_one('.animeTitle').text.strip()
            link = card.select_one('a')['href']
            img = card.select_one('img')
            img_src = img.get('data-src') or img.get('src')
            results.append({'title': title, 'url': link, 'img': img_src})
            
        return results
    except Exception as e:
        # Return error message to user via UI logic, or empty list
        print(f"Search Error: {e}")
        return []

def get_episodes(anime_url):
    try:
        response = requests.get(anime_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        episodes = []
        for link in soup.select('a.lEp'):
            try: num = int(re.search(r'\d+', link.text).group())
            except: num = 0
            episodes.append({'title': link.text.strip(), 'url': link['href'], 'num': num})
        episodes.sort(key=lambda x: x['num'])
        return episodes
    except: return []

def get_video_url(episode_url):
    try:
        resp = requests.get(episode_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        vid_elem = soup.select_one('#my-video')
        if not vid_elem or not vid_elem.get('data-video-src'): return None
        api_url = vid_elem.get('data-video-src')
        api_data = requests.get(api_url, headers=HEADERS, timeout=10).json()
        if 'data' in api_data and api_data['data']:
            return api_data['data'][-1]['src']
        return None
    except: return None

# --- UI Components ---

def ui_card(anime, key_prefix):
    """Renders a single anime card."""
    with st.container(border=True):
        st.image(anime['img'], use_container_width=True)
        st.markdown(f"<div class='card-title'>{anime['title']}</div>", unsafe_allow_html=True)
        if st.button("Assistir", key=f"{key_prefix}_{anime['url']}", use_container_width=True):
            st.session_state.selected_anime = anime
            st.session_state.view = "anime"
            st.rerun()

def top_bar():
    """Professional Header with Logo and Search."""
    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("ANIMEFLOW", key="logo_home", type="secondary"):
            st.session_state.view = "home"
            st.session_state.selected_anime = None
            st.session_state.current_episode = None
            st.rerun()
            
    with c2:
        # Search directly in header
        query = st.text_input("Buscar", placeholder="Pesquisar animes...", label_visibility="collapsed", key="search_bar")
        if query:
            st.session_state.search_query = query
            st.session_state.view = "search_results"
            # No rerun usually needed for text_input unless enter is pressed
            
# --- Views ---

def view_home():
    # 1. Continue Watching
    history = load_history()
    if history:
        st.subheader("Continuar Assistindo")
        sorted_hist = sorted(history.values(), key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Horizontal scroll feel via columns
        cols = st.columns(4)
        for idx, item in enumerate(sorted_hist[:4]):
            anime = {'title': item['anime_title'], 'url': item['anime_url'], 'img': item['cover_image']}
            with cols[idx]:
                ui_card(anime, "hist")

    # 2. Latest Releases (New Feature)
    st.subheader("Lançamentos Recentes")
    latest = get_latest_animes()
    
    if latest:
        # Grid of 4 columns
        rows = [latest[i:i+4] for i in range(0, len(latest), 4)]
        for row in rows:
            cols = st.columns(4)
            for idx, anime in enumerate(row):
                with cols[idx]:
                    ui_card(anime, f"latest_{idx}")
    else:
        st.info("Carregando catálogo...")

def view_search_results():
    query = st.session_state.get("search_query", "")
    st.subheader(f"Resultados para '{query}'")
    
    if not query:
        st.warning("Digite algo para buscar.")
        return

    with st.spinner("Buscando..."):
        results = search_anime(query)
    
    if results:
        rows = [results[i:i+4] for i in range(0, len(results), 4)]
        for row in rows:
            cols = st.columns(4)
            for idx, anime in enumerate(row):
                with cols[idx]:
                    ui_card(anime, f"src_{idx}")
    else:
        st.error("Nenhum anime encontrado. Verifique a ortografia.")
        st.markdown(f"*Dica: Tente buscar pelo nome em japonês ou inglês.*")

def view_anime_details():
    anime = st.session_state.selected_anime
    if not anime:
        st.session_state.view = "home"
        st.rerun()
        return

    # Back Button
    if st.button("Voltar", key="back_btn"):
        st.session_state.view = "home"
        st.rerun()

    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(anime['img'], use_container_width=True)
    with c2:
        st.title(anime['title'])
        history = load_history()
        last_ep = history.get(anime['title'], {}).get('last_episode', 0)
        
        if last_ep > 0:
            st.markdown(f"**Progresso:** Parou no episódio {last_ep}")

        with st.spinner("Carregando temporadas..."):
            episodes = get_episodes(anime['url'])
            
        if episodes:
            with st.container(height=500):
                for i, ep in enumerate(episodes):
                    ep['index'] = i
                    label = f"Episódio {ep['num']}"
                    
                    # Style
                    kind = "secondary"
                    if ep['num'] == last_ep + 1:
                        kind = "primary" # Next up
                        label += " (Próximo)"
                    elif ep['num'] <= last_ep:
                        label += " (Visto)"

                    if st.button(label, key=f"ep_btn_{ep['url']}", type=kind, use_container_width=True):
                        st.session_state.current_episode = ep
                        st.session_state.episode_list = episodes
                        st.session_state.view = "player"
                        st.rerun()

def view_player():
    ep = st.session_state.current_episode
    anime = st.session_state.selected_anime
    
    if not ep:
        st.session_state.view = "anime"
        st.rerun()
        return

    # Header with Back
    c1, c2 = st.columns([1, 6])
    with c1:
        if st.button("Fechar Player"):
            st.session_state.view = "anime"
            st.rerun()
    with c2:
        st.subheader(f"{anime['title']} - Ep. {ep['num']}")

    # Video
    with st.spinner("Carregando vídeo..."):
        url = get_video_url(ep['url'])
        
    if url:
        st.video(url)
        save_history(anime, ep['num'])
    else:
        st.error("Vídeo indisponível no momento.")
        st.markdown(f"[Assistir no site original]({ep['url']})")

    # Controls
    ep_list = st.session_state.get('episode_list', [])
    curr_idx = ep.get('index', 0)
    
    c_prev, c_space, c_next = st.columns([1, 3, 1])
    with c_prev:
        if curr_idx > 0:
            if st.button("Anterior", use_container_width=True):
                st.session_state.current_episode = ep_list[curr_idx - 1]
                st.rerun()
    with c_next:
        if curr_idx < len(ep_list) - 1:
            if st.button("Próximo", type="primary", use_container_width=True):
                st.session_state.current_episode = ep_list[curr_idx + 1]
                st.rerun()

# --- Main Logic ---

def main():
    # Session State Init
    if 'view' not in st.session_state: st.session_state.view = "home"
    if 'selected_anime' not in st.session_state: st.session_state.selected_anime = None
    if 'current_episode' not in st.session_state: st.session_state.current_episode = None
    
    # 1. Fixed Top Bar
    top_bar() 
    
    # 2. Dynamic Content
    st.markdown("---") # Soft divider
    
    if st.session_state.search_query and st.session_state.view != "player" and st.session_state.view != "anime":
         # If user typed in search, force search view unless watching
         # NOTE: This allows keeping search active while browsing
         view_search_results()
    elif st.session_state.view == "home":
        view_home()
    elif st.session_state.view == "search_results":
        view_search_results()
    elif st.session_state.view == "anime":
        view_anime_details()
    elif st.session_state.view == "player":
        view_player()

if __name__ == "__main__":
    if 'search_query' not in st.session_state: st.session_state.search_query = ""
    main()
