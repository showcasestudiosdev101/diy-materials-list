import streamlit as st
from google import genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import os

# ---------- VERSION ----------
APP_VERSION = "1"
# ----------------------------

st.set_page_config(
    page_title=f"Bid and Build It by Showcase Studios v{APP_VERSION}",
    page_icon="🛠️",
    layout="wide"
)

st.title("🛠️ Bid and Build It by Showcase Studios")
st.caption(f"Version {APP_VERSION}  •  Upload photos → Materials list + PDF bid")

# --- API Key ---
api_key = st.secrets.get("GEMINI_API_KEY", None)
if not api_key:
    st.error("Missing Gemini API key. Please add it in Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- Session state ---
if "photos" not in st.session_state:
    st.session_state.photos = []

# --- Inputs ---
col1, col2 = st.columns([2, 1])

with col1:
    project_type = st.selectbox(
        "Project Type",
        ["Deck", "Fence", "Roof / Roofing", "Stairs / Steps", "Room Painting", "Other / General"]
    )

with col2:
    st.write("")
    if st.button("Clear All Photos"):
        st.session_state.photos = []
        st.rerun()

dimensions = st.text_input(
    "Dimensions / Measurements (highly recommended)",
    placeholder="Example: 12 ft x 16 ft, 8 ft high, 10x12 room, etc."
)

notes = st.text_area(
    "Additional notes",
    placeholder="Example: Prefer pressure-treated lumber, replace only damaged boards, focus on leaks, etc.",
    height=90
)

uploaded_files = st.file_uploader(
    "Upload photos (multiple angles recommended)",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True
)

if uploaded_files:
    st.session_state.photos = uploaded_files

# Show current photos
if st.session_state.photos:
    st.write(f"**{len(st.session_state.photos)} photo(s) selected**")
    cols = st.columns(min(4, len(st.session_state.photos)))
    for idx, file in enumerate(st.session_state.photos):
        with cols[idx % 4]:
            st.image(file, caption=f"Photo {idx+1}", use_container_width=True)

# --- Generate ---
if st.button("Generate Materials List & Bid", type="primary"):
    if not st.
