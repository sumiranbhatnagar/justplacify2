"""
TERMS & CONDITIONS MODULE
=========================
Features:
1. Fetch T&C PDF from Google Drive (Terms_Version_master folder)
2. Display T&C in Streamlit
3. Accept/Reject logic
4. Save acceptance to Google Sheets
5. Check if user already accepted current version
"""

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime
import base64
from io import BytesIO
import requests

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

SHEET_ID = "1hXZdwIOatc_oUoX-AzAiBQywe7E4kq9IFUglMcY04_A"
DRIVE_FOLDER_ID = "1M59F_NKkgJKWtFAzh_BC_g11874-rCWK"  # Terms_Version_master folder
CRED_FILE = "credentials.json" if os.path.exists("credentials.json") else None

SCOPES = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

# ═══════════════════════════════════════════════════════════════
# GOOGLE CLIENT & CREDENTIALS
# ═══════════════════════════════════════════════════════════════

def get_credentials():
    """Get Google API credentials"""
    try:
        if CRED_FILE:
            with open(CRED_FILE, 'r') as f:
                json.load(f)
            credentials = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, SCOPES)
        else:
            creds_dict = dict(st.secrets["gcp_service_account"])
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPES)
        return credentials
    except Exception as e:
        st.error(f"❌ Credentials error: {str(e)}")
        return None

@st.cache_resource
def get_sheets_client():
    """Get gspread client for Google Sheets"""
    try:
        credentials = get_credentials()
        if not credentials:
            return None
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"❌ Sheets client error: {str(e)}")
        return None

@st.cache_resource
def get_drive_service():
    """Get Google Drive service"""
    try:
        from googleapiclient.discovery import build
        credentials = get_credentials()
        if not credentials:
            return None
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        st.error(f"❌ Drive service error: {str(e)}")
        return None

# ═══════════════════════════════════════════════════════════════
# GOOGLE DRIVE - FETCH T&C PDFs
# ═══════════════════════════════════════════════════════════════
def get_latest_tc_pdf():
    """Fetch latest version from Terms_Version_Master sheet"""
    try:
        client = get_sheets_client()
        if not client:
            return None, None, None
        
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("Terms_Version_Master")
        
        data = sheet.get_all_records()
        
        if not data:
            st.error("❌ No versions in Terms_Version_Master")
            return None, None, None
        
        # Latest version (last row)
        latest = data[-1]
        
        version = latest.get('Version', 'v1.0.0')
        file_name = latest.get('File_Name', 'TC_v1.0.0.pdf')
        file_id = "1shJN0YEAdLLDJDSUYnlLhFlSYWh32DL2"  # ← यह FILE_ID
        
        st.info(f"📥 Using version: {version} | File: {file_name}")
        
        return file_name, file_id, version
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None, None, None
    
    
def get_pdf_download_link(file_id):
    """Get direct download URL for Google Drive file"""
    return f"https://drive.google.com/uc?export=download&id={file_id}"

def display_pdf_in_streamlit(file_id):
    """Display PDF in Streamlit using embed URL"""
    embed_url = f"https://drive.google.com/file/d/{file_id}/preview"
    st.markdown(f'<iframe src="{embed_url}" width="100%" height="600" frameborder="0"></iframe>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# GOOGLE SHEETS - T&C ACCEPTANCE TRACKING
# ═══════════════════════════════════════════════════════════════

def get_or_create_tc_sheets():
    """
    Ensure Terms_Version_Master and User_T&C_Acceptance sheets exist
    """
    try:
        client = get_sheets_client()
        if not client:
            return False
        
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Check if sheets exist
        sheet_names = [ws.title for ws in spreadsheet.worksheets()]
        
        # Create Terms_Version_Master if not exists
        if "Terms_Version_Master" not in sheet_names:
            ws = spreadsheet.add_worksheet("Terms_Version_Master", rows=100, cols=5)
            ws.append_row([
                "Version", "Effective_Date", "File_Name", "SHA256_Hash", "Notes"
            ])
        
        # Create User_T&C_Acceptance if not exists
        if "User_T&C_Acceptance" not in sheet_names:
            ws = spreadsheet.add_worksheet("User_T&C_Acceptance", rows=1000, cols=7)
            ws.append_row([
                "User_ID", "User_Type", "Accepted_Version", 
                "Acceptance_Date", "Acceptance_Time", "Hash", "IP_Address"
            ])
        
        return True
    
    except Exception as e:
        st.error(f"❌ Sheet creation error: {str(e)}")
        return False

def save_tc_acceptance(user_id, user_type, version):
    """
    Save T&C acceptance to Google Sheets
    user_type: "Agency", "Company", "Candidate"
    """
    try:
        client = get_sheets_client()
        if not client:
            return False
        
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("User_T&C_Acceptance")
        
        now = datetime.now()
        date_str = now.strftime("%d-%m-%Y")
        time_str = now.strftime("%H:%M:%S")
        
        # Generate simple hash (can be improved)
        import hashlib
        hash_val = hashlib.sha256(f"{user_id}{version}{date_str}".encode()).hexdigest()[:16]
        
        row = [
            user_id,
            user_type,
            version,
            date_str,
            time_str,
            hash_val,
            "Web"  # IP address placeholder
        ]
        
        sheet.append_row(row)
        return True
    
    except Exception as e:
        st.error(f"❌ Error saving acceptance: {str(e)}")
        return False

def check_user_accepted_current_tc(user_id, current_version):
    """
    Check if user has already accepted current T&C version
    Returns: (has_accepted, acceptance_date)
    """
    try:
        client = get_sheets_client()
        if not client:
            return False, None
        
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("User_T&C_Acceptance")
        
        data = sheet.get_all_records()
        
        # Find latest acceptance for this user
        user_records = [row for row in data if row.get('User_ID', '').strip() == str(user_id).strip()]
        
        if not user_records:
            return False, None
        
        # Get latest record
        latest = user_records[-1]
        accepted_version = latest.get('Accepted_Version', '').strip()
        acceptance_date = latest.get('Acceptance_Date', '')
        
        # Check if version matches
        if accepted_version == current_version.strip():
            return True, acceptance_date
        
        return False, None
    
    except Exception as e:
        return False, None

def update_login_master_tc_acceptance(agency_code, version):
    """
    Update login_master sheet with T&C acceptance for agency
    """
    try:
        client = get_sheets_client()
        if not client:
            return False
        
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet("login_master")
        
        data = sheet.get_all_records()
        headers = sheet.row_values(1)
        
        # Find agency row
        agency_row_num = None
        for i, row in enumerate(data):
            if row.get('Agency_Code', '').strip() == agency_code.strip():
                agency_row_num = i + 2  # +2 because row 1 is header, i starts from 0
                break
        
        if agency_row_num is None:
            return False
        
        # Get column numbers for T&C fields
        col_version = None
        col_date = None
        col_time = None
        
        for j, header in enumerate(headers):
            if header.strip() == "T&C_Version_Accepted":
                col_version = j + 1
            elif header.strip() == "T&C_Acceptance_Date":
                col_date = j + 1
            elif header.strip() == "T&C_Acceptance_Time":
                col_time = j + 1
        
        # If columns don't exist, we'll skip (can be added manually to sheet)
        if col_version:
            now = datetime.now()
            sheet.update_cell(agency_row_num, col_version, version)
            if col_date:
                sheet.update_cell(agency_row_num, col_date, now.strftime("%d-%m-%Y"))
            if col_time:
                sheet.update_cell(agency_row_num, col_time, now.strftime("%H:%M:%S"))
        
        return True
    
    except Exception as e:
        return False

# ═══════════════════════════════════════════════════════════════
# UI - RENDER T&C PAGE
# ═══════════════════════════════════════════════════════════════

def render_tc_acceptance_page():
    """
    Main T&C Acceptance page
    Shows PDF and Accept/Reject buttons
    """
    
    # Styling
    st.markdown("""
    <style>
        .tc-container {
            background: linear-gradient(135deg, #f0f9ff 0%, #f5f3ff 100%);
            padding: 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            max-width: 900px; 
            margin-left: auto;
            margin-right: auto;
        }
        .tc-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .tc-header h1 {
            color: #1e293b;
            font-size: 2.5rem;
            margin: 0;
        }
        .tc-header p {
            color: #64748b;
            font-size: 1.1rem;
        }
        .tc-pdf-container {
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }
        .tc-buttons {
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin-top: 2rem;
        }
        .tc-checkbox {
            background: #f8fafc;
            border: 2px solid #cbd5e1;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        .version-badge {
            display: inline-block;
            background: #06b6d4;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'tc_accept_checkbox' not in st.session_state:
        st.session_state.tc_accept_checkbox = False
    
    # Fetch latest T&C
    file_name, file_id, version = get_latest_tc_pdf()
    
    if not file_id:
        st.error("❌ Unable to fetch T&C PDF from Google Drive")
        st.info("📌 Please check if Terms_Version_master folder has any PDF files")
        return False
    
    # Header
    #st.markdown("<div class='tc-container'>", unsafe_allow_html=True)
    st.markdown("<div class='tc-container' style='max-width: 900px; margin-left: auto; margin-right: auto;'>", unsafe_allow_html=True)
    st.markdown("<div class='tc-header'>", unsafe_allow_html=True)
    st.markdown("# ⚖️ Terms & Conditions")
    st.markdown(f"<div class='version-badge'>Version {version}</div>", unsafe_allow_html=True)
    st.markdown(f"<p>Please read and accept the Terms & Conditions to proceed</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # PDF Display
    st.markdown("<div class='tc-pdf-container'>", unsafe_allow_html=True)
    st.markdown(f"### 📄 {file_name}")
    
    with st.expander("📖 View Full T&C (Click to expand)", expanded=False):
        try:
            display_pdf_in_streamlit(file_id)
        except:
            # Fallback: Show download link
            download_link = get_pdf_download_link(file_id)
            st.markdown(f"[📥 Download T&C PDF]({download_link})")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Checkbox
    st.markdown("<div class='tc-checkbox'>", unsafe_allow_html=True)
    st.markdown("### ✅ Agreement Required")
    
    accept_checkbox = st.checkbox(
        "✔️ I have read and agree to the Terms & Conditions",
        value=st.session_state.tc_accept_checkbox,
        key="tc_checkbox_main"
    )
    
    st.session_state.tc_accept_checkbox = accept_checkbox
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        st.markdown("<div style='margin-top: 1rem;'>", unsafe_allow_html=True)
        
        if st.button("✅ Accept & Continue", type="primary", use_container_width=True, disabled=not accept_checkbox):
            if accept_checkbox:
                st.session_state.tc_accepted = True
                st.session_state.tc_version = version
                st.session_state.tc_file_id = file_id
                st.success("✅ T&C accepted! Redirecting...")
                st.session_state.page = "login"
                flow = st.session_state.get('tc_flow', 'login')
        
                if flow == "register_company":
                    st.session_state.page = "verify_agency_company"
                elif flow == "register_candidate":
                    st.session_state.page = "verify_agency_candidate"
                elif flow == "register_agency":
                    st.session_state.page = "register_agency"
                else:
                    st.session_state.page = "login"
                import time
                time.sleep(1)
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Note
    st.markdown("""
    ---
    **📌 Important:**
    - You must accept the Terms & Conditions to continue
    - This is a one-time requirement for new registrations
    - Checkbox will unlock the Continue button
    """)
    
    return True

# ═══════════════════════════════════════════════════════════════
# QUICK CHECK - Has user accepted current T&C?
# ═══════════════════════════════════════════════════════════════

def show_tc_update_dialog_if_needed(user_id, user_type="Agency"):
    """
    Check if user has accepted latest T&C
    If not, show modal dialog to accept new version
    """
    try:
        # Get latest T&C version
        _, _, current_version = get_latest_tc_pdf()
        
        if not current_version:
            return True  # No T&C available, proceed
        
        # Check if user accepted this version
        has_accepted, _ = check_user_accepted_current_tc(user_id, current_version)
        
        if has_accepted:
            return True  # User already accepted, proceed
        
        # Show modal dialog
        st.warning(f"⚠️ **New Terms & Conditions Available**")
        st.info(f"Version {current_version} - Please review and accept to continue")
        
        file_name, file_id, version = get_latest_tc_pdf()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📖 View T&C", use_container_width=True):
                with st.expander("T&C Content", expanded=True):
                    try:
                        display_pdf_in_streamlit(file_id)
                    except:
                        download_link = get_pdf_download_link(file_id)
                        st.markdown(f"[📥 Download]({download_link})")
        
        with col2:
            if st.button("✅ Accept New T&C", type="primary", use_container_width=True):
                # Save acceptance
                if save_tc_acceptance(user_id, user_type, current_version):
                    st.success("✅ T&C accepted successfully!")
                    st.rerun()
                else:
                    st.error("❌ Error saving acceptance")
                    return False
        
        return False  # Don't proceed until accepted
    
    except Exception as e:
        st.warning(f"⚠️ Error checking T&C: {str(e)}")
        return True  # Proceed anyway

# ═══════════════════════════════════════════════════════════════
# INIT
# ═══════════════════════════════════════════════════════════════

def init_tc_system():
    """Initialize T&C system - ensure sheets exist"""
    get_or_create_tc_sheets()

if __name__ == "__main__":
    init_tc_system()
    render_tc_acceptance_page()


# ═══════════════════════════════════════════════════════════════
# INTEGRATION POINTS FOR login_master_with_branding.py
# ═══════════════════════════════════════════════════════════════

"""
HOW TO USE IN login_master_with_branding.py:

1. At the top, import this module:
   from terms_conditions_module import (
       render_tc_acceptance_page, 
       save_tc_acceptance,
       check_user_accepted_current_tc,
       show_tc_update_dialog_if_needed,
       get_latest_tc_pdf,
       update_login_master_tc_acceptance,
       init_tc_system
   )

2. In main() function, modify the flow:
   
   if page == "landing":
       # ... existing landing page code ...
       if st.button("Login / Register"):
           st.session_state.page = "accept_tc"  # ← NEW: Go to T&C first
           st.rerun()
   
   elif page == "accept_tc":  # ← NEW PAGE
       render_tc_acceptance_page()
   
   elif page == "login":
       # ... existing login code ...
   
3. After successful login, check if user needs to accept T&C:
   
   if process_login(username, password, portal_code):
       # User logged in successfully
       # Check T&C status
       if not show_tc_update_dialog_if_needed(user_id, user_type):
           return  # Don't show dashboard until T&C accepted
       
       # Show dashboard
       st.success("✅ Login successful")

4. When registering new agency:
   
   if register_new_agency(...):
       # Get latest T&C version
       _, _, version = get_latest_tc_pdf()
       # Save acceptance to Google Sheets
       save_tc_acceptance(agency_code, "Agency", version)
       # Update login_master with acceptance date
       update_login_master_tc_acceptance(agency_code, version)
"""