import streamlit as st
from google import genai
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import re
import io

# ---------- VERSION ----------
APP_VERSION = "1.4"
# ----------------------------

st.set_page_config(
    page_title=f"Bid and Build It by Showcase Studios v{APP_VERSION}",
    page_icon="🛠️",
    layout="wide"
)

# ---------- THEME ----------
st.markdown(
    """
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    .stApp, .stMarkdown, .stText, p, h1, h2, h3, h4 {
        color: #f1f5f9 !important;
    }
    h1 {
        color: #f59e0b !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    h2, h3 {
        color: #fbbf24 !important;
        font-weight: 700 !important;
    }
    .stButton>button {
        background: linear-gradient(90deg, #f59e0b, #ef4444);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
    }
    section[data-testid="stSidebar"] {
        background: #0b1220;
        border-right: 1px solid #334155;
    }
    [data-testid="stFileUploader"] {
        background: #1e293b;
        border: 2px dashed #f59e0b;
        border-radius: 12px;
        padding: 1rem;
    }
    [data-testid="stMetric"] {
        background: #1e293b;
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #334155;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ---------- PASSWORD ----------
def check_password():
    def password_entered():
        if st.session_state.get("password") == st.secrets.get("password"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("## 🛠️ Showcase Studios")
        st.markdown("### Bid and Build It")
        st.write("Private tool for contractors and builders")
        st.write("")
        st.text_input(
            "Enter password",
            type="password",
            on_change=password_entered,
            key="password",
            placeholder="Password",
        )
        st.caption("Contact Melinda for access")
        return False

    if not st.session_state["password_correct"]:
        st.markdown("## 🛠️ Showcase Studios")
        st.markdown("### Bid and Build It")
        st.write("")
        st.text_input(
            "Enter password",
            type="password",
            on_change=password_entered,
            key="password",
            placeholder="Password",
        )
        st.error("Incorrect password. Please try again.")
        return False

    return True


if not check_password():
    st.stop()


# --- API Key ---
api_key = st.secrets.get("GEMINI_API_KEY", None)
if not api_key:
    st.error("Missing Gemini API key. Please add it in Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

st.title("🛠️ Bid and Build It by Showcase Studios")
st.caption(f"Version {APP_VERSION}  •  Upload photos → Materials list + PDF bids")

# --- Session state ---
if "photos" not in st.session_state:
    st.session_state.photos = []

# --- Sidebar: Labor Inputs ---
st.sidebar.header("Labor Settings")
hourly_rate = st.sidebar.number_input(
    "Hourly rate per person ($)",
    min_value=0.0,
    value=25.0,
    step=1.0,
)
crew_size = st.sidebar.selectbox(
    "Crew size (people available)",
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    index=1,
)
hours_needed = st.sidebar.number_input(
    "Estimated hours for the job",
    min_value=0.0,
    value=8.0,
    step=0.5,
)
total_labor = hours_needed * crew_size * hourly_rate
st.sidebar.markdown("---")
st.sidebar.metric("Total labor cost", f"${total_labor:,.2f}")

# --- Inputs ---
col1, col2 = st.columns([2, 1])

with col1:
    project_type = st.selectbox(
        "Project Type",
        ["Deck", "Fence", "Roof / Roofing", "Stairs / Steps", "Room Painting", "Other / General"],
    )

with col2:
    st.write("")
    if st.button("Clear All Photos"):
        st.session_state.photos = []
        st.rerun()

dimensions = st.text_input(
    "Dimensions / Measurements (highly recommended)",
    placeholder="Example: 12 ft x 16 ft, 8 ft high, 10x12 room, etc.",
)

notes = st.text_area(
    "Additional notes",
    placeholder="Example: Prefer pressure-treated lumber, replace only damaged boards, focus on leaks, etc.",
    height=90,
)

uploaded_files = st.file_uploader(
    "Upload photos (multiple angles recommended)",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
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
Crew size available: {crew_size}
Hourly rate per person: ${hourly_rate:.2f}

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
- Suggested crew size for this job

Be honest. Accuracy is more important than sounding complete.
"""

        with st.spinner("Analyzing photos..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[prompt] + images,
                )
                result_text = response.text

                st.markdown("---")
                st.markdown(result_text)

                # --- Labor Cost Breakdown (on screen) ---
                st.markdown("---")
                st.markdown("### 💰 Labor Cost Breakdown")
                st.write(f"**Estimated hours:** {hours_needed}")
                st.write(f"**People required / available:** {crew_size}")
                st.write(f"**Hourly rate per person:** ${hourly_rate:.2f}")
                st.write(f"**Total labor cost:** ${total_labor:,.2f}")
                st.caption("Materials are not included in this labor total.")

                # ---------- Helper: Clean text ----------
                def clean_for_pdf(text):
                    text = text.replace("–", "-").replace("—", "-")
                    text = text.replace("“", '"').replace("”", '"')
                    text = text.replace("‘", "'").replace("’", "'")
                    text = text.replace("•", "-")
                    text = text.replace("**", "").replace("*", "").replace("#", "")
                    text = re.sub(r"[^\x00-\x7F]+", "", text)
                    return text.strip()

                # ---------- Create both PDFs ----------
                def create_pdf(version="Contractor"):
                    class PDF(FPDF):
                        def header(self):
                            self.set_font("Helvetica", "B", 14)
                            self.cell(0, 7, "Bid and Build It by Showcase Studios", ln=True, align="C")
                            self.set_font("Helvetica", "", 10)
                            self.cell(
                                0,
                                6,
                                f"Version {APP_VERSION}  |  {version} Version",
                                ln=True,
                                align="C",
                            )
                            self.ln(2)
                            self.set_draw_color(100, 100, 100)
                            self.line(12, self.get_y(), 198, self.get_y())
                            self.ln(5)

                        def footer(self):
                            self.set_y(-12)
                            self.set_font("Helvetica", "I", 8)
                            self.cell(
                                0,
                                8,
                                f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Page {self.page_no()}",
                                align="C",
                            )

                    pdf = PDF()
                    pdf.set_auto_page_break(auto=True, margin=14)
                    pdf.set_left_margin(12)
                    pdf.set_right_margin(12)
                    pdf.add_page()

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
                    for i, img in enumerate(images[:4]):
                        try:
                            img_byte_arr = io.BytesIO()
                            img_resized = img.copy()
                            img_resized.thumbnail((400, 400))
                            img_resized.save(img_byte_arr, format="JPEG")
                            img_byte_arr.seek(0)
                            pdf.image(img_byte_arr, x=photo_x, y=y_start + (i * 55), w=photo_width)
                        except Exception:
                            pass

                    # Write text content
                    pdf.set_font("Helvetica", "", 9)
                    pdf.set_xy(12, 55)

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

                        while len(line) > 0:
                            chunk = line[:78]
                            line = line[78:]
                            pdf.cell(text_width, 4.5, chunk, ln=True)

                    # Contractor labor breakdown
                    if version == "Contractor":
                        pdf.ln(6)
                        pdf.set_font("Helvetica", "B", 11)
                        pdf.cell(text_width, 6, "Labor Cost Breakdown", ln=True)
                        pdf.set_font("Helvetica", "", 10)
                        pdf.cell(text_width, 5, f"Estimated hours: {hours_needed}", ln=True)
                        pdf.cell(text_width, 5, f"People available / on crew: {crew_size}", ln=True)
                        pdf.cell(text_width, 5, f"Hourly rate per person: ${hourly_rate:.2f}", ln=True)
                        pdf.set_font("Helvetica", "B", 11)
                        pdf.cell(text_width, 6, f"Total labor cost: ${total_labor:,.2f}", ln=True)
                        pdf.set_font("Helvetica", "I", 8)
                        pdf.cell(text_width, 5, "Materials are not included in this labor total.", ln=True)

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
                        pdf.cell(
                            0,
                            6,
                            "Signature: _______________________________     Date: ______________",
                            ln=True,
                        )
                        pdf.ln(2)
                        pdf.cell(0, 6, "Date work to begin: ____________________", ln=True)
                        pdf.cell(
                            0,
                            6,
                            "Who purchases supplies (Customer / Contractor): ____________________",
                            ln=True,
                        )

                    # Disclaimer
                    pdf.ln(8)
                    pdf.set_font("Helvetica", "I", 8)
                    if version == "Customer":
                        disclaimer = (
                            "All bids subject to price changes for substitute or material changes "
                            "or in the scope of work modifications. Deposit due before work commencement."
                        )
                    else:
                        disclaimer = (
                            "This is an AI-assisted estimate. Final quantities and decisions should be "
                            "verified by a qualified professional. Showcase Studios is not responsible "
                            "for construction outcomes."
                        )
                    pdf.multi_cell(text_width, 4, disclaimer)

                    return bytes(pdf.output())

                contractor_pdf = create_pdf("Contractor")
                customer_pdf = create_pdf("Customer")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.download_button(
                        label="📄 Download Contractor Version",
                        data=contractor_pdf,
                        file_name=f"Bid_and_Build_It_Contractor_v{APP_VERSION}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                    )
                with col_b:
                    st.download_button(
                        label="📄 Download Customer Version",
                        data=customer_pdf,
                        file_name=f"Bid_and_Build_It_Customer_v{APP_VERSION}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                    )

            except Exception as e:
                st.error(f"Error: {str(e)}")
