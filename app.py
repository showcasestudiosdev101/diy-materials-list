import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import os

st.set_page_config(
    page_title="Bid and Build by Showcase Studios",
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
    if not st.session_state.photos:
        st.warning("Please upload at least one photo.")
    else:
        images = [Image.open(f) for f in st.session_state.photos]

        prompt = f"""
You are a practical construction estimator for Showcase Studios.

Project Type: {project_type}
Dimensions: {dimensions if dimensions else "None given – estimate carefully from the photos"}
User notes: {notes if notes else "None"}

You have {len(images)} photo(s). Use all of them.

Create a realistic materials and supplies list. Be conservative with quantities.
Clearly state any assumptions you are making.

Respond in this exact format:

**Project Assessment**
- What the photos show
- Recommended approach
- Key assumptions

**Materials & Supplies List**
- Grouped by category with approximate quantities

**Tools Needed**
- Main tools required

**Suggested Work Sequence**
- Numbered high-level steps

**Difficulty & Rough Time**
- Difficulty level
- Estimated time range

Be honest. Accuracy is more important than sounding complete.
"""

        with st.spinner("Analyzing photos..."):
            try:
                response = model.generate_content([prompt] + images)
                result_text = response.text

                st.markdown("---")
                st.markdown(result_text)

                # ---------- PDF Generation ----------
                class PDF(FPDF):
                    def header(self):
                        self.set_font("Helvetica", "B", 16)
                        self.cell(0, 10, "Showcase Studios", ln=True, align="C")
                        self.set_font("Helvetica", "", 11)
                        self.cell(0, 8, "Bid and Build App", ln=True, align="C")
                        self.ln(3)
                        self.set_draw_color(100, 100, 100)
                        self.line(12, self.get_y(), 198, self.get_y())
                        self.ln(8)

                    def footer(self):
                        self.set_y(-15)
                        self.set_font("Helvetica", "I", 8)
                        self.cell(0, 10, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Page {self.page_no()}", align="C")

                pdf = PDF()
                pdf.set_auto_page_break(auto=True, margin=18)
                pdf.set_margins(left=12, top=15, right=12)
                pdf.add_page()
                pdf.set_font("Helvetica", "", 10)

                # Project header
                pdf.set_font("Helvetica", "B", 12)
                pdf.multi_cell(0, 7, f"Project Type: {project_type}")
                if dimensions:
                    pdf.multi_cell(0, 7, f"Dimensions: {dimensions}")
                pdf.ln(5)

                # Write AI response
                pdf.set_font("Helvetica", "", 10)
                for line in result_text.split("\n"):
                    clean = line.replace("**", "").replace("*", "").replace("#", "").strip()
                    if not clean:
                        pdf.ln(3)
                        continue
                    try:
                        pdf.multi_cell(w=186, h=6, text=clean)
                    except:
                        pdf.multi_cell(w=186, h=6, text=clean[:100] + "...")

                pdf.ln(10)
                pdf.set_font("Helvetica", "I", 8)
                pdf.multi_cell(0, 5,
                    "Disclaimer: This is an AI-assisted estimate based on the photos and information provided. "
                    "Final quantities, structural decisions, and costs should be verified by a qualified professional. "
                    "Showcase Studios is not responsible for construction outcomes."
                )

                # Download button
                pdf_bytes = pdf.output()
                st.download_button(
                    label="📄 Download PDF Bid",
                    data=pdf_bytes,
                    file_name=f"Showcase_Studios_Bid_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"Error: {str(e)}")
