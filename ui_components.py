"""
Modern UI Components for JustPlacify
Unified design system with modern SaaS aesthetics
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# ============================================================================
# DESIGN TOKENS - Single source of truth for the entire app
# ============================================================================
COLORS = {
    'primary': '#6366F1',       # Indigo
    'primary_hover': '#4F46E5', # Indigo darker
    'primary_light': '#EEF2FF', # Indigo-50
    'secondary': '#8B5CF6',     # Violet
    'success': '#10B981',       # Emerald
    'success_light': '#ECFDF5', # Emerald-50
    'warning': '#F59E0B',       # Amber
    'warning_light': '#FFFBEB', # Amber-50
    'danger': '#EF4444',        # Red
    'danger_light': '#FEF2F2',  # Red-50
    'info': '#3B82F6',          # Blue
    'info_light': '#EFF6FF',    # Blue-50
    'light_bg': '#F8FAFC',      # Slate-50
    'surface': '#FFFFFF',
    'surface_hover': '#F1F5F9', # Slate-100
    'border': '#E2E8F0',        # Slate-200
    'border_light': '#F1F5F9',  # Slate-100
    'text_dark': '#0F172A',     # Slate-900
    'text_primary': '#1E293B',  # Slate-800
    'text_secondary': '#64748B',# Slate-500
    'text_muted': '#94A3B8',    # Slate-400
    'hover': '#F1F5F9',
}

# Load fonts and icons
st.markdown('''
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/lucide-static@latest/font/lucide.css">
''', unsafe_allow_html=True)

# ============================================================================
# 1. GLOBAL CSS - Modern design system
# ============================================================================

def apply_global_styling():
    """Apply modern global CSS styling"""
    css = f"""
    <style>
    /* ---- CSS Variables ---- */
    :root {{
        --primary: {COLORS['primary']};
        --primary-hover: {COLORS['primary_hover']};
        --primary-light: {COLORS['primary_light']};
        --success: {COLORS['success']};
        --warning: {COLORS['warning']};
        --danger: {COLORS['danger']};
        --info: {COLORS['info']};
        --bg: {COLORS['light_bg']};
        --surface: {COLORS['surface']};
        --border: {COLORS['border']};
        --text-primary: {COLORS['text_dark']};
        --text-secondary: {COLORS['text_secondary']};
        --text-muted: {COLORS['text_muted']};
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
        --radius-xl: 20px;
        --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
        --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
        --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.04);
        --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}

    /* ---- Base ---- */
    body, .stApp {{
        font-family: var(--font) !important;
        background-color: var(--bg) !important;
        color: var(--text-primary);
        -webkit-font-smoothing: antialiased;
    }}

    h1, h2, h3, h4, h5, h6, p, span, div, label, button, input, textarea, select {{
        font-family: var(--font) !important;
    }}

    /* ---- Buttons ---- */
    .stButton > button {{
        width: 100%;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        border: 1px solid var(--border) !important;
        padding: 10px 20px !important;
        transition: all 0.15s ease !important;
        background: var(--surface) !important;
        color: var(--text-primary) !important;
        cursor: pointer !important;
    }}

    .stButton > button:hover {{
        background: var(--primary-light) !important;
        border-color: var(--primary) !important;
        color: var(--primary) !important;
        box-shadow: var(--shadow-sm) !important;
        transform: none !important;
    }}

    .stButton > button:active {{
        transform: scale(0.98) !important;
    }}

    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stFormSubmitButton"] {{
        background: var(--primary) !important;
        color: white !important;
        border: none !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        background: var(--primary-hover) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
    }}

    /* ---- Inputs ---- */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {{
        border: 1.5px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
        font-family: var(--font) !important;
        color: var(--text-primary) !important;
        background: var(--surface) !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    }}

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12) !important;
        outline: none !important;
    }}

    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {{
        color: var(--text-muted) !important;
    }}

    /* ---- Labels ---- */
    label {{
        font-weight: 500 !important;
        font-size: 13px !important;
        color: var(--text-secondary) !important;
        letter-spacing: 0.01em !important;
        text-transform: none !important;
    }}

    /* ---- Selectbox ---- */
    .stSelectbox > div > div {{
        border-radius: var(--radius-sm) !important;
    }}

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0px;
        border-bottom: 1px solid var(--border);
        background: transparent;
    }}

    .stTabs [data-baseweb="tab"] {{
        padding: 12px 20px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        font-family: var(--font) !important;
        border-radius: 0 !important;
        border: none !important;
        background: transparent !important;
        color: var(--text-muted) !important;
        transition: color 0.15s ease !important;
    }}

    .stTabs [aria-selected="true"] {{
        color: var(--primary) !important;
        border-bottom: 2px solid var(--primary) !important;
        font-weight: 600 !important;
        background: transparent !important;
    }}

    .stTabs [aria-selected="false"]:hover {{
        color: var(--text-primary) !important;
        background: var(--primary-light) !important;
    }}

    /* ---- DataFrames ---- */
    .stDataFrame {{
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border) !important;
        overflow: hidden !important;
    }}

    /* ---- Expander ---- */
    .streamlit-expanderHeader {{
        font-weight: 600 !important;
        font-size: 14px !important;
        color: var(--text-primary) !important;
        font-family: var(--font) !important;
        background: var(--surface) !important;
        border-radius: var(--radius-sm) !important;
    }}

    /* ---- Divider ---- */
    hr {{
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 1.5rem 0 !important;
    }}

    /* ---- Radio & Checkbox ---- */
    .stRadio > div {{ gap: 12px; }}
    .stCheckbox > div {{ gap: 8px; }}

    .stRadio label, .stCheckbox label {{
        font-size: 14px !important;
        color: var(--text-primary) !important;
    }}

    /* ---- Status Badge Classes ---- */
    .status-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: var(--radius-xl);
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.02em;
    }}

    .status-badge::before {{
        content: '';
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
    }}

    .status-active, .status-success {{ background: {COLORS['success_light']}; color: {COLORS['success']}; }}
    .status-active::before, .status-success::before {{ background: {COLORS['success']}; }}
    .status-pending, .status-warning {{ background: {COLORS['warning_light']}; color: #B45309; }}
    .status-pending::before, .status-warning::before {{ background: {COLORS['warning']}; }}
    .status-rejected {{ background: {COLORS['danger_light']}; color: {COLORS['danger']}; }}
    .status-rejected::before {{ background: {COLORS['danger']}; }}
    .status-closed {{ background: {COLORS['surface_hover']}; color: var(--text-muted); }}
    .status-closed::before {{ background: var(--text-muted); }}
    .status-info {{ background: {COLORS['info_light']}; color: {COLORS['info']}; }}
    .status-info::before {{ background: {COLORS['info']}; }}

    /* ---- Empty State ---- */
    .empty-state {{
        text-align: center;
        padding: 48px 24px;
        color: var(--text-muted);
    }}
    .empty-state-icon {{
        font-size: 40px;
        margin-bottom: 12px;
        opacity: 0.6;
    }}

    /* ---- Metric Box ---- */
    .metric-box {{
        background: var(--surface);
        padding: 20px;
        border-radius: var(--radius-md);
        border: 1px solid var(--border);
        transition: box-shadow 0.2s ease;
    }}
    .metric-box:hover {{
        box-shadow: var(--shadow-md);
    }}

    /* ---- Page Header ---- */
    .page-header {{
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--border);
    }}
    .page-header h2 {{
        margin: 0 0 4px 0;
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
    }}
    .page-header p {{
        margin: 0;
        font-size: 0.9rem;
        color: var(--text-secondary);
    }}

    /* ---- Responsive ---- */
    @media (max-width: 768px) {{
        .stColumn {{ flex: 1 1 100% !important; }}
        .stButton > button {{ padding: 12px 16px !important; font-size: 15px !important; }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ============================================================================
# 2. PAGE HEADER
# ============================================================================

def render_page_header(title: str, description: str = ""):
    """Render a clean page header with optional description"""
    desc_html = f'<p>{description}</p>' if description else ''
    st.markdown(f'''
    <div class="page-header">
        <h2>{title}</h2>
        {desc_html}
    </div>
    ''', unsafe_allow_html=True)


# ============================================================================
# 3. KPI CARDS
# ============================================================================

def render_kpi_card(title, value, icon="", delta=None, color="primary"):
    """Modern KPI card with top accent border"""
    accent_map = {
        'primary': COLORS['primary'],
        'success': COLORS['success'],
        'warning': COLORS['warning'],
        'danger': COLORS['danger'],
        'info': COLORS['info'],
    }
    accent = accent_map.get(color, COLORS['primary'])

    # Create background for icon circle
    icon_bg_map = {
        'primary': COLORS['primary_light'],
        'success': COLORS['success_light'],
        'warning': COLORS['warning_light'],
        'danger': COLORS['danger_light'],
        'info': COLORS['info_light'],
    }
    icon_bg = icon_bg_map.get(color, COLORS['primary_light'])

    delta_html = ""
    if delta:
        is_negative = str(delta).startswith("-")
        d_color = COLORS['danger'] if is_negative else COLORS['success']
        d_icon = "trending-down" if is_negative else "trending-up"
        delta_html = f'''
        <div style="display:flex; align-items:center; gap:4px; margin-top:8px; font-size:12px; color:{d_color}; font-weight:600;">
            <i class="lucide-{d_icon}" style="width:14px; height:14px;"></i> {delta}
        </div>'''

    st.markdown(f'''
    <div style="
        background: {COLORS['surface']};
        border-radius: var(--radius-md, 10px);
        padding: 1.25rem;
        border: 1px solid {COLORS['border']};
        border-top: 3px solid {accent};
        transition: box-shadow 0.2s ease;
    " onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.08)'" onmouseout="this.style.boxShadow='none'">
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
            <div style="
                width:40px; height:40px; border-radius:10px;
                background:{icon_bg}; display:flex; align-items:center;
                justify-content:center; font-size:20px; flex-shrink:0;
            ">{icon}</div>
            <span style="font-size:12px; font-weight:600; color:{COLORS['text_secondary']}; text-transform:uppercase; letter-spacing:0.05em;">
                {title}
            </span>
        </div>
        <div style="font-size:2rem; font-weight:800; color:{COLORS['text_dark']}; line-height:1.1;">
            {value}
        </div>
        {delta_html}
    </div>
    ''', unsafe_allow_html=True)


def render_kpi_row(metrics: List[Dict[str, Any]], cols: int = 4):
    """Render a row of KPI cards"""
    columns = st.columns(cols)
    for i, metric in enumerate(metrics):
        with columns[i % cols]:
            render_kpi_card(
                title=metric.get('title', ''),
                value=metric.get('value', '0'),
                icon=metric.get('icon', ''),
                color=metric.get('color', 'primary'),
                delta=metric.get('delta')
            )


# ============================================================================
# 4. BREADCRUMB
# ============================================================================

def render_breadcrumb(items):
    """Render breadcrumb navigation"""
    parts = []
    for i, item in enumerate(items):
        if i == len(items) - 1:
            parts.append(f'<span style="color:{COLORS["primary"]}; font-weight:600;">{item}</span>')
        else:
            parts.append(f'<span style="color:{COLORS["text_muted"]};">{item}</span>')

    html = ' <span style="color:{c}; margin:0 6px;">/</span> '.format(c=COLORS['text_muted']).join(parts)

    st.markdown(f'''
    <div style="font-size:13px; margin-bottom:0.5rem; font-family:var(--font, Inter, sans-serif);">
        {html}
    </div>
    ''', unsafe_allow_html=True)


# ============================================================================
# 5. STATUS BADGES
# ============================================================================

def render_status_badge(status: str) -> str:
    """Return HTML for a modern status badge with dot indicator"""
    status_map = {
        'active':      ('status-active',   'Active'),
        'pending':     ('status-pending',  'Pending'),
        'rejected':    ('status-rejected', 'Rejected'),
        'closed':      ('status-closed',   'Closed'),
        'completed':   ('status-success',  'Completed'),
        'in_progress': ('status-info',     'In Progress'),
        'approved':    ('status-success',  'Approved'),
        'scheduled':   ('status-info',     'Scheduled'),
    }

    class_name, display_text = status_map.get(status.lower(), ('status-info', status))
    return f'<span class="status-badge {class_name}">{display_text}</span>'


def render_status_column(df: pd.DataFrame, status_col: str) -> pd.DataFrame:
    """Apply status badge styling to a dataframe column"""
    df[status_col] = df[status_col].apply(render_status_badge)
    return df


# ============================================================================
# 6. FORMS
# ============================================================================

def render_form_section(title: str, description: str = ""):
    """Section header inside a form"""
    desc_html = f'<p style="margin:4px 0 0; color:{COLORS["text_secondary"]}; font-size:13px;">{description}</p>' if description else ''
    st.markdown(f"""
    <div style="margin:20px 0 12px;">
        <h3 style="margin:0; color:{COLORS['text_dark']}; font-size:16px; font-weight:700;">{title}</h3>
        {desc_html}
    </div>
    """, unsafe_allow_html=True)


def render_form_field(label: str, required: bool = False, help_text: str = ""):
    """Render a form field label"""
    req = f' <span style="color:{COLORS["danger"]};">*</span>' if required else ''
    help_html = f'<p style="margin:2px 0 6px; color:{COLORS["text_muted"]}; font-size:12px;">{help_text}</p>' if help_text else ''
    st.markdown(f"""
    <label style="font-weight:600; color:{COLORS['text_dark']}; font-size:13px;">
        {label}{req}
    </label>
    {help_html}
    """, unsafe_allow_html=True)


def render_validation_message(message: str, message_type: str = "error"):
    """Render validation message"""
    config = {
        'error':   (COLORS['danger'],  COLORS['danger_light']),
        'success': (COLORS['success'], COLORS['success_light']),
        'warning': (COLORS['warning'], COLORS['warning_light']),
        'info':    (COLORS['info'],    COLORS['info_light']),
    }
    color, bg = config.get(message_type, (COLORS['info'], COLORS['info_light']))

    st.markdown(f"""
    <div style="padding:12px 16px; border-radius:{COLORS.get('radius_sm','6px') if False else '6px'}; background:{bg}; border-left:3px solid {color}; margin:12px 0;">
        <p style="margin:0; color:{color}; font-size:13px; font-weight:500;">{message}</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# 7. EMPTY STATE
# ============================================================================

def render_empty_state(icon: str = "", title: str = "No Data", description: str = ""):
    """Render an empty state placeholder"""
    desc_html = f'<p style="margin:0; color:{COLORS["text_muted"]}; font-size:14px;">{description}</p>' if description else ''
    st.markdown(f"""
    <div class="empty-state">
        <div class="empty-state-icon">{icon if icon else '📭'}</div>
        <h3 style="margin:8px 0; color:{COLORS['text_secondary']}; font-size:16px; font-weight:600;">{title}</h3>
        {desc_html}
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# 8. ENHANCED DATAFRAME
# ============================================================================

def render_enhanced_dataframe(df: pd.DataFrame, key: str = "",
                             searchable: bool = True,
                             sortable: bool = True):
    """Render dataframe with optional search"""
    if df.empty:
        render_empty_state(title="No Data Available", description="No records found matching your criteria.")
        return

    if searchable and len(df) > 0:
        search_term = st.text_input(
            "Search records",
            key=f"{key}_search",
            placeholder="Type to filter..."
        )
        if search_term:
            mask = df.astype(str).apply(
                lambda x: x.str.contains(search_term, case=False, na=False).any(),
                axis=1
            )
            df = df[mask]

    st.dataframe(df, use_container_width=True, hide_index=True, key=key)
    st.caption(f"Showing {len(df)} record(s)")


# ============================================================================
# 9. FEEDBACK COMPONENTS
# ============================================================================

def show_success(message: str, icon: str = ""):
    render_validation_message(message, "success")

def show_error(message: str, icon: str = ""):
    render_validation_message(message, "error")

def show_warning(message: str, icon: str = ""):
    render_validation_message(message, "warning")

def show_info(message: str, icon: str = ""):
    render_validation_message(message, "info")


# ============================================================================
# 10. UTILITIES
# ============================================================================

def format_metric(value: Any, metric_type: str = "number") -> str:
    """Format metric values for display"""
    if metric_type == "currency":
        return f"₹{value:,.2f}" if isinstance(value, (int, float)) else str(value)
    elif metric_type == "percentage":
        return f"{value:.1f}%" if isinstance(value, (int, float)) else str(value)
    elif metric_type == "number":
        return f"{value:,.0f}" if isinstance(value, (int, float)) else str(value)
    return str(value)


def create_two_column_form():
    """Helper to create responsive two-column form layout"""
    return st.columns(2)


# Initialize styling on import
apply_global_styling()
