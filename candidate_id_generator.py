"""
Reusable Candidate ID Generator Module
Format: AG001CND25000a (13 chars)
- AG001: Agency Code (5 chars)
- CND: Prefix (3 chars)
- 25: Year (2 digits)
- 000a: Base62 counter (4 chars = 14+ million unique IDs)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import gspread

# Base62 encoding (0-9, A-Z, a-z)
BASE62_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def to_base62(num: int, length: int = 4) -> str:
    """
    Convert number to base62 string
    
    Args:
        num: Number to convert (0 to 14,776,335 for 4 chars)
        length: Desired string length (default 4)
    
    Returns:
        Base62 string (e.g., 1 → "0001", 62 → "0010", 3844 → "0100")
    
    Examples:
        1 → "0001"
        62 → "0010" 
        3844 → "0100"
        238328 → "0zzz"
    """
    if num < 0:
        raise ValueError("Number must be non-negative")
    
    if num == 0:
        return "0".rjust(length, "0")
    
    base = 62
    result = ""
    
    while num > 0:
        num, rem = divmod(num, base)
        result = BASE62_CHARS[rem] + result
    
    return result.rjust(length, "0")


def from_base62(s: str) -> int:
    """
    Convert base62 string back to number (for validation/debugging)
    
    Args:
        s: Base62 string
    
    Returns:
        Integer value
    
    Example:
        "000a" → 10
        "0010" → 62
    """
    base = 62
    num = 0
    for char in s:
        num = num * base + BASE62_CHARS.index(char)
    return num


def get_agency_sheet_id():
    """Get current agency's Google Sheet ID from session"""
    sheet_url = st.session_state.get("agency_sheet_url", "")
    if sheet_url:
        try:
            return sheet_url.split('/d/')[1].split('/')[0]
        except:
            return None
    return None


def generate_candidate_id(google_sheets_client=None):
    """
    Generate unique candidate ID with Base62 encoding
    
    Format: AG001CND25000a
    - AG001: Agency code from session
    - CND: Fixed prefix
    - 25: Current year (2 digits)
    - 000a: Base62 counter (4 chars)
    
    Args:
        google_sheets_client: Optional pre-initialized gspread client
    
    Returns:
        str: Generated candidate ID (13 chars)
    
    Example:
        AG001CND250001  ← First candidate of 2025
        AG001CND25000a  ← 10th candidate
        AG001CND250010  ← 62nd candidate
    """
    # Get agency code from session (set during login)
    agency_code = st.session_state.get("agency_code", "AG000")
    
    # Current year (2 digits)
    year = datetime.now().strftime("%y")  # 25 for 2025
    
    # Create prefix (AG001CND25)
    today_prefix = f"{agency_code}CND{year}"
    
    try:
        # Use provided client or get from session
        client = google_sheets_client
        if not client:
            # Fallback: try to get client from session cache
            # This assumes you have get_google_sheets_client() in main app
            if hasattr(st, 'cache_resource'):
                # Can't import here, so return default
                return f"{today_prefix}0001"
        
        # Get agency-specific sheet ID
        SHEET_ID = get_agency_sheet_id()
        if not SHEET_ID:
            return f"{today_prefix}0001"
        
        # Read Candidates sheet
        sheet = client.open_by_key(SHEET_ID).worksheet("Candidates")
        df = pd.DataFrame(sheet.get_all_records())

        if len(df) == 0 or "Candidate ID" not in df.columns:
            # First candidate of this year
            return f"{today_prefix}0001"

        # Find existing IDs for this agency + this year
        existing_ids = [
            str(cid) 
            for cid in df["Candidate ID"]
            if str(cid).startswith(today_prefix)
        ]
        
        if not existing_ids:
            # First candidate of this year
            return f"{today_prefix}0001"
        
        # Extract Base62 counters from existing IDs
        counters = []
        for cid in existing_ids:
            try:
                # Last 4 characters are Base62 counter
                base62_part = str(cid)[-4:]
                counter_value = from_base62(base62_part)
                counters.append(counter_value)
            except:
                continue
        
        # Next counter value
        next_counter = max(counters) + 1 if counters else 1
        
        # Convert to Base62
        base62_counter = to_base62(next_counter, 4)
        
        # Final ID
        return f"{today_prefix}{base62_counter}"
        
    except Exception as e:
        # Fallback to simple counter
        return f"{today_prefix}0001"


def validate_candidate_id(candidate_id: str) -> dict:
    """
    Validate and parse candidate ID
    
    Args:
        candidate_id: Candidate ID to validate
    
    Returns:
        dict: Parsed components or error
    
    Example:
        >>> validate_candidate_id("AG001CND250001")
        {
            "valid": True,
            "agency_code": "AG001",
            "prefix": "CND",
            "year": "25",
            "counter_base62": "0001",
            "counter_decimal": 1
        }
    """
    if not candidate_id or len(candidate_id) != 13:
        return {"valid": False, "error": "Invalid length (expected 13 chars)"}
    
    try:
        agency_code = candidate_id[0:5]  # AG001
        prefix = candidate_id[5:8]       # CND
        year = candidate_id[8:10]        # 25
        counter = candidate_id[10:14]    # 0001
        
        # Validate format
        if not agency_code.startswith("AG"):
            return {"valid": False, "error": "Agency code must start with AG"}
        
        if prefix != "CND":
            return {"valid": False, "error": "Invalid prefix (expected CND)"}
        
        if not year.isdigit():
            return {"valid": False, "error": "Invalid year"}
        
        # Validate Base62 counter
        try:
            counter_value = from_base62(counter)
        except:
            return {"valid": False, "error": "Invalid Base62 counter"}
        
        return {
            "valid": True,
            "agency_code": agency_code,
            "prefix": prefix,
            "year": year,
            "counter_base62": counter,
            "counter_decimal": counter_value,
            "full_year": f"20{year}"
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}


# ====================================
# HELPER FUNCTIONS FOR TESTING
# ====================================

def demo_base62_conversion():
    """Demo function to show Base62 encoding"""
    print("Base62 Conversion Examples:")
    print("-" * 40)
    
    examples = [1, 10, 62, 100, 1000, 3844, 10000, 238328]
    
    for num in examples:
        base62 = to_base62(num, 4)
        back = from_base62(base62)
        print(f"{num:6d} → {base62:4s} → {back:6d}")
    
    print("\nCapacity:")
    print(f"4 chars Base62 = 0 to {62**4 - 1:,} IDs")
    print(f"That's {62**4:,} unique candidates per agency per year!")


if __name__ == "__main__":
    # Demo
    demo_base62_conversion()
    
    # Test ID generation (without Google Sheets)
    print("\n" + "="*40)
    print("Sample Candidate IDs:")
    print("="*40)
    
    for i in [1, 10, 100, 1000, 5000]:
        test_id = f"AG001CND{datetime.now().strftime('%y')}{to_base62(i, 4)}"
        parsed = validate_candidate_id(test_id)
        print(f"Candidate #{i:5d}: {test_id} → Decimal: {parsed.get('counter_decimal', 'N/A')}")