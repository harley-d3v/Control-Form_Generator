import os
import streamlit as st
import pandas as pd
import json, math, base64, io
from datetime import datetime

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas as rl_canvas

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HIS Mode Choice — Control Form System",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USAGE_FILE = os.path.join(DATA_DIR, "usage.json")
ROWS_PER_FORM_DEFAULT = 6

CITIES = {
    "Metro Laoag": {
        "key": "laoag",
        "file": os.path.join(DATA_DIR, "laoag.csv"),
        "num_col": "#",
        "stratum_col": "Stratum",
        "color": "#1C4587",
    
    },
    "Metro La Union": {
        "key": "launion",
        "file": os.path.join(DATA_DIR, "launion.csv"),
        "num_col": "Point #",
        "stratum_col": "Point #",
        "color": "#276749",
    
    },
}

# ════════════════════════════════════════════════════════════════
# Data helpers
# ════════════════════════════════════════════════════════════════
@st.cache_data
def get_logos():
    d = p = ""
    for attr, fname in [("d", "dotr_logo_b64.txt"), ("p", "palafox_logo_b64.txt")]:
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            with open(path) as f:
                if attr == "d":
                    d = f.read().strip()
                else:
                    p = f.read().strip()
    return d, p

@st.cache_data
def load_city_data(city_key: str) -> pd.DataFrame:
    cfg = next(v for v in CITIES.values() if v["key"] == city_key)
    df = pd.read_csv(cfg["file"])
    df["_num"] = df[cfg["num_col"]].astype(str)
    df["_stratum"] = df[cfg["stratum_col"]].astype(str)
    df["_lat"] = df["Latitude"].astype(float)
    df["_lon"] = df["Longitude"].astype(float)
    df["_gps"] = (df["_lat"].map(lambda x: f"{x:.7f}") + ", "
                  + df["_lon"].map(lambda x: f"{x:.7f}"))
    return df.reset_index(drop=True)

def load_usage() -> dict:
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE) as f:
            return json.load(f)
    return {v["key"]: {"used": 0, "history": []} for v in CITIES.values()}

def save_usage(u: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USAGE_FILE, "w") as f:
        json.dump(u, f, indent=2)

# ════════════════════════════════════════════════════════════════
# CSS with modern sidebar style
# ════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* Professional clean design */
[data-testid="stAppViewContainer"] { 
    background: #F8FAFE; 
}

/* Modern Sidebar Design - Dark background */
[data-testid="stSidebar"] { 
    background: #171c2b !important;
    border-right: none !important;
    padding-top: 1rem !important;
    display: flex;
    flex-direction: column;
}
[data-testid="stSidebar"] * { 
    color: #FFFFFF !important; 
}
[data-testid="stSidebar"] label { 
    color: #B0B7C3 !important; 
    font-size: 13px !important; 
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { 
    color: #FFFFFF !important; 
}
[data-testid="stSidebarNav"] { 
    display: none; 
}

/* Sidebar buttons - Light background with dark text */
[data-testid="stSidebar"] div.stButton > button {
    background-color: #171c2b !important;
    color: #1F2937 !important;
    border: 1px solid #182c4e !important;
    border-radius: 4px !important;
    font-weight: 500 !important;
    padding: 0.75rem 1rem !important;
    margin: 6px 0 !important;
    width: 100% !important;
    font-size: 15px !important;
    text-align: left !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}
[data-testid="stSidebar"] div.stButton > button:hover {
    background-color: #171c2b !important;
    transform: translateX(2px);
    color: #111827 !important;
    border-color: #D1D5DB !important;
}
[data-testid="stSidebar"] div.stButton > button:active {
    background-color: #12086f !important;
    transform: translateX(1px);
}

/* Ensure sidebar content scrolls properly */
[data-testid="stSidebar"] > div:first-child {
    display: flex;
    flex-direction: column;
    height: 100%;
}

/* Metric cards - clean and professional */
div[data-testid="metric-container"] {
    background: white;
    border-radius: 12px;
    padding: 20px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid #E9ECF0;
    transition: all 0.2s ease;
}
div[data-testid="metric-container"]:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

/* Page header */
.page-header {
    background: linear-gradient(135deg, #1A2C3E 0%, #171c2b 100%);
    color: white;
    padding: 28px 32px;
    border-radius: 16px;
    margin-bottom: 28px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.page-header h1 { 
    font-size: 24px; 
    font-weight: 600; 
    margin: 0; 
    letter-spacing: -0.3px;
}
.page-header p { 
    font-size: 14px; 
    opacity: 0.85; 
    margin: 8px 0 0; 
}

/* KPI grid */
.kpi-grid { 
    display: grid; 
    grid-template-columns: repeat(4, 1fr); 
    gap: 20px; 
    margin-bottom: 28px; 
}
.kpi-card {
    background: white;
    border-radius: 16px;
    padding: 24px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid #E9ECF0;
    transition: all 0.2s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.kpi-label { 
    font-size: 13px; 
    font-weight: 600; 
    color: #5A6E8A; 
    text-transform: uppercase; 
    letter-spacing: 0.5px; 
    margin-bottom: 8px; 
}
.kpi-value { 
    font-size: 32px; 
    font-weight: 700; 
    color: #1A2C3E; 
    line-height: 1.1; 
    margin-bottom: 4px;
}
.kpi-sub { 
    font-size: 12px; 
    color: #8A9BB0; 
    margin-top: 4px; 
}
.kpi-blue { border-top: 3px solid #1C4587; }
.kpi-green { border-top: 3px solid #276749; }
.kpi-teal { border-top: 3px solid #0694A2; }
.kpi-red { border-top: 3px solid #C53030; }

/* Progress bar */
.prog-wrap { 
    background: #F0F3F8; 
    border-radius: 99px; 
    height: 8px; 
    margin: 8px 0 12px; 
    overflow: hidden; 
}
.prog-fill { 
    border-radius: 99px; 
    height: 8px; 
}

/* Status badge */
.sbadge { 
    display: inline-flex; 
    align-items: center; 
    gap: 6px; 
    padding: 4px 12px;
    border-radius: 99px; 
    font-size: 12px; 
    font-weight: 500; 
}
.sb-ok { 
    background: #E8F5E9; 
    color: #2E7D32; 
}
.sb-warn { 
    background: #FFF3E0; 
    color: #EF6C00; 
}
.sb-danger { 
    background: #FFEBEE; 
    color: #C62828; 
}

/* Activity chips */
.chip { 
    display: inline-block; 
    border-radius: 6px; 
    padding: 3px 10px;
    font-size: 12px; 
    font-weight: 500; 
    margin: 2px 4px 2px 0; 
}
.chip-blue { 
    background: #E8F0FE; 
    color: #1C4587; 
}
.chip-green { 
    background: #E8F5E9; 
    color: #276749; 
}
.chip-gray { 
    background: #F5F7FA; 
    color: #4A5568; 
}
.chip-date { 
    background: #F5F7FA; 
    color: #64748B; 
    border: 1px solid #E4EAF2; 
}
.activity-row { 
    padding: 8px 0; 
    border-bottom: 1px solid #F0F3F8; 
    font-size: 13px; 
}
.activity-row:last-child { 
    border-bottom: none; 
}

/* Form sheet - clean for print */
.form-sheet {
    background: white;
    padding: 24px 28px;
    margin-bottom: 24px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid #E9ECF0;
}
.form-label-bar {
    font-size: 13px;
    color: #1C4587;
    font-weight: 600;
    margin-bottom: 16px;
    padding: 8px 14px;
    background: #F8FAFE;
    border-radius: 8px;
    border-left: 3px solid #1C4587;
}

/* HIS tables - clean and readable */
.his-table { 
    width: 100%; 
    border-collapse: collapse; 
    font-size: 10px; 
    font-family: Arial, sans-serif; 
}
.his-table th, .his-table td {
    border: 1px solid #D0D5DD;
    padding: 6px 8px;
    vertical-align: middle;
    text-align: center;
}
.his-table th { 
    font-size: 10px;
    font-weight: 600;
    background: #F8FAFE;
    color: #1A2C3E;
}

/* Print styles */
@media print {
    [data-testid="stSidebar"],
    [data-testid="stToolbar"],
    [data-testid="stHeader"],
    .stButton,
    button,
    .no-print,
    .form-label-bar {
        display: none !important;
    }
    [data-testid="stAppViewContainer"] {
        background: white !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    .form-sheet {
        box-shadow: none !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 0 !important;
        page-break-after: always;
        margin: 0 !important;
        padding: 15px 20px !important;
    }
    .form-sheet:last-child {
        page-break-after: auto;
    }
    @page {
        margin: 10mm;
        size: A4 portrait;
    }
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# Form HTML builders (for Streamlit preview only)
# ════════════════════════════════════════════════════════════════

def _header_html(dotr: str, palafox: str) -> str:
    di = (f'<img src="data:image/png;base64,{dotr}" '
          f'style="height:65px;width:auto;display:block;object-fit:contain;"/>' if dotr else "")
    pi = (f'<img src="data:image/png;base64,{palafox}" '
          f'style="height:26px;width:auto;display:block;margin-top:5px;object-fit:contain;"/>' if palafox else "")
    return f"""
<table style="width:100%;border:none;border-collapse:collapse;margin-bottom:8px;font-family:Arial,sans-serif;">
<tr>
  <td style="border:none;width:38%;vertical-align:middle;padding:0;">
    <div style="display:flex;align-items:center;gap:12px;">{di}{pi}</div>
    </td>
  <td style="border:none;width:62%;vertical-align:top;padding:0;">
    <table style="width:100%;border-collapse:collapse;font-size:11px;">
      <tr>
        <td style="border:2px solid #000;padding:5px 10px;font-weight:bold;width:36%;">Enumerator:</td>
        <td style="border:2px solid #000;padding:5px 10px;width:64%;">&nbsp;</td>
      </tr>
      <tr>
        <td style="border:2px solid #000;padding:5px 10px;font-weight:bold;">Date of fieldwork:</td>
        <td style="border:2px solid #000;padding:5px 10px;">&nbsp;</td>
      </tr>
    </table>
    </td>
</tr>
</table>"""

def _page1_html(pts: pd.DataFrame, rpf: int, dotr: str, palafox: str) -> str:
    """Master Tracker – Page 1."""
    tbody = ""
    for i in range(rpf):
        if i < len(pts):
            p = pts.iloc[i]
            nv, sv, gv = p["_num"], p["_stratum"], p["_gps"]
            ng = sg = "background:#F8FAFE;font-weight:500;"
            gg = "background:#F8FAFE;font-weight:500;font-size:9px;"
        else:
            nv = sv = gv = ""
            ng = sg = gg = ""

        tbody += f"""
<tr style="height:30px;">
  <td style="{ng}">{nv}</td>
  <td style="{sg}">{sv}</td>
  <td style="{gg}">{gv}</td>
  <td></td>
  <td></td>
  <td></td>
  <td style="color:#1C4587;"></td>
  <td style="color:#1C4587;"></td>
  <td style="color:#1C4587;"></td>
  <td style="color:#1C4587;"></td>
  <td style="color:#980000;font-size:12px;">●</td>
</tr>"""

    return f"""
{_header_html(dotr, palafox)}
<div style="text-align:center;font-weight:bold;font-size:14px;font-family:Arial,sans-serif;margin:8px 0 2px;">
  Household Interview Survey For Mode Choice
</div>
<div style="text-align:center;font-size:12px;font-family:Arial,sans-serif;margin-bottom:8px;">
  Master Tracker (Page 1)
</div>
<table class="his-table" style="font-size:11px;">
<thead>
  <tr>
    <th rowspan="2" style="width:5%;">#</th>
    <th rowspan="2" style="width:7%;">Stratum</th>
    <th colspan="4" style="font-size:11px;">Original</th>
    <th colspan="4" style="color:#1C4587;font-size:11px;">
      Replacement <span style="font-style:italic;">(use only if original location result = 5)</span>
    </th>
    <th rowspan="2" style="color:#980000;width:9%;font-size:9px;">
      Replaced<br>from the<br>shared<br>pool?<sup>C</sup>
    </th>
  </tr>
  <tr>
    <th style="width:14%;">GPS Point<br>Coordinates</th>
    <th style="width:10%;">Location result<br><i style="font-weight:normal;">(Required)</i></th>
    <th style="width:9%;">Reason for<br>replacement<sup>A</sup></th>
    <th style="width:9%;">Reason for<br>ineligibility<sup>B</sup></th>
    <th style="color:#1C4587;width:14%;">GPS Point<br>Coordinates</th>
    <th style="color:#1C4587;width:11%;">Location Result<br>
      <i style="font-weight:normal;">(Required if GPS point used)</i></th>
    <th style="color:#1C4587;width:9%;">Reason for<br>replacement<sup>A</sup></th>
    <th style="color:#1C4587;width:9%;">Reason for<br>ineligibility<sup>B</sup></th>
  </tr>
</thead>
<tbody>{tbody}</tbody>
</table>"""

def _page2_html(pts: pd.DataFrame, rpf: int, dotr: str, palafox: str) -> str:
    """Usage of Shared Pool Tracker – Page 2."""
    tbody = ""
    for i in range(rpf):
        if i < len(pts):
            p = pts.iloc[i]
            val = p['_num']
            sty = "background:#F8FAFE;font-weight:500;"
        else:
            val, sty = "", ""
        tbody += f"""
<tr style="height:30px;">
  <td style="{sty}">{val}</td>
  <td></td>
  <td></td>
  <td></td>
  <td></td>
  <td></td>
  <td style="color:#980000;font-size:12px;">●</td>
</tr>"""

    td = "border:1px solid #D0D5DD;padding:5px 8px;font-size:10px;color:#4A5568;"
    leg = [
        ("1", "Completed interview <i>(specify household code)</i>",
         "1", "GPS point located, but did not lead to an eligible housing unit <i>(select reason from B)</i>",
         "1", "Housing unit is a verified vacant house (unoccupied)"),
        ("2", "Interviewed with take home forms <i>(specify household code, fill up Page 3 after)</i>",
         "2", "GPS point was not located (e.g., due to security concerns or inaccessible area)",
         "2", "Address is an empty lot or housing unit is destroyed/abolished/under construction"),
        ("3", "For revisiting, unattended during initial visit",
         "3", "Selected household refused",
         "3", "Not a permanent housing unit or non-residential building"),
        ("4", "For last revisit, unattended during 2nd visit",
         "4", "Housing unit still unattended after two revisits",
         "4", "Others: <i>Write reason in the box</i>"),
        ("5", "<i>Replaced (select reason from A)</i>", "", "", "", ""),
    ]
    lrows = ""
    for n1, t1, n2, t2, n3, t3 in leg:
        m = (f'<td style="{td}text-align:center;width:4%">{n2}</td>'
             f'<td style="{td}text-align:left;">{t2}</td>'
             if n2 else f'<td style="{td}" colspan="2"></td>')
        r = (f'<td style="{td}text-align:center;width:4%">{n3}</td>'
             f'<td style="{td}text-align:left;">{t3}</td>'
             if n3 else f'<td style="{td}" colspan="2"></td>')
        lrows += (f'<tr><td style="{td}text-align:center;width:4%">{n1}</td>'
                  f'<td style="{td}text-align:left;">{t1}</td>{m}{r}</tr>')

    return f"""
{_header_html(dotr, palafox)}
<div style="text-align:center;font-size:13px;font-family:Arial,sans-serif;margin:4px 0 8px;">
  Usage of Shared Pool Tracker (Page 2)
</div>
<table class="his-table" style="font-size:11px;">
<thead>
  <tr>
    <th style="width:16%;">#<br>
      <span style="font-weight:normal;font-size:9px;">(Copy from page 1 or 2)</span></th>
    <th style="width:13%;">#<br>
      <span style="font-weight:normal;font-size:9px;">(Replacement GPS point no.)</span></th>
    <th style="width:22%;">Replacement GPS Point Coordinates<br>
      <span style="font-weight:normal;font-size:9px;">(Can be filled up later on)</span></th>
    <th style="width:16%;">Location result<br><i style="font-weight:normal;">(Required)</i></th>
    <th style="width:13%;">Reason for<br>replacement<sup>A</sup></th>
    <th style="width:13%;">Reason for<br>ineligibility<sup>B</sup></th>
    <th style="color:#980000;width:12%;">Replaced from the<br>shared pool?</th>
  </tr>
</thead>
<tbody>{tbody}</tbody>
</table>
<div style="margin-top:12px;">
<table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;">
<thead>
  <tr>
    <th colspan="2" style="border:1px solid #D0D5DD;padding:6px 10px;text-align:left;width:34%;
        font-size:10px;color:#4A5568;font-style:italic;">Location Result (Required field)</th>
    <th colspan="2" style="border:1px solid #D0D5DD;padding:6px 10px;text-align:center;width:33%;
        font-size:10px;color:#4A5568;">(A) Reasons for replacement</th>
    <th colspan="2" style="border:1px solid #D0D5DD;padding:6px 10px;text-align:center;width:33%;
        font-size:10px;color:#4A5568;">(B) Housing unit ineligibility</th>
  </tr>
</thead>
<tbody>{lrows}</tbody>
</table>
</div>"""

def _page3_html(pts: pd.DataFrame, rpf: int, dotr: str, palafox: str) -> str:
    """Collection of Take Home Forms Tracker – Page 3."""
    y = "background:#FFF8E7;"
    tbody = ""
    for i in range(rpf):
        if i < len(pts):
            p = pts.iloc[i]
            nv, sv = p["_num"], p["_stratum"]
            ns = ss = "font-weight:500;"
        else:
            nv = sv = ""
            ns = ss = ""
        tbody += f"""
<tr style="height:34px;">
  <td style="{ns}">{nv}</td>
  <td style="{ss}">{sv}</td>
  <td style="{y}"></td>
  <td style="{y}"></td>
  <td style="{y}"></td>
  <td style="{y}"></td>
  <td style="{y}"></td>
  <td></td>
  <td></td>
</tr>"""

    return f"""
{_header_html(dotr, palafox)}
<div style="text-align:center;font-weight:bold;font-size:14px;font-family:Arial,sans-serif;margin:6px 0 2px;">
  Household Interview Survey For Mode Choice
</div>
<div style="text-align:center;font-size:12px;font-family:Arial,sans-serif;margin-bottom:4px;">
  Collection of Take Home Forms Tracker (Page 3)
</div>
<div style="font-size:10px;font-family:Arial,sans-serif;margin-bottom:8px;font-style:italic;">
  If you have provided take home forms to a sampled household, log it here at the end of the interview.
</div>
<table class="his-table" style="font-size:11px;">
<thead>
  <tr>
    <th rowspan="2" style="width:10%;">#<br>
      <span style="font-weight:normal;font-size:9px;">(Copy from<br>page 1 or page 2)</span></th>
    <th rowspan="2" style="width:9%;">Stratum</th>
    <th rowspan="2" style="width:13%;">Household Code</th>
    <th rowspan="2" style="width:19%;">Collection Date</th>
    <th rowspan="2" style="width:6%;">Pick-<br>up</th>
    <th rowspan="2" style="width:5%;">Drop<br>off*</th>
    <th rowspan="2" style="width:22%;">Contact person &amp; Contact no. for texting<br>
      Drop off location/Barangay Hall*</th>
    <th colspan="2" style="width:16%;">No. of Forms Given</th>
  </tr>
  <tr>
    <th style="width:8%;">Form 4<br>only</th>
    <th style="width:8%;">Form 3 &amp;&nbsp;4</th>
  </tr>
</thead>
<tbody>{tbody}</tbody>
</table>"""

SEP = '<div style="border-top:1.5px solid #E4EAF2;margin:20px 0 16px;"></div>'

# ── ReportLab helpers ────────────────────────────────────────────────────────

_BLACK = colors.black
_GREEN_BG = colors.HexColor("#F8FAFE")
_YELLOW_BG = colors.HexColor("#FFF8E7")
_BLUE = colors.HexColor("#1C4587")
_RED = colors.HexColor("#980000")
_DGREEN = colors.HexColor("#276749")
_GRAY = colors.HexColor("#4A5568")
_LGRAY = colors.HexColor("#D0D5DD")

def _b64_to_image(b64str: str, height_mm: float = None, width_mm: float = None) -> RLImage | None:
    """Decode a base-64 PNG/JPEG string into a ReportLab Image with proper sizing."""
    if not b64str:
        return None
    try:
        data = base64.b64decode(b64str)
        buf = io.BytesIO(data)
        img = RLImage(buf)
        
        if width_mm and height_mm:
            # Use both dimensions (for palafox logo)
            img.drawWidth = width_mm * mm
            img.drawHeight = height_mm * mm
        elif width_mm:
            # Use width and maintain aspect ratio
            w = width_mm * mm
            h = (w * img.imageHeight) / img.imageWidth
            img.drawWidth = w
            img.drawHeight = h
        elif height_mm:
            # Use height and maintain aspect ratio
            h = height_mm * mm
            w = (h * img.imageWidth) / img.imageHeight
            img.drawWidth = w
            img.drawHeight = h
        return img
    except Exception as e:
        print(f"Error loading image: {e}")
        return None

def _para(text: str, size: float = 9, bold: bool = False,
          color=_BLACK, align=TA_CENTER) -> Paragraph:
    """Convenience: HTML-capable Paragraph with larger default size."""
    face = "Helvetica-Bold" if bold else "Helvetica"
    style = ParagraphStyle(
        "tmp", fontName=face, fontSize=size, textColor=color,
        alignment=align, leading=size * 1.3, spaceAfter=0, spaceBefore=0,
    )
    return Paragraph(text, style)

def _rl_header(dotr: str, palafox: str, page_width: float) -> Table:
    """Header row: logos left, Enumerator/Date fields right with horizontal layout."""
    # Load logos with appropriate sizes
    dotr_img = _b64_to_image(dotr, height_mm=16)
    palafox_img = _b64_to_image(palafox, height_mm=6, width_mm=41)

    # Create a horizontal table for logos instead of a list
    if dotr_img or palafox_img:
        logo_items = []
        if dotr_img:
            logo_items.append(dotr_img)
        if palafox_img:
            logo_items.append(palafox_img)
        
        # Create a horizontal table for logos
        if len(logo_items) == 2:
            logo_table = Table(
                [logo_items],
                colWidths=[None, None],
                rowHeights=[16 * mm],
            )
            logo_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            logo_cell = logo_table
        elif len(logo_items) == 1:
            logo_cell = logo_items[0]
        else:
            logo_cell = _para("", size=8)
    else:
        logo_cell = _para("", size=8)

    field_table = Table(
        [
            [_para("Enumerator:", size=9, bold=True, align=TA_LEFT), _para("", size=9)],
            [_para("Date of fieldwork:", size=9, bold=True, align=TA_LEFT), _para("", size=9)],
        ],
        colWidths=[page_width * 0.38 * 0.40, page_width * 0.38 * 0.60],
        rowHeights=[9 * mm, 9 * mm],
    )
    field_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.2, _BLACK),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _BLACK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    hdr = Table(
        [[logo_cell, field_table]],
        colWidths=[page_width * 0.55, page_width * 0.45],
    )
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return hdr

def _rl_page1(pts: pd.DataFrame, rpf: int, dotr: str, palafox: str,
              page_width: float) -> list:
    """Returns a list of ReportLab flowables for Page 1 with larger tables."""
    
    cw = [
        page_width * 0.045,   # #
        page_width * 0.065,   # Stratum
        page_width * 0.145,   # GPS (orig)
        page_width * 0.10,    # Loc result
        page_width * 0.085,   # Reason A
        page_width * 0.085,   # Reason B
        page_width * 0.14,    # GPS (repl)
        page_width * 0.105,   # Loc result (repl)
        page_width * 0.085,   # Reason A (repl)
        page_width * 0.085,   # Reason B (repl)
        page_width * 0.11,    # Replaced from pool
    ]

    TH = _para

    header_row1 = [
        TH("#", 8, bold=True),
        TH("Stratum", 8, bold=True),
        TH("Original", 8, bold=True),
        "", "", "",
        TH("Replacement (use only if original = 5)", 7.5, bold=True, color=_BLUE),
        "", "", "",
        TH("Replaced\nfrom the\nshared\npool? C", 7.5, bold=True, color=_RED),
    ]
    header_row2 = [
        "", "",
        TH("GPS Point\nCoordinates", 8, bold=True),
        TH("Location\nresult\n(Required)", 8, bold=True),
        TH("Reason for\nreplacement A", 8, bold=True),
        TH("Reason for\nineligibility B", 8, bold=True),
        TH("GPS Point\nCoordinates", 8, bold=True, color=_BLUE),
        TH("Location Result\n(Req. if used)", 8, bold=True, color=_BLUE),
        TH("Reason for\nreplacement A", 8, bold=True, color=_BLUE),
        TH("Reason for\nineligibility B", 8, bold=True, color=_BLUE),
        "",
    ]

    data = [header_row1, header_row2]
    span_cmds = [
        ("SPAN", (0, 0), (0, 1)),
        ("SPAN", (1, 0), (1, 1)),
        ("SPAN", (2, 0), (5, 0)),
        ("SPAN", (6, 0), (9, 0)),
        ("SPAN", (10, 0), (10, 1)),
    ]

    row_cmds = []
    row_height = 8.5 * mm
    
    for i in range(rpf):
        ri = i + 2
        if i < len(pts):
            p = pts.iloc[i]
            nv = str(p["_num"])
            sv = str(p["_stratum"])
            gv = str(p["_gps"])
            row = [
                TH(nv, 8, bold=True), TH(sv, 8, bold=True),
                TH(gv, 7.5, bold=True),
                "", "", "",
                "", "", "", "",
                TH("●", 9, color=_RED),
            ]
            row_cmds += [
                ("BACKGROUND", (0, ri), (2, ri), _GREEN_BG),
            ]
        else:
            row = ["", "", "", "", "", "", "", "", "", "", TH("●", 9, color=_RED)]

        data.append(row)

    tbl = Table(data, colWidths=cw, rowHeights=[None, None] + [row_height] * rpf)
    style = TableStyle([
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _BLACK),
        ("BOX", (0, 0), (-1, -1), 0.8, _BLACK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, 1), 8),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#F8FAFE")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ] + span_cmds + row_cmds)
    tbl.setStyle(style)

    title1 = TH("Household Interview Survey For Mode Choice", 11, bold=True, align=TA_CENTER)
    title2 = TH("Master Tracker (Page 1)", 9.5, align=TA_CENTER)

    return [
        _rl_header(dotr, palafox, page_width),
        Spacer(1, 4 * mm),
        title1,
        Spacer(1, 2 * mm),
        title2,
        Spacer(1, 3 * mm),
        tbl,
    ]

def _rl_page2(pts: pd.DataFrame, rpf: int, dotr: str, palafox: str,
              page_width: float) -> list:
    """Returns flowables for Page 2 with larger tables and simplified # column."""
    cw = [
        page_width * 0.165,
        page_width * 0.135,
        page_width * 0.22,
        page_width * 0.16,
        page_width * 0.13,
        page_width * 0.12,
        page_width * 0.09,
    ]

    header = [[
        _para("#\n(Copy from pg 1 or 2)", 8, bold=True),
        _para("#\n(Replacement GPS pt no.)", 8, bold=True),
        _para("Replacement GPS Point Coordinates\n(Can be filled later)", 8, bold=True),
        _para("Location result\n(Required)", 8, bold=True),
        _para("Reason for\nreplacement A", 8, bold=True),
        _para("Reason for\nineligibility B", 8, bold=True),
        _para("Replaced from the\nshared pool?", 8, bold=True, color=_RED),
    ]]

    data = header[:]
    row_cmds = []
    row_height = 8.5 * mm
    
    for i in range(rpf):
        ri = i + 1
        if i < len(pts):
            p = pts.iloc[i]
            val = str(p["_num"])
            row = [_para(val, 8, bold=True), "", "", "", "", "", _para("●", 9, color=_RED)]
            row_cmds.append(("BACKGROUND", (0, ri), (0, ri), _GREEN_BG))
        else:
            row = ["", "", "", "", "", "", _para("●", 9, color=_RED)]
        data.append(row)

    tbl = Table(data, colWidths=cw, rowHeights=[None] + [row_height] * rpf)
    tbl.setStyle(TableStyle([
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _BLACK),
        ("BOX", (0, 0), (-1, -1), 0.8, _BLACK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFE")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ] + row_cmds))

    td_style = ParagraphStyle("leg", fontName="Helvetica", fontSize=8,
                               textColor=_GRAY, leading=10)
    legend_data = [
        [
            _para("Location Result (Required field)", 8, bold=False, color=_GRAY, align=TA_LEFT),
            "",
            _para("(A) Reasons for replacement", 8, bold=True, color=_GRAY, align=TA_CENTER),
            "",
            _para("(B) Housing unit ineligibility", 8, bold=True, color=_GRAY, align=TA_CENTER),
            "",
        ],
        ["1", Paragraph("Completed interview (specify household code)", td_style),
         "1", Paragraph("GPS point located, but did not lead to an eligible housing unit", td_style),
         "1", Paragraph("Housing unit is a verified vacant house (unoccupied)", td_style)],
        ["2", Paragraph("Interviewed with take home forms (specify household code, fill Page 3 after)", td_style),
         "2", Paragraph("GPS point was not located (e.g., security concerns or inaccessible area)", td_style),
         "2", Paragraph("Address is an empty lot or housing unit destroyed/under construction", td_style)],
        ["3", Paragraph("For revisiting, unattended during initial visit", td_style),
         "3", Paragraph("Selected household refused", td_style),
         "3", Paragraph("Not a permanent housing unit or non-residential building", td_style)],
        ["4", Paragraph("For last revisit, unattended during 2nd visit", td_style),
         "4", Paragraph("Housing unit still unattended after two revisits", td_style),
         "4", Paragraph("Others: Write reason in the box", td_style)],
        ["5", Paragraph("Replaced (select reason from A)", td_style),
         "", "", "", ""],
    ]
    leg_cw = [page_width * 0.04, page_width * 0.29,
              page_width * 0.04, page_width * 0.29,
              page_width * 0.04, page_width * 0.30]
    leg_tbl = Table(legend_data, colWidths=leg_cw)
    leg_tbl.setStyle(TableStyle([
        ("INNERGRID", (0, 0), (-1, -1), 0.4, _LGRAY),
        ("BOX", (0, 0), (-1, -1), 0.6, _LGRAY),
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (2, 0), (3, 0)),
        ("SPAN", (4, 0), (5, 0)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ALIGN", (4, 0), (4, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFE")),
    ]))

    title = _para("Usage of Shared Pool Tracker (Page 2)", 10, align=TA_CENTER)

    return [
        _rl_header(dotr, palafox, page_width),
        Spacer(1, 4 * mm),
        title,
        Spacer(1, 3 * mm),
        tbl,
        Spacer(1, 6 * mm),
        leg_tbl,
    ]

def _rl_page3(pts: pd.DataFrame, rpf: int, dotr: str, palafox: str,
              page_width: float) -> list:
    """Returns flowables for Page 3 with larger tables."""
    cw = [
        page_width * 0.10, page_width * 0.09, page_width * 0.13,
        page_width * 0.19, page_width * 0.06, page_width * 0.05,
        page_width * 0.22, page_width * 0.08, page_width * 0.08,
    ]

    header1 = [
        _para("#\n(Copy from\npage 1 or 2)", 8, bold=True),
        _para("Stratum", 8, bold=True),
        _para("Household Code", 8, bold=True),
        _para("Collection Date", 8, bold=True),
        _para("Pick-\nup", 8, bold=True),
        _para("Drop\noff*", 8, bold=True),
        _para("Contact person & Contact no.\nDrop off location/Barangay Hall*", 8, bold=True),
        _para("No. of Forms Given", 8, bold=True),
        "",
    ]
    header2 = ["", "", "", "", "", "", "",
               _para("Form 4\nonly", 8, bold=True),
               _para("Form 3\n& 4", 8, bold=True)]

    data = [header1, header2]
    span_cmds = [
        ("SPAN", (0, 0), (0, 1)),
        ("SPAN", (1, 0), (1, 1)),
        ("SPAN", (2, 0), (2, 1)),
        ("SPAN", (3, 0), (3, 1)),
        ("SPAN", (4, 0), (4, 1)),
        ("SPAN", (5, 0), (5, 1)),
        ("SPAN", (6, 0), (6, 1)),
        ("SPAN", (7, 0), (8, 0)),
    ]

    row_cmds = []
    row_height = 9 * mm
    
    for i in range(rpf):
        ri = i + 2
        if i < len(pts):
            p = pts.iloc[i]
            nv = str(p["_num"])
            sv = str(p["_stratum"])
            row = [_para(nv, 8, bold=True), _para(sv, 8, bold=True),
                   "", "", "", "", "", "", ""]
            row_cmds += [
                ("BACKGROUND", (2, ri), (6, ri), _YELLOW_BG),
            ]
        else:
            row = ["", "", "", "", "", "", "", "", ""]
            row_cmds += [("BACKGROUND", (2, ri), (6, ri), _YELLOW_BG)]
        data.append(row)

    tbl = Table(data, colWidths=cw, rowHeights=[None, None] + [row_height] * rpf)
    tbl.setStyle(TableStyle([
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _BLACK),
        ("BOX", (0, 0), (-1, -1), 0.8, _BLACK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#F8FAFE")),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ] + span_cmds + row_cmds))

    title1 = _para("Household Interview Survey For Mode Choice", 11, bold=True, align=TA_CENTER)
    title2 = _para("Collection of Take Home Forms Tracker (Page 3)", 9.5, align=TA_CENTER)
    subtext = _para(
        "If you have provided take home forms to a sampled household, "
        "log it here at the end of the interview.", 8.5, align=TA_LEFT)

    return [
        _rl_header(dotr, palafox, page_width),
        Spacer(1, 4 * mm),
        title1,
        Spacer(1, 2 * mm),
        title2,
        Spacer(1, 2 * mm),
        subtext,
        Spacer(1, 3 * mm),
        tbl,
    ]

def _build_form_flowables(pts: pd.DataFrame, form_num: int, total: int,
                          city_name: str, rpf: int, dotr: str, palafox: str,
                          page_width: float) -> list:
    """All 3 pages for one form as a list of flowables."""
    elems = []
    elems += _rl_page1(pts, rpf, dotr, palafox, page_width)
    elems.append(PageBreak())
    elems += _rl_page2(pts, rpf, dotr, palafox, page_width)
    elems.append(PageBreak())
    elems += _rl_page3(pts, rpf, dotr, palafox, page_width)
    return elems

def _make_single_pdf(pts: pd.DataFrame, form_num: int, total: int,
                     city_name: str, rpf: int, dotr: str, palafox: str) -> bytes:
    buf = io.BytesIO()
    margin = 8 * mm
    page = landscape(LETTER)
    doc = SimpleDocTemplate(
        buf, pagesize=page,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
    )
    pw = page[0] - 2 * margin
    doc.build(_build_form_flowables(pts, form_num, total, city_name, rpf, dotr, palafox, pw))
    return buf.getvalue()

def _make_combined_pdf(forms: list, city_name: str, rpf: int,
                       dotr: str, palafox: str) -> bytes:
    buf = io.BytesIO()
    margin = 8 * mm
    page = landscape(LETTER)
    doc = SimpleDocTemplate(
        buf, pagesize=page,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
    )
    pw = page[0] - 2 * margin
    elems = []
    for i, f in enumerate(forms):
        elems += _build_form_flowables(
            f["points_df"], f["form_num"], len(forms),
            f["city_name"], rpf, dotr, palafox, pw,
        )
        if i < len(forms) - 1:
            elems.append(PageBreak())
    doc.build(elems)
    return buf.getvalue()

# ── HTML form body (Streamlit preview only) ─────────────────────────────────
def _form_body(pts: pd.DataFrame, form_num: int, total: int,
               city_name: str, rpf: int, dotr: str, palafox: str,
               for_pdf: bool = False) -> str:
    first = pts.iloc[0]["_num"] if len(pts) else "—"
    last = pts.iloc[-1]["_num"] if len(pts) else "—"
    label = (f"Form {form_num} of {total} &nbsp;·&nbsp; {city_name} "
             f"&nbsp;·&nbsp; Points #{first} – #{last}")
    bar = "" if for_pdf else f'<div class="form-label-bar no-print">📋 {label}</div>'
    p1 = _page1_html(pts, rpf, dotr, palafox)
    p2 = _page2_html(pts, rpf, dotr, palafox)
    p3 = _page3_html(pts, rpf, dotr, palafox)
    return f'<div class="form-sheet">{bar}{p1}{SEP}{p2}{SEP}{p3}</div>'

# ════════════════════════════════════════════════════════════════
# Session state
# ════════════════════════════════════════════════════════════════
if "usage" not in st.session_state:
    st.session_state.usage = load_usage()
if "generated_forms" not in st.session_state:
    st.session_state.generated_forms = []
if "rows_per_form" not in st.session_state:
    st.session_state.rows_per_form = ROWS_PER_FORM_DEFAULT
if "nav_selection" not in st.session_state:
    st.session_state.nav_selection = "📊 Dashboard"

dotr_b64, palafox_b64 = get_logos()

# ════════════════════════════════════════════════════════════════
# Sidebar with modern navigation menu
# ════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════
# Sidebar with modern navigation menu
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    # Title section
    st.markdown("""
    <div style="padding: 0 1rem 1rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 1rem;">
        <h2 style="color: #FFFFFF; margin-bottom: 0.25rem; font-size: 30px; font-weight: 600;">HIS Mode Choice</h2>
        <p style="color: #9CA3AF; margin: 0; font-size: 16px;">Control Form Generator</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main Menu header
    st.markdown("""
    <div style="padding: 0 1rem;">
        <div style="font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; color: #9CA3AF; margin-bottom: 0.75rem;">MAIN MENU</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Dashboard button
    if st.button("📊 Dashboard", key="nav_dash", use_container_width=True):
        st.session_state.nav_selection = "📊 Dashboard"
        st.rerun()
    
    # Generate Forms button
    if st.button("📝 Generate Forms", key="nav_gen", use_container_width=True):
        st.session_state.nav_selection = "📝 Generate Forms"
        st.rerun()
    
    # View Forms button
    if st.button("📄 View Forms", key="nav_view", use_container_width=True):
        st.session_state.nav_selection = "📄 View Forms"
        st.rerun()
    
    # Footer
    st.markdown("""
    <div style="padding: 1rem; text-align: left; font-size: 10px; color: #cbcbcb; border-top: 1px solid rgba(255,255,255,0.1); margin-top: auto;">
        HIS Mode Choice Survey · v1.0
    </div>
    """, unsafe_allow_html=True)

nav = st.session_state.nav_selection

# ════════════════════════════════════════════════════════════════
# PAGE — Dashboard
# ════════════════════════════════════════════════════════════════
# PAGE — Dashboard
if nav == "📊 Dashboard":
    st.markdown("""
    <div class="page-header">
      <h1>Operations Dashboard</h1>
      <p>Household Interview Survey for Mode Choice · Field Operations Tracker</p>
    </div>""", unsafe_allow_html=True)

    usage = st.session_state.usage
    total_all = sum(len(load_city_data(v["key"])) for v in CITIES.values())
    used_all = sum(usage.get(v["key"], {}).get("used", 0) for v in CITIES.values())
    forms_all = sum(len(usage.get(v["key"], {}).get("history", [])) for v in CITIES.values())
    rem_all = total_all - used_all
    pct_all = used_all / total_all * 100 if total_all else 0

    top_color = "kpi-red" if rem_all < 100 else "kpi-blue"
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card kpi-blue">
        <div class="kpi-label">Total GPS Points</div>
        <div class="kpi-value">{total_all:,}</div>
        <div class="kpi-sub">Across all cities</div>
      </div>
      <div class="kpi-card kpi-green">
        <div class="kpi-label">Points Assigned</div>
        <div class="kpi-value">{used_all:,}</div>
        <div class="kpi-sub">{pct_all:.1f}% of total</div>
      </div>
      <div class="kpi-card kpi-teal">
        <div class="kpi-label">Forms Generated</div>
        <div class="kpi-value">{forms_all:,}</div>
        <div class="kpi-sub">All sessions combined</div>
      </div>
      <div class="kpi-card {top_color}">
        <div class="kpi-label">Points Remaining</div>
        <div class="kpi-value">{rem_all:,}</div>
        <div class="kpi-sub">Available to assign</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # City detail cards
    col_a, col_b = st.columns(2, gap="large")
    for idx, (city_name, cfg) in enumerate(CITIES.items()):
        df_c = load_city_data(cfg["key"])
        used = usage.get(cfg["key"], {}).get("used", 0)
        hist = usage.get(cfg["key"], {}).get("history", [])
        rem = len(df_c) - used
        pct = used / len(df_c) * 100 if len(df_c) else 0
        col = col_a if idx == 0 else col_b

        with col:
            with st.container(border=True):
                st.markdown(f"#### {city_name}")

                m1, m2, m3 = st.columns(3)
                m1.metric("Total", f"{len(df_c):,}")
                m2.metric("Assigned", f"{used:,}")
                m3.metric("Remaining", f"{rem:,}")

                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"align-items:center;margin-top:10px;margin-bottom:2px;'>"
                    f"<span style='font-size:12px;font-weight:500;color:#5A6E8A;'>Usage</span>"
                    f"<span style='font-size:12px;font-weight:600;color:{cfg['color']};'>{pct:.1f}%</span>"
                    f"</div>",
                    unsafe_allow_html=True)
                st.markdown(
                    f"<div class='prog-wrap'><div class='prog-fill' "
                    f"style='width:{pct:.1f}%;background:{cfg['color']};'></div></div>",
                    unsafe_allow_html=True)

                st.markdown("<hr style='border:none;border-top:1px solid #E9ECF0;margin:16px 0 12px;'/>",
                            unsafe_allow_html=True)

                if hist:
                    st.markdown("<span style='font-size:12px;font-weight:500;color:#5A6E8A;'>"
                                "Recent Activity</span>", unsafe_allow_html=True)
                    for h in reversed(hist[-5:]):
                        st.markdown(
                            f"<div class='activity-row'>"
                            f"<span class='chip chip-date'>📅 {h['date']}</span>"
                            f"<span class='chip chip-blue'>{h['forms']} form(s)</span>"
                            f"<span class='chip chip-green'>{h['points']} pts</span>"
                            f"<span class='chip chip-gray'>#{h['from']} → #{h['to']}</span>"
                            f"</div>", unsafe_allow_html=True)
                else:
                    st.markdown(
                        "<div style='font-size:12px;color:#8A9BB0;padding:8px 0;font-style:italic;'>"
                        "No activity yet.</div>", unsafe_allow_html=True)

            with st.expander(f"⚠️ Reset {city_name} usage"):
                st.warning("This will mark all points as unused and clear history. Cannot be undone.")
                if st.button(f"Confirm Reset — {city_name}", key=f"reset_{cfg['key']}", type="secondary"):
                    st.session_state.usage[cfg["key"]] = {"used": 0, "history": []}
                    save_usage(st.session_state.usage)
                    st.success("Reset complete.")
                    st.rerun()

# ════════════════════════════════════════════════════════════════
# PAGE — Generate Forms
# ════════════════════════════════════════════════════════════════
elif nav == "📝 Generate Forms":
    st.markdown("""
    <div class="page-header">
      <h1>📝 Generate Forms</h1>
      <p>Select a city and set how many forms to generate. Points are assigned sequentially — no duplicates.</p>
    </div>""", unsafe_allow_html=True)

    city_choice = st.selectbox("Select City", list(CITIES.keys()))
    cfg = CITIES[city_choice]
    df = load_city_data(cfg["key"])
    used = st.session_state.usage.get(cfg["key"], {}).get("used", 0)
    rem = len(df) - used
    
    # Points per form setting
    st.markdown("---")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("**📄 Form Settings**")
    with col2:
        rpf = st.number_input("Points/HH per Form", min_value=1, max_value=20,
                              value=st.session_state.rows_per_form, step=1)
        st.session_state.rows_per_form = rpf
    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Total Points", f"{len(df):,}")
    c2.metric("✅ Already Assigned", f"{used:,}")
    c3.metric("📍 Available Now", f"{rem:,}")

    pct = used / len(df) * 100 if len(df) else 0
    st.markdown(
        f"<div style='font-size:12px;font-weight:500;color:#5A6E8A;"
        f"margin-top:10px;margin-bottom:4px;'>Usage: {pct:.1f}%</div>",
        unsafe_allow_html=True)
    st.progress(pct / 100)
    st.markdown("---")

    max_forms = max(1, (rem + rpf - 1) // rpf)
    form_count = st.slider("Number of forms to generate", 1, min(max_forms, 100), 1)
    pts_needed = form_count * rpf
    pts_avail = min(pts_needed, rem)
    full_forms = pts_avail // rpf
    partial = pts_avail % rpf

    if rem > 0:
        st.info(
            f"**Preview:** {form_count} form(s) · **{rpf} pts/form** · "
            f"Points **#{used+1}** → **#{used+pts_avail}** · "
            f"{full_forms} full form(s)"
            + (f" + 1 partial ({partial} pts)" if partial else "")
        )

    if rem == 0:
        st.error("⚠️ All GPS points for this city have been used. Reset from the Dashboard.")
    else:
        if st.button("Generate Forms", type="primary", use_container_width=True):
            batch = df.iloc[used: used + pts_needed].copy()
            actual_pts = len(batch)
            new_forms = []
            for i in range(form_count):
                chunk = batch.iloc[i * rpf: (i + 1) * rpf]
                if len(chunk):
                    new_forms.append({
                        "city_key": cfg["key"],
                        "city_name": city_choice,
                        "points_df": chunk,
                        "form_num": i + 1,
                    })
            st.session_state.generated_forms = new_forms
            first_num = batch.iloc[0]["_num"] if len(batch) else "—"
            last_num = batch.iloc[-1]["_num"] if len(batch) else "—"
            st.session_state.usage[cfg["key"]]["used"] = used + actual_pts
            st.session_state.usage[cfg["key"]].setdefault("history", []).append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "forms": len(new_forms), "points": actual_pts,
                "from": first_num, "to": last_num,
            })
            save_usage(st.session_state.usage)
            st.success(
                f"✅ {len(new_forms)} form(s) generated · {actual_pts} pts assigned "
                f"(#{first_num} → #{last_num}). Go to **View Forms** to download."
            )

# ════════════════════════════════════════════════════════════════
# PAGE — View Forms
# ════════════════════════════════════════════════════════════════
elif nav == "📄 View Forms":
    st.markdown("""
    <div class="page-header">
      <h1>📄 View &amp; Export Forms</h1>
      <p>All 3 pages per set — Master Tracker · Shared Pool Tracker · Take Home Forms Tracker</p>
    </div>""", unsafe_allow_html=True)

    forms = st.session_state.generated_forms
    if not forms:
        st.info("No forms generated yet. Go to **Generate Forms** first.")
    else:
        city_name = forms[0]["city_name"]
        city_key = forms[0]["city_key"]
        rpf = st.session_state.rows_per_form
        total_pts = sum(len(f["points_df"]) for f in forms)

        # Summary bar
        with st.container(border=True):
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Form Sets", len(forms))
            sc2.metric("GPS Points", total_pts)
            sc3.metric("Pts per Form", rpf)
            sc4.metric("Pages/Set", 3)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # Download / Print bar
        # with st.container(border=True):
        #     st.markdown(
        #         f"<div style='font-size:13px;font-weight:600;color:#1A2C3E;margin-bottom:12px;'>"
        #         f"📥 Export &amp; Print — {city_name}</div>",
        #         unsafe_allow_html=True)

        btn_cols = st.columns([1, 1] + [0.8] * len(forms))

        #     # # Print button - uses browser print
        #     # with btn_cols[0]:
        #     #     st.markdown(
        #     #         """
        #     #         <button onclick="window.print();" style="
        #     #             width: 100%;
        #     #             padding: 0.5rem 1rem;
        #     #             background-color: #FFFFFF;
        #     #             color: #1A2C3E;
        #     #             border: 1px solid #D0D5DD;
        #     #             border-radius: 8px;
        #     #             cursor: pointer;
        #     #             font-size: 14px;
        #     #             font-weight: 500;
        #     #             transition: all 0.2s;
        #     #         " onmouseover="this.style.backgroundColor='#F8FAFE'" 
        #     #         onmouseout="this.style.backgroundColor='#FFFFFF'">
        #     #             🖨️ Print All
        #     #         </button>
        #     #         """,
        #     #         unsafe_allow_html=True
        #     #     )

            # Combined PDF
        with btn_cols[1]:
                with st.spinner("Building PDF…"):
                    all_pdf = _make_combined_pdf(forms, city_name, rpf, dotr_b64, palafox_b64)
                    # Get first and last points of all forms combined
                    all_first_pt = forms[0]["points_df"].iloc[0]["_num"] if forms else "0"
                    all_last_pt = forms[-1]["points_df"].iloc[-1]["_num"] if forms else "0"
                    st.download_button(
                    "⬇️ All Forms (PDF)",
                    data=all_pdf,
                    file_name=f"HIS_AllForms_{city_key}_{all_first_pt}-{all_last_pt}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_all",
                )

            # Per-form PDF buttons
        for i, f in enumerate(forms):
                first_pt = f["points_df"].iloc[0]["_num"]
                last_pt = f["points_df"].iloc[-1]["_num"]
                with btn_cols[2 + i]:
                    with st.spinner(f"PDF {i+1}…"):
                        single_pdf = _make_single_pdf(
                            f["points_df"], f["form_num"], len(forms),
                            f["city_name"], rpf, dotr_b64, palafox_b64)
                    st.download_button(
                        f"⬇️ Form {f['form_num']}",
                        data=single_pdf,
                        file_name=f"HIS_Form{f['form_num']}_{city_key}_pts{first_pt}-{last_pt}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"dl_form_{i}",
                    )

        st.markdown("---")

        # Form preview
        for f in forms:
            st.markdown(
                _form_body(f["points_df"], f["form_num"], len(forms),
                           f["city_name"], rpf, dotr_b64, palafox_b64),
                unsafe_allow_html=True)