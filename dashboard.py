"""
dashboard.py

Streamlit dashboard page for SmartEval analytics and quick stats.

--- MODIFIED ---
- Replaced previous charts with three new, easy-to-analyze visualizations:
  1. A "Speedometer" Gauge Chart for the Class Average.
  2. A Donut Chart for the Pass/Fail Ratio.
  3. A sorted Bar Chart to show the Hardest/Easiest Questions.
- Fixed bug where `get_overall_scores_df` was not reading the
  correct keys from the analytics data, causing charts to show "0".
"""

import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px 
# from src.utils import save_json # Assuming utils.py has save_json

# --- Helper Functions ---

def load_student_list(student_file="data/students.json"):
    """Loads the master list of student USNs."""
    if not os.path.exists(student_file):
        st.error("CRITICAL: 'data/students.json' master list not found.")
        return []
    try:
        with open(student_file, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading student list: {e}")
        return []

def load_all_evaluations(scores_dir="outputs/scores"):
    """Loads all .json evaluation files from the scores directory."""
    if not os.path.exists(scores_dir):
        return []
        
    all_evals = []
    files = [f for f in os.listdir(scores_dir) if f.endswith(".json")]
    
    for fname in files:
        try:
            with open(os.path.join(scores_dir, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    all_evals.append(data)
        except Exception as e:
            print(f"Error reading {fname}: {e}")
            
    return all_evals

# --- Helper to get overall scores (for Gauge/Donut) ---
def get_overall_scores_df(all_evals):
    """
    Processes evaluation files to get a simple DataFrame of USN and final score percentage.
    """
    perf_data = []
    for eval_data in all_evals:
        analytics = eval_data.get("analytics_data", {})
        total_data = analytics.get("total_score", {})
        
        if not total_data:
             total_data = analytics.get("total", {})

        percentage = total_data.get("percentage")
        
        if percentage is None:
            awarded = total_data.get("awarded", total_data.get("adjusted", total_data.get("original", 0)))
            max_val = total_data.get("max", 100) 
            percentage = (awarded / max_val * 100) if max_val > 0 else 0
        
        perf_data.append({
            "usn": eval_data.get("usn", "Unknown"),
            "score_percent": percentage
        })
    
    if not perf_data:
        return pd.DataFrame(columns=["usn", "score_percent"])
        
    return pd.DataFrame(perf_data)

# --- Helper to get per-question scores (for Bar Chart) ---
def get_detailed_performance_df(all_evals):
    """
    Processes evaluation files to create a flat DataFrame for question-by-question bar chart.
    """
    detailed_data = []
    for eval_data in all_evals:
        usn = eval_data.get("usn", "Unknown")
        breakdown = eval_data.get("analytics_data", {}).get("detailed_breakdown", [])
        
        for item in breakdown:
            q_num = item.get("question", "N/A")
            part = item.get("part", "")
            q_name = f"Q{q_num}{part}"
            
            awarded = item.get("marks_awarded", 0)
            max_m = item.get("max_marks", 0)
            percentage = (awarded / max_m * 100) if max_m > 0 else 0
            
            detailed_data.append({
                "usn": usn,
                "question": q_name,
                "score_percent": percentage
            })
            
    if not detailed_data:
        return pd.DataFrame(columns=["usn", "question", "score_percent"])
        
    return pd.DataFrame(detailed_data)


# --- Main Display Function ---
def display_dashboard(subject_name):
    """Display the main dashboard with analytics and quick stats"""
    
    st.header(f"📈 Dashboard: {subject_name}")
    st.markdown("Here's a global overview of all evaluations processed by the system.")
    
    student_list = load_student_list()
    all_evaluations = load_all_evaluations()
    
    # Process the data
    overall_perf_df = get_overall_scores_df(all_evaluations)
    detailed_perf_df = get_detailed_performance_df(all_evaluations)
    
    # Calculate top-level metrics
    total_papers = len(student_list)
    attempted_papers = len(all_evaluations)
    pending_papers = total_papers - attempted_papers
    completion_pct = (attempted_papers / total_papers * 100) if total_papers > 0 else 0
    class_average = overall_perf_df['score_percent'].mean() if not overall_perf_df.empty else 0
    
    st.divider()

    # --- Top Metric Cards ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric(label="Total Papers", value=total_papers)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric(label="Evaluated", value=attempted_papers)
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric(label="Pending", value=pending_papers)
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric(label="Completion", value=f"{completion_pct:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True) 

    # --- Main Dashboard Area (Charts and Recent Evals) ---
    col_main, col_side = st.columns([2.5, 1]) # Give main col more space

    with col_main:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        
        if all_evaluations and not overall_perf_df.empty:
            
            # --- Row 1: Gauge and Donut ---
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # --- NEW: Chart 1: Class Average (Gauge) ---
                st.subheader("Class Average Score")
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = class_average,
                    title = {'text': "Average Score (%)"},
                    number = {'font': {'size': 48, 'color': "white"}},
                    gauge = {'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                             'bar': {'color': "#C48AF5"}, # Main purple
                             'steps' : [
                                 {'range': [0, 40], 'color': "#dc3545"}, # Red
                                 {'range': [40, 75], 'color': "#ffc107"}, # Yellow
                                 {'range': [75, 100], 'color': "#28a745"}]} # Green
                ))
                fig_gauge.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    font={'color': 'white'},
                    height=300, # Set a fixed height
                    margin=dict(t=50, b=50)
                )
                st.plotly_chart(fig_gauge, use_container_width=True, key="dashboard_gauge")

            with chart_col2:
                # --- NEW: Chart 2: Pass/Fail (Donut) ---
                st.subheader("Pass/Fail Ratio")
                pass_fail_df = overall_perf_df.copy()
                pass_fail_df['Status'] = pass_fail_df['score_percent'].apply(lambda x: "Pass" if x >= 40 else "Fail")
                status_counts = pass_fail_df['Status'].value_counts().reset_index()
                # BUG FIX: Make sure the column is named 'count' if it's not reset properly
                if 'count' not in status_counts.columns:
                    status_counts.columns = ['Status', 'count']

                
                fig_donut = px.pie(
                    status_counts,
                    names='Status',
                    values='count', # Use the 'count' column
                    hole=0.5, # This makes it a donut chart
                    title="Pass vs. Fail",
                    color='Status',
                    color_discrete_map={'Fail': '#dc3545', 'Pass': '#28a745'}
                )
                fig_donut.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=300,
                    margin=dict(t=50, b=50),
                    legend_title="Status"
                )
                fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_donut, use_container_width=True, key="dashboard_donut")

            st.divider()

            # --- Row 2: Hardest Questions Bar Chart ---
            if not detailed_perf_df.empty:
                st.subheader("Question Performance (Hardest to Easiest)")
                
                # Calculate average score per question
                avg_q_df = detailed_perf_df.groupby('question')['score_percent'].mean().reset_index()
                avg_q_df = avg_q_df.sort_values(by='score_percent', ascending=True) # Sort low to high
                
                fig_bar = px.bar(
                    avg_q_df,
                    x='question',
                    y='score_percent',
                    title="Average Score by Question",
                    labels={"score_percent": "Average Score (%)", "question": "Question"},
                    color='score_percent', # Color by score
                    color_continuous_scale="RdYlGn", # Red -> Yellow -> Green
                    range_color=[0, 100]
                )
                fig_bar.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(fig_bar, use_container_width=True, key="dashboard_bar")
            
            else:
                st.info("No detailed question data found to build performance charts. Run an evaluation to see this chart.")

        else:
            st.info("No evaluation data yet. Run an evaluation to see performance charts.")
            
        st.markdown('</div>', unsafe_allow_html=True)

    with col_side:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("Recent Evaluations")
        
        if all_evaluations:
            all_evaluations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            for eval_data in all_evaluations[:5]:
                usn = eval_data.get("usn", "Unknown USN")
                timestamp_val = eval_data.get("timestamp")
                if timestamp_val:
                    ts = pd.to_datetime(timestamp_val).strftime("%Y-%m-%d %H:%M")
                else:
                    ts = "N/A"
                
                with st.container(border=True):
                    st.markdown(f"**🧑‍🎓 {usn}**")
                    st.caption(f"Evaluated: {ts}")
        else:
            st.info("No evaluations found.")
            
        st.markdown('</div>', unsafe_allow_html=True)


def save_evaluation_to_history(evaluation_data, history_path):
    """
    Saves the evaluation dictionary to a specific file path.
    """
    try:
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation_data, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving evaluation history: {e}")
        return False