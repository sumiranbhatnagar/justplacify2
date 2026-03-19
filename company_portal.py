"""
COMPANY_PORTAL.PY - COMPLETE VERSION
=====================================
✅ Vacancy Management (4 tabs - like app.py)
✅ View Candidates (limited info for privacy)
✅ Settings (editable email/phone/address + functional password change)
✅ CID generation fixed
✅ Download button outside form
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import hashlib
from forgot_password import render_secret_question_setup, save_secret_qa_to_sheet
from terms_conditions_module import (
    render_tc_acceptance_page,
    save_tc_acceptance,
    get_latest_tc_pdf,  
    check_user_accepted_current_tc,
    show_tc_update_dialog_if_needed,
    init_tc_system
)

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
            return None
    return None


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
            from oauth2client.service_account import ServiceAccountCredentials
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                CRED_FILE, scope
            )
        else:
            creds_dict = st.secrets["gcp_service_account"]
            credentials = Credentials.from_service_account_info(
                creds_dict,
                scopes=scope
            )
        
        client = gspread.authorize(credentials)
        return client
        
    except Exception as e:
        st.error(f"❌ Google Sheets connection error: {e}")
        return None


# ========================================
# DATA HELPERS
# ========================================
@st.cache_data(ttl=300)
def get_companies():
    """Fetch companies from CID sheet"""
    try:
        client = get_google_sheets_client()
        SHEET_ID = get_agency_sheet_id()
        if client and SHEET_ID:
            sheet = client.open_by_key(SHEET_ID).worksheet("CID")
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            for col in df.columns:
                df[col] = df[col].astype(str)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ Error fetching companies: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_vacancies():
    """Fetch vacancies from Sheet4"""
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
        st.error(f"❌ Error fetching vacancies: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_candidates():
    """Fetch candidates from Candidates sheet"""
    try:
        client = get_google_sheets_client()
        SHEET_ID = get_agency_sheet_id()
        if client and SHEET_ID:
            sheet = client.open_by_key(SHEET_ID).worksheet("Candidates")
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            for col in df.columns:
                df[col] = df[col].astype(str)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ Error fetching candidates: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_designation_options():
    """Fetch designations from Sheet2"""
    try:
        client = get_google_sheets_client()
        SHEET_ID = get_agency_sheet_id()
        
        if not client:
            st.warning("⚠️ Google Sheets client not available")
            return []
        
        if not SHEET_ID:
            st.warning("⚠️ Agency sheet ID not found")
            return []
        
        # Open Sheet2
        sheet = client.open_by_key(SHEET_ID).worksheet("Sheet2")
        data = sheet.get_all_records()
        
        if not data:
            st.warning("⚠️ Sheet2 is empty")
            return []
        
        df = pd.DataFrame(data)
        
        if "Designation" not in df.columns:
            st.error(f"❌ 'Designation' column not found in Sheet2. Available columns: {df.columns.tolist()}")
            return []
        
        # Get unique designations
        designations = [str(x).strip() for x in df["Designation"].dropna().unique() if str(x).strip()]
        
        if not designations:
            st.warning("⚠️ No designations found in Sheet2")
            return []
        
        return sorted(designations)
        
    except Exception as e:
        st.error(f"❌ Error fetching designations: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return []


@st.cache_data(ttl=300)
def get_education_options():
    """Get education options"""
    return ["12th", "Diploma", "B.Sc", "B.Tech", "M.Sc", "MBA", "MCA", "Other"]


def lookup_dgn_id(job_title: str) -> str:
    """Lookup DGN ID from Sheet2 based on designation"""
    try:
        client = get_google_sheets_client()
        SHEET_ID = get_agency_sheet_id()
        
        if not client or not SHEET_ID:
            return ""
        
        sheet = client.open_by_key(SHEET_ID).worksheet("Sheet2")
        data = sheet.get_all_records()
        
        if not data:
            return ""
        
        df = pd.DataFrame(data)
        
        # Check if required columns exist
        if "Designation" not in df.columns or "DGN ID" not in df.columns:
            st.warning(f"⚠️ Required columns not found in Sheet2. Available: {df.columns.tolist()}")
            return ""
        
        # Find matching designation (case-insensitive)
        match = df[df["Designation"].astype(str).str.strip().str.lower() == str(job_title).strip().lower()]
        
        if not match.empty:
            dgn_id = str(match.iloc[0]["DGN ID"]).strip()
            return dgn_id
        
        return ""
        
    except Exception as e:
        st.warning(f"⚠️ Error looking up DGN ID: {str(e)}")
        return ""


def get_column_letter(n):
    """Convert column number to Excel letter"""
    result = ""
    while n > 0:
        n -= 1
        result = chr(65 + n % 26) + result
        n //= 26
    return result


def extract_first_name(full_name):
    """Extract first name from full name"""
    if not full_name or str(full_name).strip() == "":
        return "N/A"
    name_parts = str(full_name).strip().split()
    return name_parts[0] if name_parts else "N/A"


def generate_vid(company_id, dgn_id):
    """
    Generate VID from company_id and dgn_id
    Format: AG002CID0117DGN004
    
    Args:
        company_id: "AG002CID0117" (from session state)
        dgn_id: "DGN004" (from Sheet2)
    
    Returns:
        "AG002CID0117DGN004"
    """
    try:
        # company_id already has format: AG002CID0117
        # dgn_id has format: DGN004
        # Simply concatenate them
        vid = f"{company_id}{dgn_id}"
        return vid
    except Exception as e:
        st.error(f"❌ Error generating VID: {str(e)}")
        return ""


def hash_password(password):
    """Hash password for storage"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_interview_records_by_vid(vid):
    """Get active interview records for a specific VID"""
    try:
        client = get_google_sheets_client()
        SHEET_ID = get_agency_sheet_id()
        
        if not client or not SHEET_ID:
            return pd.DataFrame()
        
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Check if Interview_Records sheet exists
        try:
            sheet = spreadsheet.worksheet("Interview_Records")
        except:
            # Sheet doesn't exist
            return pd.DataFrame()
        
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Filter by VID
        if 'VID' not in df.columns:
            return pd.DataFrame()
        
        records = df[df['VID'].astype(str).str.strip() == str(vid).strip()]
        
        # Filter only active/pending interviews
        if 'Status' in records.columns:
            active_statuses = [
                'SCHEDULED', 'PENDING', 'CONTACT REQUESTED', 
                'SHORTLISTED', 'INTERVIEW SCHEDULED', 'OPEN'
            ]
            active = records[
                records['Status'].astype(str).str.strip().str.upper().isin(active_statuses)
            ]
            return active
        
        return records
        
    except Exception as e:
        st.warning(f"⚠️ Could not check Interview_Records: {str(e)}")
        return pd.DataFrame()


def close_interview_records(vid, selected_indices=None):
    """Close interview records for a VID"""
    try:
        client = get_google_sheets_client()
        SHEET_ID = get_agency_sheet_id()
        
        if not client or not SHEET_ID:
            return False, "Cannot connect to Google Sheets"
        
        spreadsheet = client.open_by_key(SHEET_ID)
        
        try:
            sheet = spreadsheet.worksheet("Interview_Records")
        except:
            # No Interview_Records sheet
            return True, "No interview records to update"
        
        all_data = sheet.get_all_values()
        if len(all_data) <= 1:
            return True, "No interview records found"
        
        headers = all_data[0]
        
        # Find VID and Status columns
        vid_col_idx = headers.index('VID') if 'VID' in headers else None
        status_col_idx = headers.index('Status') if 'Status' in headers else None
        
        if not vid_col_idx or not status_col_idx:
            return False, "Required columns not found in Interview_Records"
        
        # Find matching rows
        updates = []
        count = 0
        
        for row_idx, row in enumerate(all_data[1:], start=2):
            if len(row) > vid_col_idx and row[vid_col_idx] == str(vid):
                # Check if this row should be closed
                if selected_indices is None or (row_idx - 2) in selected_indices:
                    # Update Status to "Vacancy Closed"
                    status_col_letter = get_column_letter(status_col_idx + 1)
                    updates.append({
                        'range': f"{status_col_letter}{row_idx}",
                        'values': [["Vacancy Closed"]]
                    })
                    count += 1
        
        if updates:
            sheet.batch_update(updates)
            return True, f"Closed {count} interview record(s)"
        
        return True, "No active interview records to close"
        
    except Exception as e:
        return False, f"Error closing interview records: {str(e)}"


# ========================================
# COMPANY REGISTRATION PAGE
# ========================================
def company_registration_page():
    """Company Registration Form"""
    import hashlib
    import secrets
    import string

    def generate_password(length=8):
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))

    def hash_password(password):
        return hashlib.md5(password.encode()).hexdigest()

    # Agency branding
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 🏢 Company Registration")
        st.caption(f"🏢 Agency: {st.session_state.get('agency_name', 'N/A')}")
    with col2:
        logo = st.session_state.get('logo_url', '')
        if logo:
            try:
                st.image(logo, width=80)
            except:
                pass

    st.markdown("---")

    # Already registered check
    st.info("💡 Already registered? Login with your Portal Code")

    with st.form("company_registration_form"):
        st.markdown("#### 🏢 Basic Information")
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Company Name *")
            industry = st.selectbox("Industry *", [
                "", "IT/Software", "Finance/Banking", "Healthcare/Medical",
                "Education/Training", "Manufacturing", "Retail/FMCG",
                "Construction/Real Estate", "Hospitality", "Other"
            ])
            contact_number = st.text_input("Contact Number *", max_chars=10)
            alternate_number = st.text_input("Alternate Number", max_chars=10)
        with col2:
            email = st.text_input("Email *")
            website = st.text_input("Website", placeholder="https://")
            description = st.text_area("Company Description", height=100)

        st.markdown("#### 📍 Address")
        address = st.text_input("Address *")
        col1, col2, col3 = st.columns(3)
        with col1:
            city = st.text_input("City *")
        with col2:
            state = st.text_input("State *")
        with col3:
            pin_code = st.text_input("PIN Code *", max_chars=6)

        st.markdown("### 🔐 Security Question")
        secret_question, secret_answer = render_secret_question_setup(key_prefix="company_reg")

        st.markdown("---")
        submitted = st.form_submit_button("✅ Register Company", type="primary", use_container_width=True)
    if submitted:
        # Validation
        if not company_name or not industry or not contact_number or not email or not address or not city or not state or not pin_code:
            st.error("❌ Please fill all required fields!")
            return

        if '@' not in email or '.' not in email:
            st.error("❌ Please enter valid email")
            return

        if len(contact_number) != 10 or not contact_number.isdigit():
            st.error("❌ Contact number must be 10 digits")
            return

        if len(pin_code) != 6 or not pin_code.isdigit():
            st.error("❌ PIN Code must be 6 digits")
            return

        with st.spinner("🔄 Registering company..."):
            try:
                client = get_google_sheets_client()
                SHEET_ID = get_agency_sheet_id()

                if not client or not SHEET_ID:
                    st.error("❌ Cannot connect to Google Sheets")
                    return

                sheet = client.open_by_key(SHEET_ID).worksheet("CID")
                all_data = sheet.get_all_records()
                df = pd.DataFrame(all_data)

                # Duplicate email check
                if not df.empty and 'Email' in df.columns:
                    if email in df['Email'].astype(str).values:
                        st.error("❌ This email is already registered!")
                        return

                # CID generate karo
                agency_code = st.session_state.get("agency_code", "AG000")
                if not df.empty and 'CID' in df.columns:
                    numbers = []
                    for cid in df['CID']:
                        if isinstance(cid, str) and 'CID' in cid:
                            try:
                                numbers.append(int(cid.split('CID')[-1]))
                            except:
                                pass
                    next_num = max(numbers) + 1 if numbers else 1
                else:
                    next_num = 1

                new_cid = f"{agency_code}CID{next_num:04d}"

                # Password generate karo
                auto_password = generate_password(8)
                password_hash = hash_password(auto_password)

                # Data prepare karo — exact headers ke hisaab se
                headers = sheet.row_values(1)
                data = {
                    "Company Name": company_name,
                    "CID": new_cid,
                    "Industry": industry,
                    "Company Description": description,
                    "Contact Number": contact_number,
                    "Address of Company": address,
                    "City": city,
                    "State": state,
                    "PIN Code": pin_code,
                    "Email": email,
                    "Website": website,
                    "Date Added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "alternateNumber": alternate_number,
                    "Password": password_hash,
                    "Subscription_Status": "Inactive",
                    "Subscription_End_Date": "",
                    "Plan_Type": ""
                }

                row = [data.get(h.strip(), '') for h in headers]
                sheet.append_row(row)

                # Success — credentials dikhao
                st.success("✅ Company Registered Successfully!")
                st.markdown("---")
                st.warning("🔐 **Login Credentials — अभी Note करें!**")
                _, _, current_version = get_latest_tc_pdf()
                if current_version:
                    save_tc_acceptance(new_cid, "Company", current_version)


                # Secret Q&A save करो
                if secret_question and secret_answer and secret_question != "-- Select a Question --":
                    try:
                        # Last added row find करो
                        all_rows = sheet.get_all_values()
                        headers = all_rows[0]
                        row_num = len(all_rows)  # Last row
                        save_secret_qa_to_sheet(
                            sheet, row_num, headers,
                            secret_question, secret_answer
                        )
                        st.success("✅ Security Question saved!")
                    except Exception as e:
                        st.warning(f"⚠️ Security question save failed: {str(e)}")
                else:
                    st.warning("⚠️ Security question not set!")    




                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Portal Code:** {new_cid}")
                with col2:
                    st.info(f"**Password:** {auto_password}")
                st.error("⚠️ यह password दोबारा नहीं दिखेगा — अभी note कर लें!")
                st.markdown("---")
                st.info("💡 Agency द्वारा subscription activate होने के बाद login कर सकते हैं।")

            except Exception as e:
                st.error(f"❌ Registration failed: {str(e)}")


# ========================================
# COMPANY DASHBOARD - MAIN PORTAL
# ========================================
def render_company_dashboard():
    """
    Company Dashboard - Main Portal
    Features: Vacancy Management, View Candidates, Settings
    """
    
    # Get company details
    company_id = st.session_state.get("company_id", "Unknown")
    company_name = st.session_state.get("full_name", "Company")
    agency_code = st.session_state.get("agency_code", "Unknown")
    
    # Header
    st.markdown(f"""
    <div style="margin-bottom:1.5rem; font-family:'Inter',-apple-system,sans-serif;">
        <h2 style="margin:0; font-weight:700; color:#0F172A; font-size:1.5rem;">{company_name} - Company Portal</h2>
        <p style="margin:4px 0 0; color:#64748B; font-size:14px;">CID: {company_id} | Agency: {agency_code}</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar navigation
    with st.sidebar:
        st.markdown("---")
        menu = st.radio(
            "Navigation:",
            [
                "Dashboard",
                "Vacancy Management",
                "View Candidates",
                "Settings"
            ],
            label_visibility="collapsed",
            key="company_menu"
        )

        st.markdown("---")

        # Logout button
        if st.button("Logout", use_container_width=True, type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ========== DASHBOARD ==========
    if menu == "Dashboard":
        st.markdown("""
        <div style="font-size:15px; font-weight:700; color:#0F172A; margin-bottom:12px; font-family:'Inter',sans-serif;">
            Dashboard Overview
        </div>
        """, unsafe_allow_html=True)
        
        # Get company-specific vacancies (filter by CID)
        all_vacancies = get_vacancies()
        
        # Find CID column (case-insensitive, strip spaces)
        cid_col = None
        for col in all_vacancies.columns:
            if col.strip().upper() == 'CID':
                cid_col = col
                break
        
        # Filter vacancies for this company
        if cid_col:
            company_vacancies = all_vacancies[
                all_vacancies[cid_col].astype(str).str.strip().str.upper() == str(company_id).strip().upper()
            ]
        else:
            company_vacancies = pd.DataFrame()
            st.warning("⚠️ CID column not found in Sheet4")
        
        st.markdown("---")
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_vac = len(company_vacancies)
            st.metric("Posted Vacancies", total_vac, help="All vacancies (Open + Closed + Filled)")
        
        with col2:
            if 'Status' in company_vacancies.columns:
                open_vac = len(company_vacancies[company_vacancies['Status'].astype(str).str.strip().str.upper() == 'OPEN'])
            else:
                open_vac = 0
                st.caption("⚠️ No Status column")
            st.metric("🟢 Open Positions", open_vac, help="Currently open vacancies")
        
        with col3:
            if 'Status' in company_vacancies.columns:
                closed_vac = len(company_vacancies[company_vacancies['Status'].astype(str).str.strip().str.upper() == 'CLOSED'])
            else:
                closed_vac = 0
            st.metric("🔴 Closed", closed_vac, help="Closed vacancies")
        
        with col4:
            if 'Status' in company_vacancies.columns:
                filled_vac = len(company_vacancies[company_vacancies['Status'].astype(str).str.strip().str.upper() == 'FILLED'])
            else:
                filled_vac = 0
            st.metric("✅ Filled", filled_vac, help="Filled positions")
        
        st.markdown("---")
        
        # Recent Vacancies
        if len(company_vacancies) > 0:
            st.markdown("### 📋 Recent Vacancies")
            recent = company_vacancies.head(5)
            display_cols = ['Job Title', 'Vacancy Count', 'Salary', 'Status', 'Date Added']
            available_cols = [col for col in display_cols if col in recent.columns]
            st.dataframe(recent[available_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No vacancies posted yet. Click 'Post New Vacancy' to get started!")
    
    # ========== VACANCY MANAGEMENT ==========
    elif menu == "Vacancy Management":
        render_vacancy_management(company_id, company_name)
    
    # ========== VIEW CANDIDATES ==========
    elif menu == "View Candidates":
        render_view_candidates()
    
    # ========== SETTINGS ==========
    elif menu == "Settings":
        render_settings(company_id)


# ========================================
# VACANCY MANAGEMENT
# ========================================
def render_vacancy_management(company_id, company_name):
    """Vacancy Management - 4 Tabs"""
    
    st.markdown("### 💼 Vacancy Management")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard",
        "📋 My Vacancies",
        "➕ Post Vacancy",
        "✏️ Edit Vacancy"
    ])
    
    # Get all vacancies
    all_vacancies = get_vacancies()
    
    # Find CID column (case-insensitive, strip spaces)
    cid_col = None
    for col in all_vacancies.columns:
        if col.strip().upper() == 'CID':
            cid_col = col
            break
    
    # Filter by CID (company-specific)
    if cid_col:
        company_vacancies = all_vacancies[
            all_vacancies[cid_col].astype(str).str.strip().str.upper() == str(company_id).strip().upper()
        ]
    else:
        company_vacancies = pd.DataFrame()
        st.error(f"❌ CID column not found! Available columns: {all_vacancies.columns.tolist()}")
    
    # TAB 1: Dashboard
    with tab1:
        st.markdown("#### 📊 Vacancy Statistics")
        
        if len(company_vacancies) > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Total", len(company_vacancies), help="All vacancies")
            
            with col2:
                if 'Status' in company_vacancies.columns:
                    open_count = len(company_vacancies[company_vacancies['Status'].astype(str).str.strip().str.upper() == 'OPEN'])
                else:
                    open_count = 0
                st.metric("🟢 Open", open_count)
            
            with col3:
                if 'Status' in company_vacancies.columns:
                    closed_count = len(company_vacancies[company_vacancies['Status'].astype(str).str.strip().str.upper() == 'CLOSED'])
                else:
                    closed_count = 0
                st.metric("🔴 Closed", closed_count)
            
            with col4:
                if 'Status' in company_vacancies.columns:
                    filled_count = len(company_vacancies[company_vacancies['Status'].astype(str).str.strip().str.upper() == 'FILLED'])
                else:
                    filled_count = 0
                st.metric("✅ Filled", filled_count)
        else:
            st.info("No vacancies posted yet!")
    
    # TAB 2: My Vacancies
    with tab2:
        st.markdown("#### 📋 All My Vacancies")
        
        if len(company_vacancies) > 0:
            # Filters
            col1, col2 = st.columns(2)
            
            with col1:
                status_filter = st.multiselect(
                    "Filter by Status",
                    options=company_vacancies.get('Status', pd.Series([])).unique().tolist(),
                    default=company_vacancies.get('Status', pd.Series([])).unique().tolist()
                )
            
            with col2:
                search = st.text_input("Search Job Title")
            
            # Apply filters
            filtered = company_vacancies.copy()
            
            if status_filter and 'Status' in filtered.columns:
                filtered = filtered[filtered['Status'].isin(status_filter)]
            
            if search and 'Job Title' in filtered.columns:
                filtered = filtered[filtered['Job Title'].str.contains(search, case=False, na=False)]
            
            st.write(f"**Showing {len(filtered)} / {len(company_vacancies)} vacancies**")
            
            display_cols = ['Job Title', 'Vacancy Count', 'Salary', 'Education Required', 'Experience Required', 'Skills Required', 'Status', 'Date Added']
            available_cols = [col for col in display_cols if col in filtered.columns]
            st.dataframe(filtered[available_cols], use_container_width=True, height=400)
            
            # Download
            csv = filtered.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                data=csv,
                file_name=f"my_vacancies_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No vacancies found. Post your first vacancy!")
    
    # TAB 3: Post Vacancy
    with tab3:
        st.markdown("#### ➕ Post New Vacancy")
        
        dgn_opts = get_designation_options()
        edu_opts = get_education_options()
        
        if not dgn_opts:
            st.warning("⚠️ No designations available. Please contact agency.")
            return
        
        with st.form("post_vacancy_form"):
            # 3 tabs inside form
            t_basic, t_req, t_log = st.tabs(["Basic", "Requirements", "Logistics"])
            
            with t_basic:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.text_input("Company Name", value=company_name, disabled=True)
                    job_title = st.selectbox("Job Title *", dgn_opts)
                    vacancy_count = st.number_input("Vacancy Count *", min_value=1, value=1)
                
                with col2:
                    salary = st.text_input("Salary *", placeholder="e.g., 3-5 LPA")
                    job_desc = st.text_area("Job Description", height=100)
            
            with t_req:
                col1, col2 = st.columns(2)
                
                with col1:
                    edu_req = st.selectbox("Education Required *", edu_opts)
                    skills_req = st.text_input("Skills Required")
                    exp_req = st.text_input("Experience Required", placeholder="e.g., 2-5 years")
                    gender_pref = st.selectbox("Gender Preference", ["Any", "Male", "Female"])
                
                with col2:
                    urgency = st.selectbox("Urgency Level", ["Low", "Medium", "High", "Critical"])
                    age_min = st.number_input("Age Min", min_value=18, value=21)
                    age_max = st.number_input("Age Max", min_value=18, value=60)
                    pref_loc = st.text_input("Preferred Location")
            
            with t_log:
                col1, col2 = st.columns(2)
                
                with col1:
                    job_city = st.text_input("Job Location *")
                    job_type = st.selectbox("Job Type *", ["Full-time", "Part-time", "Contract", "Internship"])
                    work_mode = st.selectbox("Work Mode *", ["On-site", "Remote", "Hybrid"])
                
                with col2:
                    job_timing = st.text_input("Job Timing", placeholder="9 AM - 6 PM")
                    shift_timings = st.text_input("Shift Timings")
                    notice_ok = st.selectbox("Notice Period", ["Any", "Immediate", "15 days", "30 days"])
                
                contact_person = st.text_input("Contact Person")
                contact_number = st.text_input("Contact Number")
                notes = st.text_area("Additional Notes")
            
            submitted = st.form_submit_button("✅ Post Vacancy", type="primary")
            
            if submitted:
                if not job_title or not salary or not job_city:
                    st.error("❌ Please fill all required fields!")
                else:
                    try:
                        client = get_google_sheets_client()
                        SHEET_ID = get_agency_sheet_id()
                        
                        if client and SHEET_ID:
                            sheet = client.open_by_key(SHEET_ID).worksheet("Sheet4")
                            all_data = sheet.get_all_values()
                            headers = all_data[0]
                            
                            # Find last row
                            last_row = 1
                            for idx, row in enumerate(all_data[1:], start=2):
                                if any(cell.strip() for cell in row):
                                    last_row = idx
                            next_row = last_row + 1
                            
                            # Get DGN ID from Sheet2
                            dgn_id = lookup_dgn_id(job_title)
                            
                            if not dgn_id:
                                st.error("❌ Could not find DGN ID for selected job title!")
                                st.stop()
                            
                            # Generate VID: AG002CID0117DGN004
                            vid = generate_vid(company_id, dgn_id)
                            
                            if not vid:
                                st.error("❌ Could not generate VID!")
                                st.stop()
                            
                            st.success(f"✅ Generated VID: **{vid}**")
                            
                            # Prepare data
                            vacancy_data = {
                                "VID": vid,
                                "Company Name": company_name,
                                "CID": company_id,
                                "Job Title": job_title,
                                "DGN ID": dgn_id,
                                "Salary": salary,
                                "Job Description": job_desc,
                                "Education Required": edu_req,
                                "Skills Required": skills_req,
                                "Experience Required": exp_req,
                                "Vacancy Count": vacancy_count,
                                "Contact Person": contact_person,
                                "Contact Number": contact_number,
                                "Additional Notes": notes,
                                "Date Added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Job Location/City": job_city,
                                "Gender Preference": gender_pref,
                                "Job Type": job_type,
                                "Job Timing": job_timing,
                                "Shift Timings": shift_timings,
                                "Notice Period Acceptable": notice_ok,
                                "Work Mode": work_mode,
                                "Age Range Min": age_min,
                                "Age Range Max": age_max,
                                "Urgency Level": urgency,
                                "Preferred Candidate Location": pref_loc,
                                "vacancy filled": "0",
                                "Status": "Open",
                                "Created Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Created By": company_name
                            }
                            
                            # Create row
                            row_data = [vacancy_data.get(h, '') for h in headers]
                            
                            # Update sheet
                            last_col = get_column_letter(len(headers))
                            range_to_update = f"A{next_row}:{last_col}{next_row}"
                            sheet.update(range_to_update, [row_data])
                            
                            st.success(f"✅ Vacancy posted successfully!")
                            st.info(f"📋 VID: **{vid}**")
                            st.balloons()
                            st.cache_data.clear()
                            
                            import time
                            time.sleep(2)
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
    
    # TAB 4: Edit Vacancy
    with tab4:
        st.markdown("#### ✏️ Edit Vacancy")
        
        if len(company_vacancies) > 0:
            vacancy_options = company_vacancies.apply(
                lambda x: f"{x.get('Job Title', 'N/A')} - {x.get('VID', 'N/A')} ({x.get('Status', 'N/A')})",
                axis=1
            ).tolist()
            
            selected = st.selectbox("Select Vacancy to Edit", vacancy_options)
            
            if selected:
                idx = vacancy_options.index(selected)
                vacancy = company_vacancies.iloc[idx]
                
                st.markdown("---")
                
                # Locked fields
                st.markdown("#### 🔒 Locked Fields (Agency Managed)")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"**Company:** {vacancy.get('Company Name', 'N/A')}")
                    st.info(f"**Job Title:** {vacancy.get('Job Title', 'N/A')}")
                    st.info(f"**VID:** {vacancy.get('VID', 'N/A')}")
                
                with col2:
                    st.info(f"**DGN ID:** {vacancy.get('DGN ID', 'N/A')}")
                    st.info(f"**Vacancy Filled:** {vacancy.get('vacancy filled', '0')} (by agency)")
                    st.info(f"**Posted:** {vacancy.get('Date Added', 'N/A')}")
                
                st.markdown("---")
                st.markdown("#### ✏️ Edit Fields")
                
                edu_opts = get_education_options()
                
                with st.form("edit_vacancy_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        status = st.selectbox(
                            "Status ⭐⭐⭐",
                            ["Open", "Closed", "On Hold"],
                            index=["Open", "Closed", "On Hold"].index(vacancy.get('Status', 'Open')) if vacancy.get('Status') in ["Open", "Closed", "On Hold"] else 0,
                            help="Change to 'Closed' if filled from other source"
                        )
                        
                        vacancy_count = st.number_input(
                            "Vacancy Count ⭐⭐",
                            min_value=1,
                            value=int(vacancy.get('Vacancy Count', 1))
                        )
                        
                        salary = st.text_input("Salary", value=vacancy.get('Salary', ''))
                        
                        experience = st.text_input("Experience Required", value=vacancy.get('Experience Required', ''))
                        
                        urgency = st.selectbox(
                            "Urgency Level",
                            ["Low", "Medium", "High", "Critical"],
                            index=["Low", "Medium", "High", "Critical"].index(vacancy.get('Urgency Level', 'Medium')) if vacancy.get('Urgency Level') in ["Low", "Medium", "High", "Critical"] else 1
                        )
                    
                    with col2:
                        skills = st.text_input("Skills Required", value=vacancy.get('Skills Required', ''))
                        
                        work_mode = st.selectbox(
                            "Work Mode",
                            ["On-site", "Remote", "Hybrid"],
                            index=["On-site", "Remote", "Hybrid"].index(vacancy.get('Work Mode', 'On-site')) if vacancy.get('Work Mode') in ["On-site", "Remote", "Hybrid"] else 0
                        )
                        
                        notice = st.selectbox(
                            "Notice Period",
                            ["Any", "Immediate", "15 days", "30 days"],
                            index=["Any", "Immediate", "15 days", "30 days"].index(vacancy.get('Notice Period Acceptable', 'Any')) if vacancy.get('Notice Period Acceptable') in ["Any", "Immediate", "15 days", "30 days"] else 0
                        )
                        
                        current_edu = vacancy.get('Education Required', '')
                        edu_idx = edu_opts.index(current_edu) if current_edu in edu_opts else 0
                        education = st.selectbox("Education", edu_opts, index=edu_idx)
                    
                    job_desc = st.text_area("Job Description", value=vacancy.get('Job Description', ''), height=100)
                    notes = st.text_area("Additional Notes", value=vacancy.get('Additional Notes', ''), height=60)
                    
                    st.info("ℹ️ 'Vacancy Filled' is managed by agency. If filled from other source, set Status to 'Closed'.")
                    
                    update_btn = st.form_submit_button("💾 Update Vacancy", type="primary")
                    
                    if update_btn:
                        # Store old status before update
                        old_status = vacancy.get('Status', 'Open')
                        new_status = status
                        vacancy_vid = vacancy.get('VID', '')
                        
                        try:
                            client = get_google_sheets_client()
                            SHEET_ID = get_agency_sheet_id()
                            
                            if client and SHEET_ID:
                                # STEP 1: ALWAYS Update Sheet4 ✅
                                sheet = client.open_by_key(SHEET_ID).worksheet("Sheet4")
                                all_data = sheet.get_all_values()
                                headers = all_data[0]
                                
                                row_num = idx + 2
                                
                                update_data = {
                                    'Status': status,
                                    'Vacancy Count': str(vacancy_count),
                                    'Salary': salary,
                                    'Experience Required': experience,
                                    'Skills Required': skills,
                                    'Job Description': job_desc,
                                    'Urgency Level': urgency,
                                    'Work Mode': work_mode,
                                    'Notice Period Acceptable': notice,
                                    'Education Required': education,
                                    'Additional Notes': notes,
                                    'Last Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'Updated By': company_name
                                }
                                
                                updates = []
                                for field, value in update_data.items():
                                    if field in headers:
                                        col_idx = headers.index(field) + 1
                                        col_letter = get_column_letter(col_idx)
                                        updates.append({
                                            'range': f"{col_letter}{row_num}",
                                            'values': [[value]]
                                        })
                                
                                if updates:
                                    sheet.batch_update(updates)
                                    st.success("✅ Sheet4 updated!")
                                
                                # STEP 2: Check if CLOSING vacancy (Open → Closed) ✅
                                if old_status.upper() != "CLOSED" and new_status.upper() == "CLOSED":
                                    st.info("🔍 Checking interview records...")
                                    
                                    # Get active interview records for this VID
                                    active_records = get_interview_records_by_vid(vacancy_vid)
                                    
                                    if len(active_records) == 0:
                                        # No interviews - just close
                                        st.success("✅ Vacancy closed (no pending interviews)")
                                    
                                    elif len(active_records) == 1:
                                        # Single interview - auto close
                                        success, msg = close_interview_records(vacancy_vid)
                                        if success:
                                            st.success(f"✅ Vacancy closed + {msg}")
                                        else:
                                            st.warning(f"⚠️ Vacancy closed but: {msg}")
                                    
                                    else:
                                        # Multiple interviews - show selection UI
                                        st.warning(f"⚠️ This vacancy has {len(active_records)} pending interview records")
                                        
                                        st.markdown("#### Select interviews to close:")
                                        
                                        selected_interviews = []
                                        
                                        for record_idx, record in active_records.iterrows():
                                            candidate = record.get('Candidate Name', record.get('Candidate_Name', 'N/A'))
                                            record_status = record.get('Status', 'N/A')
                                            interview_date = record.get('Interview Date', record.get('Interview_Date', 'N/A'))
                                            
                                            if st.checkbox(
                                                f"{candidate} - {record_status} ({interview_date})",
                                                value=True,  # Default: select all
                                                key=f"int_close_{record_idx}"
                                            ):
                                                selected_interviews.append(record_idx)
                                        
                                        col1, col2 = st.columns(2)
                                        
                                        with col1:
                                            if st.button(
                                                f"❌ Close Selected ({len(selected_interviews)})",
                                                type="primary",
                                                disabled=len(selected_interviews) == 0,
                                                key="close_selected_interviews"
                                            ):
                                                success, msg = close_interview_records(vacancy_vid, selected_interviews)
                                                if success:
                                                    st.success(f"✅ Vacancy closed + {msg}")
                                                    st.cache_data.clear()
                                                    import time
                                                    time.sleep(2)
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ {msg}")
                                        
                                        with col2:
                                            if st.button("🔙 Cancel Closure", key="cancel_closure"):
                                                st.info("💡 Vacancy closure cancelled")
                                                st.stop()
                                
                                elif old_status.upper() == "CLOSED" and new_status.upper() != "CLOSED":
                                    # SCENARIO C: Reopening vacancy
                                    st.info("💡 Vacancy reopened. Old interview records remain closed (historical data).")
                                    st.success("✅ Vacancy updated!")
                                
                                else:
                                    # SCENARIO A or D: No status change or editing while closed
                                    st.success("✅ Vacancy updated!")
                                
                                # Clear cache and reload if not in interview selection mode
                                if not (old_status.upper() != "CLOSED" and new_status.upper() == "CLOSED" and len(active_records) > 1):
                                    st.cache_data.clear()
                                    import time
                                    time.sleep(1)
                                    st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
        else:
            st.info("No vacancies to edit")


# ========================================
# VIEW CANDIDATES (Privacy Protected)
# ========================================
def save_contact_requests(selected_indices, display_df, filtered_df):
    """Save contact requests to Contact_Requests sheet"""
    try:
        client = get_google_sheets_client()
        SHEET_ID = get_agency_sheet_id()
        
        if not client or not SHEET_ID:
            return False, "Cannot connect to Google Sheets"
        
        # Get company details from session
        company_cid = st.session_state.get("company_id", "Unknown")
        company_name = st.session_state.get("full_name", "Unknown")
        
        # Open or create Contact_Requests sheet
        spreadsheet = client.open_by_key(SHEET_ID)
        
        try:
            sheet = spreadsheet.worksheet("Contact_Requests")
        except:
            # Create sheet if doesn't exist
            sheet = spreadsheet.add_worksheet(title="Contact_Requests", rows="1000", cols="15")
            headers = [
                "Request_ID", "Company_CID", "Company_Name", "Candidate_Name", 
                "Candidate_Mobile", "Job_Preference", "Date_Requested", 
                "Status", "Agency_Action", "Date_Approved", "Notes"
            ]
            sheet.append_row(headers)
        
        # Get existing requests to generate next Request_ID
        all_data = sheet.get_all_values()
        if len(all_data) > 1:
            last_id = all_data[-1][0] if all_data[-1][0] else "REQ000"
            try:
                num = int(last_id.replace("REQ", ""))
                next_num = num + 1
            except:
                next_num = 1
        else:
            next_num = 1
        
        # Add requests for selected candidates
        added_count = 0
        for idx in selected_indices:
            if idx < len(display_df):
                display_row = display_df.iloc[idx]
                filtered_row = filtered_df.iloc[idx]
                
                request_id = f"REQ{next_num:04d}"
                candidate_name = display_row.get('First Name', 'N/A')
                
                # Get mobile from original filtered dataframe
                mobile = filtered_row.get('Mobile', filtered_row.get('Phone', 'N/A'))
                
                job_pref = display_row.get('Job Pref 1', 'N/A')
                date_requested = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                row_data = [
                    request_id,
                    company_cid,
                    company_name,
                    candidate_name,
                    mobile,
                    job_pref,
                    date_requested,
                    "Pending",
                    "",
                    "",
                    f"Requested via Company Portal"
                ]
                
                sheet.append_row(row_data)
                added_count += 1
                next_num += 1
        
        return True, f"Successfully sent {added_count} contact requests"
        
    except Exception as e:
        return False, f"Error saving requests: {str(e)}"


# ========================================
# VIEW CANDIDATES (Privacy Protected)
# ========================================
def render_view_candidates():
    """View Candidates - Limited Info for Privacy"""
    
    st.markdown("### 👥 View Candidates")
    
    st.info("💡 Full contact details available upon request to agency")
    
    # Get candidates
    candidates_df = get_candidates()
    
    if len(candidates_df) == 0:
        st.warning("No candidates found in database")
        return
    
    # Extract first names
    if 'Full Name' in candidates_df.columns:
        candidates_df['First Name'] = candidates_df['Full Name'].apply(extract_first_name)
    else:
        candidates_df['First Name'] = 'N/A'
    
    # Filters (Dropdowns)
    st.markdown("#### 🔍 Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if 'Education' in candidates_df.columns:
            edu_options = ['All'] + sorted(candidates_df['Education'].unique().tolist())
            edu_filter = st.selectbox("Education", edu_options)
        else:
            edu_filter = 'All'
    
    with col2:
        if 'Experience' in candidates_df.columns:
            exp_options = ['All'] + sorted(candidates_df['Experience'].unique().tolist())
            exp_filter = st.selectbox("Experience", exp_options)
        else:
            exp_filter = 'All'
    
    with col3:
        if 'Gender' in candidates_df.columns:
            gender_options = ['All'] + sorted(candidates_df['Gender'].unique().tolist())
            gender_filter = st.selectbox("Gender", gender_options)
        else:
            gender_filter = 'All'
    
    with col4:
        search = st.text_input("Search Skills")
    
    # Apply filters
    filtered = candidates_df.copy()
    
    # Filter out selected candidates (Status = Selected)
    if 'Status' in filtered.columns:
        filtered = filtered[filtered['Status'].astype(str).str.strip().str.upper() != 'SELECTED']
    
    if edu_filter != 'All' and 'Education' in filtered.columns:
        filtered = filtered[filtered['Education'] == edu_filter]
    
    if exp_filter != 'All' and 'Experience' in filtered.columns:
        filtered = filtered[filtered['Experience'] == exp_filter]
    
    if gender_filter != 'All' and 'Gender' in filtered.columns:
        filtered = filtered[filtered['Gender'] == gender_filter]
    
    if search and 'Skills' in filtered.columns:
        filtered = filtered[filtered['Skills'].str.contains(search, case=False, na=False)]
    
    st.write(f"**Showing {len(filtered)} / {len(candidates_df)} candidates**")
    
    st.markdown("---")
    
    # Display candidates in table with checkboxes (Job Matching style)
    if len(filtered) > 0:
        # Prepare display columns - ONLY PROFESSIONAL INFO
        display_cols = [
            'First Name',
            'Gender',
            'Age',
            'Mobile',
            'Current City',
            'Job Pref 1',
            'Job Pref 2',
            'Job Pref 3',
            'Expected Salary',
            'Experience Years',
            'Graduation Degree',
            'Computer Skills',
            'Technical Skills'
        ]
        
        # Alternative column names mapping
        alt_col_map = {
            'First Name': ['First Name', 'Full Name'],
            'Gender': ['Gender'],
            'Age': ['Age'],
            'Mobile': ['Mobile'],
            'Current City': ['Current City', 'Current_City', 'Preferred_City', 'City'],
            'Job Pref 1': ['Job Pref 1', 'Job_Preference_1', 'Job Preference 1'],
            'Job Pref 2': ['Job Pref 2', 'Job_Preference_2', 'Job Preference 2'],
            'Job Pref 3': ['Job Pref 3', 'Job_Preference_3', 'Job Preference 3'],
            'Expected Salary': ['Expected Salary', 'Expected_Salary'],
            'Experience Years': ['Experience Years', 'Experience_Years', 'Experience'],
            'Graduation Degree': ['Graduation Degree', 'Graduation_Degree', 'Education'],
            'Computer Skills': ['Computer Skills', 'Computer_Skills'],
            'Technical Skills': ['Technical Skills', 'Technical_Skills', 'Skills']
        }
        
        # Build display dataframe
        display_data = []
        original_indices = []
        
        for idx, row in filtered.iterrows():
            row_data = {}
            
            for display_col, possible_cols in alt_col_map.items():
                value = None
                for col in possible_cols:
                    if col in filtered.columns:
                        value = row.get(col)
                        
                        # Extract first name if Full Name
                        if display_col == 'First Name' and col == 'Full Name':
                            value = extract_first_name(value)
                        
                        break
                
                row_data[display_col] = value if value else 'N/A'
            
            display_data.append(row_data)
            original_indices.append(idx)
        
        display_df = pd.DataFrame(display_data)
        
        if display_df.empty:
            st.warning("⚠️ No candidate data available")
            return
        
        st.markdown("#### 📋 Candidates List")
        
        # Initialize session state for selections
        if 'selected_candidates' not in st.session_state:
            st.session_state.selected_candidates = []
        
        # Selection controls
        col1, col2, col3 = st.columns([2, 2, 6])
        
        with col1:
            if st.button("☑️ Select All", key="select_all"):
                st.session_state.selected_candidates = list(range(len(display_df)))
                st.rerun()
        
        with col2:
            if st.button("☐ Clear All", key="clear_all"):
                st.session_state.selected_candidates = []
                st.rerun()
        
        with col3:
            st.info(f"Selected: {len(st.session_state.selected_candidates)} / {len(display_df)}")
        
        st.markdown("---")
        
        # Display table with checkboxes
        for idx, row in display_df.iterrows():
            col_check, col_data = st.columns([0.5, 9.5])
            
            with col_check:
                is_selected = idx in st.session_state.selected_candidates
                if st.checkbox("", value=is_selected, key=f"cb_{idx}", label_visibility="collapsed"):
                    if idx not in st.session_state.selected_candidates:
                        st.session_state.selected_candidates.append(idx)
                else:
                    if idx in st.session_state.selected_candidates:
                        st.session_state.selected_candidates.remove(idx)
            
            with col_data:
                # Display row data
                row_text = " | ".join([f"**{col}:** {row[col]}" for col in display_df.columns[:6]])
                st.text(row_text)
                
                # Second line for remaining columns
                if len(display_df.columns) > 6:
                    row_text_2 = " | ".join([f"**{col}:** {row[col]}" for col in display_df.columns[6:]])
                    st.caption(row_text_2)
            
            st.markdown("---")
        
        # Action buttons
        st.markdown("### 📞 Request Contact Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                f"📞 Send Request for Selected ({len(st.session_state.selected_candidates)})",
                type="primary",
                disabled=len(st.session_state.selected_candidates) == 0,
                use_container_width=True,
                key="send_request_btn"
            ):
                if len(st.session_state.selected_candidates) > 0:
                    with st.spinner("📤 Sending contact requests..."):
                        success, message = save_contact_requests(
                            st.session_state.selected_candidates,
                            display_df,
                            filtered
                        )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.info("💡 Agency will review and share contact details via email")
                        st.balloons()
                        
                        # Clear selections
                        st.session_state.selected_candidates = []
                        
                        import time
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        with col2:
            if st.button(
                "📤 Export All to Interview Records",
                disabled=len(display_df) == 0,
                use_container_width=True,
                key="export_all_btn"
            ):
                st.info("💡 Export feature coming soon - will save all to Interview Records sheet")
    
    else:
        st.info("No candidates match your filters")


# ========================================
# SETTINGS (Editable + Functional Password)
# ========================================
def render_settings(company_id):
    """Settings - Editable Company Info + Functional Password Change"""
    
    st.markdown("### ⚙️ Company Settings")
    
    tab1, tab2 = st.tabs(["🏢 Company Info", "🔐 Security"])
    
    # TAB 1: Company Info (Editable)
    with tab1:
        st.markdown("#### 🏢 Company Information")
        
        try:
            companies_df = get_companies()
            company_data = companies_df[companies_df['CID'] == company_id]
            
            if not company_data.empty:
                company = company_data.iloc[0]
                
                # Read-only fields
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"**Company Name:** {company.get('Company Name', 'N/A')}")
                    st.info(f"**Industry:** {company.get('Industry', 'N/A')}")
                
                with col2:
                    st.info(f"**Registered:** {company.get('Date Added', 'N/A')}")
                
                st.markdown("---")
                st.markdown("#### ✏️ Edit Details")
                
                # Editable fields
                with st.form("edit_company_info"):
                    email = st.text_input("Email *", value=company.get('Email', ''))
                    phone = st.text_input("Contact Number *", value=company.get('Contact Number', ''))
                    address = st.text_area("Address *", value=company.get('Address of Company', ''), height=100)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        city = st.text_input("City *", value=company.get('City', ''))
                    with col2:
                        state = st.text_input("State *", value=company.get('State', ''))
                    
                    website = st.text_input("Website", value=company.get('Website', ''))
                    
                    update_btn = st.form_submit_button("💾 Update Information", type="primary")
                    
                    if update_btn:
                        if not email or not phone or not address:
                            st.error("❌ Please fill all required fields!")
                        else:
                            try:
                                client = get_google_sheets_client()
                                SHEET_ID = get_agency_sheet_id()
                                
                                if client and SHEET_ID:
                                    sheet = client.open_by_key(SHEET_ID).worksheet("CID")
                                    all_data = sheet.get_all_values()
                                    headers = all_data[0]
                                    
                                    # Find company row
                                    row_num = None
                                    for idx, row in enumerate(all_data[1:], start=2):
                                        if len(row) > 0 and row[headers.index('CID') if 'CID' in headers else 0] == company_id:
                                            row_num = idx
                                            break
                                    
                                    if row_num:
                                        # Update fields
                                        updates = []
                                        
                                        update_map = {
                                            'Email': email,
                                            'Contact Number': phone,
                                            'Address of Company': address,
                                            'City': city,
                                            'State': state,
                                            'Website': website
                                        }
                                        
                                        for field, value in update_map.items():
                                            if field in headers:
                                                col_idx = headers.index(field) + 1
                                                col_letter = chr(64 + col_idx)
                                                updates.append({
                                                    'range': f"{col_letter}{row_num}",
                                                    'values': [[value]]
                                                })
                                        
                                        if updates:
                                            sheet.batch_update(updates)
                                            st.success("✅ Information updated successfully!")
                                            st.cache_data.clear()
                                            
                                            import time
                                            time.sleep(1)
                                            st.rerun()
                                    else:
                                        st.error("❌ Company record not found")
                            except Exception as e:
                                st.error(f"❌ Update failed: {str(e)}")
            else:
                st.warning("⚠️ Company details not found")
        except Exception as e:
            st.error(f"❌ Error loading details: {str(e)}")
    
    # TAB 2: Security (Functional Password Change)
    with tab2:
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
                            sheet = client.open_by_key(SHEET_ID).worksheet("CID")
                            all_data = sheet.get_all_values()
                            headers = all_data[0]
                            
                            # Find company row
                            row_num = None
                            current_pwd_stored = None
                            
                            for idx, row in enumerate(all_data[1:], start=2):
                                if 'CID' in headers and len(row) > headers.index('CID'):
                                    if row[headers.index('CID')] == company_id:
                                        row_num = idx
                                        if 'Password' in headers:
                                            current_pwd_stored = row[headers.index('Password')]
                                        break
                            
                            if not row_num:
                                st.error("❌ Company record not found")
                            elif not current_pwd_stored:
                                st.error("❌ Password field not found in sheet")
                            elif current_password != current_pwd_stored:
                                st.error("❌ Current password is incorrect!")
                            else:
                                # Update password
                                if 'Password' in headers:
                                    pwd_col = headers.index('Password') + 1
                                    pwd_letter = chr(64 + pwd_col)
                                    
                                    sheet.update(f"{pwd_letter}{row_num}", new_password)
                                    
                                    st.success("✅ Password changed successfully!")
                                    st.info("🔐 Please use your new password for next login")
                                    st.cache_data.clear()
                                else:
                                    st.error("❌ Password column not found")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")