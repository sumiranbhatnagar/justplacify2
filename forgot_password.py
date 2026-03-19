"""
FORGOT_PASSWORD.PY - UNIVERSAL PASSWORD RESET MODULE
=====================================================
✅ Works for ALL 3 user types:
   - Agency Owner (AG001) → login_master sheet
   - Company User (CID)   → CID sheet in agency worksheet
   - Candidate (CND)      → Candidates sheet in agency worksheet

✅ Flow:
   1. Select User Type
   2. Enter Portal Code / CID / Candidate ID
   3. Secret Question shown
   4. Answer verified
   5. New Password set

✅ HOW TO USE IN OTHER FILES:
   from forgot_password import render_forgot_password

   # In login page:
   if st.button("🔑 Forgot Password?"):
       st.session_state.page = "forgot_password"

   # In page router:
   elif page == "forgot_password":
       render_forgot_password()
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import hashlib
import os
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
MAIN_SHEET_ID = "1hXZdwIOatc_oUoX-AzAiBQywe7E4kq9IFUglMcY04_A"
CRED_FILE = "credentials.json" if os.path.exists("credentials.json") else None
SCOPES = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

# Secret Questions List
SECRET_QUESTIONS = [
    "-- Select a Question --",
    "आपकी माँ का maiden name क्या है?",
    "आपका पहला school कौन सा था?",
    "आपका पहला pet का नाम क्या था?",
    "आपके best friend का नाम क्या है?",
    "आपकी पहली car/bike कौन सी थी?",
    "आप किस city में पैदा हुए?",
    "आपका favorite teacher का नाम क्या था?",
    "आपके childhood का nickname क्या था?",
]


# ─────────────────────────────────────────────
# GOOGLE SHEETS CLIENT
# ─────────────────────────────────────────────
@st.cache_resource
def get_fp_client():
    """Get Google Sheets client for forgot password module"""
    try:
        if CRED_FILE:
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                CRED_FILE, SCOPES)
        else:
            creds_dict = dict(st.secrets["gcp_service_account"])
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                creds_dict, SCOPES)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"❌ Connection Error: {str(e)}")
        return None


# ─────────────────────────────────────────────
# PASSWORD HELPERS
# ─────────────────────────────────────────────
def hash_md5(text):
    """MD5 hash — used by login_master & candidates"""
    return hashlib.md5(text.encode()).hexdigest()

def hash_sha256(text):
    """SHA256 hash — used by company_portal"""
    return hashlib.sha256(text.encode()).hexdigest()

def normalize_answer(answer):
    """Normalize secret answer — lowercase, strip spaces"""
    return str(answer).strip().lower()


# ─────────────────────────────────────────────
# SHEET HELPERS
# ─────────────────────────────────────────────
def get_agency_sheet_id_from_code(agency_code):
    """Get agency worksheet URL/ID from login_master using agency code"""
    try:
        client = get_fp_client()
        if not client:
            return None
        sheet = client.open_by_key(MAIN_SHEET_ID).worksheet("login_master")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        match = df[df['Agency_Code'].astype(str).str.strip() == str(agency_code).strip()]
        if match.empty:
            return None
        worksheet_url = match.iloc[0].get('Worksheet_URL', '')
        if not worksheet_url:
            return None
        return worksheet_url.split('/d/')[1].split('/')[0]
    except Exception as e:
        st.error(f"❌ Error getting agency sheet: {str(e)}")
        return None


def get_col_letter(n):
    """Convert column number to Excel-style letter"""
    result = ""
    while n > 0:
        n -= 1
        result = chr(65 + n % 26) + result
        n //= 26
    return result


# ─────────────────────────────────────────────
# CORE: FIND USER & VERIFY SECRET ANSWER
# ─────────────────────────────────────────────
def find_agency_owner(agency_code):
    """
    Find agency owner in login_master
    Returns: (row_num, row_data, sheet_obj) or (None, None, None)
    """
    try:
        client = get_fp_client()
        if not client:
            return None, None, None
        sheet = client.open_by_key(MAIN_SHEET_ID).worksheet("login_master")
        all_data = sheet.get_all_values()
        headers = all_data[0]
        for idx, row in enumerate(all_data[1:], start=2):
            if len(row) > 0:
                row_dict = dict(zip(headers, row))
                if row_dict.get('Agency_Code', '').strip() == agency_code.strip():
                    return idx, row_dict, sheet
        return None, None, None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None, None, None


def find_company_user(cid_code):
    """
    Find company in CID sheet of agency worksheet
    CID format: AG001CID0001 → agency_code = AG001
    Returns: (row_num, row_data, sheet_obj) or (None, None, None)
    """
    try:
        # Extract agency code from CID
        if 'CID' not in cid_code:
            st.error("❌ Invalid CID format. Expected: AG001CID0001")
            return None, None, None

        agency_code = cid_code.split('CID')[0]
        agency_sheet_id = get_agency_sheet_id_from_code(agency_code)

        if not agency_sheet_id:
            st.error(f"❌ Agency {agency_code} not found or no worksheet")
            return None, None, None

        client = get_fp_client()
        if not client:
            return None, None, None

        sheet = client.open_by_key(agency_sheet_id).worksheet("CID")
        all_data = sheet.get_all_values()
        headers = all_data[0]

        for idx, row in enumerate(all_data[1:], start=2):
            if len(row) > 0:
                row_dict = dict(zip(headers, row))
                if row_dict.get('CID', '').strip() == cid_code.strip():
                    return idx, row_dict, sheet

        return None, None, None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None, None, None


def find_candidate(candidate_id):
    """
    Find candidate in Candidates sheet
    Candidate ID format: AG001CND202510230015 → agency_code = AG001
    Returns: (row_num, row_data, sheet_obj) or (None, None, None)
    """
    try:
        if 'CND' not in candidate_id:
            st.error("❌ Invalid Candidate ID format. Expected: AG001CND...")
            return None, None, None

        agency_code = candidate_id.split('CND')[0]
        agency_sheet_id = get_agency_sheet_id_from_code(agency_code)

        if not agency_sheet_id:
            st.error(f"❌ Agency {agency_code} not found or no worksheet")
            return None, None, None

        client = get_fp_client()
        if not client:
            return None, None, None

        sheet = client.open_by_key(agency_sheet_id).worksheet("Candidates")
        all_data = sheet.get_all_values()
        headers = all_data[0]

        for idx, row in enumerate(all_data[1:], start=2):
            if len(row) > 0:
                row_dict = dict(zip(headers, row))
                if row_dict.get('Candidate ID', '').strip() == candidate_id.strip():
                    return idx, row_dict, sheet

        return None, None, None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None, None, None


def verify_secret_answer(stored_answer, provided_answer):
    """Verify secret answer (case-insensitive, trimmed)"""
    return normalize_answer(stored_answer) == normalize_answer(provided_answer)


def update_password_in_sheet(sheet, row_num, headers, new_password, user_type):
    """
    Update password in sheet
    - Agency Owner & Candidate → MD5
    - Company → SHA256 (as per company_portal.py)
    """
    try:
        if 'Password' not in headers:
            return False, "Password column not found in sheet"

        # Hash based on user type
        if user_type in ["agency", "candidate"]:
            hashed = hash_md5(new_password)
        else:  # company
            hashed = hash_sha256(new_password)

        pwd_col_idx = headers.index('Password') + 1
        pwd_col_letter = get_col_letter(pwd_col_idx)
        sheet.update(f"{pwd_col_letter}{row_num}", hashed)
        return True, "Password updated successfully"
    except Exception as e:
        return False, f"Error updating password: {str(e)}"


# ─────────────────────────────────────────────
# SETUP: Save Secret Q&A during Registration
# ─────────────────────────────────────────────
def render_secret_question_setup(key_prefix="setup"):
    """
    Render Secret Q&A fields for Registration forms
    Call this in registration forms to collect secret question/answer

    Returns: (selected_question, answer) tuple
    Usage:
        question, answer = render_secret_question_setup(key_prefix="agency_reg")
        # Then save question & answer to sheet during registration
    """
    st.markdown("#### 🔐 Security Question (Forgot Password के लिए)")
    st.caption("यह password reset करने के लिए काम आएगा")

    question = st.selectbox(
        "Security Question चुनें *",
        SECRET_QUESTIONS,
        key=f"{key_prefix}_question"
    )

    answer = st.text_input(
        "Answer *",
        placeholder="आपका answer (याद रखें!)",
        key=f"{key_prefix}_answer"
    )

    return question, answer


# ─────────────────────────────────────────────
# MAIN: FORGOT PASSWORD UI
# ─────────────────────────────────────────────
def render_forgot_password():
    """
    Main Forgot Password UI
    Call this from your page router:
        elif page == "forgot_password":
            render_forgot_password()
    """

    st.markdown("""
    <style>
    .fp-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem; border-radius: 15px; color: white;
        text-align: center; margin-bottom: 1.5rem;
    }
    .fp-step {
        background: white; padding: 1rem 1.5rem; border-radius: 10px;
        border-left: 4px solid #667eea; margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="fp-header"><h2>🔑 Forgot Password</h2>'
                '<p>Secret Question से password reset करें</p></div>',
                unsafe_allow_html=True)

    # Initialize session state for forgot password flow
    if 'fp_step' not in st.session_state:
        st.session_state.fp_step = 1
    if 'fp_user_type' not in st.session_state:
        st.session_state.fp_user_type = None
    if 'fp_user_id' not in st.session_state:
        st.session_state.fp_user_id = None
    if 'fp_row_num' not in st.session_state:
        st.session_state.fp_row_num = None
    if 'fp_sheet' not in st.session_state:
        st.session_state.fp_sheet = None
    if 'fp_headers' not in st.session_state:
        st.session_state.fp_headers = None
    if 'fp_question' not in st.session_state:
        st.session_state.fp_question = None

    # Progress indicator
    steps = ["1️⃣ User Type", "2️⃣ Enter ID", "3️⃣ Secret Answer", "4️⃣ New Password"]
    step = st.session_state.fp_step

    cols = st.columns(4)
    for i, (col, label) in enumerate(zip(cols, steps), start=1):
        with col:
            if i < step:
                st.success(label)
            elif i == step:
                st.info(f"**{label}** ◀")
            else:
                st.caption(label)

    st.divider()

    # ── STEP 1: Select User Type ──────────────────
    if step == 1:
        st.markdown('<div class="fp-step"><b>Step 1:</b> आप कौन हैं?</div>',
                    unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🏢 Agency Owner\n(AG001)",
                         use_container_width=True, key="fp_type_agency"):
                st.session_state.fp_user_type = "agency"
                st.session_state.fp_step = 2
                st.rerun()

        with col2:
            if st.button("🏭 Company User\n(AG001CID0001)",
                         use_container_width=True, key="fp_type_company"):
                st.session_state.fp_user_type = "company"
                st.session_state.fp_step = 2
                st.rerun()

        with col3:
            if st.button("👨‍💼 Candidate\n(AG001CND...)",
                         use_container_width=True, key="fp_type_candidate"):
                st.session_state.fp_user_type = "candidate"
                st.session_state.fp_step = 2
                st.rerun()

    # ── STEP 2: Enter ID ──────────────────────────
    elif step == 2:
        user_type = st.session_state.fp_user_type

        type_labels = {
            "agency": ("🏢 Agency Owner", "Agency Code", "AG001", 5),
            "company": ("🏭 Company User", "Company Portal Code", "AG001CID0001", None),
            "candidate": ("👨‍💼 Candidate", "Candidate ID", "AG001CND202510230015", None),
        }

        label, id_label, placeholder, max_chars = type_labels[user_type]

        st.markdown(f'<div class="fp-step"><b>Step 2:</b> {label} — अपना ID डालें</div>',
                    unsafe_allow_html=True)

        user_id = st.text_input(
            f"{id_label} *",
            placeholder=placeholder,
            max_chars=max_chars,
            key="fp_user_id_input"
        ).strip()

        col1, col2 = st.columns(2)

        with col1:
            if st.button("⬅️ Back", key="fp_back_1"):
                st.session_state.fp_step = 1
                st.session_state.fp_user_type = None
                st.rerun()

        with col2:
            if st.button("🔍 Find My Account", type="primary",
                         use_container_width=True, key="fp_find"):
                if not user_id:
                    st.error("❌ Please enter your ID")
                else:
                    with st.spinner("🔍 Searching..."):
                        # Find user based on type
                        if user_type == "agency":
                            row_num, row_data, sheet = find_agency_owner(user_id)
                        elif user_type == "company":
                            row_num, row_data, sheet = find_company_user(user_id)
                        else:
                            row_num, row_data, sheet = find_candidate(user_id)

                    if not row_num:
                        st.error(f"❌ ID not found: {user_id}")
                    else:
                        # Check if secret question is set
                        question = row_data.get('Secret_Question', '').strip()

                        if not question or question == "-- Select a Question --":
                            st.error("❌ Security question not set for this account!")
                            st.warning("📞 Please contact your agency/admin to reset password manually.")
                        else:
                            # Save to session
                            st.session_state.fp_user_id = user_id
                            st.session_state.fp_row_num = row_num
                            st.session_state.fp_sheet = sheet
                            st.session_state.fp_headers = list(row_data.keys())
                            st.session_state.fp_question = question
                            st.session_state.fp_stored_answer = row_data.get('Secret_Answer', '')
                            st.session_state.fp_step = 3
                            st.rerun()

    # ── STEP 3: Secret Answer ─────────────────────
    elif step == 3:
        st.markdown('<div class="fp-step"><b>Step 3:</b> Security Question का Answer दें</div>',
                    unsafe_allow_html=True)

        st.info(f"**🔐 Your Question:** {st.session_state.fp_question}")
        st.caption(f"Account: **{st.session_state.fp_user_id}**")

        answer = st.text_input(
            "Your Answer *",
            placeholder="Answer यहाँ डालें",
            key="fp_answer_input"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("⬅️ Back", key="fp_back_2"):
                st.session_state.fp_step = 2
                st.session_state.fp_question = None
                st.rerun()

        with col2:
            if st.button("✅ Verify Answer", type="primary",
                         use_container_width=True, key="fp_verify"):
                if not answer:
                    st.error("❌ Please enter your answer")
                else:
                    stored = st.session_state.fp_stored_answer

                    if verify_secret_answer(stored, answer):
                        st.session_state.fp_step = 4
                        st.success("✅ Answer correct! Set new password.")
                        st.rerun()
                    else:
                        st.error("❌ Wrong answer! Please try again.")
                        st.warning("💡 Answer case-insensitive है — spelling check करें")

    # ── STEP 4: Set New Password ──────────────────
    elif step == 4:
        st.markdown('<div class="fp-step"><b>Step 4:</b> नया Password set करें</div>',
                    unsafe_allow_html=True)

        st.success(f"✅ Verified: **{st.session_state.fp_user_id}**")

        new_password = st.text_input(
            "New Password *",
            type="password",
            placeholder="Min 6 characters",
            key="fp_new_pwd"
        )

        confirm_password = st.text_input(
            "Confirm New Password *",
            type="password",
            placeholder="Same password again",
            key="fp_confirm_pwd"
        )

        # Password strength indicator
        if new_password:
            strength = 0
            tips = []
            if len(new_password) >= 8: strength += 1
            else: tips.append("8+ characters रखें")
            if any(c.isupper() for c in new_password): strength += 1
            else: tips.append("Capital letter add करें")
            if any(c.isdigit() for c in new_password): strength += 1
            else: tips.append("Number add करें")
            if any(c in "!@#$%^&*" for c in new_password): strength += 1
            else: tips.append("Special character add करें (!@#$)")

            strength_labels = ["", "Weak 🔴", "Fair 🟡", "Good 🟢", "Strong 💪"]
            st.caption(f"Password Strength: {strength_labels[strength]}")
            if tips:
                st.caption(f"💡 Tips: {', '.join(tips)}")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("⬅️ Back", key="fp_back_3"):
                st.session_state.fp_step = 3
                st.rerun()

        with col2:
            if st.button("🔒 Reset Password", type="primary",
                         use_container_width=True, key="fp_reset"):
                if not new_password or not confirm_password:
                    st.error("❌ Please fill both fields!")
                elif len(new_password) < 6:
                    st.error("❌ Password must be at least 6 characters!")
                elif new_password != confirm_password:
                    st.error("❌ Passwords do not match!")
                else:
                    with st.spinner("🔒 Updating password..."):
                        success, message = update_password_in_sheet(
                            st.session_state.fp_sheet,
                            st.session_state.fp_row_num,
                            st.session_state.fp_headers,
                            new_password,
                            st.session_state.fp_user_type
                        )

                    if success:
                        st.success("✅ Password reset successfully!")
                        st.balloons()
                        st.info("🔐 अब नए password से login करें")

                        # Clear forgot password session
                        for key in ['fp_step', 'fp_user_type', 'fp_user_id',
                                    'fp_row_num', 'fp_sheet', 'fp_headers',
                                    'fp_question', 'fp_stored_answer']:
                            if key in st.session_state:
                                del st.session_state[key]

                        import time
                        time.sleep(2)

                        # Go back to login
                        st.session_state.page = "login"
                        st.rerun()
                    else:
                        st.error(f"❌ Reset failed: {message}")

    # ── Back to Login ─────────────────────────────
    st.divider()
    if st.button("⬅️ Back to Login", key="fp_to_login"):
        # Clear all fp state
        for key in list(st.session_state.keys()):
            if key.startswith('fp_'):
                del st.session_state[key]
        st.session_state.page = "login"
        st.rerun()


# ─────────────────────────────────────────────
# HELPER: Save Secret Q&A to Sheet (for registration)
# ─────────────────────────────────────────────
def save_secret_qa_to_sheet(sheet, row_num, headers, question, answer):
    """
    Save secret question & answer to sheet after registration
    Call this after registering a new user

    Usage:
        from forgot_password import save_secret_qa_to_sheet
        save_secret_qa_to_sheet(sheet, row_num, headers, question, answer)
    """
    try:
        updates = []

        for col_name, value in [('Secret_Question', question),
                                 ('Secret_Answer', normalize_answer(answer))]:
            if col_name in headers:
                col_idx = headers.index(col_name) + 1
                col_letter = get_col_letter(col_idx)
                updates.append({
                    'range': f"{col_letter}{row_num}",
                    'values': [[value]]
                })

        if updates:
            sheet.batch_update(updates)
            return True, "Secret Q&A saved"
        else:
            return False, "Secret_Question or Secret_Answer column not found in sheet"

    except Exception as e:
        return False, f"Error saving Q&A: {str(e)}"


# ─────────────────────────────────────────────
# DIRECT RUN (for testing)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(page_title="🔑 Forgot Password", layout="centered")
    render_forgot_password()