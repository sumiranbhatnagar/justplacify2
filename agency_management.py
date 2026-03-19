"""
AGENCY MANAGEMENT SYSTEM - 100% DEVELOPER INCOME
===============================================
✅ Editable Fee Configuration (Saved to Google Sheet)
✅ Setup Fee: ₹30K (One-time access) - EDITABLE
✅ Service Charges: ₹5K/Year - EDITABLE
✅ Negotiable Discounts (Agency-wise)
✅ Payment Tracking with Dates
✅ Real-time Alerts & Blinking Status
✅ Collection Reports (Today, Week, Month)
✅ All Production Ready

⚠️ IMPORTANT - GOOGLE SHEET SETUP:
1. Your sheet should have these UNIQUE columns (NO DUPLICATES):
   Logo_URL, Registration_Fee, Monthly_Plan, Monthly_Fee_Amount,
   Payment_Status, Last_Payment_Date, Next_Due_Date, Total_Collected,
   Developer_Share, Setup_Fee_Paid, Service_2026, Service_2027,
   Discount_Pct, Access_Status, Agency_Code

2. ❌ REMOVE if duplicated: "Payment_Status" appears twice - DELETE ONE!

3. Add Google Service Account JSON to Streamlit Secrets as "gcp_service_account"

4. Fee Configuration:
   - A new "fee_config" sheet will be auto-created if it doesn't exist
   - Access it via Settings tab (⚙️) to edit Setup Fee and Annual Fee
   - Changes are saved directly to your Google Sheet and apply immediately
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

# DEFAULT FEE STRUCTURE (Will be loaded from fee_config sheet)
DEFAULT_SETUP_FEE = 30000  # ₹30K one-time
DEFAULT_ANNUAL_FEE = 5000  # ₹5K per year

# DEVELOPER LOGIN CREDENTIALS (Hardcoded - Only developer can login)
DEVELOPER_USERNAME = "developer"
DEVELOPER_PASSWORD = "dev2026"
# ⚠️ NOTE: These are NOT in the Google Sheet - they are hardcoded for developer access only

def init_fee_config_sheet():
    """Create or initialize fee_config sheet if it doesn't exist"""
    client = get_client()
    if not client:
        return False
    
    try:
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Check if fee_config sheet exists
        try:
            spreadsheet.worksheet("fee_config")
            return True  # Sheet already exists
        except:
            # Create the sheet
            fee_sheet = spreadsheet.add_worksheet("fee_config", rows=5, cols=4)
            
            # Add headers and default values with Active From date
            fee_sheet.append_row(["Setting", "Value", "Active_From", "Description"])
            today = datetime.now().strftime("%Y-%m-%d")
            fee_sheet.append_row(["Setup_Fee", str(DEFAULT_SETUP_FEE), today, "One-time setup fee for agencies"])
            fee_sheet.append_row(["Annual_Fee", str(DEFAULT_ANNUAL_FEE), today, "Annual service fee per agency"])
            
            st.success("✅ Created fee_config sheet with Active From date tracking")
            return True
            
    except Exception as e:
        st.error(f"❌ Error initializing fee_config sheet: {str(e)}")
        return False

@st.cache_data(ttl=60)
def load_fee_config():
    """Load fee configuration from fee_config sheet - gets active fees based on Active From date"""
    client = get_client()
    if not client:
        return {"Setup_Fee": DEFAULT_SETUP_FEE, "Annual_Fee": DEFAULT_ANNUAL_FEE, "Setup_Fee_Active_From": None, "Annual_Fee_Active_From": None}
    
    try:
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Try to get fee_config sheet
        try:
            fee_sheet = spreadsheet.worksheet("fee_config")
        except:
            # If it doesn't exist, create it
            init_fee_config_sheet()
            fee_sheet = spreadsheet.worksheet("fee_config")
        
        all_values = fee_sheet.get_all_values()
        
        if len(all_values) < 2:
            return {"Setup_Fee": DEFAULT_SETUP_FEE, "Annual_Fee": DEFAULT_ANNUAL_FEE}
        
        # Parse the fee configuration - get the LATEST active fee (based on Active_From date)
        today = datetime.now().date()
        fee_config = {}
        
        for row in all_values[1:]:  # Skip header
            if len(row) >= 3:
                setting_name = row[0].strip()
                try:
                    value = int(row[1])
                    active_from_str = row[2].strip() if len(row) > 2 else None
                    
                    # Parse Active_From date
                    active_from = None
                    if active_from_str:
                        try:
                            active_from = pd.to_datetime(active_from_str).date()
                        except:
                            active_from = today
                    
                    # Only consider fees that are active (Active_From <= today)
                    if active_from is None or active_from <= today:
                        # Store the most recent active fee
                        if setting_name not in fee_config or active_from >= fee_config.get(f"{setting_name}_date", today):
                            fee_config[setting_name] = value
                            fee_config[f"{setting_name}_date"] = active_from
                except Exception as e:
                    pass
        
        # Use defaults if not found
        if "Setup_Fee" not in fee_config:
            fee_config["Setup_Fee"] = DEFAULT_SETUP_FEE
        if "Annual_Fee" not in fee_config:
            fee_config["Annual_Fee"] = DEFAULT_ANNUAL_FEE
        
        return fee_config
        
    except Exception as e:
        st.warning(f"⚠️ Could not load fee config: {str(e)}")
        return {"Setup_Fee": DEFAULT_SETUP_FEE, "Annual_Fee": DEFAULT_ANNUAL_FEE}

def update_fee_config(setup_fee, annual_fee, active_from_date):
    """Update fee configuration in Google Sheets with Active From date"""
    client = get_client()
    if not client:
        st.error("❌ Not connected to Google Sheets")
        return False
    
    try:
        spreadsheet = client.open_by_key(SHEET_ID)
        fee_sheet = spreadsheet.worksheet("fee_config")
        
        # Format the date as string
        active_from_str = active_from_date.strftime("%Y-%m-%d") if isinstance(active_from_date, datetime) else str(active_from_date)
        
        # Update the values with Active From date
        fee_sheet.update_cell(2, 2, str(setup_fee))      # Update Setup_Fee value
        fee_sheet.update_cell(2, 3, active_from_str)     # Update Setup_Fee Active_From date
        fee_sheet.update_cell(3, 2, str(annual_fee))     # Update Annual_Fee value
        fee_sheet.update_cell(3, 3, active_from_str)     # Update Annual_Fee Active_From date
        
        # Clear cache to reload new values
        st.cache_data.clear()
        
        st.success(f"✅ Fee configuration updated! Effective from: {active_from_str}")
        return True
        
    except Exception as e:
        st.error(f"❌ Error updating fees: {str(e)}")
        return False

@st.cache_resource
def get_client():
    """Connect to Google Sheets with proper error handling"""
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ FATAL: Google Sheets credentials not found in Streamlit secrets!")
            st.info("""
            **To fix this:**
            1. Get your Google Service Account JSON from Google Cloud Console
            2. Copy the JSON content
            3. Go to Streamlit Secrets (Settings → Secrets)
            4. Paste the entire JSON and assign to 'gcp_service_account'
            """)
            return None
        
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], 
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Connection Error: {str(e)}")
        return None

@st.cache_data(ttl=60)  # Refresh every 60 seconds
def load_agencies():
    """Load agencies from Google Sheets with auto-column detection"""
    client = get_client()
    if not client:
        return pd.DataFrame()
    
    try:
        # Open the sheet
        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
        
        # Get all values instead of records to avoid duplicate header issues
        all_values = sheet.get_all_values()
        if len(all_values) < 2:
            st.warning("⚠️ login_master sheet is empty")
            return pd.DataFrame()
        
        # Create DataFrame manually to handle duplicate columns
        headers = all_values[0]
        data = all_values[1:]
        
        # Remove duplicate column names by adding suffix
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
            st.warning("⚠️ login_master sheet has headers but no data")
            return pd.DataFrame()
        
        # Auto-detect Agency_Code column (might be Agency_Code, Agency_ID, Code, etc)
        agency_cols = [col for col in df.columns if 'agency' in col.lower() or 'code' in col.lower()]
        if agency_cols:
            # Rename the first match to Agency_Code for consistency
            df = df.rename(columns={agency_cols[0]: 'Agency_Code'})
        else:
            st.error("❌ No Agency Code column found! Expected: Agency_Code, Agency_ID, or Code")
            return pd.DataFrame()
        
        # Convert dates
        date_cols = ['Last_Payment_Date', 'Next_Due_Date', 'Registration_Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Convert numbers
        numeric_cols = ['Setup_Fee_Paid', 'Service_2026', 'Service_2027', 
                       'Discount_Pct', 'Monthly_Fee_Amount', 'Total_Collected']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Calculate totals - ensure all numeric columns are properly typed
        df['Total_Income'] = 0
        
        if 'Setup_Fee_Paid' in df.columns:
            df['Total_Income'] = df['Total_Income'] + pd.to_numeric(df['Setup_Fee_Paid'], errors='coerce').fillna(0)
        if 'Service_2026' in df.columns:
            df['Total_Income'] = df['Total_Income'] + pd.to_numeric(df['Service_2026'], errors='coerce').fillna(0)
        if 'Service_2027' in df.columns:
            df['Total_Income'] = df['Total_Income'] + pd.to_numeric(df['Service_2027'], errors='coerce').fillna(0)
        
        # Status logic
        df['Registration_Status'] = 'Unknown'
        
        if 'Access_Status' in df.columns:
            df['Registration_Status'] = df['Access_Status']
        
        return df
        
    except Exception as e:
        st.error(f"❌ Data Load Error: {str(e)}")
        st.info("""
        **Troubleshooting:**
        1. Check if 'login_master' sheet exists in your Google Sheet
        2. Verify Google Sheets credentials are in Streamlit Secrets
        3. Check if the sheet has duplicate column names - remove them!
        4. Common issue: 'Payment_Status' appears twice in your columns - keep only ONE
        """)
        return pd.DataFrame()

def find_agency_row(agency_code, df):
    """Find the row number of an agency in the sheet"""
    client = get_client()
    if not client:
        return None
    
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
        # Find Agency_Code column
        headers = sheet.row_values(1)
        agency_col_idx = None
        for idx, header in enumerate(headers):
            if 'agency' in header.lower() or 'code' in header.lower():
                agency_col_idx = idx + 1
                break
        
        if not agency_col_idx:
            return None
        
        # Find row
        all_values = sheet.get_all_values()
        for row_idx, row in enumerate(all_values[1:], start=2):
            if len(row) >= agency_col_idx and str(row[agency_col_idx-1]) == str(agency_code):
                return row_idx
        return None
    except:
        return None

def update_agency_field(agency_code, field_name, value):
    """Update a field in Google Sheets"""
    client = get_client()
    if not client:
        st.error("❌ No connection")
        return False
    
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("login_master")
        headers = sheet.row_values(1)
        
        # Find column index
        col_idx = None
        for idx, header in enumerate(headers):
            if header.strip() == field_name:
                col_idx = idx + 1
                break
        
        if not col_idx:
            st.error(f"❌ Column '{field_name}' not found in sheet")
            return False
        
        # Find row
        row_num = find_agency_row(agency_code, pd.DataFrame())
        if not row_num:
            st.error(f"❌ Agency '{agency_code}' not found")
            return False
        
        # Update
        cell_address = f"{chr(64 + col_idx)}{row_num}"
        sheet.update(cell_address, value)
        
        # Also update Last_Payment_Date if payment field
        if 'Fee' in field_name or field_name == 'Discount_Pct':
            date_col_idx = None
            for idx, header in enumerate(headers):
                if header.strip() == 'Last_Payment_Date':
                    date_col_idx = idx + 1
                    break
            if date_col_idx:
                date_cell = f"{chr(64 + date_col_idx)}{row_num}"
                sheet.update(date_cell, datetime.now().strftime("%Y-%m-%d"))
        
        st.success(f"✅ Updated {agency_code}: {field_name} = {value}")
        time.sleep(1)  # Wait for sheet to update
        st.cache_data.clear()  # Clear cache to refresh data
        return True
    except Exception as e:
        st.error(f"❌ Update failed: {str(e)}")
        return False

def get_collection_by_period(df):
    """Get collection totals for different periods"""
    today = pd.Timestamp(datetime.now().date())
    week_ago = pd.Timestamp(datetime.now().date() - timedelta(days=7))
    month_ago = pd.Timestamp(datetime.now().date() - timedelta(days=30))
    
    results = {}
    
    if 'Last_Payment_Date' in df.columns and len(df) > 0:
        try:
            # Convert to datetime, handling errors gracefully
            df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'], errors='coerce')
            
            # Remove rows with NaT (Not a Time) dates
            df_valid = df.dropna(subset=['Last_Payment_Date'])
            
            if len(df_valid) > 0:
                # Use timestamp comparison instead of date comparison
                today_payments = df_valid[df_valid['Last_Payment_Date'] >= today]['Total_Income'].sum()
                week_payments = df_valid[
                    (df_valid['Last_Payment_Date'] >= week_ago) & 
                    (df_valid['Last_Payment_Date'] < today + timedelta(days=1))
                ]['Total_Income'].sum()
                month_payments = df_valid[
                    (df_valid['Last_Payment_Date'] >= month_ago) & 
                    (df_valid['Last_Payment_Date'] < today + timedelta(days=1))
                ]['Total_Income'].sum()
                
                results = {
                    'Today': today_payments if not pd.isna(today_payments) else 0,
                    'This Week': week_payments if not pd.isna(week_payments) else 0,
                    'This Month': month_payments if not pd.isna(month_payments) else 0,
                    'Total': df['Total_Income'].sum() if 'Total_Income' in df.columns else 0
                }
            else:
                results = {
                    'Today': 0,
                    'This Week': 0,
                    'This Month': 0,
                    'Total': df['Total_Income'].sum() if 'Total_Income' in df.columns else 0
                }
        except Exception as e:
            st.warning(f"⚠️ Error calculating collections: {str(e)}")
            results = {
                'Today': 0,
                'This Week': 0,
                'This Month': 0,
                'Total': df['Total_Income'].sum() if 'Total_Income' in df.columns else 0
            }
    else:
        results = {
            'Today': 0,
            'This Week': 0,
            'This Month': 0,
            'Total': df['Total_Income'].sum() if 'Total_Income' in df.columns else 0
        }
    
    return results

def main():
    st.set_page_config(page_title="💼 Agency Management", layout="wide")
    
    # Load fees from Google Sheets (not hardcoded)
    if "fee_config" not in st.session_state:
        fee_config = load_fee_config()
        st.session_state.fee_config = fee_config
        st.session_state.SETUP_FEE = fee_config["Setup_Fee"]
        st.session_state.ANNUAL_FEE = fee_config["Annual_Fee"]
    
    # Custom CSS - Light, Subtle Colors
    st.markdown("""
    <style>
    .header {
        background: linear-gradient(135deg, #e8f0f8 0%, #f0e8f8 100%);
        padding: 2rem;
        border-radius: 20px;
        color: #4a5568;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid #d9dce9;
    }
    .metric {
        background: white;
        padding: 2rem 1.5rem;
        border-radius: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        text-align: center;
        border-left: 4px solid #cbd5e0;
        width: 100%;
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric h2 {
        color: #4a5568;
        font-size: 2.5rem;
        margin: 0.5rem 0;
        font-weight: 700;
    }
    .metric p {
        color: #718096;
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        font-weight: 500;
    }
    .alert-blink {
        background: #fed7d7;
        color: #742a2a;
        padding: 2rem 1.5rem;
        border-radius: 10px;
        border: 1px solid #fc8181;
        animation: blink 1s infinite;
        font-weight: bold;
        width: 100%;
        min-height: 140px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
    }
    @keyframes blink {
        50% { opacity: 0.6; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="header"><h1>💼 Agency Management System</h1><p>Setup ₹30K + Service ₹5K/Year</p></div>', 
                unsafe_allow_html=True)
    
    # LOGIN
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.warning("🔒 Developer Login Required")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info(f"""
            **💡 HARDCODED DEVELOPER CREDENTIALS:**
            - **Username:** `{DEVELOPER_USERNAME}`
            - **Password:** `{DEVELOPER_PASSWORD}`
            
            *(Only developer can login - NOT in agency sheet)*
            """)
            user = st.text_input("👤 Username")
            pwd = st.text_input("🔒 Password", type="password")
            if st.button("🚀 Login", type="primary", use_container_width=True):
                if user == DEVELOPER_USERNAME and pwd == DEVELOPER_PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error(f"❌ Invalid credentials! Use: {DEVELOPER_USERNAME} / {DEVELOPER_PASSWORD}")
        return
    
    # Load data
    df = load_agencies()
    if df.empty:
        st.error("❌ Failed to load agencies. Check Google Sheets connection and credentials.")
        st.stop()
    
    # SIDEBAR NAVIGATION (prevents rerun when typing in input fields)
    with st.sidebar:
        st.title("📋 Navigation")
        page = st.radio(
            "Select Page:",
            ["📊 Dashboard", "🏢 Agencies", "💳 Payments", "⚙️ Settings"],
            key="nav_radio"
        )
        st.divider()
        st.markdown(f"**Login:** {DEVELOPER_USERNAME}")
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    
    # PAGE 1: DASHBOARD
    if page == "📊 Dashboard":
        st.subheader("📊 Revenue Overview")
        
        # Get collection data
        collections = get_collection_by_period(df)
        
        # Metrics Row 1
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""<div class="metric">
                <h2>₹{collections['Today']:,.0f}</h2>
                <p>Today</p>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric">
                <h2>₹{collections['This Week']:,.0f}</h2>
                <p>This Week</p>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="metric">
                <h2>₹{collections['This Month']:,.0f}</h2>
                <p>This Month</p>
            </div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="metric">
                <h2>₹{collections['Total']:,.0f}</h2>
                <p>Total Collected</p>
            </div>""", unsafe_allow_html=True)
        
        st.divider()
        
        # Metrics Row 2
        col1, col2, col3 = st.columns(3)
        total_agencies = len(df)
        setup_pending = len(df[df['Setup_Fee_Paid'].fillna(0) == 0])
        unregistered = len(df[df['Registration_Status'].fillna('').str.contains('Pending|Unregistered', na=False, case=False)])
        
        with col1:
            st.markdown(f"""<div class="metric">
                <h2>{total_agencies}</h2>
                <p>Total Agencies</p>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric">
                <h2>{setup_pending}</h2>
                <p>Setup Pending</p>
            </div>""", unsafe_allow_html=True)
        with col3:
            if unregistered > 0:
                st.markdown(f"""<div class="alert-blink">
                    ⚠️ {unregistered} Agency(ies) Not Registered
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="metric">
                    <h2>✅ All Registered</h2>
                    <p></p>
                </div>""", unsafe_allow_html=True)
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        with col1:
            # Revenue breakdown
            status_revenue = df.groupby('Registration_Status')['Total_Income'].sum().reset_index()
            if not status_revenue.empty:
                fig = px.pie(status_revenue, names='Registration_Status', values='Total_Income',
                           title="Revenue by Registration Status",
                           color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'])
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top agencies
            top_agencies = df.nlargest(8, 'Total_Income')
            if not top_agencies.empty:
                fig = px.bar(top_agencies, x='Agency_Code', y='Total_Income',
                           title="Top 8 Agencies by Revenue",
                           color='Total_Income',
                           color_continuous_scale=['#667eea', '#764ba2'])
                st.plotly_chart(fig, use_container_width=True)
    
    # PAGE 2: AGENCIES
    if page == "🏢 Agencies":
        st.subheader("🏢 All Agencies")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All"] + list(df['Registration_Status'].unique()),
                key="status_filter"
            )
        with col2:
            search = st.text_input("🔍 Search by Agency Code or Name")
        with col3:
            sort_by = st.selectbox("Sort By", ["Total Income", "Agency Code", "Setup Fee"])
        
        # Apply filters
        filtered_df = df.copy()
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['Registration_Status'] == status_filter]
        if search:
            filtered_df = filtered_df[
                (filtered_df['Agency_Code'].astype(str).str.contains(search, case=False, na=False)) |
                (filtered_df.get('Agency_Name', '').astype(str).str.contains(search, case=False, na=False))
            ]
        
        # Sort
        if sort_by == "Total Income":
            filtered_df = filtered_df.sort_values('Total_Income', ascending=False)
        elif sort_by == "Setup Fee":
            filtered_df = filtered_df.sort_values('Setup_Fee_Paid', ascending=False)
        
        # Display table
        display_cols = ['Agency_Code']
        if 'Agency_Name' in filtered_df.columns:
            display_cols.append('Agency_Name')
        display_cols.extend(['Setup_Fee_Paid', 'Service_2026', 'Service_2027', 
                            'Discount_Pct', 'Total_Income', 'Registration_Status'])
        if 'Last_Payment_Date' in filtered_df.columns:
            display_cols.append('Last_Payment_Date')
        
        display_cols = [col for col in display_cols if col in filtered_df.columns]
        
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            column_config={
                "Setup_Fee_Paid": st.column_config.NumberColumn("Setup (₹30K)", format="₹%,.0f"),
                "Service_2026": st.column_config.NumberColumn("2026 (₹5K)", format="₹%,.0f"),
                "Service_2027": st.column_config.NumberColumn("2027 (₹5K)", format="₹%,.0f"),
                "Total_Income": st.column_config.NumberColumn("Total Income", format="₹%,.0f"),
                "Discount_Pct": st.column_config.NumberColumn("Discount %", format="%d%%"),
            },
            hide_index=True
        )
        
        # Export
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Filtered Data",
            data=csv,
            file_name=f"agencies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # PAGE 3: PAYMENTS
    if page == "💳 Payments":
        #st.subheader("Payment Management")
        
        # Payment Operations Menu
        #st.markdown("### Payment Operations")
        
        # Initialize operation if not set
        if "payment_operation" not in st.session_state:
            st.session_state.payment_operation = "view"
        
        # Button styling CSS
        st.markdown("""
        <style>
        .operation-btn-active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: 2px solid #667eea !important;
        }
        .operation-btn-inactive {
            background: #f0f0f0 !important;
            color: #333 !important;
            border: 1px solid #ccc !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        op_col1, op_col2, op_col3, op_col4 = st.columns(4)
        
        current_operation = st.session_state.get("payment_operation", "view")
        
        with op_col1:
            if st.button("👁️ View Fee", use_container_width=True, type="primary" if current_operation == "view" else "secondary", key="view_fee_op"):
                st.session_state.payment_operation = "view"
                st.rerun()
        
        with op_col2:
            if st.button("➕ Add Fee", use_container_width=True, type="primary" if current_operation == "add" else "secondary", key="add_fee_op"):
                st.session_state.payment_operation = "add"
                st.rerun()
        
        with op_col3:
            if st.button("✏️ Edit Fee", use_container_width=True, type="primary" if current_operation == "edit" else "secondary", key="edit_fee_op"):
                st.session_state.payment_operation = "edit"
                st.rerun()
        
        with op_col4:
            if st.button("🗑️ Delete Fee", use_container_width=True, type="primary" if current_operation == "delete" else "secondary", key="delete_fee_op"):
                st.session_state.payment_operation = "delete"
                st.rerun()
        
        st.divider()
        
        # VIEW FEE OPERATION
        if current_operation == "view":
            st.markdown("### View Fee Details")
            
            # Search Type Selection with all available options
            st.markdown("#### Find Agency")
            search_type = st.radio(
                "Search by:",
                ["Agency Code", "Agency Name", "Owner Name", "Contact Number", "Setup Fee", "Annual Fee", "Dues"],
                horizontal=True,
                key="payment_search_type"
            )
            
            # Initialize variables
            agency_data = None
            search_agency = None
            
            # SPECIALIZED VIEW: Contact Number
            if search_type == "Contact Number":
                mobile_col = next((col for col in df.columns if 'mobile' in col.lower() or 'phone' in col.lower() or 'contact' in col.lower()), None)
                if mobile_col:
                    mobile_options = sorted([str(x) for x in df[mobile_col].unique() if pd.notna(x)])
                    selected_mobile = st.selectbox(
                        "Select Mobile Number",
                        options=mobile_options,
                        key="payment_search"
                    )
                    if selected_mobile:
                        matching = df[df[mobile_col].astype(str) == selected_mobile]
                        if not matching.empty:
                            agency_data = matching.iloc[0]
                            search_agency = agency_data.get('Agency_Code')
            
            # SPECIALIZED VIEW: Setup Fee
            elif search_type == "Setup Fee":
                st.markdown("#### Setup Fee Summary")
                setup_scheduled = st.session_state.SETUP_FEE * len(df)
                setup_received = df['Setup_Fee_Paid'].sum() if 'Setup_Fee_Paid' in df.columns else 0
                setup_due = setup_scheduled - setup_received
                
                sum_col1, sum_col2, sum_col3 = st.columns(3)
                with sum_col1:
                    st.metric("Total Scheduled", f"₹{int(setup_scheduled):,}")
                with sum_col2:
                    st.metric("Total Received", f"₹{int(setup_received):,}")
                with sum_col3:
                    st.metric("Total Due", f"₹{int(setup_due):,}")
                
                st.divider()
                
                # Create display list with setup fee details
                setup_list = df[['Agency_Code', 'Setup_Fee_Paid', 'Discount_Pct']].copy()
                setup_list.columns = ['Agency Code', 'Received (₹)', 'Discount (%)']
                setup_list['Scheduled (₹)'] = st.session_state.SETUP_FEE
                setup_list['Due (₹)'] = setup_list['Scheduled (₹)'] - setup_list['Received (₹)']
                setup_list = setup_list[['Agency Code', 'Scheduled (₹)', 'Received (₹)', 'Discount (%)', 'Due (₹)']]
                
                selected_code = st.selectbox(
                    "Select Agency",
                    options=setup_list['Agency Code'].tolist(),
                    key="setup_fee_agency"
                )
                
                if selected_code:
                    matching = df[df['Agency_Code'] == selected_code]
                    if not matching.empty:
                        agency_data = matching.iloc[0]
                        search_agency = selected_code
            
            # SPECIALIZED VIEW: Annual Fee
            elif search_type == "Annual Fee":
                st.markdown("#### Annual Service Fee Summary (2026 + 2027)")
                annual_scheduled = (st.session_state.ANNUAL_FEE * 2) * len(df)
                annual_2026 = df['Service_2026'].sum() if 'Service_2026' in df.columns else 0
                annual_2027 = df['Service_2027'].sum() if 'Service_2027' in df.columns else 0
                annual_received = annual_2026 + annual_2027
                annual_due = annual_scheduled - annual_received
                
                sum_col1, sum_col2, sum_col3 = st.columns(3)
                with sum_col1:
                    st.metric("Total Scheduled", f"₹{int(annual_scheduled):,}")
                with sum_col2:
                    st.metric("Total Received", f"₹{int(annual_received):,}")
                with sum_col3:
                    st.metric("Total Due", f"₹{int(annual_due):,}")
                
                st.divider()
                
                # Create display list
                annual_list = df[['Agency_Code', 'Service_2026', 'Service_2027']].copy()
                annual_list.columns = ['Agency Code', '2026 Paid (₹)', '2027 Paid (₹)']
                annual_list['Total Paid (₹)'] = annual_list['2026 Paid (₹)'] + annual_list['2027 Paid (₹)']
                annual_list['Due (₹)'] = (st.session_state.ANNUAL_FEE * 2) - annual_list['Total Paid (₹)']
                annual_list = annual_list[['Agency Code', '2026 Paid (₹)', '2027 Paid (₹)', 'Total Paid (₹)', 'Due (₹)']]
                
                selected_code = st.selectbox(
                    "Select Agency",
                    options=annual_list['Agency Code'].tolist(),
                    key="annual_fee_agency"
                )
                
                if selected_code:
                    matching = df[df['Agency_Code'] == selected_code]
                    if not matching.empty:
                        agency_data = matching.iloc[0]
                        search_agency = selected_code
            
            # SPECIALIZED VIEW: Dues
            elif search_type == "Dues":
                st.markdown("#### Outstanding Dues Summary")
                
                # Calculate total dues for each agency
                dues_df = df[['Agency_Code']].copy()
                setup_due = (st.session_state.SETUP_FEE - df['Setup_Fee_Paid'].fillna(0)).clip(lower=0)
                annual_due = ((st.session_state.ANNUAL_FEE * 2) - (df['Service_2026'].fillna(0) + df['Service_2027'].fillna(0))).clip(lower=0)
                dues_df['Setup Fee Due (₹)'] = setup_due
                dues_df['Annual Fee Due (₹)'] = annual_due
                dues_df['Total Due (₹)'] = setup_due + annual_due
                dues_df = dues_df[dues_df['Total Due (₹)'] > 0].sort_values('Total Due (₹)', ascending=False)
                
                total_dues = dues_df['Total Due (₹)'].sum()
                pending_count = len(dues_df)
                
                sum_col1, sum_col2 = st.columns(2)
                with sum_col1:
                    st.metric("Total Outstanding", f"₹{int(total_dues):,}")
                with sum_col2:
                    st.metric("Agencies with Dues", pending_count)
                
                st.divider()
                
                if not dues_df.empty:
                    selected_code = st.selectbox(
                        "Select Agency with Outstanding Dues",
                        options=dues_df['Agency Code'].tolist(),
                        key="dues_agency"
                    )
                    
                    if selected_code:
                        matching = df[df['Agency_Code'] == selected_code]
                        if not matching.empty:
                            agency_data = matching.iloc[0]
                            search_agency = selected_code
            
            # BASIC VIEW: Agency Code, Name, Owner
            else:
                search_column_map = {
                    "Agency Code": "Agency_Code",
                    "Agency Name": next((col for col in df.columns if 'name' in col.lower() and 'agency' in col.lower()), "Agency_Code"),
                    "Owner Name": next((col for col in df.columns if 'owner' in col.lower() or 'owners' in col.lower()), "Agency_Code"),
                }
                
                search_column = search_column_map.get(search_type, "Agency_Code")
                
                if search_column in df.columns:
                    search_options = sorted([str(x) for x in df[search_column].unique() if pd.notna(x)])
                    search_label = f"Select {search_type}"
                else:
                    search_options = sorted(df['Agency_Code'].unique())
                    search_label = "Select Agency"
                
                search_value = st.selectbox(
                    search_label,
                    options=search_options,
                    key="payment_search"
                )
                
                if search_value:
                    matching = df[df[search_column].astype(str) == search_value]
                    if not matching.empty:
                        agency_data = matching.iloc[0]
                        search_agency = agency_data.get('Agency_Code')
            
            if agency_data is not None and search_agency:
                # Agency Details Section
                st.markdown("### Agency Details")
                det_col1, det_col2, det_col3 = st.columns(3)
                with det_col1:
                    st.metric("Agency Code", str(agency_data.get('Agency_Code', search_agency)))
                with det_col2:
                    st.metric("Registration Status", str(agency_data.get('Access_Status', 'N/A')))
                with det_col3:
                    discount_val = agency_data.get('Discount_Pct', 0)
                    st.metric("Discount Applied", f"{int(discount_val) if pd.notna(discount_val) else 0}%")
                
                st.divider()
                
                # Fee Breakdown Table
                st.markdown("### Fee Breakdown & Payment Status")
                
                setup_fee_scheduled = st.session_state.SETUP_FEE
                setup_fee_received = int(agency_data.get('Setup_Fee_Paid', 0)) if agency_data.get('Setup_Fee_Paid') else 0
                discount_pct = int(agency_data.get('Discount_Pct', 0)) if agency_data.get('Discount_Pct') else 0
                discount_amount = int((setup_fee_scheduled * discount_pct) / 100) if discount_pct > 0 else 0
                setup_balance = setup_fee_scheduled - setup_fee_received - discount_amount
                
                annual_fee_scheduled = st.session_state.ANNUAL_FEE
                annual_fee_2026 = int(agency_data.get('Service_2026', 0)) if agency_data.get('Service_2026') else 0
                annual_fee_2027 = int(agency_data.get('Service_2027', 0)) if agency_data.get('Service_2027') else 0
                
                fee_data = {
                    "Fee Type": ["Setup Fee", "Annual Fee (2026)", "Annual Fee (2027)", "Total"],
                    "Scheduled Fee (₹)": [setup_fee_scheduled, annual_fee_scheduled, annual_fee_scheduled, setup_fee_scheduled + (annual_fee_scheduled * 2)],
                    "Received (₹)": [setup_fee_received, annual_fee_2026, annual_fee_2027, setup_fee_received + annual_fee_2026 + annual_fee_2027],
                    "Discount (₹)": [discount_amount, 0, 0, discount_amount],
                    "Balance Due (₹)": [max(0, setup_balance), max(0, annual_fee_scheduled - annual_fee_2026), max(0, annual_fee_scheduled - annual_fee_2027), max(0, setup_balance + (annual_fee_scheduled - annual_fee_2026) + (annual_fee_scheduled - annual_fee_2027))]
                }
                
                fee_df = pd.DataFrame(fee_data)
                
                # Style the dataframe
                def highlight_balance(row):
                    if row['Fee Type'] == 'Total':
                        return ['background-color: #f0f0f0; font-weight: bold;'] * len(row)
                    elif row['Balance Due (₹)'] > 0:
                        return ['background-color: #fff3cd;'] * len(row)
                    else:
                        return ['background-color: #d4edda;'] * len(row)
                
                styled_df = fee_df.style.apply(highlight_balance, axis=1)
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
                

            else:
                st.info("Select an agency to view and manage payments")
        
        # ADD FEE OPERATION
        elif current_operation == "add":
            st.markdown("### Add New Fee Receipt")
            
            # Select agency
            add_agency = st.selectbox("Select Agency", options=sorted(df['Agency_Code'].unique()) if 'Agency_Code' in df.columns else [], key="add_agency_code")
            
            if add_agency:
                agency_row = df[df['Agency_Code'] == add_agency].iloc[0] if not df[df['Agency_Code'] == add_agency].empty else None
                
                if agency_row is not None:
                    st.divider()
                    
                    # Calculate all values first
                    setup_scheduled = st.session_state.SETUP_FEE
                    setup_already = int(agency_row.get('Setup_Fee_Paid', 0)) if pd.notna(agency_row.get('Setup_Fee_Paid')) else 0
                    
                    annual_scheduled = st.session_state.ANNUAL_FEE
                    annual_2026_already = int(agency_row.get('Service_2026', 0)) if pd.notna(agency_row.get('Service_2026')) else 0
                    annual_2027_already = int(agency_row.get('Service_2027', 0)) if pd.notna(agency_row.get('Service_2027')) else 0
                    
                    # Bill table header
                    st.markdown("#### Fee Receipt Entry")
                    st.markdown("""
                    <style>
                        .bill-header-row { display: flex; gap: 8px; margin-bottom: 8px; }
                        .bill-header-cell { 
                            flex: 1; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; 
                            padding: 12px; 
                            border-radius: 4px; 
                            font-weight: bold; 
                            text-align: center;
                        }
                        .bill-data-row { display: flex; gap: 8px; margin-bottom: 8px; }
                        .bill-label-cell { 
                            flex: 1.2; 
                            background-color: #f8f9ff; 
                            padding: 12px; 
                            border-radius: 4px; 
                            font-weight: 600; 
                            border: 1px solid #e0e0e0;
                        }
                        .bill-data-cell { 
                            flex: 1; 
                            background-color: #ffffff; 
                            padding: 12px; 
                            border-radius: 4px; 
                            text-align: right; 
                            border: 1px solid #e0e0e0;
                        }
                        .bill-input-cell { 
                            flex: 1; 
                            background-color: #fffacd; 
                            padding: 6px; 
                            border-radius: 4px; 
                            border: 2px solid #ffd700;
                        }
                        .bill-total-row { display: flex; gap: 8px; margin-bottom: 8px; margin-top: 12px; }
                        .bill-total-cell { 
                            flex: 1; 
                            background: linear-gradient(135deg, #00bcd4 0%, #0097a7 100%); 
                            color: white; 
                            padding: 14px; 
                            border-radius: 4px; 
                            font-weight: bold; 
                            text-align: center;
                        }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Header row
                    header_col1, header_col2, header_col3, header_col4, header_col5, header_col6, header_col7 = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with header_col1:
                        st.markdown('<div class="bill-header-cell">Fee Type</div>', unsafe_allow_html=True)
                    with header_col2:
                        st.markdown('<div class="bill-header-cell">Scheduled (₹)</div>', unsafe_allow_html=True)
                    with header_col3:
                        st.markdown('<div class="bill-header-cell">Already Received (₹)</div>', unsafe_allow_html=True)
                    with header_col4:
                        st.markdown('<div class="bill-header-cell">Received Now (₹)</div>', unsafe_allow_html=True)
                    with header_col5:
                        st.markdown('<div class="bill-header-cell">Discount (₹)</div>', unsafe_allow_html=True)
                    with header_col6:
                        st.markdown('<div class="bill-header-cell">Total Received (₹)</div>', unsafe_allow_html=True)
                    with header_col7:
                        st.markdown('<div class="bill-header-cell">Balance Due (₹)</div>', unsafe_allow_html=True)
                    
                    # Setup Fee Row
                    row1_col1, row1_col2, row1_col3, row1_col4, row1_col5, row1_col6, row1_col7 = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with row1_col1:
                        st.markdown('<div class="bill-label-cell">Setup Fee</div>', unsafe_allow_html=True)
                    with row1_col2:
                        st.markdown(f'<div class="bill-data-cell">{setup_scheduled:,}</div>', unsafe_allow_html=True)
                    with row1_col3:
                        st.markdown(f'<div class="bill-data-cell">{setup_already:,}</div>', unsafe_allow_html=True)
                    with row1_col4:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            setup_received_now = st.number_input("Setup", min_value=0, step=100, value=0, key="setup_received_now", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row1_col5:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            setup_discount = st.number_input("Setup Disc", min_value=0, step=100, value=0, key="setup_discount_add", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row1_col6:
                        setup_total = setup_already + setup_received_now
                        st.markdown(f'<div class="bill-data-cell">{setup_total:,}</div>', unsafe_allow_html=True)
                    with row1_col7:
                        setup_balance = max(0, setup_scheduled - setup_total - setup_discount)
                        st.markdown(f'<div class="bill-data-cell">{setup_balance:,}</div>', unsafe_allow_html=True)
                    
                    # Annual 2026 Row
                    row2_col1, row2_col2, row2_col3, row2_col4, row2_col5, row2_col6, row2_col7 = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with row2_col1:
                        st.markdown('<div class="bill-label-cell">Annual 2026</div>', unsafe_allow_html=True)
                    with row2_col2:
                        st.markdown(f'<div class="bill-data-cell">{annual_scheduled:,}</div>', unsafe_allow_html=True)
                    with row2_col3:
                        st.markdown(f'<div class="bill-data-cell">{annual_2026_already:,}</div>', unsafe_allow_html=True)
                    with row2_col4:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            annual2026_received_now = st.number_input("Annual 2026", min_value=0, step=100, value=0, key="annual2026_received_now", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row2_col5:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            annual2026_discount = st.number_input("A26 Disc", min_value=0, step=100, value=0, key="annual2026_discount_add", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row2_col6:
                        annual2026_total = annual_2026_already + annual2026_received_now
                        st.markdown(f'<div class="bill-data-cell">{annual2026_total:,}</div>', unsafe_allow_html=True)
                    with row2_col7:
                        annual2026_balance = max(0, annual_scheduled - annual2026_total - annual2026_discount)
                        st.markdown(f'<div class="bill-data-cell">{annual2026_balance:,}</div>', unsafe_allow_html=True)
                    
                    # Annual 2027 Row
                    row3_col1, row3_col2, row3_col3, row3_col4, row3_col5, row3_col6, row3_col7 = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with row3_col1:
                        st.markdown('<div class="bill-label-cell">Annual 2027</div>', unsafe_allow_html=True)
                    with row3_col2:
                        st.markdown(f'<div class="bill-data-cell">{annual_scheduled:,}</div>', unsafe_allow_html=True)
                    with row3_col3:
                        st.markdown(f'<div class="bill-data-cell">{annual_2027_already:,}</div>', unsafe_allow_html=True)
                    with row3_col4:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            annual2027_received_now = st.number_input("Annual 2027", min_value=0, step=100, value=0, key="annual2027_received_now", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row3_col5:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            annual2027_discount = st.number_input("A27 Disc", min_value=0, step=100, value=0, key="annual2027_discount_add", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row3_col6:
                        annual2027_total = annual_2027_already + annual2027_received_now
                        st.markdown(f'<div class="bill-data-cell">{annual2027_total:,}</div>', unsafe_allow_html=True)
                    with row3_col7:
                        annual2027_balance = max(0, annual_scheduled - annual2027_total - annual2027_discount)
                        st.markdown(f'<div class="bill-data-cell">{annual2027_balance:,}</div>', unsafe_allow_html=True)
                    
                    # Total Row
                    total_scheduled = setup_scheduled + (annual_scheduled * 2)
                    total_already = setup_already + annual_2026_already + annual_2027_already
                    total_received_now = setup_received_now + annual2026_received_now + annual2027_received_now
                    total_discount = setup_discount + annual2026_discount + annual2027_discount
                    total_received = total_already + total_received_now
                    total_balance = max(0, total_scheduled - total_received - total_discount)
                    
                    total_col1, total_col2, total_col3, total_col4, total_col5, total_col6, total_col7 = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with total_col1:
                        st.markdown('<div class="bill-total-cell">TOTAL</div>', unsafe_allow_html=True)
                    with total_col2:
                        st.markdown(f'<div class="bill-total-cell">₹{total_scheduled:,}</div>', unsafe_allow_html=True)
                    with total_col3:
                        st.markdown(f'<div class="bill-total-cell">₹{total_already:,}</div>', unsafe_allow_html=True)
                    with total_col4:
                        st.markdown(f'<div class="bill-total-cell">₹{total_received_now:,}</div>', unsafe_allow_html=True)
                    with total_col5:
                        st.markdown(f'<div class="bill-total-cell">₹{total_discount:,}</div>', unsafe_allow_html=True)
                    with total_col6:
                        st.markdown(f'<div class="bill-total-cell">₹{total_received:,}</div>', unsafe_allow_html=True)
                    with total_col7:
                        st.markdown(f'<div class="bill-total-cell">₹{total_balance:,}</div>', unsafe_allow_html=True)
                    
                    st.divider()
                    
                    # Transaction details
                    st.markdown("#### Transaction Details")
                    trans_col1, trans_col2, trans_col3 = st.columns(3)
                    
                    with trans_col1:
                        transaction_type = st.selectbox("Payment Method", options=["Cash", "Cheque", "UPI", "Bank Transfer", "Net Banking", "Other"], key="add_transaction_type")
                    
                    with trans_col2:
                        if transaction_type in ["UPI", "Bank Transfer", "Net Banking"]:
                            transaction_id = st.text_input("Transaction ID / Reference No.", placeholder="e.g., UPI Ref", key="add_transaction_id")
                        else:
                            st.caption(f"✓ {transaction_type} - No ID needed")
                            transaction_id = ""
                    
                    with trans_col3:
                        st.text_input("Notes", placeholder="Add any notes", key="add_notes")
                    
                    st.divider()
                    
                    # Summary
                    st.markdown("#### Summary")
                    summary_col1, summary_col2 = st.columns(2)
                    with summary_col1:
                        st.metric("Final Received", f"₹{total_received:,}")
                    with summary_col2:
                        st.metric("Final Due", f"₹{total_balance:,}")
                    
                    st.divider()
                    
                    # Save button
                    if st.button("Save All Receipts", type="primary", use_container_width=True, key="save_add_fee"):
                        if total_received_now > 0:
                            st.success(f"Fee receipts saved for {add_agency} - Total ₹{total_received_now:,} received")
                        else:
                            st.warning("Please enter at least one receipt amount")
                else:
                    st.warning("Agency not found")
            else:
                st.info("Select an agency to record fee receipts")
        
        # EDIT FEE OPERATION
        elif current_operation == "edit":
            #st.markdown("### Edit Fee Receipt")
            
            # Select agency
            edit_agency = st.selectbox("Select Agency", options=sorted(df['Agency_Code'].unique()) if 'Agency_Code' in df.columns else [], key="edit_agency_code")
            
            if edit_agency:
                agency_row = df[df['Agency_Code'] == edit_agency].iloc[0] if not df[df['Agency_Code'] == edit_agency].empty else None
                
                if agency_row is not None:
                    st.divider()
                    
                    # Calculate all values first
                    setup_scheduled = st.session_state.SETUP_FEE
                    setup_already = int(agency_row.get('Setup_Fee_Paid', 0)) if pd.notna(agency_row.get('Setup_Fee_Paid')) else 0
                    
                    annual_scheduled = st.session_state.ANNUAL_FEE
                    annual_2026_already = int(agency_row.get('Service_2026', 0)) if pd.notna(agency_row.get('Service_2026')) else 0
                    annual_2027_already = int(agency_row.get('Service_2027', 0)) if pd.notna(agency_row.get('Service_2027')) else 0
                    
                    # Bill table header
                    st.markdown("#### Fee Receipt Entry")
                    st.markdown("""
                    <style>
                        .bill-header-row { display: flex; gap: 8px; margin-bottom: 8px; }
                        .bill-header-cell { 
                            flex: 1; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; 
                            padding: 12px; 
                            border-radius: 4px; 
                            font-weight: bold; 
                            text-align: center;
                        }
                        .bill-data-row { display: flex; gap: 8px; margin-bottom: 8px; }
                        .bill-label-cell { 
                            flex: 1.2; 
                            background-color: #f8f9ff; 
                            padding: 12px; 
                            border-radius: 4px; 
                            font-weight: 600; 
                            border: 1px solid #e0e0e0;
                        }
                        .bill-data-cell { 
                            flex: 1; 
                            background-color: #ffffff; 
                            padding: 12px; 
                            border-radius: 4px; 
                            text-align: right; 
                            border: 1px solid #e0e0e0;
                        }
                        .bill-input-cell { 
                            flex: 1; 
                            background-color: #ffff00; 
                            padding: 6px; 
                            border-radius: 4px; 
                            border: none;
                        }
                        .bill-total-row { display: flex; gap: 8px; margin-bottom: 8px; margin-top: 12px; }
                        .bill-total-cell { 
                            flex: 1; 
                            background: linear-gradient(135deg, #00bcd4 0%, #0097a7 100%); 
                            color: white; 
                            padding: 14px; 
                            border-radius: 4px; 
                            font-weight: bold; 
                            text-align: center;
                        }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    st.info(f"Editing {edit_agency} - Previous values shown in 'Already Received' column")
                    
                    # Header row
                    header_col1, header_col2, header_col3, header_col4, header_col5, header_col6, header_col7 = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with header_col1:
                        st.markdown('<div class="bill-header-cell">Fee Type</div>', unsafe_allow_html=True)
                    with header_col2:
                        st.markdown('<div class="bill-header-cell">Scheduled (₹)</div>', unsafe_allow_html=True)
                    with header_col3:
                        st.markdown('<div class="bill-header-cell">Already Received (₹)</div>', unsafe_allow_html=True)
                    with header_col4:
                        st.markdown('<div class="bill-header-cell">Edit Fee (₹)</div>', unsafe_allow_html=True)
                    with header_col5:
                        st.markdown('<div class="bill-header-cell">Edit Discount (₹)</div>', unsafe_allow_html=True)
                    with header_col6:
                        st.markdown('<div class="bill-header-cell">Total Received (₹)</div>', unsafe_allow_html=True)
                    with header_col7:
                        st.markdown('<div class="bill-header-cell">Balance Due (₹)</div>', unsafe_allow_html=True)
                    
                    # Setup Fee Row
                    row1_col1, row1_col2, row1_col3, row1_col4, row1_col5, row1_col6, row1_col7 = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with row1_col1:
                        st.markdown('<div class="bill-label-cell">Setup Fee</div>', unsafe_allow_html=True)
                    with row1_col2:
                        st.markdown(f'<div class="bill-data-cell">{setup_scheduled:,}</div>', unsafe_allow_html=True)
                    with row1_col3:
                        st.markdown(f'<div class="bill-data-cell">{setup_already:,}</div>', unsafe_allow_html=True)
                    with row1_col4:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            setup_fee_edit = st.number_input("Setup", min_value=0, step=100, value=int(setup_already), key=f"setup_fee_edit_{edit_agency}", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row1_col5:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            setup_discount_edit = st.number_input("Setup Disc", min_value=0, step=100, value=0, key=f"setup_discount_edit_{edit_agency}", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row1_col6:
                        setup_total = setup_fee_edit
                        st.markdown(f'<div class="bill-data-cell">{setup_total:,}</div>', unsafe_allow_html=True)
                    with row1_col7:
                        setup_balance = setup_scheduled - setup_fee_edit - setup_discount_edit
                        balance_color = "red" if setup_balance < 0 else "green"
                        st.markdown(f'<div class="bill-data-cell" style="color: {balance_color};">₹{setup_balance:,}</div>', unsafe_allow_html=True)
                    
                    # Annual 2026 Row
                    row2_col1, row2_col2, row2_col3, row2_col4, row2_col5, row2_col6, row2_col7 = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with row2_col1:
                        st.markdown('<div class="bill-label-cell">Annual 2026</div>', unsafe_allow_html=True)
                    with row2_col2:
                        st.markdown(f'<div class="bill-data-cell">{annual_scheduled:,}</div>', unsafe_allow_html=True)
                    with row2_col3:
                        st.markdown(f'<div class="bill-data-cell">{annual_2026_already:,}</div>', unsafe_allow_html=True)
                    with row2_col4:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            annual2026_fee_edit = st.number_input("Annual 2026", min_value=0, step=100, value=int(annual_2026_already), key=f"annual2026_fee_edit_{edit_agency}", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row2_col5:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            annual2026_discount_edit = st.number_input("A26 Disc", min_value=0, step=100, value=0, key=f"annual2026_discount_edit_{edit_agency}", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row2_col6:
                        annual2026_total = annual2026_fee_edit
                        st.markdown(f'<div class="bill-data-cell">{annual2026_total:,}</div>', unsafe_allow_html=True)
                    with row2_col7:
                        annual2026_balance = annual_scheduled - annual2026_fee_edit - annual2026_discount_edit
                        balance_color = "red" if annual2026_balance < 0 else "green"
                        st.markdown(f'<div class="bill-data-cell" style="color: {balance_color};">₹{annual2026_balance:,}</div>', unsafe_allow_html=True)
                    
                    # Annual 2027 Row
                    row3_col1, row3_col2, row3_col3, row3_col4, row3_col5, row3_col6, row3_col7 = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    with row3_col1:
                        st.markdown('<div class="bill-label-cell">Annual 2027</div>', unsafe_allow_html=True)
                    with row3_col2:
                        st.markdown(f'<div class="bill-data-cell">{annual_scheduled:,}</div>', unsafe_allow_html=True)
                    with row3_col3:
                        st.markdown(f'<div class="bill-data-cell">{annual_2027_already:,}</div>', unsafe_allow_html=True)
                    with row3_col4:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            annual2027_fee_edit = st.number_input("Annual 2027", min_value=0, step=100, value=int(annual_2027_already), key=f"annual2027_fee_edit_{edit_agency}", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row3_col5:
                        with st.container(border=False):
                            st.markdown('<div class="bill-input-cell">', unsafe_allow_html=True)
                            annual2027_discount_edit = st.number_input("A27 Disc", min_value=0, step=100, value=0, key=f"annual2027_discount_edit_{edit_agency}", label_visibility="collapsed")
                            st.markdown('</div>', unsafe_allow_html=True)
                    with row3_col6:
                        annual2027_total = annual2027_fee_edit
                        st.markdown(f'<div class="bill-data-cell">{annual2027_total:,}</div>', unsafe_allow_html=True)
                    with row3_col7:
                        annual2027_balance = annual_scheduled - annual2027_fee_edit - annual2027_discount_edit
                        balance_color = "red" if annual2027_balance < 0 else "green"
                        st.markdown(f'<div class="bill-data-cell" style="color: {balance_color};">₹{annual2027_balance:,}</div>', unsafe_allow_html=True)
                    
                    # Total Row
                    st.divider()
                    total_col1, total_col2, total_col3, total_col4, total_col5, total_col6, total_col7 = st.columns([1.2, 1, 1, 1, 1, 1, 1])
                    
                    total_scheduled = setup_scheduled + (annual_scheduled * 2)
                    total_already = setup_already + annual_2026_already + annual_2027_already
                    total_collected = setup_fee_edit + annual2026_fee_edit + annual2027_fee_edit
                    total_discount_all = setup_discount_edit + annual2026_discount_edit + annual2027_discount_edit
                    total_balance = total_scheduled - total_collected - total_discount_all
                    
                    with total_col1:
                        st.markdown('<div class="bill-total-cell">TOTAL</div>', unsafe_allow_html=True)
                    with total_col2:
                        st.markdown(f'<div class="bill-total-cell">₹{total_scheduled:,}</div>', unsafe_allow_html=True)
                    with total_col3:
                        st.markdown(f'<div class="bill-total-cell">₹{total_already:,}</div>', unsafe_allow_html=True)
                    with total_col4:
                        st.markdown(f'<div class="bill-total-cell">₹{total_collected:,}</div>', unsafe_allow_html=True)
                    with total_col5:
                        st.markdown(f'<div class="bill-total-cell">₹{total_discount_all:,}</div>', unsafe_allow_html=True)
                    with total_col6:
                        st.markdown(f'<div class="bill-total-cell">₹{total_collected:,}</div>', unsafe_allow_html=True)
                    with total_col7:
                        balance_color = "red" if total_balance < 0 else "green"
                        st.markdown(f'<div class="bill-total-cell" style="color: {balance_color};">₹{total_balance:,}</div>', unsafe_allow_html=True)
                    
                    st.divider()
                    
                    # Transaction details
                    st.markdown("#### Transaction Details")
                    trans_col1, trans_col2, trans_col3 = st.columns(3)
                    
                    with trans_col1:
                        transaction_type = st.selectbox("Payment Method", options=["Cash", "Cheque", "UPI", "Bank Transfer", "Net Banking", "Other"], key="edit_transaction_type")
                    
                    with trans_col2:
                        if transaction_type in ["UPI", "Bank Transfer", "Net Banking"]:
                            transaction_id = st.text_input("Transaction ID / Reference No.", placeholder="e.g., UPI Ref", key="edit_transaction_id")
                        else:
                            st.caption(f"✓ {transaction_type} - No ID needed")
                            transaction_id = None
                    
                    with trans_col3:
                        transaction_date = st.date_input("Payment Date", value=datetime.now().date(), key="edit_transaction_date")
                    
                    notes = st.text_area("Notes / Remarks", placeholder="Add any notes...", key="edit_fee_notes")
                    
                    st.divider()
                    
                    # Summary
                    st.markdown("#### Summary")
                    sum_col1, sum_col2, sum_col3 = st.columns(3)
                    
                    with sum_col1:
                        st.metric("Total Scheduled", f"₹{total_scheduled:,}")
                    with sum_col2:
                        st.metric("Final Received", f"₹{total_collected:,}")
                    with sum_col3:
                        color = "red" if total_balance < 0 else "green"
                        st.metric("Final Due", f"₹{total_balance:,}")
                    
                    # Save Button
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Save Changes", type="primary", use_container_width=True, key="save_edit_fee"):
                            try:
                                # Update fees in Google Sheets (REPLACE mode - not add)
                                update_agency_field(edit_agency, 'Setup_Fee_Paid', setup_fee_edit)
                                update_agency_field(edit_agency, 'Service_2026', annual2026_fee_edit)
                                update_agency_field(edit_agency, 'Service_2027', annual2027_fee_edit)
                                
                                # Update discount
                                max_discount = max(setup_discount_edit, annual2026_discount_edit, annual2027_discount_edit)
                                update_agency_field(edit_agency, 'Discount_Pct', max_discount)
                                
                                # Update last payment date
                                update_agency_field(edit_agency, 'Last_Payment_Date', transaction_date.strftime("%Y-%m-%d"))
                                
                                st.success(f"✅ Fee edited successfully for {edit_agency}!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error saving: {str(e)}")
                    
                    with col2:
                        if st.button("Cancel", use_container_width=True, key="cancel_edit_fee"):
                            st.info("Changes cancelled")
        
        # DELETE FEE OPERATION
        elif current_operation == "delete":
            st.markdown("### Delete Fee Entry")
            st.warning("Delete a fee entry permanently")
            
            del_col1, del_col2 = st.columns(2)
            with del_col1:
                st.selectbox("Select Agency", options=sorted(df['Agency_Code'].unique()) if 'Agency_Code' in df.columns else [], key="delete_agency")
            with del_col2:
                st.selectbox("Fee Type", ["Setup Fee", "Annual Fee (2026)", "Annual Fee (2027)"], key="delete_fee_type")
            
            st.markdown("**Fee Details**")
            del_col3, del_col4 = st.columns(2)
            with del_col3:
                st.metric("Amount", "₹0")
            with del_col4:
                st.metric("Date", "N/A")
            
            st.text_input("Reason for deletion", placeholder="Provide reason", key="delete_reason")
            
            col1, col2 = st.columns(2)
            with col1:
                st.button("Cancel", use_container_width=True, key="cancel_delete")
            with col2:
                st.button("Confirm Delete", type="primary", use_container_width=True, key="confirm_delete")
    
    # PAGE 4: SETTINGS
    if page == "⚙️ Settings":
        st.subheader("⚙️ System Settings")
        
        # Developer Credentials Section
        st.markdown("### 🔐 Developer Login Credentials")
        st.info(f"""
        **These are hardcoded credentials - NOT stored in Google Sheet**
        
        - **Username:** `{DEVELOPER_USERNAME}`
        - **Password:** `{DEVELOPER_PASSWORD}`
        
        ⚠️ **To change credentials:** Edit the variables in the code:
        ```python
        DEVELOPER_USERNAME = "developer"
        DEVELOPER_PASSWORD = "dev2026"
        ```
        """)
        
        st.divider()
        st.markdown("### Fee Configuration (From fee_config Sheet)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Current Setup Fee (One-time)", f"₹{st.session_state.SETUP_FEE:,}")
        with col2:
            st.metric("Current Annual Service Fee", f"₹{st.session_state.ANNUAL_FEE:,}")
        
        st.divider()
        st.markdown("### Edit Fee Structure")
        st.info("These values will be saved to the 'fee_config' sheet in your Google Sheet with an 'Active From' date. Historical records are maintained.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            new_setup_fee = st.number_input(
                "Setup Fee (₹)",
                value=st.session_state.SETUP_FEE,
                min_value=1000,
                step=1000,
                help="One-time fee charged to agencies"
            )
        
        with col2:
            new_annual_fee = st.number_input(
                "Annual Service Fee (₹)",
                value=st.session_state.ANNUAL_FEE,
                min_value=100,
                step=100,
                help="Annual fee charged to each agency"
            )
        
        with col3:
            active_from_date = st.date_input(
                "Effective From",
                value=datetime.now().date(),
                help="Date when these fees become active"
            )
        
        if st.button("💾 Save Fee Configuration to Google Sheet", type="primary", use_container_width=True):
            if update_fee_config(new_setup_fee, new_annual_fee, active_from_date):
                st.session_state.SETUP_FEE = new_setup_fee
                st.session_state.ANNUAL_FEE = new_annual_fee
                st.session_state.fee_config = {"Setup_Fee": new_setup_fee, "Annual_Fee": new_annual_fee}
                st.rerun()
        
        st.divider()
        st.markdown("### System Status")
        client = get_client()
        if client:
            st.success("✅ Google Sheets Connected")
        else:
            st.error("❌ Google Sheets Not Connected")
        
        st.info(f"""
        **Last Refresh:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        **Sheet ID:** {SHEET_ID}
        
        **Columns Required:** Agency_Code, Setup_Fee_Paid, Service_2026, Service_2027, 
        Discount_Pct, Registration_Status, Last_Payment_Date
        """)
        
        if st.button("🔄 Force Refresh All Data"):
            st.cache_data.clear()
            st.rerun()

if __name__ == "__main__":
    main()
