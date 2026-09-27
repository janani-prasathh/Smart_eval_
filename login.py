"""
login.py - Authentication System for Smart Eval

--- MODIFIED ---
- Removed the redundant `st.rerun()` call from the `logout()` function.
  Streamlit automatically reruns after an on_click callback anyway.
"""

import streamlit as st
import json
import hashlib
import os
from datetime import datetime

# File to store user data (Teachers/Admins)
USERS_FILE = "data/users.json"
STUDENTS_FILE = "data/students.json"

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def load_students():
    """Load master student list"""
    if os.path.exists(STUDENTS_FILE):
        with open(STUDENTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_users(users):
    """Save users to JSON file"""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def register_user(username, password, email, role="teacher"):
    """Register a new user"""
    users = load_users()
    
    if username in users:
        return False, "Username already exists"
    
    users[username] = {
        "password": hash_password(password),
        "email": email,
        "role": role,
        "created_at": datetime.now().isoformat(),
        "evaluations": []
    }
    
    save_users(users)
    return True, "Registration successful"

def authenticate_user(login_identifier, password):
    """Authenticate user credentials using username or email (case-insensitive)"""
    users = load_users()
    identifier_clean = login_identifier.strip().lower()
    
    matched_username = None
    matched_user = None
    
    for uname, udata in users.items():
        if uname.lower() == identifier_clean or udata.get("email", "").strip().lower() == identifier_clean:
            matched_username = uname
            matched_user = udata.copy()
            break
            
    if not matched_user:
        return False, "User not found"
    
    hashed_input = hash_password(password)
    stored_password = matched_user.get("password")
    
    if stored_password == hashed_input or stored_password == password:
        matched_user["actual_username"] = matched_username
        return True, matched_user
    
    return False, "Invalid password"

def login_page(get_motivational_quote):
    """Display login page"""
    st.markdown("""
    <style>
    @keyframes fadeSlideIn {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: rgba(18, 18, 18, 0.8);
        border-radius: 15px;
        backdrop-filter: blur(10px);
        
        border: 2px solid transparent;
        background-clip: padding-box;
        border-image: linear-gradient(135deg, #C48AF5, #00FFFF) 1;
        box-shadow: 0 0 30px rgba(196, 138, 245, 0.3), 0 0 30px rgba(0, 255, 255, 0.3);
        
        animation: fadeSlideIn 1s ease-out;
    }
    .login-header {
        text-align: center;
        color: #00FFFF;
        margin-bottom: 2rem;
        font-size: 2rem;
    }
    
    div[data-testid="stForm"] div[data-testid="stTextInput"] > div > div > input {
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid rgba(196, 138, 245, 0.5) !important;
        color: #FFFFFF !important;
        border-radius: 0 !important;
        transition: all 0.3s ease;
    }
    div[data-testid="stForm"] div[data-testid="stTextInput"] > div > div > input:focus {
        border-bottom-color: #00FFFF !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        
        # 1. Show Logo
        if 'logo_header_html' in st.session_state and st.session_state.logo_header_html:
             st.markdown(st.session_state.logo_header_html, unsafe_allow_html=True)
        
        # 2. Show Quote
        st.markdown(f'> ### *"{get_motivational_quote()}"*')
        
        # 3. Show Divider
        st.divider()

        # 4. Show Login Box
        st.markdown('<div class="login-container">', unsafe_allow_html=True)

        # 5. Radio buttons INSIDE the box
        login_role = st.radio(
            "Login As:", 
            ["Student", "Teacher / Admin"], 
            horizontal=True,
            label_visibility="collapsed"
        )
        
        st.markdown("---") # A separator line
        
        # --- STUDENT LOGIN ---
        if login_role == "Student":
            st.markdown('<h2 class="login-header">Student Login</h2>', unsafe_allow_html=True)
            master_student_list = load_students()
            if not master_student_list:
                st.error("Student list 'data/students.json' not found. Student login is disabled.")
            
            with st.form("student_login_form"):
                usn = st.text_input("Enter your USN (e.g., 2C30309)", help="Sample USNs: 2C30301 to 2C30370")
                student_submit = st.form_submit_button("Check Status", type="primary", use_container_width=True, disabled=(not master_student_list))
                
                if student_submit:
                    if usn:
                        usn_upper = usn.upper()
                        if usn_upper in master_student_list:
                            st.session_state.logged_in = True
                            st.session_state.username = usn_upper
                            st.session_state.role = "student"
                            st.success("✅ Login successful! Loading status...")
                            st.rerun() # This one is NOT in a callback, so it's OK
                        else:
                            st.error("❌ USN not found in master list. Please contact your teacher.")
                    else:
                        st.warning("⚠️ Please enter your USN")

        # --- TEACHER / ADMIN LOGIN ---
        elif login_role == "Teacher / Admin":
            st.markdown('<h2 class="login-header">Login</h2>', unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["Login", "SignUp"])
            
            with tab1:
                with st.form("login_form"):
                    username = st.text_input("Username or Email", key="login_username")
                    password = st.text_input("Password", type="password", key="login_password")
                    submit = st.form_submit_button("Login", type="primary", use_container_width=True)
                    
                    if submit:
                        if username and password:
                            success, result = authenticate_user(username, password)
                            
                            if success and isinstance(result, dict):
                                st.session_state.logged_in = True
                                st.session_state.username = result.get("actual_username", username)
                                st.session_state.user_data = result
                                st.session_state.role = result.get("role", "teacher")
                                st.success("✅ Login successful!")
                                st.rerun() # This one is also NOT in a callback, so it's OK
                            elif not success:
                                st.error(f"❌ {result}")
                            else:
                                st.error("❌ An unexpected authentication error occurred.")
                        else:
                            st.warning("⚠️ Please fill all fields")
                
                st.markdown("""
                <div style="text-align: left; margin-top: 1rem;">
                    <a href="#" style="color: #00FFFF; text-decoration: none; font-size: 0.9rem;">Forgot Password ?</a>
                </div>
                """, unsafe_allow_html=True)

            
            with tab2: # This is now the "SignUp" tab
                with st.form("register_form"):
                    new_username = st.text_input("Username", key="reg_username")
                    new_email = st.text_input("Email", key="reg_email")
                    new_password = st.text_input("Password", type="password", key="reg_password")
                    confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
                    role = st.selectbox("Role", ["teacher", "admin"], key="reg_role")
                    
                    register = st.form_submit_button("Register", type="primary", use_container_width=True)
                    
                    if register:
                        if new_username and new_email and new_password and confirm_password:
                            if new_password != confirm_password:
                                st.error("❌ Passwords don't match")
                            elif len(new_password) < 6:
                                st.error("❌ Password must be at least 6 characters")
                            else:
                                success, message = register_user(new_username, new_password, new_email, role)
                                if success:
                                    st.success(f"✅ {message}")
                                else:
                                    st.error(f"❌ {message}")
                        else:
                            st.warning("⚠️ Please fill all fields")
        
        # --- The Login Box ends HERE ---
        st.markdown('</div>', unsafe_allow_html=True)

def logout():
    """Logout user"""
    keys_to_clear = [
        "logged_in", "username", "user_data", "role", 
        "evaluation_complete", "evaluation_report", "evaluation_data", "evaluation_analytics"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    # st.rerun() # <-- THIS IS THE LINE TO REMOVE/COMMENT OUT
    # The app will re-run automatically because this function is in an on_click.

def is_logged_in():
    """Check if user is logged in"""
    return st.session_state.get('logged_in', False)