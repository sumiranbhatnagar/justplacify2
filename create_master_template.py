"""
CREATE AGENCY TEMPLATE - FROM MASTER TEMPLATE URL
==================================================================
Creates new Google Sheets by copying from MASTER TEMPLATE URL
Uses provided template and transfers ownership to agency owner
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import os
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ====================================================
# CONFIGURATION
# ====================================================

CRED_FILE = "credentials.json" if os.path.exists("credentials.json") else None
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

# MASTER TEMPLATE URL (Extracted from your provided link)
MASTER_TEMPLATE_URL = "https://docs.google.com/spreadsheets/d/1PkawpwbRahqzsxtZkQS9JdlizK1XS2PyJv1vfhN7ipE/edit"
MASTER_TEMPLATE_ID = "1PkawpwbRahqzsxtZkQS9JdlizK1XS2PyJv1vfhN7ipE"

# ====================================================
# HELPER FUNCTIONS
# ====================================================

def get_credentials():
    """Get Google API credentials"""
    try:
        if CRED_FILE:
            print("✅ Using credentials.json")
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                CRED_FILE,
                SCOPES
            )
        else:
            print("✅ Using Streamlit Secrets")
            creds_dict = dict(st.secrets["gcp_service_account"])
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                creds_dict,
                SCOPES
            )
        return credentials
    except Exception as e:
        print(f"❌ Credentials error: {e}")
        return None

def get_sheets_client():
    """Get gspread client"""
    try:
        credentials = get_credentials()
        if not credentials:
            return None
        
        client = gspread.authorize(credentials)
        print("✅ Sheets client authorized")
        return client
    except Exception as e:
        print(f"❌ Sheets client error: {e}")
        return None

def get_drive_service():
    """Get Google Drive API service for ownership transfer"""
    try:
        if CRED_FILE:
            credentials = service_account.Credentials.from_service_account_file(
                CRED_FILE, scopes=['https://www.googleapis.com/auth/drive']
            )
        else:
            creds_dict = dict(st.secrets["gcp_service_account"])
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=['https://www.googleapis.com/auth/drive']
            )
        
        service = build('drive', 'v3', credentials=credentials)
        print("✅ Drive service authorized")
        return service
    except Exception as e:
        print(f"❌ Drive service error: {e}")
        return None

# ====================================================
# MAIN FUNCTION: COPY FROM MASTER TEMPLATE
# ====================================================

def copy_master_template_for_agency(agency_code, agency_name, owner_email=None):
    """
    Copy from MASTER TEMPLATE URL and transfer ownership
    
    Args:
        agency_code (str): Agency code (e.g., "AG001")
        agency_name (str): Agency name
        owner_email (str, optional): Email to transfer ownership to
    
    Returns:
        dict: {
            'success': bool,
            'spreadsheet_id': str,
            'spreadsheet_url': str,
            'workbook_name': str,
            'created_at': str
        }
    """
    
    try:
        print("=" * 60)
        print(f"🚀 COPYING FROM MASTER TEMPLATE")
        print(f"   Template ID: {MASTER_TEMPLATE_ID}")
        print(f"   Agency Code: {agency_code}")
        print(f"   Agency Name: {agency_name}")
        print("=" * 60)
        
        # Step 1: Get clients
        sheets_client = get_sheets_client()
        drive_service = get_drive_service()
        
        if not sheets_client or not drive_service:
            return {
                'success': False,
                'error': 'Failed to get Google clients'
            }
        
        # Step 2: Copy spreadsheet from master template
        print(f"\n📋 Copying master template...")
        workbook_name = f"Agency_{agency_code}_{agency_name.replace(' ', '_')}"
        
        # Copy using Drive API (more reliable for ownership transfer)
        copied_file = drive_service.files().copy(
            fileId=MASTER_TEMPLATE_ID,
            body={
                'name': workbook_name
            }
        ).execute()
        
        new_spreadsheet_id = copied_file['id']
        new_spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{new_spreadsheet_id}/edit"
        
        print(f"✅ Template copied!")
        print(f"   New ID: {new_spreadsheet_id}")
        print(f"   New URL: {new_spreadsheet_url}")
        
        # Step 3: Open the new spreadsheet with gspread
        new_spreadsheet = sheets_client.open_by_key(new_spreadsheet_id)
        print(f"✅ Opened new spreadsheet")
        
        # Step 4: Ownership transfer (CRITICAL STEP)
        if owner_email:
            try:
                print(f"\n👑 TRANSFERRING OWNERSHIP to {owner_email}...")
                
                # Method 1: Transfer ownership using Drive API
                drive_service.permissions().create(
                    fileId=new_spreadsheet_id,
                    body={
                        'emailAddress': owner_email,
                        'role': 'owner',
                        'type': 'user',
                        'transferOwnership': True  # This transfers ownership
                    },
                    sendNotificationEmail=True
                ).execute()
                
                print(f"✅ ✅ OWNERSHIP TRANSFERRED to {owner_email}")
                print(f"   File moved to {owner_email}'s Drive!")
                print(f"   Service account no longer owns it!")
                
            except Exception as ownership_error:
                print(f"⚠️ Ownership transfer failed: {ownership_error}")
                print("🔄 Trying fallback: Share as Editor...")
                
                # Fallback: Share as editor with high permissions
                try:
                    new_spreadsheet.share(owner_email, perm_type='user', role='writer')
                    print(f"✅ Shared with {owner_email} as EDITOR (fallback)")
                except Exception as share_error:
                    print(f"⚠️ Share also failed: {share_error}")
        else:
            print(f"\n⚠️ No owner email - keeping in service account Drive")
        
        # Step 5: Verify all tabs exist (from master template)
        print(f"\n🔍 Verifying tabs from master template...")
        worksheets = new_spreadsheet.worksheets()
        tab_names = [ws.title for ws in worksheets]
        
        print(f"✅ Found {len(tab_names)} tabs:")
        for tab in tab_names:
            print(f"   📂 {tab}")
        
        print("\n" + "=" * 60)
        print("✅ AGENCY TEMPLATE CREATED SUCCESSFULLY FROM MASTER!")
        print("=" * 60)
        print(f"📊 Workbook: {workbook_name}")
        print(f"🔗 URL: {new_spreadsheet_url}")
        print(f"📂 Tabs: {len(tab_names)}")
        print(f"👤 Owner: {owner_email or 'Service Account'}")
        print("=" * 60)
        
        return {
            'success': True,
            'spreadsheet_id': new_spreadsheet_id,
            'spreadsheet_url': new_spreadsheet_url,
            'workbook_name': workbook_name,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tabs_count': len(tab_names),
            'owner_email': owner_email
        }
    
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'template_used': MASTER_TEMPLATE_URL
        }

# ====================================================
# VERIFICATION FUNCTION
# ====================================================

def verify_agency_template(spreadsheet_id):
    """Verify copied template structure"""
    try:
        print("\n🔍 VERIFYING COPIED TEMPLATE...")
        
        client = get_sheets_client()
        if not client:
            return {'success': False, 'error': 'Failed to get client'}
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheets = spreadsheet.worksheets()
        
        print(f"✅ Found {len(worksheets)} tabs:")
        for ws in worksheets:
            print(f"   📂 {ws.title}")
            print(f"   📏 Rows: {ws.row_count}, Cols: {ws.col_count}")
        
        return {
            'success': True,
            'tabs_found': [ws.title for ws in worksheets],
            'total_tabs': len(worksheets)
        }
    
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }

# ====================================================
# STREAMLIT INTERFACE
# ====================================================

def create_agency_template_ui():
    """Streamlit UI for creating agency templates"""
    st.title("🚀 Agency Template Creator")
    st.markdown("**Copy from Master Template + Ownership Transfer**")
    
    with st.form("agency_form"):
        agency_code = st.text_input("Agency Code", value="AG001", help="e.g., AG001, DEL01")
        agency_name = st.text_input("Agency Name", value="Test Agency")
        owner_email = st.text_input("Owner Email (optional)", 
                                  help="Email to transfer ownership to")
        create_btn = st.form_submit_button("🎯 CREATE AGENCY TEMPLATE")
    
    if create_btn:
        with st.spinner("Creating agency template..."):
            result = copy_master_template_for_agency(
                agency_code=agency_code,
                agency_name=agency_name,
                owner_email=owner_email
            )
        
        if result['success']:
            st.success("✅ Agency Template Created!")
            st.balloons()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Workbook", result['workbook_name'])
            with col2:
                st.metric("📂 Tabs", result.get('tabs_count', 'N/A'))
            with col3:
                st.metric("👤 Owner", result.get('owner_email', 'Service Account'))
            
            st.markdown("**🔗 Copy this URL:**")
            st.code(result['spreadsheet_url'])
            
            # Verify button
            if st.button("🔍 Verify Template"):
                verification = verify_agency_template(result['spreadsheet_id'])
                st.json(verification)
                
        else:
            st.error(f"❌ Failed: {result.get('error')}")

# ====================================================
# TEST FUNCTION
# ====================================================

if __name__ == "__main__":
    """
    Test template creation from MASTER URL
    """
    
    print("\n" + "🎯" * 30)
    print("TEST: COPY FROM MASTER TEMPLATE URL")
    print(f"Template: {MASTER_TEMPLATE_URL}")
    print("🎯" * 30)
    
    # Test data
    test_agency_code = "AG_TEST_001"
    test_agency_name = "Test Agency Delhi"
    test_owner_email = "your-email@gmail.com"  # PUT YOUR EMAIL HERE
    
    # Create template
    result = copy_master_template_for_agency(
        agency_code=test_agency_code,
        agency_name=test_agency_name,
        owner_email=test_owner_email
    )
    
    if result['success']:
        print("\n✅ SUCCESS!")
        print(f"   URL: {result['spreadsheet_url']}")
        print(f"   ID: {result['spreadsheet_id']}")
        
        # Verify
        verification = verify_agency_template(result['spreadsheet_id'])
        st.json(verification)
        
    else:
        print(f"\n❌ FAILED: {result.get('error')}")

# Run Streamlit UI
if __name__ == "__main__":
    create_agency_template_ui()
