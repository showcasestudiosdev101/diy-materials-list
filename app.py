import streamlit as st
import google.generativeai as genai
from PIL import Image
import os

import streamlit as st

# --- Password Protection ---
def check_password():
    """Returns True if the user entered the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run → show input box
        st.text_input(
            "Enter password to access the app",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False

    elif not st.session_state["password_correct"]:
        # Wrong password
        st.text_input(
            "Enter password to access the app",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("Incorrect password")
        return False

    else:
        # Correct password
        return True

if not check_password():
    st.stop()  # Stop the app if password is wrong
# --- End Password Protection ---

st.set_page_config(page_title="DIY Photo → Materials List", page_icon="🛠️")

st.title("🛠️ DIY Photo → Materials & Supplies List")
st.write("Upload a photo of a deck, fence, or any DIY project and get a materials list.")

# Get API key from Streamlit secrets
api_key = st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    st.error("Missing Gemini API key. Please add it in Streamlit secrets.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-flash-latest")

# Upload section
uploaded_file = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png", "webp"])
notes = st.text_area("Optional notes (example: replace deck boards and railing)", height=100)

if st.button("Generate Materials List", type="primary"):
    if uploaded_file is None:
        st.warning("Please upload a photo first.")
    else:
        image = Image.open(uploaded_file)
        st.image(image, caption="Your photo", use_container_width=True)

        prompt = f"""
You are an experienced DIY and outdoor construction advisor.

Analyze the uploaded photo carefully. The user wants a materials and supplies list.

User notes: {notes if notes else "No extra notes provided."}

Provide a clear, practical response in this exact format:

**Project Assessment**
- Brief description of what you see
- Recommended approach (repair / partial rebuild / full rebuild / refinishing, etc.)

**Materials & Supplies List**
- List items with approximate quantities
- Group by category if helpful (lumber, fasteners, finish, etc.)

**Tools Needed**
- List the main tools required

**Basic Steps**
- Numbered high-level steps

**Difficulty & Time Estimate**
- Difficulty (Beginner / Intermediate / Advanced)
- Rough time estimate

Be realistic and practical. Prefer common, readily available materials.
"""

        with st.spinner("Analyzing photo..."):
            try:
                response = model.generate_content([prompt, image])
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {str(e)}")
