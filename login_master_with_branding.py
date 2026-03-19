"""
LOGIN_MASTER.PY - WITH AGENCY BRANDING + LANDING PAGE NAVIGATION
=================================================================
✅ NEW FEATURES:
1. Landing page with 4 navigation buttons
2. Agency verification for Company & Candidate registration
3. Session-based page routing
4. Agency branding support (Logo & Name)
5. Complete login system (len=5 and len>5)
6. All original functions preserved
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
from forgot_password import render_forgot_password
from forgot_password import render_secret_question_setup, save_secret_qa_to_sheet
from terms_conditions_module import (
       render_tc_acceptance_page, 
       save_tc_acceptance,
       check_user_accepted_current_tc,
       show_tc_update_dialog_if_needed,
       get_latest_tc_pdf,
       update_login_master_tc_acceptance,
       init_tc_system
   )

# ====================================================
# LANDING PAGE STYLING (Pure Streamlit - No HTML)
# ====================================================
LANDING_PAGE_CSS = """
<style>
/* Modern Landing Page Styles */

/* Card buttons - modern, compact */
.stButton > button {
    width: 100%;
    height: auto !important;
    min-height: 180px !important;
    max-height: 220px !important;
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    padding: 1.5rem 1.2rem !important;
    text-align: left !important;
    transition: all 0.2s ease !important;
    font-size: 0.9rem !important;
    line-height: 1.5 !important;
    white-space: pre-wrap;
    display: flex !important;
    flex-direction: column !important;
    justify-content: flex-start !important;
    align-items: flex-start !important;
    overflow: hidden;
    color: #334155 !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(99, 102, 241, 0.15) !important;
    border-color: #6366F1 !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

/* Icon line */
.stButton > button::first-line {
    font-size: 1.8rem;
    line-height: 2.5rem;
}

/* Card text */
.stButton > button p {
    margin: 0.3rem 0 !important;
}

/* Remove focus outline */
.stButton > button:focus {
    outline: none !important;
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12) !important;
}
</style>
"""

# Import external template creator
try:
    from create_master_template import copy_master_template_for_agency
    TEMPLATE_CREATOR_AVAILABLE = True
except ImportError:
    TEMPLATE_CREATOR_AVAILABLE = False

# ====================================================
# CONFIGURATION
# ====================================================

SHEET_ID = "1hXZdwIOatc_oUoX-AzAiBQywe7E4kq9IFUglMcY04_A"
CRED_FILE = "credentials.json" if os.path.exists("credentials.json") else None

SCOPES = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

# ====================================================
# DEBUG LOGGING
# ====================================================
def debug_log(message, level="INFO"):
    return None

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
# FIXED: check_company_subscription() FUNCTION
# ====================================================
# REPLACE the function starting at line ~210 with this:

def check_company_subscription(company_id, agency_sheet_url):
    """
    Check company subscription from CID sheet in agency worksheet
    Returns: (is_valid, sub_data, message)
    """
    try:
        debug_log(f"📊 Reading CID sheet for: {company_id}")
        
        # ✅ FIX: Get client properly (not using global)
        client = get_client()
        if not client:
            debug_log("❌ Failed to get Google Sheets client", "ERROR")
            return False, {}, "Failed to connect to Google Sheets"
        
        # Extract spreadsheet ID from URL
        sheet_id = agency_sheet_url.split('/d/')[1].split('/')[0]
        
        # Open spreadsheet and get CID sheet
        spreadsheet = client.open_by_key(sheet_id)
        cid_sheet = spreadsheet.worksheet("CID")
        data = cid_sheet.get_all_records()
        
        debug_log(f"📋 CID sheet rows: {len(data)}")
        
        # Find company record
        company_record = None
        for row in data:
            if row.get('CID') == company_id:
                company_record = row
                break
        
        if not company_record:
            debug_log(f"❌ Company not found: {company_id}", "ERROR")
            return False, {}, f"Company {company_id} not found in system"
        
        # Get subscription details
        subscription_status = str(company_record.get('Subscription_Status', '')).strip().upper()
        subscription_end_date = company_record.get('Subscription_End_Date', '')
        plan_type = company_record.get('Plan_Type', 'Standard')
        
        debug_log(f"📊 Status: {subscription_status}, End: {subscription_end_date}")


        if subscription_status != "ACTIVE":
            return False, {}, f"Subscription is {subscription_status}. Please contact your agency to activate."

        # ✅ Date empty hai to error do
        if not subscription_end_date or str(subscription_end_date).strip() == "":
            return False, {}, "Subscription end date not set. Please contact your agency."
        
        # Parse end date
        try:
            if isinstance(subscription_end_date, str):
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                    try:
                        end_date = datetime.strptime(subscription_end_date, fmt).date()
                        break
                    except:
                        continue
                else:
                    raise ValueError("Invalid date format")
            else:
                end_date = subscription_end_date.date() if hasattr(subscription_end_date, 'date') else subscription_end_date
        except Exception as e:
            debug_log(f"❌ Date parse error: {e}", "ERROR")
            return False, {}, f"Invalid subscription end date format: {subscription_end_date}"
        
        today = datetime.now().date()
        days_remaining = (end_date - today).days
        
        debug_log(f"📅 Days remaining: {days_remaining}")
        
        # Prepare subscription data
        sub_data = {
            'Status': subscription_status,
            'End_Date': end_date.strftime('%d-%b-%Y'),
            'days_remaining': days_remaining,
            'Plan_Type': plan_type
        }
        
        # Check status
        if subscription_status != "ACTIVE":
            debug_log(f"❌ Status not ACTIVE: {subscription_status}", "ERROR")
            return False, sub_data, f"Subscription is {subscription_status}. Please contact your agency."
        
        # Check expiry
        if days_remaining < 0:
            debug_log(f"❌ Subscription expired", "ERROR")
            return False, sub_data, f"Subscription expired on {end_date.strftime('%d-%b-%Y')}. Please renew to continue."
        
        # Valid subscription
        success_msg = f"Subscription active until {end_date.strftime('%d-%b-%Y')}"
        
        if days_remaining <= 5:
            success_msg = f"⚠️ Expiring in {days_remaining} days - Renew soon!"
            debug_log(f"⚠️ Expiring soon: {days_remaining} days", "WARNING")
        
        debug_log(f"✅ Subscription valid: {days_remaining} days", "SUCCESS")
        return True, sub_data, success_msg
        
    except Exception as e:
        debug_log(f"❌ Subscription check error: {str(e)}", "ERROR")
        return False, {}, f"Error checking subscription: {str(e)}"


# ====================================================
def show_subscription_alerts(subscription_data):
    """
    Show subscription alerts (expiry warning, etc.)
    """
    if not subscription_data:
        return
    
    days_remaining = subscription_data.get('days_remaining', 0)
    
    # Show warning if expiring in 5 days or less
    if days_remaining <= 5 and days_remaining > 0:
        st.warning(
            f"⚠️ **Subscription Expiring Soon!**\n\n"
            f"Your subscription will expire in **{days_remaining} days** "
            f"({subscription_data.get('End_Date')})\n\n"
            f"Please contact your agency to renew."
        )
    elif days_remaining == 0:
        st.error(
            "🚨 **Subscription Expires Today!**\n\n"
            "Please renew immediately to avoid service interruption."
        )



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
# AGENCY REGISTRATION - WITH BRANDING SUPPORT
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
        
        # WITH BRANDING: Added Agency_Name and Logo_URL
        debug_log("STEP 6: Preparing data for login_master sheet")
        row_data = {
            'Agency_Code': agency_code,
            'Agency_Owner': agency_owner,
            'Email': email,
            'Mobile': mobile,
            'Agency_Name': Agency_Name,
            'Logo_URL': logo_url,
            'Worksheet_URL': worksheet_url,
            'Password': password_hash,
            'Is_Active': 'Pending' if not worksheet_url else 'Yes',
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
# LOGIN FUNCTIONS - WITH BRANDING DATA RETRIEVAL
# ====================================================

def verify_in_login_master(username, password, agency_code):
    """
    Verify credentials directly in login_master sheet (For portal_code length == 5)
    NOW RETURNS: agency_name and logo_url for UI branding
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
        
        # Dynamic column check
        required_cols = ['Agency_Code', 'Agency_Owner', 'Password']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            debug_log(f"❌ Missing columns: {missing}", "ERROR")
            return {'valid': False, 'role': ''}
        
        # Hash password
        password_hash = hash_password(password)
        
        # Exact column matching
        match = df[
            (df['Agency_Code'].astype(str).str.strip() == agency_code) &
            (df['Agency_Owner'].astype(str).str.strip() == username) &
            (df['Password'].astype(str).str.strip() == password_hash)
        ]
        
        if len(match) == 0:
            debug_log(f"❌ No match found for {agency_code}/{username}", "ERROR")
            return {'valid': False, 'role': ''}
        
        user_data = match.iloc[0]
        
        # Extract branding info (with fallbacks)
        agency_name = user_data.get('Agency_Name', 'Placement Agency')
        logo_url = user_data.get('Logo_URL', '')
        
        result = {
            'valid': True,
            'role': 'admin',
            'full_name': user_data.get('Agency_Owner', username),
            'email': user_data.get('Email', ''),
            'worksheet_url': user_data.get('Worksheet_URL', ''),
            'agency_name': agency_name,
            'logo_url': logo_url
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
    NOW RETURNS: agency_name and logo_url
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
        
        # Add branding info with fallbacks
        if 'Agency_Name' not in result or not result['Agency_Name']:
            result['Agency_Name'] = 'Placement Agency'
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
# AGENCY VERIFICATION FOR COMPANY/CANDIDATE
# ====================================================

def render_agency_verification_for_company():
    """Agency verification screen for company registration"""
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <h3 style="margin:0; font-weight:700; color:#0F172A; font-family:'Inter',sans-serif;">Company Registration</h3>
        <p style="margin:4px 0 0; color:#64748B; font-size:14px; font-family:'Inter',sans-serif;">Enter the agency code provided by your placement agency</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        agency_code = st.text_input(
            "Agency Code *",
            max_chars=5,
            placeholder="AG001",
            help="5-character code from your agency",
            key="company_agency_code"
        ).strip()
        
        if st.button("Verify & Continue", type="primary", use_container_width=True):
            if not agency_code or len(agency_code) != 5:
                st.error("❌ Please enter valid 5-character agency code")
            else:
                with st.spinner("🔍 Verifying agency..."):
                    agency_info = get_agency_info(agency_code)
                    
                    if not agency_info:
                        st.error("❌ Invalid agency code")
                        return
                    
                    if agency_info.get('Is_Active') not in ['Yes', 'Active', 'Approved']:
                        st.error("❌ Agency is not active")
                        return
                    
                    if not agency_info.get('Worksheet_URL'):
                        st.error("❌ Agency has no worksheet configured")
                        return
                    
                    # Save to session
                    st.session_state.agency_code = agency_code
                    st.session_state.agency_name = agency_info.get('Agency_Name', 'Unknown')
                    st.session_state.agency_sheet_url = agency_info.get('Worksheet_URL', '')
                    st.session_state.logo_url = agency_info.get('Logo_URL', '')
                    st.session_state.agency_verified = True
                    st.session_state.page = "register_company"
                    st.success("✅ Agency verified! Redirecting...")
                    st.rerun()
    
    st.markdown("---")
    if st.button("Back to Home"):
        st.session_state.page = "landing"
        st.rerun()

def render_agency_verification_for_candidate():
    """Agency verification screen for candidate registration"""
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <h3 style="margin:0; font-weight:700; color:#0F172A; font-family:'Inter',sans-serif;">Candidate Registration</h3>
        <p style="margin:4px 0 0; color:#64748B; font-size:14px; font-family:'Inter',sans-serif;">Enter the agency code provided by your placement agency</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        agency_code = st.text_input(
            "Agency Code *",
            max_chars=5,
            placeholder="AG001",
            help="5-character code from your agency",
            key="candidate_agency_code"
        ).strip()
        
        if st.button("Verify & Continue", type="primary", use_container_width=True):
            if not agency_code or len(agency_code) != 5:
                st.error("❌ Please enter valid 5-character agency code")
            else:
                with st.spinner("🔍 Verifying agency..."):
                    agency_info = get_agency_info(agency_code)
                    
                    if not agency_info:
                        st.error("❌ Invalid agency code")
                        return
                    
                    if agency_info.get('Is_Active') not in ['Yes', 'Active', 'Approved']:
                        st.error("❌ Agency is not active")
                        return
                    
                    if not agency_info.get('Worksheet_URL'):
                        st.error("❌ Agency has no worksheet configured")
                        return
                    
                    # Save to session
                    st.session_state.agency_code = agency_code
                    st.session_state.agency_name = agency_info.get('Agency_Name', 'Unknown')
                    st.session_state.agency_sheet_url = agency_info.get('Worksheet_URL', '')
                    st.session_state.logo_url = agency_info.get('Logo_URL', '')
                    st.session_state.agency_verified = True
                    st.session_state.page = "register_candidate"
                    st.success("✅ Agency verified! Redirecting...")
                    st.rerun()
    
    st.markdown("---")
    if st.button("Back to Home"):
        st.session_state.page = "landing"
        st.rerun()

# ====================================================
# UI RENDERING
# ====================================================

def render_login():
    """Modern login page"""

    st.markdown("""
    <style>
    .login-header {
        text-align: center; padding: 2.5rem 2rem;
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #A78BFA 100%);
        border-radius: 16px; margin-bottom: 2rem;
        max-width: 600px; margin-left: auto; margin-right: auto;
    }
    .login-header h1 {color: white; font-size: 2rem; margin: 0; font-weight: 800; letter-spacing: -0.02em; font-family: 'Inter', sans-serif;}
    .login-header p {color: rgba(255,255,255,0.8); font-size: 0.95rem; margin: 0.5rem 0 0; font-weight: 400; font-family: 'Inter', sans-serif;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='login-header'><h1>Welcome Back</h1><p>Sign in to your Placify account</p></div>", unsafe_allow_html=True)
    
    # Check if in registration mode
    if not st.session_state.get('show_register', False):
        # Show login form centered
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            username = st.text_input("Username", key="login_username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
            portal_code = st.text_input("Portal Code", key="login_portal", placeholder="e.g. AG001 or AG001CID123")

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            if st.button("Sign In", type="primary", key="login_btn", use_container_width=True):
                if not all([username, password, portal_code]):
                    st.warning("Please fill all fields")
                else:
                    process_login(username, password, portal_code)

            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Register New Agency", key="register", use_container_width=True):
                    st.session_state.show_register = True
                    st.rerun()
            with col_b:
                if st.button("Forgot Password?", key="forgot_btn", use_container_width=True):
                    st.session_state.page = "forgot_password"
                    st.rerun()



    
    # Register form (show when show_register = True)
    if st.session_state.get('show_register', False):
        st.markdown("---")
        st.markdown("""
        <div style="margin-bottom:1rem;">
            <h3 style="margin:0; font-weight:700; color:#0F172A; font-family:'Inter',sans-serif;">New Agency Registration</h3>
            <p style="margin:4px 0 0; color:#64748B; font-size:14px; font-family:'Inter',sans-serif;">Fill in the details to create your agency account</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("new_agency"):
            col1, col2 = st.columns(2)
            with col1:
                owner = st.text_input("Owner Name *")
                email = st.text_input("Email Address *")
            with col2:
                mobile = st.text_input("Mobile Number *")
                company = st.text_input("Company Name *")
            
            st.markdown("#### Agency Branding (Optional)")
            
            logo_option = st.radio(
                "Logo Option:",
                ["Use Online URL", "Upload Local Image"],
                horizontal=True
            )
            
            if logo_option == "Use Online URL":
                logo_url = st.text_input(
                    "Logo URL", 
                    placeholder="https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                    help="Paste image URL from Imgur, Flaticon, UI Avatars, etc."
                )
            else:
                uploaded_logo = st.file_uploader(
                    "Upload Logo (PNG/JPG/SVG)",
                    type=['png', 'jpg', 'jpeg', 'svg'],
                    help="File will be converted to online URL using ImgBB"
                )
                
                if uploaded_logo:
                    st.image(uploaded_logo, width=150, caption="Preview")
                    logo_url = f"data:image/{uploaded_logo.type.split('/')[-1]};base64,{uploaded_logo.getvalue().hex()}"
                    st.info("📌 Logo will be saved (online hosting coming soon)")
                else:
                    logo_url = ""
            st.markdown("#### Security Question")
            secret_question, secret_answer = render_secret_question_setup(key_prefix="agency_reg")


            st.markdown("#### Password Setup")
            st.info("A secure password will be auto-generated for you")
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Register Agency", type="primary"):
                    if all([owner, email, mobile, company]):
                        # Always auto-generate password
                        final_password = generate_password()
                        st.success(f"🔐 Generated Password: **{final_password}**")
                        
                        with st.spinner("🔄 Registering agency..."):
                            result = register_new_agency(
                                owner, email, mobile, company, 
                                final_password, logo_url, False  # Template creation disabled
                            )
                            
                            if result['success']:
                                st.success(f"✅ Agency Code: **{result['agency_code']}**")
                                st.success(f"🔐 Password: **{final_password}**")
                                st.warning("⚠️ Save this password! It won't be shown again.")
                                st.balloons()
                                
                                # Secret Q&A save करो
                                if secret_question and secret_answer and secret_question != "-- Select a Question --":
                                    try:
                                        client = get_client()
                                        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
                                        all_data = sheet.get_all_values()
                                        headers = all_data[0]
                                        row_num = len(all_data)  # Last row (newly added agency)
                                        save_secret_qa_to_sheet(
                                            sheet, row_num, headers,
                                            secret_question, secret_answer
                                        )
                                        st.success("✅ Security Question saved!")
                                    except Exception as e:
                                        st.warning(f"⚠️ Security question save failed: {str(e)}")
                                else:
                                    st.warning("⚠️ Security question not set — password reset नहीं होगा!")
                                
                                st.session_state.show_register = False

                            else:
                                st.error(f"❌ Registration failed: {result.get('error')}")
                    else:
                        st.error("❌ All fields required")
                                        
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.show_register = False
                    st.rerun()
    
    # Back to landing button
    st.markdown("---")
    if st.button("Back to Home"):
        st.session_state.page = "landing"
        st.session_state.show_register = False
        st.rerun()

def process_login(username, password, portal_code):
    """
    Process login based on portal code length
    NOW SAVES: agency_name and logo_url to session state
    """
    
    debug_log(f"🔐 Login attempt: {username} / {portal_code}")
    
    # Case 1: Portal code length == 5 (AG001) - Owner login
    if len(portal_code) == 5:
        debug_log("📋 Portal code length = 5, checking login_master directly")
        
        user_info = verify_in_login_master(username, password, portal_code)
        
        if not user_info['valid']:
            st.error("❌ Invalid credentials in login_master")
            return
        
        # Save to session with branding info
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.full_name = user_info.get('full_name', username)
        st.session_state.email = user_info.get('email', '')
        st.session_state.agency_code = portal_code
        st.session_state.agency_sheet_url = user_info.get('worksheet_url', '')
        st.session_state.role = 'admin'
        st.session_state.agency_name = user_info.get('agency_name', 'Placement Agency')
        st.session_state.logo_url = user_info.get('logo_url', '')
        
        debug_log(f"🎨 Branding saved: {st.session_state.agency_name}", "SUCCESS")
        st.success(f"✅ Welcome {user_info['full_name']}")
        st.rerun()
    
    # Case 2: Portal code length > 5 (AG001CID0001 or AG001CND202510230015)
    elif len(portal_code) > 5:
        debug_log(f"📋 Checking CND/CID for: {portal_code}")
        
        agency_code = portal_code[:5]
        suffix = portal_code[5:8].upper()
        entity_id = portal_code[8:]
        
        debug_log(f"🔍 Agency: {agency_code}, Suffix: {suffix}, ID: {entity_id}")
        
        
        # CID → Company Portal
        # ====================================================
        if suffix == "CID":
            # Get agency info from login_master
            debug_log(f"🔍 Getting agency info for: {agency_code}")
            agency_info = get_agency_info(agency_code)
            
            if not agency_info:
                st.error(f"❌ Agency {agency_code} not found in login_master")
                debug_log(f"❌ Agency {agency_code} not found", "ERROR")
                return
            
            agency_sheet_url = agency_info.get('Worksheet_URL', '')
            
            if not agency_sheet_url:
                st.error(f"❌ No worksheet URL found for agency {agency_code}")
                debug_log(f"❌ No worksheet URL for {agency_code}", "ERROR")
                return
            
            # ========================================
            # NEW: CHECK SUBSCRIPTION STATUS
            # ========================================
            debug_log(f"🔍 Checking subscription for: {portal_code}")
            
            with st.spinner("🔍 Verifying subscription..."):
                is_valid, sub_data, message = check_company_subscription(portal_code, agency_sheet_url)
            
            debug_log(f"📊 Subscription check: {message}", "INFO" if is_valid else "WARNING")
            
            if not is_valid:
                # Subscription expired or not found
                st.error(f"❌ Subscription Error: {message}")
                st.warning(
                    f"📞 **Contact Your Agency**\n\n"
                    f"Agency: {agency_info.get('Agency_Name', 'N/A')}\n\n"
                    f"Please renew your subscription to continue using the portal."
                )
                st.info("💡 After renewal, you can login immediately.")
                debug_log(f"❌ Subscription invalid: {message}", "ERROR")
                return
            
            debug_log(f"✅ Subscription valid: {message}", "SUCCESS")
            # ========================================
            # END SUBSCRIPTION CHECK
            # ========================================
            
            # Save to session state
            st.session_state.logged_in = True
            st.session_state.redirect_to = "company_portal.py"
            st.session_state.agency_code = agency_code
            st.session_state.company_id = portal_code  # ✅ FULL CODE: AG002CID0118
            st.session_state.agency_sheet_url = agency_sheet_url  # ✅ Sheet URL
            st.session_state.full_name = username  # Company name
            st.session_state.agency_name = agency_info.get('Agency_Name', 'Placement Agency')
            st.session_state.logo_url = agency_info.get('Logo_URL', '')
            st.session_state.role = "company"
            
            # Store subscription info in session
            st.session_state.subscription_end = sub_data.get('End_Date', '')
            st.session_state.days_remaining = sub_data.get('days_remaining', 0)
            st.session_state.plan_type = sub_data.get('Plan_Type', 'N/A')
            
            debug_log(f"✅ Company login successful", "SUCCESS")
            debug_log(f"📋 Company ID: {portal_code}", "INFO")
            debug_log(f"📊 Sheet URL: {agency_sheet_url[:50]}...", "INFO")
            debug_log(f"📅 Subscription: {sub_data.get('Plan_Type')} - {sub_data.get('days_remaining')} days left", "INFO")
            
            # Show subscription alerts if expiring soon
            show_subscription_alerts(sub_data)
            
            st.success(f"✅ Redirecting to Company Portal ({portal_code})")
            
            # Small delay to show alert if present
            if sub_data.get('days_remaining', 999) <= 5:
                import time
                time.sleep(3)
            
            st.rerun()            
            # CND → Candidate Wizard
        elif suffix == "CND":
        # Agency info lo
            agency_info = get_agency_info(agency_code)
            
            if not agency_info:
                st.error(f"❌ Agency {agency_code} not found")
                return
            
            agency_sheet_url = agency_info.get('Worksheet_URL', '')
            if not agency_sheet_url:
                st.error("❌ Agency sheet not configured")
                return
            
            with st.spinner("🔍 Verifying..."):
                try:
                    client = get_client()
                    sheet_id = agency_sheet_url.split('/d/')[1].split('/')[0]
                    sheet = client.open_by_key(sheet_id).worksheet("Candidates")
                    data = sheet.get_all_records()
                    df = pd.DataFrame(data)
                    
                    # Full candidate ID banao
                    full_candidate_id = portal_code  
                    
                    # Password hash karo
                    password_hash = hash_password(password)
                    
                    # Match karo
                    match = df[
                        (df['Candidate ID'].astype(str).str.strip() == full_candidate_id) &
                        (df['Password'].astype(str).str.strip() == password_hash)
                    ]
                    
                    if len(match) == 0:
                        st.error("❌ Invalid Candidate ID or Password")
                        return
                    
                    candidate_data = match.iloc[0]
                    
                    # Session save karo
                    st.session_state.logged_in = True
                    st.session_state.role = "candidate"
                    st.session_state.agency_code = agency_code
                    st.session_state.agency_sheet_url = agency_sheet_url
                    st.session_state.agency_name = agency_info.get('Agency_Name', '')
                    st.session_state.logo_url = agency_info.get('Logo_URL', '')
                    st.session_state.candidate_id = full_candidate_id
                    st.session_state.full_name = candidate_data.get('Full Name', username)
                    st.session_state.email = candidate_data.get('Email', '')
                    
                    st.success(f"✅ Welcome {candidate_data.get('Full Name', '')}!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    return
            
    else:
        st.error("❌ Invalid format! Use: AG001CID0001 or AG001CND202510230015")
        debug_log(f"❌ Invalid suffix: {suffix}", "ERROR")


# ====================================================
# MAIN FUNCTION (Called by app.py or run directly)
# ====================================================

def main():
    """
    Main function - handles landing page, login, and registration flows
    Returns "ROUTE_TO_APP" when user successfully logs in as agency admin
    Returns None for all other cases (landing/login/registration pages)
    """
    init_tc_system()
    # Initialize session state
    if "page" not in st.session_state:
        st.session_state.page = "landing"
    if "show_register" not in st.session_state:
        st.session_state.show_register = False
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "tc_accepted" not in st.session_state:
        st.session_state.tc_accepted = False
    if "tc_version" not in st.session_state:
        st.session_state.tc_version = None

    # Check if logged in
    if st.session_state.get("logged_in", False):
        # User is logged in - show basic info and route to app.py
        #Check if user needs to accept new T&C version
        user_id = st.session_state.get('agency_code', '')
        user_type = st.session_state.get('role', 'Agency')
        
        # Show T&C update dialog if needed
        tc_accepted = show_tc_update_dialog_if_needed(user_id, user_type)
        
        if not tc_accepted:
            # Don't show dashboard until T&C accepted
            return


        st.markdown("---")

        # Display logo if available
        if st.session_state.get('logo_url', ''):
            col1, col2 = st.columns([1, 4])
            with col1:
                try:
                    st.image(st.session_state.logo_url, width=80)
                except:
                    pass
            with col2:
                st.success(f"Logged in as: **{st.session_state.get('full_name', 'User')}**")
                st.info(f"Agency: **{st.session_state.get('agency_name', 'N/A')}**")
        else:
            st.success(f"Logged in as: **{st.session_state.get('full_name', 'User')}**")
            st.info(f"Agency: **{st.session_state.get('agency_name', 'N/A')}**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Role", st.session_state.get('role', 'N/A'))
        with col2:
            st.metric("Agency Code", st.session_state.get('agency_code', 'N/A'))
        with col3:
            st.metric("Email", st.session_state.get('email', 'N/A'))
        
        st.markdown("---")
        
        # with st.expander("🔍 Debug: Session State"):
        #     st.json({
        #         'logged_in': st.session_state.get('logged_in'),
        #         'username': st.session_state.get('username'),
        #         'full_name': st.session_state.get('full_name'),
        #         'email': st.session_state.get('email'),
        #         'agency_code': st.session_state.get('agency_code'),
        #         'agency_name': st.session_state.get('agency_name'),
        #         'logo_url': st.session_state.get('logo_url'),
        #         'agency_sheet_url': st.session_state.get('agency_sheet_url'),
        #         'role': st.session_state.get('role')
        #     })
        
        if st.button("Logout", type="primary", use_container_width=True):
            logout()
        
        # Return signal to app.py to show agency dashboard
        return "ROUTE_TO_APP"
    
    else:
        # Not logged in - show landing/login/registration pages
        page = st.session_state.page
        
        if page == "landing":
            # Apply landing page CSS
            st.markdown(LANDING_PAGE_CSS, unsafe_allow_html=True)

            # Modern hero section
            st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #A78BFA 100%);
                    padding: 3rem 2rem;
                    border-radius: 16px;
                    color: white;
                    text-align: center;
                    margin-bottom: 2rem;
                    max-width: 900px;
                    margin-left: auto;
                    margin-right: auto;
                    position: relative;
                    overflow: hidden;
                    font-family: 'Inter', sans-serif;
                ">
                    <div style="position:relative; z-index:1;">
                        <h1 style="font-size: 2.8rem; margin: 0 0 0.5rem 0; font-weight: 800; letter-spacing: -0.03em; color: white;">
                            PLACIFY
                        </h1>
                        <p style="font-size: 1.1rem; margin-bottom: 1.5rem; opacity: 0.9; color: rgba(255,255,255,0.9); font-weight: 400;">
                            Hire Talent, Build Futures - One Placement at a Time
                        </p>
                        <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 1.5rem; font-size: 0.9rem;">
                            <div style="background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 8px; backdrop-filter: blur(10px);">
                                <span style="font-weight: 700; color: white;">Agencies</span>
                            </div>
                            <div style="background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 8px; backdrop-filter: blur(10px);">
                                <span style="font-weight: 700; color: white;">Companies</span>
                            </div>
                            <div style="background: rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 8px; backdrop-filter: blur(10px);">
                                <span style="font-weight: 700; color: white;">Applicants</span>
                            </div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Modern card buttons
            col_left, col_center, col_right = st.columns([0.4, 1, 0.4])

            with col_center:
                col1, col2, col3, col4 = st.columns(4)
            
                with col1:
                    if st.button(
                        "🏢\n**Register Agency**\n\nGet your branded dashboard with candidate management & auto-reports.",
                        key="card_agency",
                        use_container_width=True
                    ):
                        st.session_state.page = "accept_tc"
                        st.session_state.tc_flow = "register_agency"

                        st.rerun()
                
                with col2:
                    if st.button(
                        "🔑\n**Login**\n\nAccess your dashboard with your Portal Code.",
                        key="card_login",
                        use_container_width=True
                    ):
                        st.session_state.page = "accept_tc"
                        st.session_state.tc_flow = "login"

                        st.rerun()
                
                with col3:
                    if st.button(
                        "🏭\n**Register Company**\n\nPost jobs, manage interviews, track candidates.",
                        key="card_company",
                        use_container_width=True
                    ):
                        st.session_state.page = "accept_tc"
                        st.session_state.tc_flow = "register_company"

                        st.rerun()
                
                with col4:
                    if st.button(
                        "👤\n**Register as Applicant**\n\nApply to jobs and get interview calls.",
                        key="card_applicant",
                        use_container_width=True
                    ):
                        st.session_state.page = "accept_tc"
                        st.session_state.tc_flow = "register_candidate"
                        st.rerun()
        # ═════════════════════════════════════════════
        # T&C ACCEPTANCE PAGE (NEW)
        # ═════════════════════════════════════════════
        elif page == "accept_tc":
            render_tc_acceptance_page()
                # T&C accept होने के बाद
            if st.session_state.tc_accepted:
                # tc_flow के according redirect करो
                flow = st.session_state.get('tc_flow', 'landing')
                
                if flow == "register_company":
                    st.session_state.page = "verify_agency_company"
                elif flow == "register_candidate":
                    st.session_state.page = "verify_agency_candidate"
                elif flow == "register_agency":
                    st.session_state.page = "register_agency"
                elif flow == "login":
                    st.session_state.page = "login"
                
                st.rerun()

            
            # Button to go back to landing
            if st.button("Back to Home"):
                st.session_state.page = "landing"
                st.session_state.tc_accepted = False
                st.rerun()
            
        
        elif page == "login":
            render_login()
        elif page == "forgot_password":
            render_forgot_password()    
        
        elif page == "register_agency":
            st.session_state.show_register = True
            render_login()
        
        elif page == "verify_agency_company":
            render_agency_verification_for_company()
        
        elif page == "verify_agency_candidate":
            render_agency_verification_for_candidate()
        
        elif page == "register_company":
            from company_portal import company_registration_page
            company_registration_page()
            #st.info(f"✅ Agency verified: {st.session_state.get('agency_name')}")
            #st.info(f"📊 Sheet URL: {st.session_state.get('agency_sheet_url')}")
            if st.button("Back to Home"):
                st.session_state.page = "landing"
                st.session_state.agency_verified = False
                st.rerun()
        
        elif page == "register_candidate":
            from candidate_wizard_module import candidate_registration_page
            candidate_registration_page()
            if st.button("Back to Home"):
                st.session_state.page = "landing"
                st.session_state.agency_verified = False
                st.rerun()
                        
        return None


if __name__ == "__main__":
    # Allow direct run for testing
    main()
