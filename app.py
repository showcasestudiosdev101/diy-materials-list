import streamlit as st
import google-genai as genai
from PIL import Image
from fpdf2 import FPDF
from datetime import datetime
import io
import os

st.set_page_config(
    page_title="Bid and Build It by Showcase Studios",
    page_icon="🛠️",
    layout="wide"
)

st.title("🛠️ Bid and Build App")
st.caption("Photo → Materials List + Professional Bid PDF")

# --- API Key ---
api_key = st.secrets.get("GEMINI_API_KEY", None)
if not api_key:
    st.error("Missing Gemini API key in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

# --- Session state for clearing ---
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
    st.write("")  # spacing
    if st.button("Clear All Previous Photos?"):
        st.session_state.photos = []
        st.rerun()

dimensions = st.text_input(
    "Dimensions / Measurements (highly recommended)",
    placeholder="Example: 12 ft x 16 ft deck, 8 ft high fence, 10x12 room, etc."
)

notes = st.text_area(
    "Additional notes or special requests",
    placeholder="Example: Prefer pressure-treated lumber, replace only the top boards, focus on structural issues, etc.",
    height=90
)

uploaded_files = st.file_uploader(
    "Upload photos (multiple angles strongly recommended)",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True
)

if uploaded_files:
    st.session_state.photos = uploaded_files

# Show current photos
if st.session_state.photos:
    st.write(f"**{len(st.session_state.photos)} photo(s) ready**")
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
You are a practical, experienced construction and DIY estimator working with an app built by Showcase Studios.

Project Type: {project_type}
Dimensions provided by user: {dimensions if dimensions else "None given – estimate carefully from photos"}
User notes: {notes if notes else "None"}

You have been given {len(images)} photo(s). Use ALL of them.

Create a realistic, conservative materials and supplies list. 
Do NOT invent precise board counts if the photos + dimensions are insufficient — clearly state assumptions.
Prefer common, readily available materials.

Respond in this exact structure:

**Project Assessment**
- What the photos show
- Recommended approach (repair / partial rebuild / full rebuild / refinish / paint, etc.)
- Key assumptions you are making

**Materials & Supplies List**
- Grouped by category
- Approximate quantities (or ranges when uncertain)
- Notes on any items that need verification on-site

**Tools Needed**
- Main tools required

**Suggested Work Sequence**
- Numbered high-level steps

**Difficulty & Rough Time Estimate for Job**
- Difficulty level
- Estimated time range

Be honest about limitations. Accuracy is more important than sounding complete.
"""

        with st.spinner("Analyzing photos and creating materials list..."):
            try:
                response = model.generate_content([prompt] + images)
                result_text = response.text
                st.markdown("---")
                st.markdown(result_text)

                # --- PDF Generations ---
                # --- Improved PDF Generation ---
                class PDF(FPDF):
                    def header(self):
                        self.set_font("Helvetica", "B", 16)
                        self.cell(0, 10, "Showcase Studios", ln=True, align="C")
                        self.set_font("Helvetica", "", 11)
                        self.cell(0, 8, "Bid and Build App", ln=True, align="C")
                        self.ln(3)
                        self.set_draw_color(100, 100, 100)
                        self.line(10, self.get_y(), 200, self.get_y())
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

                # Project info
                pdf.set_font("Helvetica", "B", 12)
                pdf.multi_cell(0, 7, f"Project Type: {project_type}")
                if dimensions:
                    pdf.multi_cell(0, 7, f"Dimensions: {dimensions}")
                pdf.ln(4)

                # Clean and write the AI response
                pdf.set_font("Helvetica", "", 10)
                
                for line in result_text.split("\n"):
                    clean = line.replace("**", "").replace("*", "").replace("#", "").strip()
                    
                    if not clean:
                        pdf.ln(3)
                        continue
                    
                    # Force wrapping with explicit width
                    try:
                        pdf.multi_cell(w=186, h=6, text=clean, align="L")
                    except Exception:
                        # Fallback for problematic lines
                        pdf.multi_cell(w=186, h=6, text=clean[:90] + "...", align="L")

                pdf.ln(10)
                pdf.set_font("Helvetica", "I", 8)
                pdf.multi_cell(0, 5, 
                    "Disclaimer: This is an AI-assisted estimate based on the photos and information provided. "
                    "Final quantities, structural decisions, and costs should be verified by a qualified professional. "
                    "Showcase Studios is not responsible for construction outcomes."
                )

                # Create downloadable PDF
                pdf_bytes = pdf.output()
                st.download_button(
                    label="📄 Download PDF Bid",
                    data=pdf_bytes,
                    file_name=f"Showcase_Studios_Bid_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"Error: {str(e)}")
