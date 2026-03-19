"""
CANDIDATE_PORTAL.PY
====================
✅ Dashboard - Interview status, applied jobs
✅ Browse Vacancies - Readonly view
✅ My Profile - Personal data view
✅ Settings - Password change
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import hashlib

# ========================================
# CONFIG
# ========================================
def get_agency_sheet_id():
    """Get agency sheet ID from session state"""
    sheet_url = st.session_state.get("agency_sheet_url", "")
    if sheet_url:
        try:
            return sheet_url.split('/d/')[1].split('/')[0]
        except:
            st.error("❌ Invalid agency sheet URL. Please login again.")
            st.stop()
    else:
        st.error("❌ Agency sheet not configured. Please login again.")
        st.stop()


CRED_FILE = "credentials.json" if os.path.exists("credentials.json") else None


# ========================================
# GOOGLE SHEETS CLIENT
# ========================================
@st.cache_resource
def get_google_sheets_client():
    """Connect to Google Sheets"""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        if CRED_FILE:
            credentials = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, scope)
        else:
            creds_dict = st.secrets["gcp_service_account"]
            from google.oauth2.service_account import Credentials
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)

        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"❌ Google Sheets connection error: {e}")
        return None


# ========================================
# PASSWORD
# ========================================
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


# ========================================
# DATA HELPERS
# ========================================
@st.cache_data(ttl=300)
def get_my_profile(candidate_id):
    """Get candidate profile from Candidates sheet"""
    try:
        client = get_google_sheets_client()
        SHEET_ID = get_agency_sheet_id()
        if not client or not SHEET_ID:
            return None

        sheet = client.open_by_key(SHEET_ID).worksheet("Candidates")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        if 'Candidate ID' not in df.columns:
            return None

        match = df[df['Candidate ID'].astype(str).str.strip() == str(candidate_id).strip()]

        if len(match) == 0:
            return None

        return match.iloc[0].to_dict()

    except Exception as e:
        st.error(f"❌ Error fetching profile: {e}")
        return None


@st.cache_data(ttl=300)
def get_all_vacancies():
    """Get all open vacancies"""
    try:
        client = get_google_sheets_client()
        SHEET_ID = get_agency_sheet_id()
        if not client or not SHEET_ID:
            return pd.DataFrame()

        sheet = client.open_by_key(SHEET_ID).worksheet("Sheet4")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        for col in df.columns:
            df[col] = df[col].astype(str)

        return df
    except Exception as e:
        st.error(f"❌ Error fetching vacancies: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_my_interviews(candidate_id):
    """Get interview records for this candidate"""
    try:
        client = get_google_sheets_client()
        SHEET_ID = get_agency_sheet_id()
        if not client or not SHEET_ID:
            return pd.DataFrame()

        sheet = client.open_by_key(SHEET_ID).worksheet("Interview_Records")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        if 'Candidate ID' not in df.columns:
            return pd.DataFrame()

        my_records = df[df['Candidate ID'].astype(str).str.strip() == str(candidate_id).strip()]
        return my_records

    except Exception as e:
        return pd.DataFrame()


# ========================================
# MAIN DASHBOARD
# ========================================
def render_candidate_dashboard():
    """Main Candidate Portal Entry Point"""

    # Session से data lo
    candidate_id = st.session_state.get("candidate_id", "")
    full_name = st.session_state.get("full_name", "Candidate")
    agency_name = st.session_state.get("agency_name", "")

    # Header
    st.markdown(f"""
    <div style="margin-bottom:1.5rem; font-family:'Inter',-apple-system,sans-serif;">
        <h2 style="margin:0; font-weight:700; color:#0F172A; font-size:1.5rem;">Welcome, {full_name}</h2>
        <p style="margin:4px 0 0; color:#64748B; font-size:14px;">ID: {candidate_id} | Agency: {agency_name}</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        # Logo
        logo = st.session_state.get('logo_url', '')
        if logo:
            try:
                st.sidebar.image(logo, width=100)
            except:
                pass

        st.markdown(f"**{agency_name}**")
        st.markdown("---")

        menu = st.radio(
            "Navigation:",
            [
                "Dashboard",
                "Browse Vacancies",
                "My Profile",
                "Settings"
            ],
            label_visibility="collapsed",
            key="candidate_menu"
        )

        st.markdown("---")

        if st.button("Logout", use_container_width=True, type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ========== DASHBOARD ==========
    if menu == "Dashboard":
        render_dashboard(candidate_id)

    # ========== BROWSE VACANCIES ==========
    elif menu == "Browse Vacancies":
        render_browse_vacancies()

    # ========== MY PROFILE ==========
    elif menu == "My Profile":
        render_my_profile(candidate_id)

    # ========== SETTINGS ==========
    elif menu == "Settings":
        render_settings(candidate_id)


# ========================================
# DASHBOARD
# ========================================
def render_dashboard(candidate_id):
    """Dashboard - Interview status overview"""

    st.markdown("### 📊 My Dashboard")

    interviews_df = get_my_interviews(candidate_id)
    vacancies_df = get_all_vacancies()

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total = len(interviews_df)
        st.metric("📋 Total Applications", total)

    with col2:
        if len(interviews_df) > 0 and 'Interview Status' in interviews_df.columns:
            scheduled = len(interviews_df[
                interviews_df['Interview Status'].astype(str).str.strip() == 'Interview Scheduled'
            ])
        else:
            scheduled = 0
        st.metric("🗓️ Interviews Scheduled", scheduled)

    with col3:
        if len(interviews_df) > 0 and 'Result Status' in interviews_df.columns:
            selected = len(interviews_df[
                interviews_df['Result Status'].astype(str).str.strip() == 'Selected'
            ])
        else:
            selected = 0
        st.metric("🎉 Selected", selected)

    with col4:
        # Open vacancies count
        if len(vacancies_df) > 0 and 'Status' in vacancies_df.columns:
            open_vac = len(vacancies_df[
                vacancies_df['Status'].astype(str).str.strip().str.upper() == 'OPEN'
            ])
        else:
            open_vac = 0
        st.metric("💼 Open Vacancies", open_vac)

    st.markdown("---")

    # Interview Status
    if len(interviews_df) > 0:
        st.markdown("### 📋 My Interview Status")

        display_cols = ['Company Name', 'Job Title', 'Interview Status', 'Result Status', 'Interview Date']
        available_cols = [col for col in display_cols if col in interviews_df.columns]

        if available_cols:
            st.dataframe(
                interviews_df[available_cols],
                use_container_width=True,
                hide_index=True
            )

        # Upcoming interviews
        if 'Interview Status' in interviews_df.columns:
            upcoming = interviews_df[
                interviews_df['Interview Status'].astype(str).str.strip() == 'Interview Scheduled'
            ]

            if len(upcoming) > 0:
                st.markdown("### 🔥 Upcoming Interviews")
                for _, row in upcoming.iterrows():
                    st.info(
                        f"🏢 **{row.get('Company Name', 'N/A')}** | "
                        f"💼 {row.get('Job Title', 'N/A')} | "
                        f"📅 {row.get('Interview Date', 'N/A')} | "
                        f"⏰ {row.get('Interview Time', 'N/A')}"
                    )
    else:
        st.info("📋 No interview records yet. Browse vacancies to get started!")


# ========================================
# BROWSE VACANCIES
# ========================================
def render_browse_vacancies():
    """Browse all open vacancies - Readonly"""

    st.markdown("### 💼 Browse Vacancies")
    st.info("💡 Contact your agency to apply for any vacancy")

    vacancies_df = get_all_vacancies()

    if len(vacancies_df) == 0:
        st.warning("No vacancies available right now")
        return

    # Sirf open vacancies dikhao
    if 'Status' in vacancies_df.columns:
        open_vacancies = vacancies_df[
            vacancies_df['Status'].astype(str).str.strip().str.upper() == 'OPEN'
        ]
    else:
        open_vacancies = vacancies_df

    st.write(f"**{len(open_vacancies)} Open Vacancies Available**")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        if 'Job Title' in open_vacancies.columns:
            job_options = ['All'] + sorted(open_vacancies['Job Title'].unique().tolist())
            job_filter = st.selectbox("Job Title", job_options)
        else:
            job_filter = 'All'

    with col2:
        if 'Job Location/City' in open_vacancies.columns:
            location_options = ['All'] + sorted(open_vacancies['Job Location/City'].unique().tolist())
            location_filter = st.selectbox("Location", location_options)
        else:
            location_filter = 'All'

    with col3:
        search = st.text_input("Search")

    # Filters apply karo
    filtered = open_vacancies.copy()

    if job_filter != 'All' and 'Job Title' in filtered.columns:
        filtered = filtered[filtered['Job Title'] == job_filter]

    if location_filter != 'All' and 'Job Location/City' in filtered.columns:
        filtered = filtered[filtered['Job Location/City'] == location_filter]

    if search:
        mask = filtered.apply(
            lambda row: row.astype(str).str.contains(search, case=False).any(),
            axis=1
        )
        filtered = filtered[mask]

    st.write(f"**Showing {len(filtered)} vacancies**")
    st.markdown("---")

    # Vacancy cards
    display_cols = [
        'Company Name', 'Job Title', 'Salary',
        'Education Required', 'Experience Required',
        'Skills Required', 'Job Location/City',
        'Work Mode', 'Job Type', 'Vacancy Count'
    ]

    for _, row in filtered.iterrows():
        with st.expander(
            f"🏢 {row.get('Company Name', 'N/A')} — 💼 {row.get('Job Title', 'N/A')} | 💰 {row.get('Salary', 'N/A')}"
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**📍 Location:** {row.get('Job Location/City', 'N/A')}")
                st.write(f"**🎓 Education:** {row.get('Education Required', 'N/A')}")
                st.write(f"**💼 Experience:** {row.get('Experience Required', 'N/A')}")
                st.write(f"**🛠️ Skills:** {row.get('Skills Required', 'N/A')}")

            with col2:
                st.write(f"**💻 Work Mode:** {row.get('Work Mode', 'N/A')}")
                st.write(f"**⏰ Job Type:** {row.get('Job Type', 'N/A')}")
                st.write(f"**👥 Vacancies:** {row.get('Vacancy Count', 'N/A')}")
                st.write(f"**⚡ Urgency:** {row.get('Urgency Level', 'N/A')}")

            if row.get('Job Description', ''):
                st.write(f"**📝 Description:** {row.get('Job Description', '')}")

            st.info("📞 Interested? Contact your agency to apply!")


# ========================================
# MY PROFILE
# ========================================
def render_my_profile(candidate_id):
    """View personal profile"""

    st.markdown("### 👤 My Profile")

    profile = get_my_profile(candidate_id)

    if not profile:
        st.error("❌ Profile not found. Please contact agency.")
        return

    # Personal Info
    with st.expander("👤 Personal Information", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Full Name:** {profile.get('Full Name', 'N/A')}")
            st.write(f"**DOB:** {profile.get('DOB', 'N/A')}")
            st.write(f"**Gender:** {profile.get('Gender', 'N/A')}")
            st.write(f"**Category:** {profile.get('Category', 'N/A')}")
        with col2:
            st.write(f"**Father Name:** {profile.get('Father Name', 'N/A')}")
            st.write(f"**Marital Status:** {profile.get('Marital Status', 'N/A')}")
            st.write(f"**Aadhaar:** {profile.get('Aadhaar', 'N/A')}")
            st.write(f"**PAN:** {profile.get('PAN', 'N/A')}")

    # Contact Info
    with st.expander("📍 Contact & Address", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Mobile:** {profile.get('Mobile', 'N/A')}")
            st.write(f"**Email:** {profile.get('Email', 'N/A')}")
            st.write(f"**WhatsApp:** {profile.get('WhatsApp', 'N/A')}")
        with col2:
            st.write(f"**City:** {profile.get('Current City', 'N/A')}")
            st.write(f"**State:** {profile.get('Current State', 'N/A')}")
            st.write(f"**PIN:** {profile.get('Current PIN', 'N/A')}")

    # Job Preferences
    with st.expander("💼 Job Preferences", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Pref 1:** {profile.get('Job Pref 1', 'N/A')}")
            st.write(f"**Pref 2:** {profile.get('Job Pref 2', 'N/A')}")
            st.write(f"**Pref 3:** {profile.get('Job Pref 3', 'N/A')}")
        with col2:
            st.write(f"**Expected Salary:** ₹{profile.get('Expected Salary', 'N/A')}")
            st.write(f"**Notice Period:** {profile.get('Notice Period', 'N/A')}")
            st.write(f"**Relocate:** {profile.get('Willing to Relocate', 'N/A')}")

    # Education
    with st.expander("🎓 Education", expanded=False):
        st.write(f"**10th:** {profile.get('10th Board', 'N/A')} ({profile.get('10th Year', 'N/A')}) - {profile.get('10th Percentage', 'N/A')}")
        st.write(f"**12th:** {profile.get('12th Board', 'N/A')} - {profile.get('12th Stream', 'N/A')} ({profile.get('12th Year', 'N/A')}) - {profile.get('12th Percentage', 'N/A')}")
        st.write(f"**Graduation:** {profile.get('Graduation Degree', 'N/A')} - {profile.get('Graduation Specialization', 'N/A')}")
        st.write(f"**University:** {profile.get('Graduation University', 'N/A')} ({profile.get('Graduation Year', 'N/A')}) - {profile.get('Graduation Percentage', 'N/A')}")

    # Skills
    with st.expander("🏆 Skills & Experience", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Computer Skills:** {profile.get('Computer Skills', 'N/A')}")
            st.write(f"**Technical Skills:** {profile.get('Technical Skills', 'N/A')}")
            st.write(f"**Hindi:** {profile.get('Hindi Level', 'N/A')}")
        with col2:
            st.write(f"**Other Skills:** {profile.get('Other Skills', 'N/A')}")
            st.write(f"**English:** {profile.get('English Level', 'N/A')}")
            if profile.get('Is Fresher', '') == 'Yes':
                st.write("**Experience:** Fresher")
            else:
                st.write(f"**Experience:** {profile.get('Experience Years', 0)} years {profile.get('Experience Months', 0)} months")


# ========================================
# SETTINGS
# ========================================
def render_settings(candidate_id):
    """Settings - Password change only"""

    st.markdown("### ⚙️ Settings")

    st.markdown("#### 🔐 Change Password")

    with st.form("change_password_form"):
        current_password = st.text_input("Current Password *", type="password")
        new_password = st.text_input("New Password *", type="password", help="Min 6 characters")
        confirm_password = st.text_input("Confirm New Password *", type="password")

        change_btn = st.form_submit_button("🔒 Change Password", type="primary")

        if change_btn:
            if not current_password or not new_password or not confirm_password:
                st.error("❌ Please fill all fields!")
            elif len(new_password) < 6:
                st.error("❌ Password must be at least 6 characters!")
            elif new_password != confirm_password:
                st.error("❌ New passwords do not match!")
            else:
                try:
                    client = get_google_sheets_client()
                    SHEET_ID = get_agency_sheet_id()

                    if client and SHEET_ID:
                        sheet = client.open_by_key(SHEET_ID).worksheet("Candidates")
                        all_data = sheet.get_all_values()
                        headers = all_data[0]

                        # Candidate row dhundo
                        row_num = None
                        stored_password = None

                        cid_col = headers.index('Candidate ID') if 'Candidate ID' in headers else -1
                        pwd_col = headers.index('Password') if 'Password' in headers else -1

                        if cid_col == -1:
                            st.error("❌ Candidate ID column not found")
                            return

                        if pwd_col == -1:
                            st.error("❌ Password column not found in sheet")
                            return

                        for idx, row in enumerate(all_data[1:], start=2):
                            if len(row) > cid_col and str(row[cid_col]).strip() == str(candidate_id).strip():
                                row_num = idx
                                stored_password = row[pwd_col] if len(row) > pwd_col else None
                                break

                        if not row_num:
                            st.error("❌ Candidate record not found")
                        elif hash_password(current_password) != stored_password:
                            st.error("❌ Current password is incorrect!")
                        else:
                            # New password save karo
                            col_letter = chr(64 + pwd_col + 1)
                            sheet.update(f"{col_letter}{row_num}", hash_password(new_password))
                            st.success("✅ Password changed successfully!")
                            st.cache_data.clear()

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")