"""
LOGIN_MASTER.PY - WITH AGENCY BRANDING (Agency_Name & Logo_URL)
=================================================================
✅ NEW FEATURES:
1. Agency_Name column support (for display in UI)
2. Logo_URL column support (for agency logo)
3. Dynamic column reading (works with any column names)
4. Is_Active instead of Status (Pending/Yes/No)
5. Worksheet_URL (not Sheet_Name)
6. Session state stores agency_name and logo_url for UI branding
"""

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import os
import json
import hashlib
import secrets
import string


# Import external template creator
try:
    from create_master_template import copy_master_template_for_agency
    TEMPLATE_CREATOR_AVAILABLE = True
except ImportError:
    TEMPLATE_CREATOR_AVAILABLE = False
    st.warning("⚠️ Template creator module not found. Template creation will be disabled.")


# ====================================================
# CONFIGURATION
# ====================================================


# Login Master Sheet ID (contains all agency registrations)
SHEET_ID = "1hXZdwIOatc_oUoX-AzAiBQywe7E4kq9IFUglMcY04_A"


# Credentials
CRED_FILE = "credentials.json" if os.path.exists("credentials.json") else None
DEBUG_MODE = True


# Google API Scopes
SCOPES = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]


# ====================================================
# DEBUG LOGGING
# ====================================================


def debug_log(message, level="INFO"):
    """Enhanced debug logging"""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    if level == "ERROR":
        st.error(f"[{timestamp}] ❌ {message}")
    elif level == "SUCCESS":
        st.success(f"[{timestamp}] ✅ {message}")
    elif level == "WARNING":
        st.warning(f"[{timestamp}] ⚠️ {message}")
    elif level == "CRITICAL":
        st.error(f"[{timestamp}] 🔴 CRITICAL: {message}")
    else:
        st.info(f"[{timestamp}] ℹ️ {message}")


# ====================================================
# PASSWORD UTILITIES
# ====================================================


def generate_password(length=12):
    """Generate secure random password"""
    characters = string.ascii_letters + string.digits + "!@#$%"
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password


def hash_password(password):
    """Hash password using MD5"""
    return hashlib.md5(password.encode()).hexdigest()


# ====================================================
# CREDENTIALS & CLIENT
# ====================================================


def get_credentials():
    """Get Google API credentials"""
    try:
        debug_log("🔐 Getting credentials...")
        
        if CRED_FILE:
            debug_log(f"📁 Using credentials.json")
            with open(CRED_FILE, 'r') as f:
                json.load(f)
            credentials = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, SCOPES)
        else:
            debug_log(f"☁️ Using Streamlit Secrets")
            creds_dict = dict(st.secrets["gcp_service_account"])
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPES)
        
        debug_log("✅ Credentials loaded", "SUCCESS")
        return credentials
    except Exception as e:
        debug_log(f"Credentials error: {str(e)}", "CRITICAL")
        return None


@st.cache_resource
def get_client():
    """Google Sheets client"""
    try:
        debug_log("🔌 Connecting to Google Sheets...")
        credentials = get_credentials()
        if not credentials:
            debug_log("❌ No credentials", "ERROR")
            return None
        
        client = gspread.authorize(credentials)
        debug_log("✅ Client authorized", "SUCCESS")
        return client
    except Exception as e:
        debug_log(f"Client error: {str(e)}", "ERROR")
        return None


# ====================================================
# TEMPLATE CREATION - USING EXTERNAL MODULE
# ====================================================


def create_agency_template(agency_code, agency_name, owner_email=None):
    """Create template using external module"""
    
    if not TEMPLATE_CREATOR_AVAILABLE:
        debug_log("❌ Template creator module not available", "ERROR")
        return {
            'success': False,
            'error': 'Template creator module not found'
        }
    
    st.markdown("---")
    st.markdown("### 🔄 Template Creation Process")
    
    try:
        debug_log(f"🎯 Creating template for {agency_code} - {agency_name}")
        
        with st.spinner("🔄 Creating template from master... Please wait..."):
            result = copy_master_template_for_agency(
                agency_code=agency_code,
                agency_name=agency_name,
                owner_email=owner_email
            )
        
        if result.get('success'):
            debug_log(f"✅ Template created successfully!", "SUCCESS")
            st.success(f"📊 Template created: {result.get('workbook_name')}")
            st.info(f"🔗 URL: {result.get('spreadsheet_url')}")
            
            return {
                'success': True,
                'sheet_id': result.get('spreadsheet_id'),
                'sheet_url': result.get('spreadsheet_url'),
                'workbook_name': result.get('workbook_name'),
                'created_at': result.get('created_at')
            }
        else:
            debug_log(f"❌ Template creation failed: {result.get('error')}", "ERROR")
            return {
                'success': False,
                'error': result.get('error', 'Unknown error')
            }
    
    except Exception as e:
        debug_log(f"❌ Template creation FAILED: {e}", "CRITICAL")
        st.exception(e)
        return {
            'success': False,
            'error': str(e)
        }


# ====================================================
# AGENCY REGISTRATION - ✅ WITH BRANDING SUPPORT
# ====================================================


def register_new_agency(agency_owner, email, mobile, Agency_Name, password, logo_url="", auto_create_template=True):
    """Register new agency with branding support (Agency_Name & Logo_URL)"""
    
    st.markdown("---")
    st.markdown("### 📝 Agency Registration Process")
    
    try:
        debug_log("STEP 1: Getting Google Sheets client")
        client = get_client()
        if not client:
            return {'success': False, 'error': 'Failed to get client'}
        
        debug_log("STEP 2: Opening login_master sheet")
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("login_master")
        
        headers = sheet.row_values(1)
        data = sheet.get_all_records()
        
        debug_log(f"📊 Found {len(data)} existing agencies")
        debug_log(f"📋 Headers found: {headers}")
        
        # Generate agency code
        debug_log("STEP 3: Generating Agency Code")
        max_num = 0
        if data:
            df = pd.DataFrame(data)
            if 'Agency_Code' in df.columns:
                for code in df['Agency_Code']:
                    code = str(code).strip()
                    if code.startswith('AG'):
                        try:
                            num = int(code[2:])
                            if num > max_num:
                                max_num = num
                        except:
                            pass
        
        next_num = max_num + 1
        agency_code = f"AG{next_num:03d}"
        
        st.success(f"🎯 Generated Agency Code: **{agency_code}**")
        debug_log(f"✅ Agency Code: {agency_code}", "SUCCESS")
        
        # Hash password
        debug_log("STEP 4: Hashing password")
        password_hash = hash_password(password)
        st.info(f"🔐 Password hashed successfully")
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        worksheet_url = ''
        
        # Create template using external module
        if auto_create_template:
            if TEMPLATE_CREATOR_AVAILABLE:
                debug_log("STEP 5: Creating template workbook using external module")
                template_result = create_agency_template(agency_code, Agency_Name, email)
                
                if template_result['success']:
                    worksheet_url = template_result['sheet_url']
                    debug_log(f"✅ Template created: {worksheet_url}", "SUCCESS")
                    st.balloons()
                else:
                    debug_log(f"❌ Template creation failed: {template_result.get('error')}", "ERROR")
                    st.error("Template creation failed. You can add worksheet URL manually later.")
            else:
                st.warning("⚠️ Template creator not available. Skipping template creation.")
        
        # ✅ WITH BRANDING: Added Agency_Name and Logo_URL
        debug_log("STEP 6: Preparing data for login_master sheet")
        row_data = {
            'Agency_Code': agency_code,
            'Agency_Owner': agency_owner,
            'Email': email,
            'Mobile': mobile,
            'Agency_Name': Agency_Name,
            'Agency_Name': Agency_Name,  # 🆕 For UI display (can be different from Agency_Name)
            'Logo_URL': logo_url,  # 🆕 Agency logo URL
            'Worksheet_URL': worksheet_url,
            'Password': password_hash,
            'Is_Active': 'Pending' if not worksheet_url else 'Yes',  # ✅ Changed from Status
            'Created_Date': timestamp,
            'Created_By': 'System'
        }
        
        # Build row matching exact header order (dynamic)
        row = []
        for header in headers:
            row.append(row_data.get(header.strip(), ''))
        
        debug_log(f"📝 Row to append: {row}")
        debug_log("STEP 7: Saving to login_master sheet")
        sheet.append_row(row)
        debug_log(f"✅ Agency {agency_code} registered successfully!", "SUCCESS")
        
        return {
            'success': True,
            'agency_code': agency_code,
            'password': password,
            'password_hash': password_hash,
            'worksheet_url': worksheet_url,
            'template_created': bool(worksheet_url)
        }
        
    except Exception as e:
        debug_log(f"❌ Registration failed: {str(e)}", "CRITICAL")
        st.exception(e)
        return {
            'success': False,
            'error': str(e)
        }


# ====================================================
# LOGIN FUNCTIONS - ✅ WITH BRANDING DATA RETRIEVAL
# ====================================================


def verify_in_login_master(username, password, agency_code):
    """
    Verify credentials directly in login_master sheet (For portal_code length == 5)
    ✅ NOW RETURNS: agency_name and logo_url for UI branding
    """
    try:
        debug_log(f"🔍 Checking login_master for {agency_code}")
        
        client = get_client()
        if not client:
            return {'valid': False, 'role': ''}
        
        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
        data = sheet.get_all_records()
        
        if not data:
            debug_log("❌ No data in login_master", "ERROR")
            return {'valid': False, 'role': ''}
        
        df = pd.DataFrame(data)
        
        # ✅ Dynamic column check
        required_cols = ['Agency_Code', 'Agency_Owner', 'Password']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            debug_log(f"❌ Missing columns: {missing}", "ERROR")
            return {'valid': False, 'role': ''}
        
        # Hash password
        password_hash = hash_password(password)
        
        # ✅ Exact column matching
        match = df[
            (df['Agency_Code'].astype(str).str.strip() == agency_code) &
            (df['Agency_Owner'].astype(str).str.strip() == username) &
            (df['Password'].astype(str).str.strip() == password_hash)
        ]
        
        if len(match) == 0:
            debug_log(f"❌ No match found for {agency_code}/{username}", "ERROR")
            return {'valid': False, 'role': ''}
        
        user_data = match.iloc[0]
        
        # ✅ Extract branding info (with fallbacks)
        agency_name = user_data.get('Agency_Name', user_data.get('Agency_Name', 'Placement Agency'))
        logo_url = user_data.get('Logo_URL', '')
        
        result = {
            'valid': True,
            'role': 'admin',
            'full_name': user_data.get('Agency_Owner', username),
            'email': user_data.get('Email', ''),
            'worksheet_url': user_data.get('Worksheet_URL', ''),
            'agency_name': agency_name,  # 🆕 For UI branding
            'logo_url': logo_url  # 🆕 For logo display
        }
        
        debug_log(f"✅ Login successful: {result['full_name']}", "SUCCESS")
        debug_log(f"🎨 Agency: {agency_name}, Logo: {logo_url[:50]}...", "INFO")
        return result
        
    except Exception as e:
        debug_log(f"❌ Verification error: {str(e)}", "ERROR")
        return {'valid': False, 'role': ''}


def get_agency_info(agency_code):
    """
    Get agency details from login_master
    ✅ NOW RETURNS: agency_name and logo_url
    """
    try:
        debug_log(f"🔍 Searching agency: '{agency_code}'")
        
        client = get_client()
        if not client:
            return None
        
        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
        data = sheet.get_all_records()
        
        if not data:
            debug_log("❌ No data in login_master", "ERROR")
            return None
        
        df = pd.DataFrame(data)
        
        # Find Agency_Code column (dynamic/case insensitive)
        agency_col = None
        for col in df.columns:
            if col.lower().strip() == 'agency_code':
                agency_col = col
                break
        
        if not agency_col:
            debug_log("❌ Agency_Code column not found", "ERROR")
            return None
        
        df['_norm'] = df[agency_col].astype(str).str.strip()
        matches = df[df['_norm'] == str(agency_code).strip()]
        
        if len(matches) == 0:
            debug_log(f"❌ Agency '{agency_code}' not found", "ERROR")
            return None
        
        result = matches.iloc[0].to_dict()
        
        # ✅ Add branding info with fallbacks
        if 'Agency_Name' not in result or not result['Agency_Name']:
            result['Agency_Name'] = result.get('Agency_Name', 'Placement Agency')
        if 'Logo_URL' not in result:
            result['Logo_URL'] = ''
        
        debug_log(f"✅ Agency found: {result.get('Agency_Name', 'N/A')}", "SUCCESS")
        return result
        
    except Exception as e:
        debug_log(f"❌ Error: {str(e)}", "ERROR")
        return None


def verify_user_in_agency_sheet(worksheet_url, username, password):
    """Verify user in agency's Users sheet"""
    try:
        debug_log(f"🔍 Verifying user: '{username}' in agency sheet")
        
        client = get_client()
        if not client:
            return {'valid': False, 'role': ''}
        
        sheet_id = worksheet_url.split('/d/')[1].split('/')[0]
        agency_sheet = client.open_by_key(sheet_id)
        
        worksheets = [ws.title for ws in agency_sheet.worksheets()]
        
        if 'Users' not in worksheets:
            debug_log("❌ Users sheet not found", "ERROR")
            return {'valid': False, 'role': ''}
        
        user_sheet = agency_sheet.worksheet("Users")
        data = user_sheet.get_all_records()
        
        if not data:
            debug_log("❌ No users found", "ERROR")
            return {'valid': False, 'role': ''}
        
        df = pd.DataFrame(data)
        
        if 'Username' not in df.columns or 'Password' not in df.columns:
            debug_log("❌ Username/Password columns missing", "ERROR")
            return {'valid': False, 'role': ''}
        
        df['Username'] = df['Username'].astype(str).str.strip()
        df['Password'] = df['Password'].astype(str).str.strip()
        
        clean_username = username.strip()
        password_hash = hash_password(password)
        
        user_row = df[(df['Username'] == clean_username) & (df['Password'] == password_hash)]
        
        if len(user_row) == 0:
            debug_log("❌ Invalid credentials", "ERROR")
            return {'valid': False, 'role': ''}
        
        user_data = user_row.iloc[0]
        result = {
            'valid': True,
            'role': user_data.get('Role', 'user'),
            'full_name': user_data.get('Full_Name', username),
            'email': user_data.get('Email', '')
        }
        
        debug_log(f"✅ User verified: {result['full_name']}", "SUCCESS")
        return result
        
    except Exception as e:
        debug_log(f"❌ Error: {str(e)}", "ERROR")
        return {'valid': False, 'role': ''}


def logout():
    """Logout - Clear all session state"""
    debug_log("🚪 Logging out...", "WARNING")
    
    keys_to_delete = list(st.session_state.keys())
    
    for key in keys_to_delete:
        try:
            del st.session_state[key]
        except:
            pass
    
    debug_log("✅ Session cleared", "SUCCESS")
    st.rerun()


# ====================================================
# UI RENDERING
# ====================================================


def render_login():
    """Login page"""
    
    st.markdown("""
    <style>
    .main-header {
        text-align: center; padding: 3rem 2rem; 
        background: linear-gradient(135deg, #9333ea 0%, #7e22ce 50%, #6b21a8 100%);
        border-radius: 20px; margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(147, 51, 234, 0.3);
    }
    .main-header h1 {color: white; font-size: 3rem; margin: 0; font-weight: 800;}
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='main-header'><h1>🔐 Placement Agency System</h1></div>", unsafe_allow_html=True)
    
    # Login form
    col1, col2 = st.columns([1, 1])
    with col1:
        username = st.text_input("👤 Username", key="login_username")
    with col2:
        password = st.text_input("🔒 Password", type="password", key="login_password")
    
    portal_code = st.text_input("📋 Portal Code (AG001 or AG001CID123)", key="login_portal")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col2:
        if st.button("➕ Register Agency", key="register"):
            st.session_state.show_register = True
            st.rerun()
    
    with col3:
        if st.button("🚀 LOGIN", type="primary", key="login_btn"):
            if not all([username, password, portal_code]):
                st.warning("⚠️ Fill all fields")
            else:
                process_login(username, password, portal_code)
    
    # Register form
    if st.session_state.get('show_register', False):
        st.markdown("---")
        st.subheader("➕ New Agency Registration")
        
        with st.form("new_agency"):
            col1, col2 = st.columns(2)
            with col1:
                owner = st.text_input("Owner Name *")
                email = st.text_input("Email Address *")
            with col2:
                mobile = st.text_input("Mobile Number *")
                company = st.text_input("Company Name *")
            
            # 🆕 Agency Branding (Optional)
            st.markdown("### 🎨 Agency Branding (Optional)")
            logo_url = st.text_input(
                "Logo URL", 
                placeholder="https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                help="Paste image URL from Imgur, Flaticon, UI Avatars, etc."
            )
            
            # Password options
            st.markdown("### 🔐 Password Setup")
            password_option = st.radio(
                "Choose password option:",
                ["Auto-generate secure password", "Set custom password"]
            )
            
            if password_option == "Set custom password":
                custom_password = st.text_input("Enter Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
            else:
                custom_password = None
            
            create_template = st.checkbox(
                "🎯 Auto-create Template Workbook", 
                value=TEMPLATE_CREATOR_AVAILABLE,
                disabled=not TEMPLATE_CREATOR_AVAILABLE,
                help="Create agency workbook from master template" if TEMPLATE_CREATOR_AVAILABLE 
                     else "Template creator module not available"
            )
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Register Agency", type="primary"):
                    if all([owner, email, mobile, company]):
                        # Validate password
                        if password_option == "Set custom password":
                            if not custom_password:
                                st.error("❌ Please enter password")
                                st.stop()
                            if custom_password != confirm_password:
                                st.error("❌ Passwords don't match")
                                st.stop()
                            final_password = custom_password
                        else:
                            final_password = generate_password()
                            st.success(f"🔐 Generated Password: **{final_password}**")
                        
                        # Register with branding
                        with st.spinner("🔄 Registering agency..."):
                            result = register_new_agency(
                                owner, email, mobile, company, 
                                final_password, logo_url, create_template  # 🆕 Added logo_url
                            )
                            
                            if result['success']:
                                st.success(f"✅ Agency Code: **{result['agency_code']}**")
                                st.success(f"🔐 Password: **{result['password']}**")
                                st.warning("⚠️ Save this password! It won't be shown again.")
                                
                                if result.get('template_created'):
                                    st.success(f"✅ Template created: {result['worksheet_url']}")
                                else:
                                    st.info("ℹ️ Template not created. Add manually later.")
                                
                                st.session_state.show_register = False
                            else:
                                st.error(f"❌ Registration failed: {result.get('error')}")
                    else:
                        st.error("❌ All fields required")
            
            with col2:
                if st.form_submit_button("❌ Cancel"):
                    st.session_state.show_register = False
                    st.rerun()


def process_login(username, password, portal_code):
    """
    Process login based on portal code length
    ✅ NOW SAVES: agency_name and logo_url to session state
    """
    
    debug_log(f"🔐 Login attempt: {username} / {portal_code}")
    
    # Case 1: Portal code length == 5 (AG001) - Owner login
    if len(portal_code) == 5:
        debug_log("📋 Portal code length = 5, checking login_master directly")
        
        user_info = verify_in_login_master(username, password, portal_code)
        
        if not user_info['valid']:
            st.error("❌ Invalid credentials in login_master")
            return
        
        # ✅ Save to session with branding info
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.full_name = user_info.get('full_name', username)
        st.session_state.email = user_info.get('email', '')
        st.session_state.agency_code = portal_code
        st.session_state.agency_sheet_url = user_info.get('worksheet_url', '')
        st.session_state.role = 'admin'
        st.session_state.agency_name = user_info.get('agency_name', 'Placement Agency')  # 🆕
        st.session_state.logo_url = user_info.get('logo_url', '')  # 🆕
        
        debug_log(f"🎨 Branding saved: {st.session_state.agency_name}", "SUCCESS")
        st.success(f"✅ Welcome {user_info['full_name']}")
        st.rerun()
    
    # Case 2: Portal code length > 5 (AG001CID123) - Staff/User login
    # Case 2: Portal code length > 5 (AG001CID0001 or AG001CND202510230015)
    elif len(portal_code) > 5:
        debug_log(f"📋 Checking CND/CID for: {portal_code}")
    
    agency_code = portal_code[:5]
    suffix = portal_code[5:8].upper()  # Extract chars 6-8 (CND/CID)
    entity_id = portal_code[8:]        # Rest is ID (0001, 202510230015)
    
    debug_log(f"🔍 Agency: {agency_code}, Suffix: {suffix}, ID: {entity_id}")
    
    # CID → Company Portal
    if suffix == "CID":
        st.session_state.logged_in = True
        st.session_state.redirect_to = "company_portal.py"
        st.session_state.agency_code = agency_code
        st.session_state.company_id = entity_id
        st.session_state.role = "company"
        st.success(f"✅ Redirecting to Company Portal (CID{entity_id})")
        st.rerun()
    
    # CND → Candidate Wizard
    elif suffix == "CND":
        st.session_state.logged_in = True
        st.session_state.redirect_to = "candidates_registration_wizard.py"
        st.session_state.agency_code = agency_code
        st.session_state.candidate_id = entity_id
        st.session_state.role = "candidate"
        st.success(f"✅ Redirecting to Candidate Registration (CND{entity_id})")
        st.rerun()
    
    else:
        st.error("❌ Invalid format! Use: AG001CID0001 or AG001CND202510230015")
        debug_log(f"❌ Invalid suffix: {suffix}", "ERROR")


# ====================================================
# MAIN
# ====================================================


if __name__ == "__main__":
    if "show_register" not in st.session_state:
        st.session_state.show_register = False
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if st.session_state.get("logged_in", False):
        st.markdown("---")
        
        # 🆕 Display logo if available
        if st.session_state.get('logo_url', ''):
            col1, col2 = st.columns([1, 4])
            with col1:
                try:
                    st.image(st.session_state.logo_url, width=100)
                except:
                    st.write("🏢")
            with col2:
                st.success(f"✅ Logged in as: **{st.session_state.get('full_name', 'User')}**")
                st.info(f"🏢 Agency: **{st.session_state.get('agency_name', 'N/A')}**")
        else:
            st.success(f"✅ Logged in as: **{st.session_state.get('full_name', 'User')}**")
            st.info(f"🏢 Agency: **{st.session_state.get('agency_name', 'N/A')}**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Role", st.session_state.get('role', 'N/A'))
        with col2:
            st.metric("Agency Code", st.session_state.get('agency_code', 'N/A'))
        with col3:
            st.metric("Email", st.session_state.get('email', 'N/A'))
        
        st.markdown("---")
        
        with st.expander("🔍 Debug: Session State"):
            st.json({
                'logged_in': st.session_state.get('logged_in'),
                'username': st.session_state.get('username'),
                'full_name': st.session_state.get('full_name'),
                'email': st.session_state.get('email'),
                'agency_code': st.session_state.get('agency_code'),
                'agency_name': st.session_state.get('agency_name'),  # 🆕
                'logo_url': st.session_state.get('logo_url'),  # 🆕
                'agency_sheet_url': st.session_state.get('agency_sheet_url'),
                'role': st.session_state.get('role')
            })
        
        if st.button("🚪 Logout", type="primary", use_container_width=True):
            logout()
    else:
        render_login()