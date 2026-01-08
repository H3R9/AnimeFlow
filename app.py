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
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed" # Mobile friendly default
)

BASE_URL = "https://animefire.plus"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": BASE_URL
}
HISTORY_FILE = "watch_history.json"

# --- Custom CSS (Netflix Style) ---
st.markdown("""
<style>
    /* Global Reset & Dark Theme */
    .stApp {
        background-color: #141414; /* Netflix Deep Black */
        color: #e5e5e5;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid #333;
    }
    
    /* Remove padding for mobile */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    
    /* Card Styling */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1f1f1f;
        border: 1px solid #333;
        border-radius: 8px;
        transition: transform 0.2s;
        padding: 0; /* Remove internal padding for cover image look */
        overflow: hidden;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: scale(1.03);
        border-color: #e50914; /* Brand Color Highlight */
        z-index: 10;
    }
    
    /* Cover Image full width in card */
    div[data-testid="stVerticalBlockBorderWrapper"] img {
        width: 100%;
        object-fit: cover;
        border-radius: 8px 8px 0 0;
    }
    
    /* Text in Cards */
    .anime-card-title {
        padding: 0.5rem;
        font-weight: bold;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 0.9rem;
    }
    
    /* Custom Buttons - Primary Red */
    .stButton button[kind="primary"] {
        background-color: #e50914;
        color: white;
        border: none;
        font-weight: bold;
    }
    .stButton button[kind="primary"]:hover {
        background-color: #f40612;
    }
    
    /* Navigation Buttons */
    .nav-btn {
        margin-top: 10px;
    }
    
</style>
""", unsafe_allow_html=True)

# --- Logic / Backend Functions (Preserved) ---

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

def search_anime(query):
    try:
        query_slug = query.lower().strip().replace(" ", "-") # Slugify
        response = requests.get(f"{BASE_URL}/pesquisar/{query_slug}", headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        for card in soup.select('.divCardUltimosEps'):
            title = card.select_one('.animeTitle').text.strip()
            link = card.select_one('a')['href']
            img = card.select_one('img')
            img_src = img.get('data-src') or img.get('src')
            results.append({'title': title, 'url': link, 'img': img_src})
        return results
    except Exception as e:
        print(e)
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
        # Step 1: Get Page
        resp = requests.get(episode_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Step 2: Get API Link
        vid_elem = soup.select_one('#my-video')
        if not vid_elem or not vid_elem.get('data-video-src'): return None
        
        # Step 3: Call API
        api_url = vid_elem.get('data-video-src')
        api_data = requests.get(api_url, headers=HEADERS, timeout=10).json()
        
        # Step 4: Extract Best Quality
        if 'data' in api_data and api_data['data']:
            return api_data['data'][-1]['src']
        return None
    except: return None

# --- UI Helpers ---

# Helper to render anime grid card
def render_anime_card(anime, key_suffix, col):
    with col:
        with st.container(border=True):
            st.image(anime['img'], use_container_width=True)
            # Custom styled title via markdown + CSS class
            st.markdown(f"<div class='anime-card-title'>{anime['title']}</div>", unsafe_allow_html=True)
            if st.button("Assistir", key=f"btn_{key_suffix}_{anime['url']}", use_container_width=True):
                st.session_state.selected_anime = anime
                st.session_state.page = "Anime"
                st.rerun()

# --- Page Views ---

def view_home():
    st.header("🏠 Início")
    
    history = load_history()
    if history:
        st.subheader("Continuar Assistindo")
        sorted_hist = sorted(history.values(), key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Responsive Grid for History
        # Mobile: 2 cols, Desktop: 4 cols
        cols = st.columns(4) 
        for idx, item in enumerate(sorted_hist[:4]):
            anime_obj = {'title': item['anime_title'], 'url': item['anime_url'], 'img': item['cover_image']}
            render_anime_card(anime_obj, f"hist_{idx}", cols[idx % 4])
            
        st.markdown("---")

    st.subheader("Sugestões para Você")
    st.info("💡 Use a barra de busca para encontrar seus animes favoritos.")
    # Placeholder for trending if we had a scraping function for that
    # For now, just a call to action

def view_search():
    st.header("🔍 Buscar")
    
    col_s1, col_s2 = st.columns([4, 1])
    with col_s1:
        query = st.text_input("Nome do Anime", placeholder="Ex: Naruto Shippuden", label_visibility="collapsed")
    with col_s2:
        search_btn = st.button("Pesquisar", type="primary", use_container_width=True)
    
    if query or search_btn:
        if query:
            with st.spinner("Buscando..."):
                results = search_anime(query)
            
            if results:
                st.write(f"Encontrados: {len(results)}")
                
                # Grid Layout 4 cols
                cols = st.columns(4)
                for idx, anime in enumerate(results):
                    render_anime_card(anime, f"search_{idx}", cols[idx % 4])
            else:
                st.warning("⚠️ Nenhum anime encontrado. Tente outro nome.")

def view_anime_details():
    if not st.session_state.selected_anime:
        st.session_state.page = "Search"
        st.rerun()
        return

    anime = st.session_state.selected_anime
    
    # Breadcrumb style back button
    if st.button("🔙 Voltar", key="back_to_search"):
        # Determine where to go back based on history? Simple: just go Home or Search
        st.session_state.page = "Search"
        st.rerun()

    # Layout: Cover (Left) | Info & Episodes (Right)
    col_cover, col_info = st.columns([1, 3])
    
    with col_cover:
        st.image(anime['img'], use_container_width=True)
        st.caption(f"**{anime['title']}**")
        
    with col_info:
        st.subheader(f"{anime['title']}")
        
        history = load_history()
        last_ep = history.get(anime['title'], {}).get('last_episode', 0)
        
        if last_ep > 0:
            st.info(f"📍 Você parou no episódio **{last_ep}**")
        
        with st.spinner("Carregando episódios..."):
            # Cache this call ideally, but keeping it simple as requested
            episodes = get_episodes(anime['url'])
            
        if episodes:
            # Scrollable container for cleaner UI
            with st.container(height=500):
                for i, ep in enumerate(episodes):
                    label = ep['title']
                    btn_kind = "secondary"
                    
                    # Markers
                    if ep['num'] <= last_ep:
                        label = f"✅ {ep['title']}"
                    elif ep['num'] == last_ep + 1:
                        label = f"▶️ {ep['title']}"
                        btn_kind = "primary" # Highlight next to watch
                    
                    # Store index for next/prev logic
                    ep['index'] = i 
                    
                    if st.button(label, key=f"ep_{ep['url']}", type=btn_kind, use_container_width=True):
                        st.session_state.current_episode = ep
                        st.session_state.episode_list = episodes # Save list for navigation
                        st.session_state.page = "Player"
                        st.rerun()
        else:
            st.error("Erro ao carregar episódios.")

def view_player():
    if not st.session_state.current_episode:
        st.session_state.page = "Home"
        st.rerun()
        return

    ep = st.session_state.current_episode
    anime = st.session_state.selected_anime
    ep_list = st.session_state.get('episode_list', [])
    current_idx = ep.get('index', 0)
    
    # Back & Title
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔙 Voltar"):
            st.session_state.page = "Anime"
            st.rerun()
    with col2:
        st.markdown(f"**{anime['title']}** - {ep['title']}")
    
    # Video Area
    container = st.container()
    with container:
        with st.spinner("Conectando ao servidor de vídeo..."):
            url = get_video_url(ep['url'])
            if url:
                save_history(anime, ep['num'])
                st.video(url)
            else:
                st.error("Erro ao carregar vídeo.")
                st.caption("O servidor pode estar protegido ou o link expirou.")
                st.link_button("Assistir no Site Original", ep['url'])

    # Navigation Controls (Prev / Next)
    c_prev, c_space, c_next = st.columns([1, 2, 1])
    
    with c_prev:
        if current_idx > 0:
            prev_ep = ep_list[current_idx - 1]
            if st.button(f"⏮️ Ep {prev_ep['num']}", use_container_width=True):
                st.session_state.current_episode = prev_ep
                st.rerun()
                
    with c_next:
        if current_idx < len(ep_list) - 1:
            next_ep = ep_list[current_idx + 1]
            # Primary color for Next button to encourage binge-watching
            if st.button(f"Ep {next_ep['num']} ⏭️", type="primary", use_container_width=True):
                st.session_state.current_episode = next_ep
                st.rerun()

# --- Main App Entry ---

def main():
    # Helper to enforce page navigation from Sidebar
    def nav_callback(key):
        st.session_state.page = st.session_state[key]
    
    # Initialize Session State
    if 'page' not in st.session_state: st.session_state.page = "Home"
    if 'selected_anime' not in st.session_state: st.session_state.selected_anime = None
    if 'current_episode' not in st.session_state: st.session_state.current_episode = None
    if 'episode_list' not in st.session_state: st.session_state.episode_list = []

    # Sidebar
    with st.sidebar:
        st.title("🌊 AnimeFlow")
        st.markdown("---")
        
        # Navigation Menu
        # We manually check the selection to update the page state
        selected = st.radio(
            "Menu", 
            ["Home", "Search", "History"],
            format_func=lambda x: {"Home": "🏠 Início", "Search": "🔍 Buscar", "History": "📜 Histórico"}[x],
            key="nav_radio",
            label_visibility="collapsed"
        )
        
        # Sync Sidebar with Main View Logic
        # If user clicks sidebar, we switch. If view switches internally (to Player), sidebar stays indicating 'context' or just ignores.
        # Simple approach: Sidebar drives High Level pages. Internal logic drives Low Level (Anime, Player).
        
        st.markdown("---")
        st.caption("v2.0 Premium | Mobile Ready")

    # Routing Logic
    # If the radio button changed this run, update the page
    # But if we are in "Anime" or "Player", we don't want the radio to reset us unless the USER clicked it.
    # Streamlit limitation: Radio sync is tricky.
    # Workaround: Check if the 'page' state matches a main category. If not, and user clicked radio, we force it.
    # For now, let's trust the logic:
    
    # If sidebar selection != current page AND current page is a top-level page, switch.
    if selected != st.session_state.get('last_selected', 'Home'):
        st.session_state.page = selected
        st.session_state.last_selected = selected
        st.rerun()

    # If we are in Search/Home/History, render.
    if st.session_state.page == "Home": view_home()
    elif st.session_state.page == "Search": view_search()
    elif st.session_state.page == "History": 
        # History is just Home's continue watching basically, or we can make a dedicated list
        st.header("📜 Histórico Completo")
        history = load_history()
        if history:
            sorted_hist = sorted(history.values(), key=lambda x: x.get('timestamp', ''), reverse=True)
            cols = st.columns(4)
            for idx, item in enumerate(sorted_hist):
                anime_obj = {'title': item['anime_title'], 'url': item['anime_url'], 'img': item['cover_image']}
                render_anime_card(anime_obj, f"full_hist_{idx}", cols[idx % 4])
        else:
            st.info("Seu histórico está vazio.")
            
    elif st.session_state.page == "Anime": view_anime_details()
    elif st.session_state.page == "Player": view_player()

if __name__ == "__main__":
    main()
