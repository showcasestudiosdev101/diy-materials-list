import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import os

st.set_page_config(
    page_title="Showcase Studios Bid and Build",
    page_icon="🛠️",
    layout="wide"
)

st.title("🛠️ Showcase Studios Bid and Build App")
st.caption("Upload photos → Get materials list + professional PDF bid")

# --- API Key ---
api_key = st.secrets.get("GEMINI_API_KEY", None)
if not api_key:
    st.error("Missing Gemini API key. Please add it in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

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
