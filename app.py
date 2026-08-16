import streamlit as st
from google import genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import re

# ---------- VERSION ----------
APP_VERSION = "1.2"
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
            st.image(file, caption=f"Photo {idx + 1}", use_container_width=True)

# --- Generate ---
if st.button("Generate Materials List & Bid", type="primary"):
    if not st.session_state.photos:
        st.warning("Please upload at least one photo.")
    else:
        images = [Image.open(f) for f in st.session_state.photos]

        prompt = f"""
You are a practical construction estimator for Showcase Studios.

Project Type: {project_type}
Dimensions: {dimensions if dimensions else "None given - estimate carefully from the photos"}
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
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[prompt] + images
                )
                result_text = response.text

                st.markdown("---")
                st.markdown(result_text)

                # ---------- Safer PDF Generation ----------
                class PDF(FPDF):
                    def header(self):
                        self.set_font("Helvetica", "B", 14)
                        self.cell(0, 8, "Bid and Build It by Showcase Studios", ln=True, align="C")
                        self.set_font("Helvetica", "", 10)
                        self.cell(0, 6, f"Version {APP_VERSION}", ln=True, align="C")
                        self.ln(3)
                        self.set_draw_color(100, 100, 100)
                        self.line(15, self.get_y(), 195, self.get_y())
                        self.ln(6)

                    def footer(self):
                        self.set_y(-12)
                        self.set_font("Helvetica", "I", 8)
                        self.cell(0, 8, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Page {self.page_no()}", align="C")

                pdf = PDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.set_left_margin(15)
                pdf.set_right_margin(15)
                pdf.add_page()

                # Project info
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 7, f"Project Type: {project_type}", ln=True)
                if dimensions:
                    pdf.cell(0, 7, f"Dimensions: {dimensions}", ln=True)
                pdf.ln(5)

                # Clean text for PDF (remove special characters)
                def clean_for_pdf(text):
                    text = text.replace("–", "-").replace("—", "-")
                    text = text.replace("“", '"').replace("”", '"')
                    text = text.replace("‘", "'").replace("’", "'")
                    text = text.replace("•", "-")
                    text = text.replace("**", "").replace("*", "").replace("#", "")
                    # Remove any other non-ascii characters
                    text = re.sub(r'[^\x00-\x7F]+', '', text)
                    return text.strip()

                pdf.set_font("Helvetica", "", 9)

                for raw_line in result_text.splitlines():
                    line = clean_for_pdf(raw_line)

                    if not line:
                        pdf.ln(3)
                        continue

                    # Force wrap every 85 characters
                    while len(line) > 0:
                        chunk = line[:85]
                        line = line[85:]
                        try:
                            pdf.cell(0, 5, chunk, ln=True)
                        except Exception:
                            pdf.cell(0, 5, chunk[:70] + "...", ln=True)

                pdf.ln(8)
                pdf.set_font("Helvetica", "I", 8)
                pdf.multi_cell(0, 4.5,
                    "Disclaimer: This is an AI-assisted estimate. Final quantities and decisions should be verified by a qualified professional. Showcase Studios is not responsible for construction outcomes."
                )

                pdf_bytes = bytes(pdf.output())
                st.download_button(
                    label="📄 Download PDF Bid",
                    data=pdf_bytes,
                    file_name=f"Bid_and_Build_It_v{APP_VERSION}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"Error: {str(e)}")
