"""
app.py (Main Application - SmartEvolve)

--- MODIFIED ---
- Fixed the Gauge Chart visual bug (number flying off) in
  `render_evaluation_report_header` by manually adding the
  number as an annotation.
- All other changes (login page fix, new report header,
  no snow, unique keys) are included.
"""

import streamlit as st
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# st.set_page_config MUST be the very first Streamlit command executed
st.set_page_config(
    page_title="SmartEval",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🤖"
)

import traceback
from datetime import datetime
import base64
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
import random

# --- Core App Imports ---
try:
    from src.ocr_extraction import convert_pdf_to_images, extract_text_from_images
    from src.answer_grader import grade_answers
    from src.diagram_detection import detect_diagrams
    from src.feedback_handler import load_feedback, save_feedback 
except ImportError as e:
    st.error(f"Could not import source files from 'src' folder: {e}. If running in a virtual environment, make sure to launch with `./venv/bin/streamlit run app.py`.")
except Exception as e:
    st.error(f"An error occurred importing source files: {e}")

# --- Page/Module Imports ---
try:
    from login import login_page, is_logged_in, logout
    from dashboard import display_dashboard, save_evaluation_to_history
except ImportError as e:
    st.error(f"Failed to import login or dashboard: {e}. Make sure login.py and dashboard.py are in the same folder.")
except Exception as e:
    st.error(f"An error occurred importing login/dashboard: {e}")

# --- START: Merged Frontend Code ---
def to_base_64(path):
    """Convert file to base64 string."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.warning(f"Asset file not found: {path}")
        return None

def get_global_animations():
    """Returns the main CSS for animations and neon glow effects."""
    return """
    <style>
    /* Global Font */
    body {
        font-family: 'Inter', sans-serif;
    }
    
    /* Global Transitions */
    .stApp {
      transition: background-color 0.6s ease, color 0.6s ease;
      overflow-x: hidden !important;
    }

    /* Page Fade-in */
    @keyframes fadeSlide {
      0% { opacity: 0; transform: translateY(20px); }
      100% { opacity: 1; transform: translateY(0); }
    }
    div[data-testid="stHorizontalBlock"] > div {
      animation: fadeSlide 0.7s cubic-bezier(0.25, 0.8, 0.25, 1);
    }

    /* Tab Animations */
    [data-testid="stTabs"] button {
      backdrop-filter: blur(6px);
      border-radius: 10px !important;
      font-weight: 600 !important;
      transition: all 0.4s ease-in-out;
      color: #C48AF5 !important; /* Purple */
      border: 1px solid rgba(196, 138, 245, 0.25);
      background: rgba(255,255,255,0.03);
    }
    [data-testid="stTabs"] button:hover {
      background: rgba(196, 138, 245, 0.15);
      box-shadow: 0 0 20px rgba(196, 138, 245, 0.55);
    }
    [data-testid="stTabs"] [aria-selected="true"] {
      background: rgba(196, 138, 245, 0.25);
      box-shadow: 0 0 25px rgba(196, 138, 245, 0.7);
    }

    /* Header Glow */
    h1, h2, h3 {
      color: #C48AF5 !important; /* Purple */
      text-shadow: 0 0 10px rgba(196, 138, 245, 0.8), 0 0 30px rgba(196, 138, 245, 0.5);
    }

    /* Button Hover */
    button[kind="primary"] {
      transition: all 0.3s ease-in-out !important;
      box-shadow: 0 0 10px rgba(196, 138, 245, 0.3) !important;
      background-color: #C48AF5 !important;
      color: #000000 !important;
    }
    button[kind="primary"]:hover {
      transform: scale(1.05);
      box-shadow: 0 0 25px rgba(196, 138, 245, 0.7) !important;
      background-color: rgba(196, 138, 245, 0.8) !important;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
      background: rgba(10, 10, 10, 0.6) !important; /* Darker sidebar */
      backdrop-filter: blur(8px);
      border-right: 1px solid rgba(196, 138, 245, 0.3);
      box-shadow: 0 0 10px rgba(196, 138, 245, 0.2);
    }
    section[data-testid="stSidebar"] h2 {
      color: #C48AF5 !important;
      text-shadow: 0 0 10px rgba(196, 138, 245, 0.5);
    }
    
    /* Sidebar Navigation */
    div[data-testid="stRadio"] > label {
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        transition: all 0.3s ease;
        font-weight: 500;
        border: 1px solid transparent;
    }
    div[data-testid="stRadio"] > label:hover {
        background: rgba(196, 138, 245, 0.1);
        border-color: rgba(196, 138, 245, 0.3);
    }
    div[data-testid="stRadio"] [aria-checked="true"] {
        background: rgba(196, 138, 245, 0.2);
        border-color: rgba(196, 138, 245, 0.5);
        font-weight: 700;
    }

    </style>
    """

def get_custom_styles():
    """
    Returns the CSS for info/warning/error boxes and other UI elements.
    """
    return """
    <style>
        /* Info/Error Boxes */
        .success-box { background-color: #d4edda; border-left: 5px solid #28a745; padding: 1rem; margin: 1rem 0; border-radius: 0.25rem; }
        .warning-box { background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 1rem; margin: 1rem 0; border-radius: 0.25rem; }
        .error-box { background-color: #f8d7da; border-left: 5px solid #dc3545; padding: 1rem; margin: 1rem 0; border-radius: 0.25rem; }
        .info-box { background-color: #d1ecf1; border-left: 5px solid #17a2b8; padding: 1rem; margin: 1rem 0; border-radius: 0.25rem; }
        
        @keyframes cardFadeIn {
            from {
                opacity: 0;
                transform: scale(0.95) translateY(10px);
            }
            to {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }

        .dashboard-card {
            background: rgba(18, 18, 18, 0.7); /* Dark Card */
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(196, 138, 245, 0.3); /* Purple Border */
            box-shadow: 0 0 20px rgba(196, 138, 245, 0.1);
            backdrop-filter: blur(10px);
            height: 100%;
            animation: cardFadeIn 0.6s ease-out forwards; /* Apply animation */
        }
        .dashboard-card [data-testid="stMetric"] {
            background-color: transparent; border: none; padding: 0;
        }
        .dashboard-card [data-testid="stMetricLabel"] {
            font-size: 1.1rem;
            color: #C48AF5; /* Purple label */
        }
        .dashboard-card [data-testid="stMetricValue"] {
            font-size: 2.5rem;
            font-weight: 600;
            color: #FFFFFF; /* White value */
        }
    </style>
    """

def get_video_background(video_b64):
    """
    Returns the HTML/CSS for a persistent video background.
    """
    if not video_b64:
        return ""
    return f"""
    <style>
    .stApp {{
        background: transparent !important;
    }}
    video.bgvideo {{
        position: fixed; top: 0; left: 0;
        width: 100vw; height: 100vh;
        object-fit: cover; z-index: -2;
        opacity: 0.9; filter: brightness(0.4) blur(1.5px);
    }}
    .overlay {{
        position: fixed; top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: rgba(10, 0, 20, 0.45); /* Dark purple overlay */
        z-index: -1;
    }}
    </style>
    <video class="bgvideo" autoplay muted loop playsinline>
        <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
    </video>
    <div class="overlay"></div>
    """

def get_logo_header(logo_base64):
    """Returns the HTML/CSS for the centered, glowing logo header."""
    if not logo_base64:
        return "<h2>SMART EVAL</h2>" # Fallback if no logo
    return f"""
    <style>
    .center-header {{
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        margin-top: -10px; animation: fadeIn 2s ease-in-out;
    }}
    .center-header img {{
        width: 110px; filter: drop-shadow(0 0 12px #C48AF5); /* Purple Glow */
        animation: pulseGlow 3s infinite ease-in-out alternate;
    }}
    .center-header h2 {{
        font-family: 'Poppins', sans-serif; color: #C48AF5; /* Purple */
        margin-top: 8px; font-weight: 700;
        letter-spacing: 1px; text-shadow: 0 0 15px #C48AF5;
    }}
    @keyframes pulseGlow {{
        0% {{ filter: drop-shadow(0 0 5px #C48AF5); transform: scale(1); }}
        50% {{ filter: drop-shadow(0 0 25px #C48AF5); transform: scale(1.08); }}
        100% {{ filter: drop-shadow(0 0 5px #C48AF5); transform: scale(1); }}
    }}
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(-20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    </style>
    <div class="center-header">
        <img src="data:image/png;base64,{logo_base64}" alt="Smart Eval Logo">
        <h2>SMART EVAL</h2>
    </div>
    """

def get_tab_animations():
    """Returns the CSS for the tab fade-in animation."""
    return """
    <style>
    /* Smooth transition when switching tabs */
    div[data-testid="stTabs"] > div > div[data-testid="stVerticalBlock"] > div {
        animation: slideFadeIn 0.8s ease-in-out;
    }
    @keyframes slideFadeIn {
        0% { opacity: 0; transform: translateY(25px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    </style>
    """
# --- END: Merged Frontend Code ---

# --- Motivational Quote Helper ---
def get_motivational_quote():
    quotes = [
        "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        "Believe you can and you're halfway there.",
        "The secret of getting ahead is getting started.",
        "It always seems impossible until it's done.",
        "The expert in anything was once a beginner.",
        "Your limitation is only your imagination."
    ]
    return random.choice(quotes)

# --- Helper Function to Save Uploaded File ---
def save_uploaded_file(uploaded_file, save_path):
    """Saves an uploaded file to a temporary path."""
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return save_path
    except Exception as e:
        st.error(f"Error saving file {uploaded_file.name}: {e}")
        return None

# --- NEW: Reusable Score GAUGE + METRICS Function ---
def render_evaluation_report_header(analytics_data, key_prefix=""):
    """
    Renders the top-level score as a Plotly Gauge Chart,
    plus the Overall Score and Pass/Fail metrics.
    """
    total_score_data = analytics_data.get("total_score", {})
    percentage = total_score_data.get("percentage", 0.0)
    awarded = total_score_data.get("awarded", 0)
    max_marks = total_score_data.get("max", 100)
    grade = "Pass" if percentage >= 40 else "Fail"

    st.subheader("Overall Performance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 1. Overall Score Metric
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric("Total Marks", f"{awarded} / {max_marks}")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        # 2. Pass/Fail Metric
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric("Result", grade)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        # 3. Gauge Chart
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge", # <-- Set mode to GAUGE ONLY
            value = percentage,
            title = {'text': "Final Score (%)", 'font': {'size': 16}},
            gauge = {'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                     'bar': {'color': "#C48AF5"}, # Main purple
                     'steps' : [
                         {'range': [0, 40], 'color': "#dc3545"}, # Red
                         {'range': [40, 75], 'color': "#ffc107"}, # Yellow
                         {'range': [75, 100], 'color': "#28a745"}]} # Green
        ))
        
        # --- THIS IS THE FIX ---
        # Manually add the number as an annotation in the center
        fig_gauge.add_annotation(
            text=f"{percentage:.0f}%", # Show number as "70%"
            x=0.5, y=0.4, # Center of the gauge
            font=dict(size=48, color="white"),
            showarrow=False
        )
        # --- END FIX ---
        
        fig_gauge.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            font={'color': 'white'},
            height=200, # Made gauge smaller to fit in column
            margin=dict(t=40, b=10, l=10, r=10) # Minimal margins
        )
        # --- FIX: Added a unique key using the prefix ---
        st.plotly_chart(fig_gauge, use_container_width=True, key=f"{key_prefix}_score_gauge")

# --- MODIFIED: Analytics Chart Function ---
def render_analytics_charts(analytics_data, key_prefix=""):
    """
    Takes the analytics dictionary and renders Plotly charts.
    """
    if not analytics_data:
        st.info("No analytics data available for this evaluation.")
        return

    # 1. Section-wise Performance
    st.subheader("Section-wise Performance")
    section_data = analytics_data.get("section_wise", [])
    if section_data:
        df_section = pd.DataFrame(section_data)
        df_section["percentage"] = df_section.get("percentage", 0)
        fig_sec = px.bar(
            df_section,
            x="section",
            y="percentage",
            title="Performance by Section",
            color="percentage",
            color_continuous_scale=["#dc3545", "#ffc107", "#28a745"],
            range_color=[0, 100],
            labels={"percentage": "Score (%)", "section": "Section"},
            template="plotly_dark",
        )
        fig_sec.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        # --- FIX: Added a unique key ---
        st.plotly_chart(fig_sec, use_container_width=True, key=f"{key_prefix}_section_perf_chart")
    else:
        st.info("No section-wise data found.")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        # 2. Question-wise Performance (Line Chart)
        st.subheader("Question-wise Performance")
        q_data = analytics_data.get("question_wise", [])
        if q_data:
            df_q = pd.DataFrame(q_data)
            fig_q = go.Figure(data=[
                go.Scatter(
                    name='Max Marks', 
                    x=df_q['question'], 
                    y=df_q['max'], 
                    mode='lines+markers',
                    line=dict(color='rgba(196, 138, 245, 0.5)', dash='dash')
                ),
                go.Scatter(
                    name='Awarded', 
                    x=df_q['question'], 
                    y=df_q['awarded'], 
                    mode='lines+markers',
                    line=dict(color='#C48AF5', width=3)
                )
            ])
            fig_q.update_layout(
                title="Marks by Question",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                legend_title_text='Marks',
                xaxis_title="Question",
                yaxis_title="Score"
            )
            # --- FIX: Added a unique key ---
            st.plotly_chart(fig_q, use_container_width=True, key=f"{key_prefix}_question_perf_chart")
        else:
            st.info("No question-wise data found.")

    with col2:
        # 3. Diagram Performance
        st.subheader("Diagram Performance (Estimate)")
        diag_data = analytics_data.get("diagram_performance", {})
        if diag_data:
            required = diag_data.get("required_estimate", 0)
            found = diag_data.get("found_estimate", 0)
            missing = max(0, required - found)
            
            pie_data = pd.DataFrame({
                "Status": ["Found", "Missing (Est.)"],
                "Count": [found, missing]
            })
            
            fig_pie = px.pie(
                pie_data,
                values='Count',
                names='Status',
                title="Diagram Completion (Estimate)",
                color_discrete_map={'Found': '#28a745', 'Missing (Est.)': '#dc3545'},
                template="plotly_dark"
            )
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            # --- FIX: Added a unique key ---
            st.plotly_chart(fig_pie, use_container_width=True, key=f"{key_prefix}_diagram_perf_chart")
        else:
            st.info("No diagram analytics data found.")


# --- Page 1: Evaluation Page (For Teacher/Admin) ---
def display_evaluation_page(subject_name):
    """
    Renders the main evaluation workflow page.
    """
    st.header("🚀 Evaluate Paper")
    st.markdown(get_tab_animations(), unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 Upload & Evaluate", 
        "📊 Evaluation Report", 
        "📈 Analytics",
        "📝 Extracted Text (Debug)"
    ])

    with tab1:
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            usn = st.text_input("Student USN (e.g., 2C30309)", key="student_usn_input", help="e.g. 2C30301 to 2C30370").upper()
        with col_meta2:
            mode = st.radio("Evaluation Mode", ["Reasonable", "Easygoing", "Stringent"], key="mode_input", horizontal=True)
        
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            uploaded_question_paper = st.file_uploader("1. Question Paper", type=["pdf"])
        with col2:
            uploaded_answer_key = st.file_uploader("2. Answer Key", type=["pdf"])
        with col3:
            uploaded_answer_sheet = st.file_uploader("3. Student's Sheet", type=["pdf"])
        
        st.divider()
        st.subheader("4. Scoring Rubrics & Rules")
        scoring_rules = st.text_area("Provide any special instructions...", height=150, key="scoring_rules_input")
        st.divider()

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            evaluate_button = st.button("🚀 Start Evaluation", type="primary", use_container_width=True)
        
        if evaluate_button:
            if 'api_key' not in st.session_state or not st.session_state.api_key:
                st.error("❌ Please enter your API Key in the sidebar under Settings.")
            elif not usn:
                st.error("❌ Please enter a Student USN.")
            elif not (uploaded_question_paper and uploaded_answer_key and uploaded_answer_sheet):
                st.error("❌ Please upload all three PDF files.")
            else:
                progress_bar = st.progress(0, text="Starting Evaluation...")
                status_text = st.empty()
                
                try:
                    api_key = st.session_state.api_key
                    
                    status_text.text("📁 Saving uploaded files...")
                    os.makedirs("data", exist_ok=True)
                    temp_q_path = save_uploaded_file(uploaded_question_paper, "data/temp_q.pdf")
                    temp_k_path = save_uploaded_file(uploaded_answer_key, "data/temp_k.pdf")
                    temp_s_path = save_uploaded_file(uploaded_answer_sheet, "data/temp_s.pdf")
                    
                    if not all([temp_q_path, temp_k_path, temp_s_path]):
                        st.error("❌ Failed to save one or more uploaded files.")
                        return

                    progress_bar.progress(10, text="Converting PDFs...")
                    q_images = convert_pdf_to_images(str(temp_q_path))
                    k_images = convert_pdf_to_images(str(temp_k_path))
                    s_images = convert_pdf_to_images(str(temp_s_path))

                    progress_bar.progress(40, text="Extracting text (OCR)...")
                    question_text = extract_text_from_images(q_images, api_key=api_key)
                    key_text = extract_text_from_images(k_images, api_key=api_key)
                    student_text = extract_text_from_images(s_images, api_key=api_key)
                    
                    st.session_state.question_text = question_text
                    st.session_state.key_text = key_text
                    st.session_state.student_text = student_text
                    
                    # --- MODIFICATION: Removed st.snow() ---

                    progress_bar.progress(70, text="Detecting diagrams...")
                    diagram_count = detect_diagrams(temp_s_path, "outputs/diagram_temp")
                    st.session_state.diagram_count = diagram_count

                    progress_bar.progress(80, text=" Applying grading rules...")
                    rules = st.session_state.scoring_rules_input
                    
                    evaluation_data_dict = grade_answers(
                        question_text, key_text, student_text, rules, mode, diagram_count, api_key=api_key
                    )
                    
                    evaluation_report_md = evaluation_data_dict.get("report", "Error: No report found.")
                    analytics_data = evaluation_data_dict.get("analytics", {})
                    
                    st.session_state.evaluation_analytics = analytics_data
                    st.session_state.evaluation_report = evaluation_report_md
                    st.session_state.evaluation_complete = True

                    save_data = {
                        "usn": usn,
                        "subject": subject_name,
                        "evaluated_by": st.session_state.username,
                        "timestamp": datetime.now().isoformat(),
                        "diagram_count": diagram_count,
                        "evaluation_report": evaluation_report_md,
                        "analytics_data": analytics_data
                    }
                    
                    save_path = f"outputs/scores/{usn}.json"
                    save_evaluation_to_history(save_data, save_path)
                    
                    progress_bar.progress(100, text="✅ Evaluation completed!")
                    
                    # --- THIS IS THE "POP-UP" MESSAGE ---
                    st.success(f"🎉 Evaluation for {usn} completed!")
                    st.info("Switch to the 'Evaluation Report' or 'Analytics' tab to see results.")

                except Exception as e:
                    st.error(f"❌ Error during evaluation: {str(e)}")
                    st.code(traceback.format_exc())
                    progress_bar.empty()
                    status_text.empty()

    with tab2: # Evaluation Report
        if st.session_state.evaluation_complete:
            st.header("📊 Personalized Feedback Report")
            analytics_data = st.session_state.evaluation_analytics
            
            # --- MODIFIED: Show new Report Header ---
            render_evaluation_report_header(analytics_data, key_prefix="teacher_report")
            st.divider()

            # --- RENDER DETAILED TABLE ---
            st.subheader("Detailed Grading Breakdown")
            breakdown = analytics_data.get("detailed_breakdown", [])
            
            if breakdown:
                df = pd.DataFrame(breakdown)
                df_display = df[['question', 'part', 'description', 'feedback', 'marks_awarded', 'max_marks']]
                st.dataframe(df_display, use_container_width=True)
            else:
                st.info("No detailed breakdown was generated.")
            
            st.divider()
            
            # --- RENDER AI SUMMARY ---
            st.subheader("Feedback Summary")
            st.markdown(st.session_state.evaluation_report)
            
            st.divider()

            # --- RENDER MOTIVATIONAL QUOTE ---
            st.subheader("A Little Motivation")
            st.success(f"**Quote:** *\"{get_motivational_quote()}\"*")

            st.download_button("📥 Download Report (Markdown)", st.session_state.evaluation_report, "report.md")
        else:
            st.info("👆 Please complete an evaluation first.")

    with tab3: # Analytics Tab
        if st.session_state.evaluation_complete:
            st.header("📈 Analytics Dashboard")
            # --- MODIFIED: This now only renders the charts ---
            render_analytics_charts(st.session_state.evaluation_analytics, key_prefix="teacher_analytics")
        else:
            st.info("👆 Run an evaluation to see the analytics.")

    with tab4: # Extracted Text (Debug)
        if st.session_state.evaluation_complete:
            st.header("📝 Extracted Text (OCR Results)")
            with st.expander("Question Paper"): st.text(st.session_state.question_text)
            with st.expander("Answer Key"): st.text(st.session_state.key_text)
            with st.expander("Student's Sheet"): st.text(st.session_state.student_text)
        else:
            st.info("👆 Run an evaluation to see extracted text.")

# --- Page 2: Dashboard Page (For Teacher/Admin) ---
def display_dashboard_page(subject_name):
    """Renders the dashboard page."""
    display_dashboard(subject_name)


# --- Page 3: Feedback Page (For Teacher/Admin) ---
def display_feedback_page():
    """
    Renders a page for teachers/admins to review all feedback.
    """
    st.header("✉️ Feedback Hub")
    st.markdown("Review feedback submitted by students and teachers.")
    
    all_feedback = load_feedback()
    
    if not all_feedback:
        st.info("No feedback has been submitted yet.")
        return
        
    df = pd.DataFrame(all_feedback)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # --- Metrics Cards ---
    st.subheader("Feedback Overview")
    avg_rating = df['rating'].mean()
    total_feedback = len(df)
    student_feedback = len(df[df['role'] == 'student'])
    teacher_feedback = len(df[df['role'] == 'teacher'])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric("Total Feedback", total_feedback)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric("Average Rating", f"{avg_rating:.2f} / 5.0")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric("Student / Teacher", f"{student_feedback} / {teacher_feedback}")
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Charts ---
    st.subheader("Feedback Analysis")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        rating_counts = df['rating'].value_counts().sort_index()
        fig_bar = go.Figure(data=[go.Bar(
            x=rating_counts.index, 
            y=rating_counts.values,
            marker_color="#2563EB"
        )])
        fig_bar.update_layout(
            title="Feedback Rating Distribution",
            xaxis_title="Rating (1-5 Stars)",
            yaxis_title="Count",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_bar, use_container_width=True, key="feedback_rating_chart")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_chart2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        role_counts = df['role'].value_counts()
        fig_pie = go.Figure(data=[go.Pie(
            labels=role_counts.index, 
            values=role_counts.values, 
            hole=.3,
            marker_colors=["#2563EB", "#38BDF8"]
        )])
        fig_pie.update_layout(
            title="Feedback by Role",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_pie, use_container_width=True, key="feedback_role_chart")
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("All Feedback")
    st.dataframe(df[['timestamp', 'role', 'rating', 'comment', 'subject']], use_container_width=True)


# --- Page 4: Student View ---
def display_student_view():
    """
    Renders the student-facing dashboard.
    """
    usn = st.session_state.username
    st.header(f"🧑‍🎓 Welcome, {usn}")
    
    col1, _, col3 = st.columns([1, 3, 1])
    with col3:
        st.button("Logout", on_click=logout, use_container_width=True)
    st.divider()

    record_path = f"outputs/scores/{usn}.json"
    
    if not os.path.exists(record_path):
        st.info("⏳ Awaiting Evaluation. Your paper has not been graded yet.")
        st.markdown("Please check back later.")
        return
        
    try:
        with open(record_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"Could not load your report. Error: {e}")
        return

    st.markdown(get_tab_animations(), unsafe_allow_html=True)
    tab_report, tab_analytics, tab_feedback = st.tabs([
        "📊 Evaluation Report", 
        "📈 Your Analytics",
        "✉️ Submit Feedback"
    ])

    with tab_report:
        st.success("✅ Your paper has been evaluated!")
        analytics_data = data.get("analytics_data", {})
        
        # --- MODIFIED: Show new Report Header ---
        render_evaluation_report_header(analytics_data, key_prefix="student_report")
        st.divider()

        st.subheader("Detailed Grading Breakdown")
        breakdown = analytics_data.get("detailed_breakdown", [])
        
        if breakdown:
            df = pd.DataFrame(breakdown)
            df_display = df[['question', 'part', 'description', 'feedback', 'marks_awarded', 'max_marks']]
            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("No detailed breakdown was generated.")
        
        st.divider()
        
        st.subheader("Feedback Summary")
        st.markdown(data.get("evaluation_report", "Error: Report is empty."))
        
        st.divider()

        st.subheader("A Little Motivation")
        st.success(f"**Quote:** *\"{get_motivational_quote()}\"*")
        
        st.download_button(
            "📥 Download Your Report",
            data=data.get("evaluation_report", ""),
            file_name=f"{usn}_report.md",
            type="primary"
        )
        
    with tab_analytics:
        st.header("📈 Your Analytics Dashboard")
        
        # --- MODIFIED: This now only renders the charts ---
        # --- FIX: We must pass a unique key for the student analytics ---
        render_analytics_charts(data.get("analytics_data", {}), key_prefix="student_analytics")

    with tab_feedback:
        st.subheader("✉️ Submit Feedback")
        st.markdown("How was your experience with this evaluation?")
        
        with st.form("student_feedback_form"):
            rating = st.select_slider("Rating (1=Poor, 5=Excellent)", [1, 2, 3, 4, 5], value=5)
            comment = st.text_area("Comments (Optional)")
            
            if st.form_submit_button("Submit Feedback", type="primary"):
                if save_feedback(usn, "student", rating, comment, subject=data.get("subject", "General")):
                    st.success("Thank you for your feedback!")
                else:
                    st.error("Could not save feedback.")


# --- Page 5: Settings Page (Now with API Key) ---
def display_settings_page():
    """
    A page for settings, including the new API Key input.
    """
    st.header("⚙️ Settings")
    
    st.subheader("API Configuration")
    
    api_key = st.text_input(
        "API Key", 
        type="password", 
        value=st.session_state.get("api_key", ""),
        help="Get your key from Google. This is saved in your session."
    )
    
    if api_key:
        st.session_state.api_key = api_key
        if st.button("Save Key"):
            st.success("API Key saved for this session!")
    
    st.divider()
    st.markdown("Other settings, like profile management, can be added here.")


# --- Main Application Router ---
def main():
    # --- Initialize all session state keys ---
    if 'evaluation_complete' not in st.session_state:
        st.session_state.evaluation_complete = False
    if 'evaluation_report' not in st.session_state:
        st.session_state.evaluation_report = ""
    if 'evaluation_data' not in st.session_state:
        st.session_state.evaluation_data = {}
    if 'evaluation_analytics' not in st.session_state:
        st.session_state.evaluation_analytics = {}
    if 'question_text' not in st.session_state:
        st.session_state.question_text = ""
    if 'key_text' not in st.session_state:
        st.session_state.key_text = ""
    if 'student_text' not in st.session_state:
        st.session_state.student_text = ""
    if 'diagram_count' not in st.session_state:
        st.session_state.diagram_count = 0
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    # --- END ---

    # --- Load Assets into Session State ONCE ---
    if 'video_b64' not in st.session_state:
        video_path = "assets/logo.mp4"
        st.session_state.video_b64 = to_base_64(video_path)
    
    if 'logo_header_html' not in st.session_state:
        logo_path = "assets/logo.png"
        logo_b64 = to_base_64(logo_path)
        if logo_b64:
            st.session_state.logo_header_html = get_logo_header(logo_b64)
        else:
            st.session_state.logo_header_html = "<h2>SMART EVAL</h2>" # Fallback

    # --- Apply Global Styles (Persistent Background) ---
    st.markdown(get_global_animations(), unsafe_allow_html=True)
    st.markdown(get_custom_styles(), unsafe_allow_html=True)
    if st.session_state.video_b64:
        st.markdown(get_video_background(st.session_state.video_b64), unsafe_allow_html=True)
    
    # --- ROUTER LOGIC ---
    if not is_logged_in():
        
        # --- MODIFICATION ---
        # ALL login page UI is now handled by login_page()
        # We pass the quote function as an argument to fix the "blank box" bug
        login_page(get_motivational_quote) 
    
    else:
        # --- ROUTE BASED ON ROLE ---
        role = st.session_state.get("role", "student")

        if role == "student":
            display_student_view()
            
        elif role in ["teacher", "admin"]:
            # --- Teacher/Admin View with Sidebar ---
            with st.sidebar:
                st.markdown(st.session_state.logo_header_html, unsafe_allow_html=True)
                st.divider()
                st.markdown(f"#### Welcome, **{st.session_state.username}**!")
                st.caption(f"Role: {st.session_state.role.title()}")
                st.divider()

                subject_name = st.text_input("Subject Name", "OS - Internal 1")
                
                st.divider()
                
                page_options = {
                    "🏠 Dashboard": "Dashboard",
                    "🚀 Evaluate": "Evaluate",
                    "✉️ Feedback": "Feedback",
                    "⚙️ Settings": "Settings"
                }
                
                if st.session_state.role == "admin":
                    pass 

                page_selection = st.radio(
                    "Main Navigation",
                    page_options.keys(),
                    label_visibility="hidden"
                )
                
                st.divider()
                st.button("Logout", on_click=logout, use_container_width=True, type="primary")

            # --- Render the selected page for Teacher/Admin ---
            page = page_options[page_selection]
            
            if page == "Dashboard":
                display_dashboard_page(subject_name)
            elif page == "Evaluate":
                display_evaluation_page(subject_name)
            elif page == "Feedback":
                display_feedback_page()
            elif page == "Settings":
                display_settings_page()

if __name__ == "__main__":
    main()