"""
Export utilities for Interview Records
Place this file as: C:\PlacementAgency_v2\export_utils.py
"""

import streamlit as st
from datetime import datetime


def get_existing_records(gc, sheet_id):
    """
    Get existing interview records from Interview_Records sheet
    
    Returns:
        tuple: (existing_ids, scheduled_pairs, interview_sheet)
    """
    try:
        sh = gc.open_by_key(sheet_id)
        interview_sheet = sh.worksheet("Interview_Records")
        existing_data = interview_sheet.get_all_values()
        
        if len(existing_data) <= 1:  # Only headers or empty
            return [], set(), interview_sheet
        
        headers = existing_data[0] if len(existing_data) > 0 else []
        
        # Find column indices dynamically
        try:
            record_id_idx = headers.index('Record_ID') if 'Record_ID' in headers else 0
            cand_id_idx = headers.index('Candidate_ID') if 'Candidate_ID' in headers else (headers.index('Candidate ID') if 'Candidate ID' in headers else 1)
            cid_idx = headers.index('CID') if 'CID' in headers else (headers.index('Company_Name') if 'Company_Name' in headers else 2)
        except ValueError:
            # Fallback to default positions
            record_id_idx = 0
            cand_id_idx = 1
            cid_idx = 2
        
        # Extract existing record IDs
        existing_ids = []
        scheduled_pairs = set()
        
        for row in existing_data[1:]:
            if len(row) > record_id_idx and row[record_id_idx]:
                existing_ids.append(str(row[record_id_idx]))
            
            # Create pair for duplicate checking
            if len(row) > max(cand_id_idx, cid_idx):
                cand_id = str(row[cand_id_idx]) if len(row) > cand_id_idx else ""
                comp_id = str(row[cid_idx]) if len(row) > cid_idx else ""
                if cand_id and comp_id:
                    scheduled_pairs.add((cand_id, comp_id))
        
        return existing_ids, scheduled_pairs, interview_sheet
    
    except Exception as e:
        st.error(f"❌ Error accessing Interview_Records sheet: {str(e)}")
        return [], set(), None


def generate_record_id(existing_ids):
    """
    Generate new interview record ID
    Format: IR001, IR002, IR003, etc.
    
    Args:
        existing_ids: List of existing record IDs
    
    Returns:
        str: Next available record ID
    """
    if len(existing_ids) == 0:
        return "IR001"
    
    # Extract numeric parts from IDs like "IR001", "IR002"
    numbers = []
    for rid in existing_ids:
        if isinstance(rid, str) and rid.startswith("IR") and len(rid) > 2:
            try:
                num = int(rid[2:])  # Extract number after "IR"
                numbers.append(num)
            except (ValueError, IndexError):
                continue
    
    if len(numbers) == 0:
        return "IR001"
    
    # Generate next ID
    next_num = max(numbers) + 1
    return f"IR{next_num:03d}"


def get_sheet_headers(sheet):
    """Get headers from sheet dynamically"""
    try:
        return sheet.row_values(1)
    except:
        return []


def create_record_row(match, record_id, headers):
    """
    Create interview record row matching YOUR exact sheet structure
    Headers: Record ID, Date Created, Candidate ID, Full Name, Company Name, CID, 
             Job Title, Match Score, Interview Status, Interview Date, Interview Time, 
             Interview Round, Result Status, Salary Offered, Joining Date, Remarks, 
             Last Updated, Updated By
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_only = datetime.now().strftime("%Y-%m-%d")
    
    row = []
    
    for header in headers:
        h = header.strip()
        
        # Exact header matching for YOUR sheet
        if h == "Record ID":
            row.append(record_id)
        
        elif h == "Date Created":
            row.append(date_only)
        
        elif h == "Candidate ID":
            row.append(str(match.get('Candidate_ID', match.get('Candidate ID', ''))))
        
        elif h == "Full Name":
            row.append(str(match.get('Candidate_Name', match.get('Full Name', ''))))
        
        elif h == "Company Name":
            row.append(str(match.get('Company_Name', '')))
        
        elif h == "CID":
            row.append(str(match.get('CID', '')))
        
        elif h == "Job Title":
            row.append(str(match.get('Job_Title', match.get('Job Title', ''))))
        
        elif h == "Match Score":
            score = match.get('Match_Score', 0)
            if isinstance(score, (int, float)):
                row.append(f"{int(score * 100)}%")
            else:
                row.append(str(score))
        
        elif h == "Interview Status":
            # ✅ FIXED: Use 'Matched' instead of 'Scheduled'
            row.append("Matched")
        
        elif h == "Interview Date":
            row.append("")  # Empty - to be filled later
        
        elif h == "Interview Time":
            row.append("")  # Empty - to be filled later
        
        elif h == "Interview Round":
            row.append("")  # Empty - to be filled later
        
        elif h == "Result Status":
            row.append("Pending")
        
        elif h == "Salary Offered":
            row.append(str(match.get('Offered_Salary', '')))
        
        elif h == "Joining Date":
            row.append("")  # Empty - to be filled later
        
        elif h == "Remarks":
            row.append("")  # Empty - to be filled later
        
        elif h == "Last Updated":
            row.append(timestamp)
        
        elif h == "Updated By":
            row.append("System")
        
        else:
            row.append("")  # Unknown column
    
    return row


def export_to_interview_sheet(gc, sheet_id, matches):
    """
    Export selected matches to Interview_Records sheet
    Prevents duplicates based on (Candidate_ID, CID/Company_Name) pair
    
    Args:
        gc: Google Sheets client
        sheet_id: Google Sheet ID
        matches: List of match dictionaries to export
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Get existing records
        existing_ids, scheduled_pairs, interview_sheet = get_existing_records(gc, sheet_id)
        
        if interview_sheet is None:
            return False, "❌ Could not access Interview_Records sheet. Please check if sheet exists."
        
        # Get headers dynamically
        headers = get_sheet_headers(interview_sheet)
        
        if not headers:
            return False, "❌ Could not read sheet headers. Please check sheet structure."
        
        records_to_insert = []
        added_count = 0
        skipped_count = 0
        skipped_details = []
        
        for match in matches:
            # Create candidate-company pair for duplicate checking
            candidate_id = str(match.get('Candidate_ID', match.get('Candidate ID', ''))).strip()
            company_id = str(match.get('CID', match.get('Company_Name', ''))).strip()
            
            if not candidate_id or not company_id:
                skipped_count += 1
                skipped_details.append(f"Missing ID - {match.get('Candidate_Name', 'Unknown')}")
                continue
            
            pair = (candidate_id, company_id)
            
            # Check if this pair already exists
            if pair in scheduled_pairs:
                skipped_count += 1
                skipped_details.append(f"{match.get('Candidate_Name', 'Unknown')} - {match.get('Company_Name', 'Unknown')}")
                continue
            
            # Generate new record ID
            record_id = generate_record_id(existing_ids)
            existing_ids.append(record_id)  # Add to list to avoid duplicates in same batch
            
            # Create row data dynamically based on headers
            row_data = create_record_row(match, record_id, headers)
            records_to_insert.append(row_data)
            added_count += 1
        
        # Batch insert all records
        if len(records_to_insert) > 0:
            interview_sheet.append_rows(records_to_insert, value_input_option='USER_ENTERED')
            
            message = f"✅ Successfully added {added_count} record(s) to Interview_Records!"
            
            if skipped_count > 0:
                message += f"\n\n⚠️ Skipped {skipped_count} duplicate(s):"
                for detail in skipped_details[:5]:  # Show first 5
                    message += f"\n  • {detail}"
                if len(skipped_details) > 5:
                    message += f"\n  • ... and {len(skipped_details) - 5} more"
            
            return True, message
        else:
            message = "⚠️ No new records to add."
            if skipped_count > 0:
                message += f"\n\nAll {skipped_count} record(s) already exist:"
                for detail in skipped_details[:5]:
                    message += f"\n  • {detail}"
            
            return False, message
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return False, f"❌ Export Error: {str(e)}\n\nDetails:\n{error_details}"


def export_single_match(gc, sheet_id, match):
    """
    Export single match to Interview_Records
    Wrapper around export_to_interview_sheet for single match
    
    Args:
        gc: Google Sheets client
        sheet_id: Google Sheet ID
        match: Single match dictionary
    
    Returns:
        tuple: (success: bool, message: str)
    """
    return export_to_interview_sheet(gc, sheet_id, [match])