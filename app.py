import streamlit as st
from google import genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import re
import io

# ---------- VERSION ----------
APP_VERSION = "1.3"
# ----------------------------

st.set_page_config(
    page_title=f"Bid and Build It by Showcase Studios v{APP_VERSION}",
    page_icon="🛠️",
    layout="wide"
)

st.title("🛠️ Bid and Build It by Showcase Studios")
st.caption(f"Version {APP_VERSION}  •  Upload photos → Materials list + PDF bids")

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

                # ---------- Helper: Clean text ----------
                def clean_for_pdf(text):
                    text = text.replace("–", "-").replace("—", "-")
                    text = text.replace("“", '"').replace("”", '"')
                    text = text.replace("‘", "'").replace("’", "'")
                    text = text.replace("•", "-")
                    text = text.replace("**", "").replace("*", "").replace("#", "")
                    text = re.sub(r'[^\x00-\x7F]+', '', text)
                    return text.strip()

                # ---------- Create both PDFs ----------
                def create_pdf(version="Contractor"):
                    class PDF(FPDF):
                        def header(self):
                            self.set_font("Helvetica", "B", 14)
                            self.cell(0, 7, "Bid and Build It by Showcase Studios", ln=True, align="C")
                            self.set_font("Helvetica", "", 10)
                            self.cell(0, 6, f"Version {APP_VERSION}  |  {version} Version", ln=True, align="C")
                            self.ln(2)
                            self.set_draw_color(100, 100, 100)
                            self.line(12, self.get_y(), 198, self.get_y())
                            self.ln(5)

                        def footer(self):
                            self.set_y(-12)
                            self.set_font("Helvetica", "I", 8)
                            self.cell(0, 8, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Page {self.page_no()}", align="C")

                    pdf = PDF()
                    pdf.set_auto_page_break(auto=True, margin=14)
                    pdf.set_left_margin(12)
                    pdf.set_right_margin(12)
                    pdf.add_page()

                    # Left text width and right photo area
                    text_width = 125
                    photo_x = 145
                    photo_width = 50

                    # Project info
                    pdf.set_font("Helvetica", "B", 11)
                    pdf.cell(text_width, 6, f"Project Type: {project_type}", ln=True)
                    if dimensions:
                        pdf.cell(text_width, 6, f"Dimensions: {dimensions}", ln=True)
                    pdf.ln(3)

                    # Place photos on the right (stacked)
                    y_start = 40
                    for i, img in enumerate(images[:4]):  # max 4 photos
                        try:
                            # Save temp image
                            img_byte_arr = io.BytesIO()
                            img_resized = img.copy()
                            img_resized.thumbnail((400, 400))
                            img_resized.save(img_byte_arr, format='JPEG')
                            img_byte_arr.seek(0)
                            pdf.image(img_byte_arr, x=photo_x, y=y_start + (i * 55), w=photo_width)
                        except:
                            pass

                    # Write text content
                    pdf.set_font("Helvetica", "", 9)
                    pdf.set_xy(12, 55)

                    # Decide what sections to include
                    lines = result_text.splitlines()
                    skip_tools = version == "Customer"
                    skip_sequence = version == "Customer"
                    in_tools = False
                    in_sequence = False

                    for raw_line in lines:
                        line = clean_for_pdf(raw_line)

                        if "Tools Needed" in line:
                            in_tools = True
                            in_sequence = False
                            if skip_tools:
                                continue
                        elif "Suggested Work Sequence" in line:
                            in_sequence = True
                            in_tools = False
                            if skip_sequence:
                                continue
                        elif "Difficulty & Rough Time" in line:
                            in_tools = False
                            in_sequence = False

                        if skip_tools and in_tools:
                            continue
                        if skip_sequence and in_sequence:
                            continue

                        if not line:
                            pdf.ln(2)
                            continue

                        # Write line with limited width
                        while len(line) > 0:
                            chunk = line[:78]
                            line = line[78:]
                            pdf.cell(text_width, 4.5, chunk, ln=True)

                    # Customer Version fill-in fields
                    if version == "Customer":
                        pdf.ln(6)
                        pdf.set_font("Helvetica", "B", 10)
                        pdf.cell(0, 6, "Pricing & Agreement", ln=True)
                        pdf.set_font("Helvetica", "", 9)
                        pdf.ln(2)
                        pdf.cell(0, 6, "Deposit Amount:  $ ____________________", ln=True)
                        pdf.cell(0, 6, "Total Price:      $ ____________________", ln=True)
                        pdf.ln(3)
                        pdf.cell(0, 6, "Signature: _______________________________     Date: ______________", ln=True)
                        pdf.ln(2)
                        pdf.cell(0, 6, "Date work to begin: ____________________", ln=True)
                        pdf.cell(0, 6, "Who purchases supplies (Customer / Contractor): ____________________", ln=True)

                    # Disclaimer
                    pdf.ln(8)
                    pdf.set_font("Helvetica", "I", 8)
                    if version == "Customer":
                        disclaimer = ("All bids subject to price changes for substitute or material changes "
                                      "or in the scope of work modifications. Deposit due before work commencement.")
                    else:
                        disclaimer = ("This is an AI-assisted estimate. Final quantities and decisions should be "
                                      "verified by a qualified professional. Showcase Studios is not responsible "
                                      "for construction outcomes.")
                    pdf.multi_cell(text_width, 4, disclaimer)

                    return bytes(pdf.output())

                # Generate both PDFs
                contractor_pdf = create_pdf("Contractor")
                customer_pdf = create_pdf("Customer")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.download_button(
                        label="📄 Download Contractor Version",
                        data=contractor_pdf,
                        file_name=f"Bid_and_Build_It_Contractor_v{APP_VERSION}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf"
                    )
                with col_b:
                    st.download_button(
                        label="📄 Download Customer Version",
                        data=customer_pdf,
                        file_name=f"Bid_and_Build_It_Customer_v{APP_VERSION}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"Error: {str(e)}")
