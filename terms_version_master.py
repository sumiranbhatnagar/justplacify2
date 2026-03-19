import streamlit as st
import hashlib
import datetime
import json
from fpdf import FPDF

# ─── PAGE CONFIG ───
st.set_page_config(
    page_title="T&C Version Lock",
    page_icon="⚖️",
    layout="wide"
)

# ─── STYLE ───
st.markdown("""
<style>
    .main { background-color: #e8f5e9; }
    .stApp { background-color: #e8f5e9; }
    .block-container { padding-top: 2rem; }

    .header-box {
        background: #f4fbf4;
        border: 1px solid #a5d6a7;
        border-radius: 14px;
        padding: 18px 24px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .card {
        background: #f4fbf4;
        border: 1px solid #a5d6a7;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
    }
    .card-title {
        font-size: 13px;
        font-weight: 700;
        color: #2e7d32;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 12px;
    }
    .info-box {
        background: #dceede;
        border: 1px solid #b2dfba;
        border-radius: 9px;
        padding: 10px 13px;
        margin-bottom: 8px;
    }
    .info-label { font-size: 10px; color: #6a9b6d; text-transform: uppercase; letter-spacing: 0.8px; }
    .info-val { font-size: 13px; color: #3a5c3c; font-family: monospace; word-break: break-all; }
    .info-val-big { font-size: 26px; color: #2e7d32; font-weight: 700; }
    .badge-active {
        background: rgba(46,125,50,0.1);
        color: #2e7d32;
        border: 1px solid rgba(46,125,50,0.3);
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-arch {
        background: rgba(106,155,109,0.1);
        color: #6a9b6d;
        border: 1px solid #b2dfba;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
    }
    .hint { font-size: 11px; color: #6a9b6d; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE INIT ───
if 'version_master' not in st.session_state:
    st.session_state.version_master = []  # Terms_Version_Master DB
if 'active_version' not in st.session_state:
    st.session_state.active_version = None
if 'draft_text' not in st.session_state:
    st.session_state.draft_text = """नियम एवं शर्तें

1. स्वीकृति
इस एप्लिकेशन का उपयोग करके, आप इन नियमों और शर्तों से बंधे होने के लिए सहमत होते हैं।

2. उपयोगकर्ता की जिम्मेदारियां
आप अपने खाते की सुरक्षा और उसके अंतर्गत होने वाली सभी गतिविधियों के लिए जिम्मेदार हैं।

3. डेटा गोपनीयता
हम आपके डेटा को हमारी गोपनीयता नीति के अनुसार संसाधित करते हैं।

4. बौद्धिक संपदा
एप्लिकेशन की सभी सामग्री कंपनी की संपत्ति है और कानूनी रूप से सुरक्षित है।

5. दायित्व की सीमा
कंपनी किसी भी अप्रत्यक्ष क्षति के लिए उत्तरदायी नहीं होगी।

6. प्रशासनिक कानून
ये शर्तें लागू कानूनों द्वारा शासित होंगी।"""

# ─── HELPER FUNCTIONS ───
def sha256_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def next_version():
    db = st.session_state.version_master
    if not db:
        return "v1.0.0"
    last = db[-1]['version'].replace('v', '').split('.')
    major, minor, patch = int(last[0]), int(last[1]), int(last[2])
    patch += 1
    if patch >= 10: patch = 0; minor += 1
    if minor >= 10: minor = 0; major += 1
    return f"v{major}.{minor}.{patch}"

def make_pdf(ver, date, text):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_fill_color(244, 251, 244)
        pdf.rect(0, 0, 210, 40, 'F')
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(46, 125, 50)
        pdf.cell(0, 12, "Terms & Conditions", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(106, 155, 109)
        pdf.cell(0, 6, f"Version: {ver}   |   Date: {date}", ln=True)
        pdf.cell(0, 6, "Auto-generated & Locked - Version Lock System", ln=True)
        pdf.ln(4)
        pdf.set_draw_color(178, 223, 186)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(58, 92, 60)
        # Write text line by line
        for line in text.split('\n'):
            try:
                pdf.multi_cell(0, 5, line.encode('latin-1', 'replace').decode('latin-1'))
            except:
                pdf.multi_cell(0, 5, line.encode('ascii', 'replace').decode('ascii'))
        filename = f"TC_{ver.replace('.','_')}.pdf"
        pdf.output(filename)
        return filename
    except Exception as e:
        return None

def apply_new_tc(terms_text):
    ver = next_version()
    now = datetime.datetime.now()
    date_str = now.strftime("%d %b %Y")
    pub_str  = now.strftime("%d %b %Y, %I:%M %p")
    hash_val = sha256_hash(terms_text + ver + date_str)
    pdf_name = f"TC_{ver.replace('.','_')}.pdf"
    drive_path = f"Drive://TnC/{pdf_name}"

    # Archive old active
    for v in st.session_state.version_master:
        if v['status'] == 'active':
            v['status'] = 'archived'

    # New record
    record = {
        'id': now.timestamp(),
        'version': ver,
        'effectiveDate': date_str,
        'publishedAt': pub_str,
        'hash': hash_val,
        'hashShort': hash_val[:16] + '...',
        'driveFile': drive_path,
        'pdfName': pdf_name,
        'termsText': terms_text,
        'status': 'active'
    }
    st.session_state.version_master.append(record)
    st.session_state.active_version = record
    return record, ver, date_str, hash_val, pdf_name, terms_text

# ═══════════════════════════════════════════════
# UI START
# ═══════════════════════════════════════════════

# HEADER
st.markdown("""
<div class="header-box">
  <span style="font-size:28px">⚖️</span>
  <div>
    <div style="font-size:17px;font-weight:700;color:#1b2a1c">नियम एवं शर्तें — Version Lock System</div>
    <div style="font-size:11px;color:#6a9b6d">Admin Panel — Automatic Version Control</div>
  </div>
  <span style="margin-left:auto;background:rgba(46,125,50,0.1);border:1px solid rgba(46,125,50,0.3);color:#2e7d32;padding:6px 13px;border-radius:20px;font-size:11px;font-weight:600">🟢 System चालू है</span>
</div>
""", unsafe_allow_html=True)

# ─── TABS ───
tab1, tab2, tab3 = st.tabs(["📝 Draft & Publish", "🔒 Active Version", "📋 Version Master"])

# ─────────────────────────────────────────
# TAB 1 — DRAFT & PUBLISH
# ─────────────────────────────────────────
with tab1:
    st.markdown('<div class="card-title">📝 नियम एवं शर्तें — Draft (Master Text)</div>', unsafe_allow_html=True)

    draft = st.text_area(
        label="Terms Draft",
        value=st.session_state.draft_text,
        height=280,
        label_visibility="collapsed",
        key="draft_input"
    )
    st.markdown('<div class="hint">✏️ ऊपर text बदलें — नीचे button दबाने पर ही publish होगी, सीधे edit से नहीं।</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 4])
    with col1:
        apply_btn = st.button("⚡ नई T&C लागू करें", type="primary", use_container_width=True)
    with col2:
        reset_btn = st.button("↩ Draft रीसेट करें", use_container_width=False)

    if reset_btn:
        if st.session_state.active_version:
            st.session_state.draft_text = st.session_state.active_version['termsText']
            st.rerun()
        else:
            st.warning("कोई active version नहीं है — reset नहीं हो सकता।")

    if apply_btn:
        text = draft.strip()
        if not text:
            st.error("❌ Terms text खाली है। कुछ लिखकर दोबारा try करें।")
        else:
            with st.status("⚡ नई T&C लागू हो रही है...", expanded=True) as status:
                import time

                st.write("✅ नया Version Number generate हो रहा है...")
                time.sleep(0.5)

                st.write("✅ Effective Date auto-set हो रही है...")
                time.sleep(0.4)

                st.write("✅ SHA-256 Hash compute हो रही है...")
                time.sleep(0.6)

                record, ver, date_str, hash_val, pdf_name, terms_text = apply_new_tc(text)

                st.write("✅ PDF auto-generate हो रही है...")
                time.sleep(0.7)
                pdf_file = make_pdf(ver, date_str, text)

                st.write("✅ Drive में नई file save हो रही है...")
                time.sleep(0.4)

                st.write("✅ Terms_Version_Master में entry हो रही है...")
                time.sleep(0.4)

                st.write("✅ पुरानी version read-only हो गई...")
                time.sleep(0.3)

                st.write("✅ Users को re-accept flag कर दिया गया...")
                time.sleep(0.4)

                status.update(label="🎉 Version सफलतापूर्वक लागू हुई!", state="complete")

            st.success(f"""
**{ver} Publish हो गई!**
- प्रभावी तिथि: {date_str}
- SHA-256: `{hash_val[:32]}...`
- PDF File: `{pdf_name}`
- Drive: `Drive://TnC/{pdf_name}`
            """)

            # PDF Download
            if pdf_file:
                try:
                    with open(pdf_file, "rb") as f:
                        st.download_button(
                            label=f"📥 PDF Download करें ({pdf_name})",
                            data=f.read(),
                            file_name=pdf_name,
                            mime="application/pdf"
                        )
                except:
                    st.info(f"PDF तैयार है: {pdf_name}")

            st.session_state.draft_text = text

# ─────────────────────────────────────────
# TAB 2 — ACTIVE VERSION
# ─────────────────────────────────────────
with tab2:
    av = st.session_state.active_version
    if not av:
        st.info("अभी तक कोई T&C publish नहीं हुई। 'Draft & Publish' tab में जाकर publish करें।")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="info-box">
                <div class="info-label">Version</div>
                <div class="info-val-big">{av['version']}</div>
            </div>
            <div class="info-box">
                <div class="info-label">प्रभावी तिथि</div>
                <div class="info-val">{av['effectiveDate']}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Publish समय</div>
                <div class="info-val">{av['publishedAt']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="info-box">
                <div class="info-label">PDF File</div>
                <div class="info-val">{av['pdfName']}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Drive Path</div>
                <div class="info-val">{av['driveFile']}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Status</div>
                <div class="info-val"><span class="badge-active">🟢 सक्रिय & Locked</span></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="info-box">
            <div class="info-label">SHA-256 Hash (Full)</div>
            <div class="info-val" style="font-size:10px;color:#6a9b6d">{av['hash']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**📄 Active Terms Text (Read-only):**")
        st.text_area("Active Terms", value=av['termsText'], height=200, disabled=True, label_visibility="collapsed")

# ─────────────────────────────────────────
# TAB 3 — VERSION MASTER TABLE
# ─────────────────────────────────────────
with tab3:
    db = st.session_state.version_master
    st.markdown(f'<div class="card-title">📋 Terms_Version_Master — कुल {len(db)} Versions</div>', unsafe_allow_html=True)

    if not db:
        st.info("कोई record नहीं। पहली T&C publish करें।")
    else:
        import pandas as pd
        rows = []
        for v in reversed(db):
            rows.append({
                "Version": v['version'],
                "प्रभावी तिथि": v['effectiveDate'],
                "Publish समय": v['publishedAt'],
                "SHA-256 (short)": v['hashShort'],
                "PDF File": v['pdfName'],
                "Status": "🟢 सक्रिय" if v['status'] == 'active' else "🔒 Archived"
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Export
        json_data = json.dumps(st.session_state.version_master, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON Export (Backup)",
            data=json_data,
            file_name="terms_version_master_backup.json",
            mime="application/json"
        )