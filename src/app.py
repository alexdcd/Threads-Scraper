import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import yaml
from dotenv import load_dotenv

# Add src to python path to import modules
sys.path.append(str(Path(__file__).parent))

from scraper.threads_scraper import ThreadsScraper
from scraper.parser import ThreadsParser
from scraper.exporter import Exporter
from scraper.utils.logger import get_logger

# Setup paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
CONFIG_DIR = ROOT / "config"

logger = get_logger(__name__)

def load_settings(config_path: Path):
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "processed").mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Threads Scraper Interface", layout="wide")

st.title("Threads Scraper Local Server")
st.markdown("Easily scrape Threads posts from users directly in your browser.")

load_dotenv()
ensure_dirs()

# Sidebar configuration
st.sidebar.header("Configuration")
default_usernames = load_settings(CONFIG_DIR / "settings.yaml").get("usernames", [])
usernames_input = st.sidebar.text_area("Usernames (one per line)", value="\n".join(default_usernames))
limit = st.sidebar.number_input("Max posts per user", min_value=1, value=10, step=1)

if st.sidebar.button("Run Scraper"):
    if not usernames_input.strip():
        st.error("Please enter at least one username.")
    else:
        usernames = [u.strip() for u in usernames_input.split("\n") if u.strip()]
        
        # Initialize components
        settings = {"limit": limit}
        scraper = ThreadsScraper(settings=settings, config_dir=CONFIG_DIR, data_dir=DATA_DIR)
        parser = ThreadsParser()
        exporter = Exporter(output_dir=OUTPUT_DIR, data_dir=DATA_DIR)
        
        all_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, username in enumerate(usernames):
            status_text.text(f"Scraping @{username}...")
            try:
                # Assuming scraper returns raw items or pre-parsed?
                # User's main.py does: raw -> parse -> export
                # My mock scraper returns parsed-like dicts for simplicity or raw?
                # Let's check my mock implementation. I returned:
                # {"id": ..., "username": ..., "text": ..., "like_count": ...} which looks parsed.
                # So I might skip parser if mock returns parsed.
                # But to be safe and compatible with real scraper later, let's see.
                # My mock returns dicts with 'text', 'like_count' etc.
                # The parser expects raw dicts. 
                # If I pass my mock dicts to parser, it might fail or work depending on parser logic.
                # Parser.parse_item checks for "id" and "text" -> offline sample shape.
                # My mock returns this shape exactly! So parser will work fine.
                
                raw_items = scraper.fetch_user_threads(username=username, limit=limit)
                
                # Parse
                parsed_items = [parser.parse_item(item, default_username=username) for item in raw_items]
                parsed_items = [p for p in parsed_items if p]
                all_results.extend(parsed_items)
                
            except Exception as e:
                st.error(f"Error for @{username}: {str(e)}")
            
            progress_bar.progress((idx + 1) / len(usernames))
            
        status_text.text("Done!")
        
        if all_results:
            st.success(f"Collected total {len(all_results)} posts.")
            
            df = pd.DataFrame(all_results)
            st.dataframe(df)
            
            # Download buttons
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download CSV",
                csv,
                "threads_data.csv",
                "text/csv",
                key='download-csv'
            )
            
            json_str = df.to_json(orient="records", indent=2)
            st.download_button(
                "Download JSON",
                json_str,
                "threads_data.json",
                "application/json",
                key='download-json'
            )
        else:
            st.warning("No results found.")

st.markdown("---")
st.caption("Note: This interface uses a mock scraper if the real implementation is missing.")
