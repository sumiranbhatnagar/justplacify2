"""
AGENCY MANAGEMENT SYSTEM - 100% DEVELOPER INCOME
===============================================
✅ Dynamic Renewal Fee System (Renewal_Fee_1, Renewal_Fee_2 ...)
✅ Auto-creates Renewal columns in Google Sheet when due
✅ Setup Fee: ₹30K (One-time) - EDITABLE
✅ Annual Service Fee: ₹5K/Year - EDITABLE
✅ Payment Tracking with Dates
✅ Real-time Alerts & Blinking Status
✅ Collection Reports (Today, Week, Month)

SHEET COLUMNS REQUIRED:
Agency_Code, Agency_Owner, Email, Mobile, Agency_Name, Worksheet_URL,
Status, Created_Date, Created_By, Is_Active, Session_Token, Password,
Logo_URL, Registration_Fee, Monthly_Plan, Monthly_Fee_Amount,
Last_Payment_Date, Next_Due_Date, Total_Collected,
Setup_Fee_Paid, Renewal_Fee_1, Renewal_Fee_2 ... (auto-created),
Discount_Pct, Access_Status, Payment_Status
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
import time

# CONFIG
SHEET_ID = "1hXZdwIOatc_oUoX-AzAiBQywe7E4kq9IFUglMcY04_A"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']

# DEFAULT FEE STRUCTURE
DEFAULT_SETUP_FEE = 30000
DEFAULT_ANNUAL_FEE = 5000

# DEVELOPER LOGIN
DEVELOPER_USERNAME = "developer"
DEVELOPER_PASSWORD = "dev2026"


# ─────────────────────────────────────────────
# GOOGLE SHEETS CONNECTION
# ─────────────────────────────────────────────
@st.cache_resource
def get_client():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Google Sheets credentials not found in Streamlit secrets!")
            return None
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Connection Error: {str(e)}")
        return None


# ─────────────────────────────────────────────
# RENEWAL COLUMN HELPERS
# ─────────────────────────────────────────────
def get_applicable_renewals(created_date):
    """
    Created_Date ke basis par batao kitne Renewals due hain aaj tak.
    Example:
      2024-01-05 → today 2026-02-25 → 2 renewals due
      2026-01-15 → today 2026-02-25 → 0 renewals due
    """
    today = datetime.now().date()
    if pd.isna(created_date) or created_date is None:
        return 0
    try:
        if hasattr(created_date, 'date'):
            reg_date = created_date.date()
        else:
            reg_date = pd.to_datetime(created_date).date()
    except:
        return 0

    renewals_due = 0
    for i in range(1, 30):  # future-proof up to 30 years
        try:
            renewal_date = reg_date.replace(year=reg_date.year + i)
        except ValueError:
            renewal_date = reg_date.replace(year=reg_date.year + i, day=28)
        if renewal_date <= today:
            renewals_due = i
        else:
            break
    return renewals_due


def get_renewal_columns_from_sheet():
    """Sheet ke headers se saare Renewal_Fee_N columns return karo"""
    client = get_client()
    if not client:
        return []
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
        headers = sheet.row_values(1)
        renewal_cols = [h for h in headers if h.startswith('Renewal_Fee_')]
        renewal_cols.sort(key=lambda x: int(x.split('_')[-1]))
        return renewal_cols
    except:
        return []


def ensure_renewal_columns_exist(max_renewal_number):
    """
    Renewal_Fee_1 se Renewal_Fee_N tak sab columns check karo,
    jo nahi hain unhe sheet mein auto-create karo
    """
    client = get_client()
    if not client:
        return False
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
        headers = sheet.row_values(1)
        all_values = sheet.get_all_values()
        total_rows = len(all_values)

        created = []
        for i in range(1, max_renewal_number + 1):
            col_name = f"Renewal_Fee_{i}"
            if col_name not in headers:
                next_col = len(headers) + 1
                sheet.update_cell(1, next_col, col_name)
                # Fill 0 for all existing rows
                for row_idx in range(2, total_rows + 1):
                    sheet.update_cell(row_idx, next_col, 0)
                headers.append(col_name)
                created.append(col_name)

        if created:
            st.cache_data.clear()
            st.success(f"✅ Auto-created columns: {', '.join(created)}")
        return True
    except Exception as e:
        st.error(f"❌ Column create error: {str(e)}")
        return False


# ─────────────────────────────────────────────
# FEE CONFIG (fee_config sheet)
# ─────────────────────────────────────────────
def init_fee_config_sheet():
    client = get_client()
    if not client:
        return False
    try:
        spreadsheet = client.open_by_key(SHEET_ID)
        try:
            spreadsheet.worksheet("fee_config")
            return True
        except:
            fee_sheet = spreadsheet.add_worksheet("fee_config", rows=5, cols=4)
            today = datetime.now().strftime("%Y-%m-%d")
            fee_sheet.append_row(["Setting", "Value", "Active_From", "Description"])
            fee_sheet.append_row(["Setup_Fee", str(DEFAULT_SETUP_FEE), today, "One-time setup fee"])
            fee_sheet.append_row(["Annual_Fee", str(DEFAULT_ANNUAL_FEE), today, "Annual service fee"])
            st.success("✅ Created fee_config sheet")
            return True
    except Exception as e:
        st.error(f"❌ fee_config init error: {str(e)}")
        return False


@st.cache_data(ttl=60)
def load_fee_config():
    client = get_client()
    if not client:
        return {"Setup_Fee": DEFAULT_SETUP_FEE, "Annual_Fee": DEFAULT_ANNUAL_FEE}
    try:
        spreadsheet = client.open_by_key(SHEET_ID)
        try:
            fee_sheet = spreadsheet.worksheet("fee_config")
        except:
            init_fee_config_sheet()
            fee_sheet = spreadsheet.worksheet("fee_config")

        all_values = fee_sheet.get_all_values()
        if len(all_values) < 2:
            return {"Setup_Fee": DEFAULT_SETUP_FEE, "Annual_Fee": DEFAULT_ANNUAL_FEE}

        today = datetime.now().date()
        fee_config = {}
        for row in all_values[1:]:
            if len(row) >= 3:
                setting_name = row[0].strip()
                try:
                    value = int(row[1])
                    active_from_str = row[2].strip() if len(row) > 2 else None
                    active_from = None
                    if active_from_str:
                        try:
                            active_from = pd.to_datetime(active_from_str).date()
                        except:
                            active_from = today
                    if active_from is None or active_from <= today:
                        if setting_name not in fee_config or active_from >= fee_config.get(f"{setting_name}_date", today):
                            fee_config[setting_name] = value
                            fee_config[f"{setting_name}_date"] = active_from
                except:
                    pass

        if "Setup_Fee" not in fee_config:
            fee_config["Setup_Fee"] = DEFAULT_SETUP_FEE
        if "Annual_Fee" not in fee_config:
            fee_config["Annual_Fee"] = DEFAULT_ANNUAL_FEE
        return fee_config
    except Exception as e:
        st.warning(f"⚠️ Could not load fee config: {str(e)}")
        return {"Setup_Fee": DEFAULT_SETUP_FEE, "Annual_Fee": DEFAULT_ANNUAL_FEE}


def update_fee_config(setup_fee, annual_fee, active_from_date):
    client = get_client()
    if not client:
        return False
    try:
        spreadsheet = client.open_by_key(SHEET_ID)
        fee_sheet = spreadsheet.worksheet("fee_config")
        active_from_str = active_from_date.strftime("%Y-%m-%d") if isinstance(active_from_date, datetime) else str(active_from_date)
        fee_sheet.update_cell(2, 2, str(setup_fee))
        fee_sheet.update_cell(2, 3, active_from_str)
        fee_sheet.update_cell(3, 2, str(annual_fee))
        fee_sheet.update_cell(3, 3, active_from_str)
        st.cache_data.clear()
        st.success(f"✅ Fee updated! Effective from: {active_from_str}")
        return True
    except Exception as e:
        st.error(f"❌ Fee update error: {str(e)}")
        return False


# ─────────────────────────────────────────────
# LOAD AGENCIES
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_agencies():
    client = get_client()
    if not client:
        return pd.DataFrame()
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
        all_values = sheet.get_all_values()
        if len(all_values) < 2:
            return pd.DataFrame()

        headers = all_values[0]
        data = all_values[1:]

        # Handle duplicate column names
        seen = {}
        new_headers = []
        for header in headers:
            if header in seen:
                seen[header] += 1
                new_headers.append(f"{header}_{seen[header]}")
            else:
                seen[header] = 0
                new_headers.append(header)

        df = pd.DataFrame(data, columns=new_headers)
        if len(df) == 0:
            return pd.DataFrame()

        # Agency_Code column detect
        agency_cols = [col for col in df.columns if 'agency' in col.lower() or 'code' in col.lower()]
        if agency_cols:
            df = df.rename(columns={agency_cols[0]: 'Agency_Code'})
        else:
            st.error("❌ No Agency Code column found!")
            return pd.DataFrame()

        # Date columns
        date_cols = ['Last_Payment_Date', 'Next_Due_Date', 'Created_Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Numeric columns (setup fee + all renewal fees)
        base_numeric = ['Setup_Fee_Paid', 'Discount_Pct', 'Monthly_Fee_Amount', 'Total_Collected']
        renewal_cols = [col for col in df.columns if col.startswith('Renewal_Fee_')]
        all_numeric = base_numeric + renewal_cols

        for col in all_numeric:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Total Income = Setup + all Renewals
        df['Total_Income'] = df.get('Setup_Fee_Paid', pd.Series([0]*len(df))).fillna(0)
        for col in renewal_cols:
            df['Total_Income'] = df['Total_Income'] + df[col].fillna(0)

        # Status
        df['Registration_Status'] = df['Access_Status'] if 'Access_Status' in df.columns else 'Unknown'

        return df
    except Exception as e:
        st.error(f"❌ Data Load Error: {str(e)}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# UPDATE HELPERS
# ─────────────────────────────────────────────
def find_agency_row(agency_code):
    client = get_client()
    if not client:
        return None
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
        headers = sheet.row_values(1)
        agency_col_idx = None
        for idx, header in enumerate(headers):
            if 'agency' in header.lower() or 'code' in header.lower():
                agency_col_idx = idx + 1
                break
        if not agency_col_idx:
            return None
        all_values = sheet.get_all_values()
        for row_idx, row in enumerate(all_values[1:], start=2):
            if len(row) >= agency_col_idx and str(row[agency_col_idx-1]) == str(agency_code):
                return row_idx
        return None
    except:
        return None


def update_agency_field(agency_code, field_name, value):
    client = get_client()
    if not client:
        st.error("❌ No connection")
        return False
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
        headers = sheet.row_values(1)
        col_idx = None
        for idx, header in enumerate(headers):
            if header.strip() == field_name:
                col_idx = idx + 1
                break
        if not col_idx:
            st.error(f"❌ Column '{field_name}' not found")
            return False
        row_num = find_agency_row(agency_code)
        if not row_num:
            st.error(f"❌ Agency '{agency_code}' not found")
            return False
        col_letter = ""
        temp = col_idx
        while temp > 0:
            temp, remainder = divmod(temp - 1, 26)
            col_letter = chr(65 + remainder) + col_letter
        cell_address = f"{col_letter}{row_num}"
        sheet.update(cell_address, value)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ Update failed: {str(e)}")
        return False


def update_multiple_fields(agency_code, field_dict):
    """Update multiple fields at once for an agency"""
    success = True
    for field_name, value in field_dict.items():
        result = update_agency_field(agency_code, field_name, value)
        if not result:
            success = False
    return success


# ─────────────────────────────────────────────
# COLLECTION SUMMARY
# ─────────────────────────────────────────────
def get_collection_by_period(df):
    today = pd.Timestamp(datetime.now().date())
    week_ago = pd.Timestamp(datetime.now().date() - timedelta(days=7))
    month_ago = pd.Timestamp(datetime.now().date() - timedelta(days=30))
    results = {'Today': 0, 'This Week': 0, 'This Month': 0, 'Total': 0}

    if 'Last_Payment_Date' in df.columns and len(df) > 0:
        try:
            df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'], errors='coerce')
            df_valid = df.dropna(subset=['Last_Payment_Date'])
            if len(df_valid) > 0:
                results['Today'] = df_valid[df_valid['Last_Payment_Date'] >= today]['Total_Income'].sum()
                results['This Week'] = df_valid[
                    (df_valid['Last_Payment_Date'] >= week_ago) &
                    (df_valid['Last_Payment_Date'] < today + timedelta(days=1))
                ]['Total_Income'].sum()
                results['This Month'] = df_valid[
                    (df_valid['Last_Payment_Date'] >= month_ago) &
                    (df_valid['Last_Payment_Date'] < today + timedelta(days=1))
                ]['Total_Income'].sum()
        except:
            pass
    results['Total'] = df['Total_Income'].sum() if 'Total_Income' in df.columns else 0
    return {k: (v if not pd.isna(v) else 0) for k, v in results.items()}


# ─────────────────────────────────────────────
# BILL TABLE CSS
# ─────────────────────────────────────────────
BILL_CSS = """
<style>
.bill-header-cell {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 12px; border-radius: 4px;
    font-weight: bold; text-align: center;
}
.bill-label-cell {
    background-color: #f8f9ff; padding: 12px; border-radius: 4px;
    font-weight: 600; border: 1px solid #e0e0e0;
}
.bill-data-cell {
    background-color: #ffffff; padding: 12px; border-radius: 4px;
    text-align: right; border: 1px solid #e0e0e0;
}
.bill-notdue-cell {
    background-color: #f0f0f0; padding: 12px; border-radius: 4px;
    text-align: center; border: 1px dashed #ccc; color: #999;
    font-style: italic;
}
.bill-total-cell {
    background: linear-gradient(135deg, #00bcd4 0%, #0097a7 100%);
    color: white; padding: 14px; border-radius: 4px;
    font-weight: bold; text-align: center;
}
</style>
"""


def render_bill_header(mode="add"):
    """Render bill table header row"""
    col4_label = "Received Now (₹)" if mode == "add" else "Edit Fee (₹)"
    col5_label = "Discount (₹)"
    cols = st.columns([1.2, 1, 1, 1, 1, 1, 1])
    labels = ["Fee Type", "Scheduled (₹)", "Already Paid (₹)", col4_label,
              col5_label, "Total Received (₹)", "Balance Due (₹)"]
    for col, label in zip(cols, labels):
        with col:
            st.markdown(f'<div class="bill-header-cell">{label}</div>', unsafe_allow_html=True)


def render_bill_row_notdue(label, scheduled):
    """Render a row for fees not yet due"""
    cols = st.columns([1.2, 1, 1, 1, 1, 1, 1])
    with cols[0]:
        st.markdown(f'<div class="bill-label-cell" style="opacity:0.5;">{label}</div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'<div class="bill-notdue-cell">{scheduled:,}</div>', unsafe_allow_html=True)
    for c in cols[2:]:
        with c:
            st.markdown('<div class="bill-notdue-cell">Not Due Yet</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────
def main():
    st.set_page_config(page_title="💼 Agency Management", layout="wide")

    # Load fees
    if "fee_config" not in st.session_state:
        fee_config = load_fee_config()
        st.session_state.fee_config = fee_config
        st.session_state.SETUP_FEE = fee_config["Setup_Fee"]
        st.session_state.ANNUAL_FEE = fee_config["Annual_Fee"]

    # CSS
    st.markdown("""
    <style>
    .header {
        background: linear-gradient(135deg, #e8f0f8 0%, #f0e8f8 100%);
        padding: 2rem; border-radius: 20px; color: #4a5568;
        text-align: center; margin-bottom: 2rem; border: 1px solid #d9dce9;
    }
    .metric {
        background: white; padding: 2rem 1.5rem; border-radius: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center;
        border-left: 4px solid #cbd5e0; width: 100%; min-height: 140px;
        display: flex; flex-direction: column; justify-content: center;
    }
    .metric h2 { color: #4a5568; font-size: 2.5rem; margin: 0.5rem 0; font-weight: 700; }
    .metric p { color: #718096; margin: 0.5rem 0 0 0; font-size: 1.1rem; font-weight: 500; }
    .alert-blink {
        background: #fed7d7; color: #742a2a; padding: 2rem 1.5rem;
        border-radius: 10px; border: 1px solid #fc8181;
        animation: blink 1s infinite; font-weight: bold; width: 100%;
        min-height: 140px; display: flex; align-items: center;
        justify-content: center; font-size: 1.1rem;
    }
    @keyframes blink { 50% { opacity: 0.6; } }
    </style>
    """ + BILL_CSS, unsafe_allow_html=True)

    st.markdown('<div class="header"><h1>💼 Agency Management System</h1>'
                '<p>Setup ₹30K + Annual Renewal Fee System</p></div>',
                unsafe_allow_html=True)

    # LOGIN
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.warning("🔒 Developer Login Required")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            user = st.text_input("👤 Username")
            pwd = st.text_input("🔒 Password", type="password")
            if st.button("🚀 Login", type="primary", use_container_width=True):
                if user == DEVELOPER_USERNAME and pwd == DEVELOPER_PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials!")
        return

    # Load data
    df = load_agencies()
    if df.empty:
        st.error("❌ Failed to load agencies.")
        st.stop()

    # Auto-check renewal columns needed
    if 'Created_Date' in df.columns:
        max_renewals = df['Created_Date'].apply(get_applicable_renewals).max()
        if max_renewals > 0:
            ensure_renewal_columns_exist(int(max_renewals))

    # Renewal columns in df
    renewal_cols_in_df = sorted(
        [col for col in df.columns if col.startswith('Renewal_Fee_')],
        key=lambda x: int(x.split('_')[-1])
    )

    # SIDEBAR
    with st.sidebar:
        st.title("📋 Navigation")
        page = st.radio("Select Page:",
                        ["📊 Dashboard", "🏢 Agencies", "💳 Payments", "⚙️ Settings"],
                        key="nav_radio")
        st.divider()
        st.markdown(f"**Login:** {DEVELOPER_USERNAME}")
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # ─────────────────────────────────────────
    # PAGE 1: DASHBOARD
    # ─────────────────────────────────────────
    if page == "📊 Dashboard":
        st.subheader("📊 Revenue Overview")
        collections = get_collection_by_period(df)

        col1, col2, col3, col4 = st.columns(4)
        for col, key in zip([col1, col2, col3, col4],
                            ['Today', 'This Week', 'This Month', 'Total']):
            with col:
                st.markdown(f"""<div class="metric">
                    <h2>₹{collections[key]:,.0f}</h2>
                    <p>{key}</p>
                </div>""", unsafe_allow_html=True)

        st.divider()
        col1, col2, col3 = st.columns(3)
        total_agencies = len(df)
        setup_pending = len(df[df.get('Setup_Fee_Paid', pd.Series([0]*len(df))).fillna(0) == 0])
        unregistered = len(df[df['Registration_Status'].fillna('').str.contains(
            'Pending|Unregistered', na=False, case=False)])

        with col1:
            st.markdown(f'<div class="metric"><h2>{total_agencies}</h2><p>Total Agencies</p></div>',
                        unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric"><h2>{setup_pending}</h2><p>Setup Pending</p></div>',
                        unsafe_allow_html=True)
        with col3:
            if unregistered > 0:
                st.markdown(f'<div class="alert-blink">⚠️ {unregistered} Agency(ies) Not Registered</div>',
                            unsafe_allow_html=True)
            else:
                st.markdown('<div class="metric"><h2>✅ All Registered</h2></div>',
                            unsafe_allow_html=True)

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            status_revenue = df.groupby('Registration_Status')['Total_Income'].sum().reset_index()
            if not status_revenue.empty:
                fig = px.pie(status_revenue, names='Registration_Status', values='Total_Income',
                             title="Revenue by Registration Status",
                             color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'])
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            top_agencies = df.nlargest(8, 'Total_Income')
            if not top_agencies.empty:
                fig = px.bar(top_agencies, x='Agency_Code', y='Total_Income',
                             title="Top 8 Agencies by Revenue",
                             color='Total_Income',
                             color_continuous_scale=['#667eea', '#764ba2'])
                st.plotly_chart(fig, use_container_width=True)

    # ─────────────────────────────────────────
    # PAGE 2: AGENCIES
    # ─────────────────────────────────────────
    if page == "🏢 Agencies":
        st.subheader("🏢 All Agencies")
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Filter by Status",
                ["All"] + list(df['Registration_Status'].unique()))
        with col2:
            search = st.text_input("🔍 Search Agency Code or Name")
        with col3:
            sort_by = st.selectbox("Sort By", ["Total Income", "Agency Code", "Setup Fee"])

        filtered_df = df.copy()
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['Registration_Status'] == status_filter]
        if search:
            filtered_df = filtered_df[
                filtered_df['Agency_Code'].astype(str).str.contains(search, case=False, na=False)]
        if sort_by == "Total Income":
            filtered_df = filtered_df.sort_values('Total_Income', ascending=False)
        elif sort_by == "Setup Fee":
            filtered_df = filtered_df.sort_values('Setup_Fee_Paid', ascending=False)

        display_cols = ['Agency_Code']
        if 'Agency_Name' in filtered_df.columns:
            display_cols.append('Agency_Name')
        display_cols.append('Setup_Fee_Paid')
        display_cols += renewal_cols_in_df
        display_cols += ['Discount_Pct', 'Total_Income', 'Registration_Status']
        if 'Last_Payment_Date' in filtered_df.columns:
            display_cols.append('Last_Payment_Date')
        display_cols = [c for c in display_cols if c in filtered_df.columns]

        col_config = {
            "Setup_Fee_Paid": st.column_config.NumberColumn("Setup (₹)", format="₹%,.0f"),
            "Total_Income": st.column_config.NumberColumn("Total Income", format="₹%,.0f"),
            "Discount_Pct": st.column_config.NumberColumn("Discount %", format="%d%%"),
        }
        for rc in renewal_cols_in_df:
            num = rc.split('_')[-1]
            col_config[rc] = st.column_config.NumberColumn(f"Renewal {num} (₹)", format="₹%,.0f")

        st.dataframe(filtered_df[display_cols], use_container_width=True,
                     column_config=col_config, hide_index=True)

        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Data", data=csv,
                           file_name=f"agencies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                           mime="text/csv")

    # ─────────────────────────────────────────
    # PAGE 3: PAYMENTS
    # ─────────────────────────────────────────
    if page == "💳 Payments":
        if "payment_operation" not in st.session_state:
            st.session_state.payment_operation = "view"

        op_col1, op_col2, op_col3, op_col4 = st.columns(4)
        current_op = st.session_state.get("payment_operation", "view")

        with op_col1:
            if st.button("👁️ View Fee", use_container_width=True,
                         type="primary" if current_op == "view" else "secondary", key="btn_view"):
                st.session_state.payment_operation = "view"; st.rerun()
        with op_col2:
            if st.button("➕ Add Fee", use_container_width=True,
                         type="primary" if current_op == "add" else "secondary", key="btn_add"):
                st.session_state.payment_operation = "add"; st.rerun()
        with op_col3:
            if st.button("✏️ Edit Fee", use_container_width=True,
                         type="primary" if current_op == "edit" else "secondary", key="btn_edit"):
                st.session_state.payment_operation = "edit"; st.rerun()
        with op_col4:
            if st.button("🗑️ Delete Fee", use_container_width=True,
                         type="primary" if current_op == "delete" else "secondary", key="btn_delete"):
                st.session_state.payment_operation = "delete"; st.rerun()

        st.divider()

        # ── VIEW ──────────────────────────────
        if current_op == "view":
            st.markdown("### View Fee Details")
            agency_list = sorted(df['Agency_Code'].unique())
            selected = st.selectbox("Select Agency", agency_list, key="view_agency")

            if selected:
                agency_row = df[df['Agency_Code'] == selected].iloc[0]
                created_date = agency_row.get('Created_Date')
                num_renewals = get_applicable_renewals(created_date)

                st.markdown("#### Agency Details")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Agency Code", str(agency_row.get('Agency_Code', '')))
                with c2:
                    st.metric("Registration Status", str(agency_row.get('Access_Status', 'N/A')))
                with c3:
                    disc = agency_row.get('Discount_Pct', 0)
                    st.metric("Discount", f"{int(disc) if pd.notna(disc) else 0}%")

                if pd.notna(created_date):
                    st.info(f"📅 Created Date: {pd.to_datetime(created_date).strftime('%d-%b-%Y')} | "
                            f"Renewals Due: {num_renewals}")
                else:
                    st.warning("⚠️ Created Date not set")

                st.divider()
                st.markdown("#### Fee Breakdown")

                SETUP = st.session_state.SETUP_FEE
                ANNUAL = st.session_state.ANNUAL_FEE
                disc_pct = int(agency_row.get('Discount_Pct', 0)) if pd.notna(agency_row.get('Discount_Pct')) else 0
                setup_paid = int(agency_row.get('Setup_Fee_Paid', 0)) if pd.notna(agency_row.get('Setup_Fee_Paid')) else 0
                disc_amt = int((SETUP * disc_pct) / 100)
                setup_balance = SETUP - setup_paid - disc_amt

                fee_data = {
                    "Fee Type": ["Setup Fee (One-time)"],
                    "Scheduled (₹)": [SETUP],
                    "Received (₹)": [setup_paid],
                    "Discount (₹)": [disc_amt],
                    "Balance (₹)": [max(0, setup_balance)]
                }

                total_scheduled = SETUP
                total_received = setup_paid
                total_disc = disc_amt
                total_balance = max(0, setup_balance)

                for i in range(1, num_renewals + 1):
                    col_name = f"Renewal_Fee_{i}"
                    paid = int(agency_row.get(col_name, 0)) if pd.notna(agency_row.get(col_name)) else 0
                    bal = max(0, ANNUAL - paid)
                    fee_data["Fee Type"].append(f"Renewal {i}")
                    fee_data["Scheduled (₹)"].append(ANNUAL)
                    fee_data["Received (₹)"].append(paid)
                    fee_data["Discount (₹)"].append(0)
                    fee_data["Balance (₹)"].append(bal)
                    total_scheduled += ANNUAL
                    total_received += paid
                    total_balance += bal

                # Total row
                fee_data["Fee Type"].append("TOTAL")
                fee_data["Scheduled (₹)"].append(total_scheduled)
                fee_data["Received (₹)"].append(total_received)
                fee_data["Discount (₹)"].append(total_disc)
                fee_data["Balance (₹)"].append(total_balance)

                fee_df = pd.DataFrame(fee_data)

                def highlight_rows(row):
                    if row['Fee Type'] == 'TOTAL':
                        return ['background-color: #e8f4fd; font-weight: bold;'] * len(row)
                    elif row['Balance (₹)'] > 0:
                        return ['background-color: #fff3cd;'] * len(row)
                    else:
                        return ['background-color: #d4edda;'] * len(row)

                st.dataframe(fee_df.style.apply(highlight_rows, axis=1),
                             hide_index=True, use_container_width=True)

                if num_renewals == 0:
                    st.info("ℹ️ No renewal fees due yet. Annual fee will appear after 1 year from Created Date.")

        # ── ADD FEE ────────────────────────────
        elif current_op == "add":
            st.markdown("### Add New Fee Receipt")
            agency_list = sorted(df['Agency_Code'].unique())
            add_agency = st.selectbox("Select Agency", agency_list, key="add_agency")

            if add_agency:
                agency_row = df[df['Agency_Code'] == add_agency].iloc[0]
                created_date = agency_row.get('Created_Date')
                num_renewals = get_applicable_renewals(created_date)

                SETUP = st.session_state.SETUP_FEE
                ANNUAL = st.session_state.ANNUAL_FEE
                setup_already = int(agency_row.get('Setup_Fee_Paid', 0)) if pd.notna(agency_row.get('Setup_Fee_Paid')) else 0

                if pd.notna(created_date):
                    st.info(f"📅 Created: {pd.to_datetime(created_date).strftime('%d-%b-%Y')} | "
                            f"Renewals Due: {num_renewals}")

                st.markdown("#### Fee Receipt Entry")
                render_bill_header(mode="add")

                # Setup Fee Row
                cols = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                with cols[0]: st.markdown('<div class="bill-label-cell">Setup Fee (One-time)</div>', unsafe_allow_html=True)
                with cols[1]: st.markdown(f'<div class="bill-data-cell">{SETUP:,}</div>', unsafe_allow_html=True)
                with cols[2]: st.markdown(f'<div class="bill-data-cell">{setup_already:,}</div>', unsafe_allow_html=True)
                with cols[3]:
                    setup_now = st.number_input("s_now", min_value=0, step=100, value=0,
                                                key="add_setup_now", label_visibility="collapsed")
                with cols[4]:
                    setup_disc = st.number_input("s_disc", min_value=0, step=100, value=0,
                                                 key="add_setup_disc", label_visibility="collapsed")
                with cols[5]:
                    setup_total = setup_already + setup_now
                    st.markdown(f'<div class="bill-data-cell">{setup_total:,}</div>', unsafe_allow_html=True)
                with cols[6]:
                    setup_bal = max(0, SETUP - setup_total - setup_disc)
                    st.markdown(f'<div class="bill-data-cell">{setup_bal:,}</div>', unsafe_allow_html=True)

                # Renewal rows
                renewal_nows = {}
                renewal_discs = {}
                renewal_totals = {}
                renewal_bals = {}

                for i in range(1, num_renewals + 1):
                    col_name = f"Renewal_Fee_{i}"
                    already = int(agency_row.get(col_name, 0)) if pd.notna(agency_row.get(col_name)) else 0
                    cols = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with cols[0]: st.markdown(f'<div class="bill-label-cell">Renewal {i}</div>', unsafe_allow_html=True)
                    with cols[1]: st.markdown(f'<div class="bill-data-cell">{ANNUAL:,}</div>', unsafe_allow_html=True)
                    with cols[2]: st.markdown(f'<div class="bill-data-cell">{already:,}</div>', unsafe_allow_html=True)
                    with cols[3]:
                        r_now = st.number_input(f"r{i}_now", min_value=0, step=100, value=0,
                                                key=f"add_r{i}_now", label_visibility="collapsed")
                    with cols[4]:
                        r_disc = st.number_input(f"r{i}_disc", min_value=0, step=100, value=0,
                                                 key=f"add_r{i}_disc", label_visibility="collapsed")
                    with cols[5]:
                        r_total = already + r_now
                        st.markdown(f'<div class="bill-data-cell">{r_total:,}</div>', unsafe_allow_html=True)
                    with cols[6]:
                        r_bal = max(0, ANNUAL - r_total - r_disc)
                        st.markdown(f'<div class="bill-data-cell">{r_bal:,}</div>', unsafe_allow_html=True)
                    renewal_nows[i] = r_now
                    renewal_discs[i] = r_disc
                    renewal_totals[i] = r_total
                    renewal_bals[i] = r_bal

                # Future renewal — not due yet
                if num_renewals == 0:
                    render_bill_row_notdue("Renewal 1 (Not Due Yet)", ANNUAL)
                else:
                    render_bill_row_notdue(f"Renewal {num_renewals+1} (Not Due Yet)", ANNUAL)

                # TOTAL row
                total_now = setup_now + sum(renewal_nows.values())
                total_already = setup_already + sum(
                    int(agency_row.get(f"Renewal_Fee_{i}", 0))
                    for i in range(1, num_renewals + 1)
                    if pd.notna(agency_row.get(f"Renewal_Fee_{i}"))
                )
                total_collected = total_already + total_now
                total_disc_all = setup_disc + sum(renewal_discs.values())
                total_bal = setup_bal + sum(renewal_bals.values())

                cols = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                total_sched = SETUP + (ANNUAL * num_renewals)
                for col, val in zip(cols, ["TOTAL", f"₹{total_sched:,}", f"₹{total_already:,}",
                                           f"₹{total_now:,}", f"₹{total_disc_all:,}",
                                           f"₹{total_collected:,}", f"₹{total_bal:,}"]):
                    with col:
                        st.markdown(f'<div class="bill-total-cell">{val}</div>', unsafe_allow_html=True)

                st.divider()
                tc1, tc2, tc3 = st.columns(3)
                with tc1:
                    pay_method = st.selectbox("Payment Method",
                        ["Cash", "Cheque", "UPI", "Bank Transfer", "Net Banking", "Other"],
                        key="add_pay_method")
                with tc2:
                    if pay_method in ["UPI", "Bank Transfer", "Net Banking"]:
                        txn_id = st.text_input("Transaction ID", key="add_txn_id")
                    else:
                        st.caption(f"✓ {pay_method} - No ID needed")
                with tc3:
                    st.text_input("Notes", key="add_notes")

                st.divider()
                s1, s2 = st.columns(2)
                with s1: st.metric("Total Received Now", f"₹{total_now:,}")
                with s2: st.metric("Balance Due", f"₹{total_bal:,}")

                # ✅ SAVE BUTTON — actually saves to Google Sheets
                if st.button("💾 Save All Receipts", type="primary",
                             use_container_width=True, key="save_add"):
                    if total_now > 0:
                        try:
                            fields_to_update = {}
                            if setup_now > 0:
                                fields_to_update['Setup_Fee_Paid'] = setup_already + setup_now
                            for i in range(1, num_renewals + 1):
                                if renewal_nows[i] > 0:
                                    col_name = f"Renewal_Fee_{i}"
                                    old_val = int(agency_row.get(col_name, 0)) if pd.notna(agency_row.get(col_name)) else 0
                                    fields_to_update[col_name] = old_val + renewal_nows[i]
                            fields_to_update['Last_Payment_Date'] = datetime.now().strftime("%Y-%m-%d")

                            with st.spinner("Saving to Google Sheet..."):
                                success = update_multiple_fields(add_agency, fields_to_update)

                            if success:
                                st.success(f"✅ Saved! {add_agency} — ₹{total_now:,} received")
                                time.sleep(1)
                                st.cache_data.clear()
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Save error: {str(e)}")
                    else:
                        st.warning("⚠️ Please enter at least one amount")

        # ── EDIT FEE ───────────────────────────
        elif current_op == "edit":
            st.markdown("### Edit Fee Receipt")
            agency_list = sorted(df['Agency_Code'].unique())
            edit_agency = st.selectbox("Select Agency", agency_list, key="edit_agency")

            if edit_agency:
                agency_row = df[df['Agency_Code'] == edit_agency].iloc[0]
                created_date = agency_row.get('Created_Date')
                num_renewals = get_applicable_renewals(created_date)

                SETUP = st.session_state.SETUP_FEE
                ANNUAL = st.session_state.ANNUAL_FEE
                setup_already = int(agency_row.get('Setup_Fee_Paid', 0)) if pd.notna(agency_row.get('Setup_Fee_Paid')) else 0

                if pd.notna(created_date):
                    st.info(f"📅 Created: {pd.to_datetime(created_date).strftime('%d-%b-%Y')} | "
                            f"Renewals Due: {num_renewals}")

                st.markdown("#### Edit Fee Entry (Yellow = Editable)")
                render_bill_header(mode="edit")

                # Setup Fee
                cols = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                with cols[0]: st.markdown('<div class="bill-label-cell">Setup Fee (One-time)</div>', unsafe_allow_html=True)
                with cols[1]: st.markdown(f'<div class="bill-data-cell">{SETUP:,}</div>', unsafe_allow_html=True)
                with cols[2]: st.markdown(f'<div class="bill-data-cell">{setup_already:,}</div>', unsafe_allow_html=True)
                with cols[3]:
                    setup_edit = st.number_input("s_edit", min_value=0, step=100, value=setup_already,
                                                 key=f"edit_setup_{edit_agency}", label_visibility="collapsed")
                with cols[4]:
                    setup_disc_e = st.number_input("s_disc_e", min_value=0, step=100, value=0,
                                                   key=f"edit_setup_disc_{edit_agency}", label_visibility="collapsed")
                with cols[5]:
                    st.markdown(f'<div class="bill-data-cell">{setup_edit:,}</div>', unsafe_allow_html=True)
                with cols[6]:
                    setup_bal_e = SETUP - setup_edit - setup_disc_e
                    color = "red" if setup_bal_e < 0 else "green"
                    st.markdown(f'<div class="bill-data-cell" style="color:{color};">₹{setup_bal_e:,}</div>',
                                unsafe_allow_html=True)

                # Renewal rows
                renewal_edits = {}
                renewal_disc_edits = {}

                for i in range(1, num_renewals + 1):
                    col_name = f"Renewal_Fee_{i}"
                    already = int(agency_row.get(col_name, 0)) if pd.notna(agency_row.get(col_name)) else 0
                    cols = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with cols[0]: st.markdown(f'<div class="bill-label-cell">Renewal {i}</div>', unsafe_allow_html=True)
                    with cols[1]: st.markdown(f'<div class="bill-data-cell">{ANNUAL:,}</div>', unsafe_allow_html=True)
                    with cols[2]: st.markdown(f'<div class="bill-data-cell">{already:,}</div>', unsafe_allow_html=True)
                    with cols[3]:
                        r_edit = st.number_input(f"r{i}_edit", min_value=0, step=100, value=already,
                                                 key=f"edit_r{i}_{edit_agency}", label_visibility="collapsed")
                    with cols[4]:
                        r_disc_e = st.number_input(f"r{i}_disc_e", min_value=0, step=100, value=0,
                                                   key=f"edit_r{i}_disc_{edit_agency}", label_visibility="collapsed")
                    with cols[5]:
                        st.markdown(f'<div class="bill-data-cell">{r_edit:,}</div>', unsafe_allow_html=True)
                    with cols[6]:
                        r_bal_e = ANNUAL - r_edit - r_disc_e
                        color = "red" if r_bal_e < 0 else "green"
                        st.markdown(f'<div class="bill-data-cell" style="color:{color};">₹{r_bal_e:,}</div>',
                                    unsafe_allow_html=True)
                    renewal_edits[i] = r_edit
                    renewal_disc_edits[i] = r_disc_e

                # Future not due
                render_bill_row_notdue(
                    f"Renewal {num_renewals+1} (Not Due Yet)" if num_renewals > 0 else "Renewal 1 (Not Due Yet)",
                    ANNUAL)

                # TOTAL
                total_sched = SETUP + (ANNUAL * num_renewals)
                total_collected_e = setup_edit + sum(renewal_edits.values())
                total_disc_e = setup_disc_e + sum(renewal_disc_edits.values())
                total_bal_e = total_sched - total_collected_e - total_disc_e
                total_already_e = setup_already + sum(
                    int(agency_row.get(f"Renewal_Fee_{i}", 0))
                    for i in range(1, num_renewals + 1)
                    if pd.notna(agency_row.get(f"Renewal_Fee_{i}"))
                )

                cols = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                for col, val in zip(cols, ["TOTAL", f"₹{total_sched:,}", f"₹{total_already_e:,}",
                                           f"₹{total_collected_e:,}", f"₹{total_disc_e:,}",
                                           f"₹{total_collected_e:,}", f"₹{total_bal_e:,}"]):
                    with col:
                        st.markdown(f'<div class="bill-total-cell">{val}</div>', unsafe_allow_html=True)

                st.divider()
                tc1, tc2, tc3 = st.columns(3)
                with tc1:
                    pay_method_e = st.selectbox("Payment Method",
                        ["Cash", "Cheque", "UPI", "Bank Transfer", "Net Banking", "Other"],
                        key="edit_pay_method")
                with tc2:
                    if pay_method_e in ["UPI", "Bank Transfer", "Net Banking"]:
                        st.text_input("Transaction ID", key="edit_txn_id")
                with tc3:
                    pay_date_e = st.date_input("Payment Date",
                        value=datetime.now().date(), key="edit_pay_date")

                st.text_area("Notes", key="edit_notes")
                st.divider()

                sc1, sc2 = st.columns(2)
                with sc1: st.metric("Total Received", f"₹{total_collected_e:,}")
                with sc2: st.metric("Balance Due", f"₹{total_bal_e:,}")

                b1, b2 = st.columns(2)
                with b1:
                    if st.button("💾 Save Changes", type="primary",
                                 use_container_width=True, key="save_edit"):
                        try:
                            fields = {'Setup_Fee_Paid': setup_edit}
                            for i in range(1, num_renewals + 1):
                                fields[f"Renewal_Fee_{i}"] = renewal_edits[i]
                            max_disc = max([setup_disc_e] + list(renewal_disc_edits.values()))
                            fields['Discount_Pct'] = max_disc
                            fields['Last_Payment_Date'] = pay_date_e.strftime("%Y-%m-%d")

                            with st.spinner("Saving..."):
                                success = update_multiple_fields(edit_agency, fields)
                            if success:
                                st.success(f"✅ Updated {edit_agency} successfully!")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                with b2:
                    if st.button("Cancel", use_container_width=True, key="cancel_edit"):
                        st.info("Changes cancelled")

        # ── DELETE FEE ─────────────────────────
        elif current_op == "delete":
            st.markdown("### Delete Fee Entry")
            st.warning("⚠️ This will reset the selected fee to 0 permanently")

            dc1, dc2 = st.columns(2)
            with dc1:
                del_agency = st.selectbox("Select Agency",
                    sorted(df['Agency_Code'].unique()), key="del_agency")

            fee_options = ["Setup Fee (Setup_Fee_Paid)"]
            for i in range(1, len(renewal_cols_in_df) + 1):
                fee_options.append(f"Renewal {i} (Renewal_Fee_{i})")

            with dc2:
                del_fee_type = st.selectbox("Fee Type to Reset", fee_options, key="del_fee_type")

            if del_agency:
                agency_row = df[df['Agency_Code'] == del_agency].iloc[0]
                if "Setup_Fee_Paid" in del_fee_type:
                    col_name = "Setup_Fee_Paid"
                else:
                    idx = int(del_fee_type.split("Renewal ")[1].split(" ")[0])
                    col_name = f"Renewal_Fee_{idx}"

                current_val = int(agency_row.get(col_name, 0)) if pd.notna(agency_row.get(col_name)) else 0
                st.metric("Current Value", f"₹{current_val:,}")
                st.text_input("Reason for deletion", key="del_reason")

                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Cancel", use_container_width=True, key="cancel_del"):
                        st.info("Cancelled")
                with b2:
                    if st.button("🗑️ Reset to 0", type="primary",
                                 use_container_width=True, key="confirm_del"):
                        with st.spinner("Deleting..."):
                            success = update_agency_field(del_agency, col_name, 0)
                        if success:
                            st.success(f"✅ {col_name} reset to 0 for {del_agency}")
                            time.sleep(1)
                            st.rerun()

    # ─────────────────────────────────────────
    # PAGE 4: SETTINGS
    # ─────────────────────────────────────────
    if page == "⚙️ Settings":
        st.subheader("⚙️ System Settings")

        st.markdown("### 🔐 Developer Credentials (Hardcoded)")
        st.info(f"**Username:** `{DEVELOPER_USERNAME}` | **Password:** `{DEVELOPER_PASSWORD}`")

        st.divider()
        st.markdown("### Fee Configuration")
        c1, c2 = st.columns(2)
        with c1: st.metric("Current Setup Fee", f"₹{st.session_state.SETUP_FEE:,}")
        with c2: st.metric("Current Annual Renewal Fee", f"₹{st.session_state.ANNUAL_FEE:,}")

        st.divider()
        st.markdown("### Edit Fee Structure")
        c1, c2, c3 = st.columns(3)
        with c1:
            new_setup = st.number_input("Setup Fee (₹)", value=st.session_state.SETUP_FEE,
                                        min_value=1000, step=1000)
        with c2:
            new_annual = st.number_input("Annual Renewal Fee (₹)", value=st.session_state.ANNUAL_FEE,
                                         min_value=100, step=100)
        with c3:
            active_from = st.date_input("Effective From", value=datetime.now().date())

        if st.button("💾 Save Fee Configuration", type="primary", use_container_width=True):
            if update_fee_config(new_setup, new_annual, active_from):
                st.session_state.SETUP_FEE = new_setup
                st.session_state.ANNUAL_FEE = new_annual
                st.rerun()

        st.divider()
        st.markdown("### Renewal Column Status")
        existing_renewals = get_renewal_columns_from_sheet()
        if existing_renewals:
            st.success(f"✅ Renewal columns in sheet: {', '.join(existing_renewals)}")
        else:
            st.warning("⚠️ No Renewal_Fee columns found yet. They will auto-create when agencies become due.")

        st.divider()
        st.markdown("### System Status")
        client = get_client()
        if client:
            st.success("✅ Google Sheets Connected")
        else:
            st.error("❌ Google Sheets Not Connected")

        st.info(f"**Last Refresh:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"**Sheet ID:** {SHEET_ID}")

        if st.button("🔄 Force Refresh All Data"):
            st.cache_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()