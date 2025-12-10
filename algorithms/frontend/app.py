"""Streamlit frontend - Optimized One-Page UI for Land Redistribution Algorithm.

Single-page design with:
- Left: Configuration + Input
- Center: Action + Status
- Right: Results + Visualization
"""

import streamlit as st
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any
import matplotlib.pyplot as plt
from shapely.geometry import shape, Polygon
import numpy as np
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration - Support both local and production deployment
API_URL = os.getenv("API_URL", "http://localhost:8000")


# Page config - Wide layout for one-page design
st.set_page_config(
    page_title="Land Redistribution Optimizer",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for premium styling
st.markdown("""
<style>
    /* ===== CSS CUSTOM PROPERTIES (THEME) ===== */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --accent-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --dark-bg: #0f0f1a;
        --card-bg: rgba(255, 255, 255, 0.03);
        --card-border: rgba(255, 255, 255, 0.08);
        --text-primary: #ffffff;
        --text-secondary: rgba(255, 255, 255, 0.7);
        --success: #10b981;
        --warning: #f59e0b;
        --error: #ef4444;
        --shadow-glow: 0 0 40px rgba(102, 126, 234, 0.15);
    }
    
    /* ===== GLOBAL STYLES ===== */
    .stApp {
        background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    .main .block-container {
        padding: 1rem 2rem;
        max-width: 100%;
    }
    
    /* ===== GLASSMORPHISM CARDS ===== */
    .stExpander {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .stExpander:hover {
        border-color: rgba(102, 126, 234, 0.3) !important;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.1);
    }
    
    /* ===== BUTTON STYLING ===== */
    .stButton > button {
        width: 100%;
        border-radius: 12px;
        font-weight: 600;
        padding: 0.875rem 1.5rem;
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: none;
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5);
    }
    
    .stButton > button[kind="primary"]:active {
        transform: translateY(0);
    }
    
    /* Secondary buttons */
    .stButton > button:not([kind="primary"]) {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: white;
    }
    
    .stButton > button:not([kind="primary"]):hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(102, 126, 234, 0.5);
    }
    
    /* ===== METRIC CARDS ===== */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    [data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.6) !important;
        font-weight: 500;
    }
    
    /* ===== INPUT FIELDS ===== */
    /* ===== INPUT FIELDS ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div,
    input[type="number"],
    input[type="text"] {
        background: #ffffff !important;
        border: 1px solid rgba(102, 126, 234, 0.5) !important;
        border-radius: 10px !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
        opacity: 1 !important;
        text-shadow: none !important;
        font-weight: 500 !important;
        transition: all 0.2s ease;
    }
    
    /* NEW: Fix Number Input Stepper Buttons (+ / -) */
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"] {
        color: #333 !important;
        background: transparent !important;
        border-color: rgba(0,0,0,0.1) !important;
    }
    
    button[data-testid="stNumberInputStepDown"]:hover,
    button[data-testid="stNumberInputStepUp"]:hover {
        background: rgba(0,0,0,0.05) !important;
        color: #000 !important;
    }
    
    /* Fix the SVG icons inside those buttons */
    button[data-testid="stNumberInputStepDown"] svg,
    button[data-testid="stNumberInputStepUp"] svg {
        fill: #333 !important;
        color: #333 !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: rgba(102, 126, 234, 0.5) !important;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
    }
    
    /* ===== RADIO & CHECKBOX ===== */
    .stRadio > div {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        padding: 0.5rem;
    }
    
    /* ===== SECTION HEADERS ===== */
    h3, .stMarkdown h3 {
        color: white !important;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* ===== STATUS INDICATORS ===== */
    .stSuccess {
        background: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-radius: 10px !important;
    }
    
    .stWarning {
        background: rgba(245, 158, 11, 0.1) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
        border-radius: 10px !important;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        border-radius: 10px !important;
    }
    
    .stInfo {
        background: rgba(102, 126, 234, 0.1) !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 10px !important;
    }
    
    /* ===== HIDE STREAMLIT BRANDING ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ===== CUSTOM SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.02);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(102, 126, 234, 0.3);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(102, 126, 234, 0.5);
    }
    
    /* ===== RESPONSIVE ===== */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0.5rem;
        }
    }
    
    /* ===== PLOTLY CHART CONTAINER ===== */
    .stPlotlyChart {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 1rem;
    }
    
    /* ===== DOWNLOAD BUTTONS ===== */
    .stDownloadButton > button {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }
    
    .stDownloadButton > button:hover {
        background: rgba(102, 126, 234, 0.2) !important;
        border-color: rgba(102, 126, 234, 0.5) !important;
    }
    
    /* ===== FIX: ALL LABELS WHITE TEXT ===== */
    /* Form labels */
    label, .stTextInput label, .stNumberInput label,
    .stSelectbox label, .stSlider label, .stRadio label,
    .stCheckbox label, .stTextArea label {
        color: rgba(255, 255, 255, 0.9) !important;
        font-weight: 500 !important;
    }
    
    /* Slider value labels */
    .stSlider > div > div > div > div {
        color: white !important;
    }
    
    /* ===== EXPANDER TITLE FIX (CRITICAL) ===== */
    /* Expander header/summary - add background for visibility */
    .stExpander > details > summary,
    .stExpander details summary,
    .stExpander summary,
    [data-testid="stExpander"] summary,
    details[data-testid] > summary {
        color: white !important;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%) !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
    }
    
    /* Expander title text - FORCE WHITE with background */
    .stExpander summary > span,
    .stExpander summary p,
    .stExpander > details > summary > span,
    .stExpander > details > summary > div,
    .stExpander > details > summary > div > p,
    .stExpander > details > summary > div > span,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary div,
    summary > div > p,
    summary > div > span,
    summary span,
    summary p {
        color: white !important;
        -webkit-text-fill-color: white !important;
        text-shadow: 0 0 1px rgba(0,0,0,0.5) !important;
    }
    
    /* SVG icons in expanders */
    .stExpander svg,
    .stExpander summary svg,
    [data-testid="stExpander"] svg {
        fill: white !important;
        color: white !important;
    }
    
    /* Override any Streamlit theme colors for expanders */
    .stExpander [class*="StyledHeader"],
    .stExpander [class*="header"],
    .stExpander [data-baseweb] {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }
    
    /* Expander content text */
    .stExpander p, .stExpander span, .stExpander div {
        color: rgba(255, 255, 255, 0.85) !important;
    }
    
    /* Radio button labels */
    .stRadio > div > label,
    .stRadio > div > div > label,
    .stRadio label span {
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Checkbox labels */
    .stCheckbox > div > label {
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* General paragraph/text */
    p, span {
        color: rgba(255, 255, 255, 0.8);
    }
    
    /* Number input min/max labels */
    .stNumberInput > div > div > span {
        color: rgba(255, 255, 255, 0.7) !important;
    }
    
    /* Selectbox text - dark on light background */
    .stSelectbox > div > div > div > div {
        color: #333 !important;
    }
    
    /* Markdown text in expanders */
    .stMarkdown p, .stMarkdown span {
        color: rgba(255, 255, 255, 0.85) !important;
    }
    
    /* Column headers and strong text */
    strong, b {
        color: white !important;
    }
    
    /* Text area styling - dark text on light background */
    textarea, .stTextArea textarea {
        color: #333 !important;
        background: #ffffff !important;
        border: 1px solid rgba(102, 126, 234, 0.5) !important;
    }
    
    /* ===== PLOTLY CHART DARK MODE FIX ===== */
    .js-plotly-plot .plotly .modebar {
        background: rgba(0,0,0,0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# Premium Header with gradient background
st.markdown("""
<div style="
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 2rem 1rem;
    margin-bottom: 2rem;
    text-align: center;
    backdrop-filter: blur(10px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
">
    <h1 style="
        margin: 0;
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #f093fb 50%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.02em;
    ">🏘️ Land Redistribution Optimizer</h1>
    <p style="
        color: rgba(255, 255, 255, 0.6);
        margin-top: 0.75rem;
        font-size: 1.1rem;
        font-weight: 400;
    ">
        NSGA-II Grid Optimization + OR-Tools Block Subdivision
    </p>
    <div style="
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin-top: 1rem;
    ">
        <span style="
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            border: 1px solid rgba(16, 185, 129, 0.3);
        ">✓ Production Ready</span>
        <span style="
            background: rgba(102, 126, 234, 0.2);
            color: #667eea;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            border: 1px solid rgba(102, 126, 234, 0.3);
        ">v2.0</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'land_plot' not in st.session_state:
    st.session_state.land_plot = None
if 'result' not in st.session_state:
    st.session_state.result = None
if 'status' not in st.session_state:
    st.session_state.status = 'ready'

# Main layout: 3 columns
col_config, col_action, col_result = st.columns([1.2, 1, 2])

# ==================== COLUMN 1: Configuration ====================
with col_config:
    st.markdown("### ⚙️ Configuration")
    
    # Quick Presets
    with st.expander("🎯 Quick Presets", expanded=True):
        preset = st.selectbox(
            "Choose a preset:",
            ["Custom", "🚀 Fastest", "⚖️ Balanced", "🏆 Best Quality"],
            help="Select a preset or use Custom to set your own values"
        )
        
        # Apply preset values
        if preset == "🚀 Fastest":
            default_pop = 20
            default_gen = 50
            default_ort = 0.5
        elif preset == "⚖️ Balanced":
            default_pop = 50
            default_gen = 75
            default_ort = 5.0
        elif preset == "🏆 Best Quality":
            default_pop = 150
            default_gen = 150
            default_ort = 15.0
        else:  # Custom
            default_pop = 50
            default_gen = 50
            default_ort = 5.0
    
    # Grid Optimization Parameters
    with st.expander("🔲 Grid Optimization", expanded=True):
        st.markdown("**Spacing (meters):**")
        c1, c2 = st.columns(2)
        with c1:
            spacing_min = st.number_input(
                "Min", 
                min_value=30.0, 
                max_value=150.0, 
                value=50.0, 
                step=5.0,
                help="Minimum grid spacing"
            )
        with c2:
            spacing_max = st.number_input(
                "Max", 
                min_value=30.0, 
                max_value=200.0, 
                value=100.0, 
                step=5.0,
                help="Maximum grid spacing"
            )
        
        st.markdown("**Rotation Angle (degrees):**")
        c1, c2 = st.columns(2)
        with c1:
            angle_min = st.number_input(
                "Min Angle", 
                min_value=0.0, 
                max_value=90.0, 
                value=0.0, 
                step=1.0,
                help="Minimum rotation angle"
            )
        with c2:
            angle_max = st.number_input(
                "Max Angle", 
                min_value=0.0, 
                max_value=90.0, 
                value=90.0, 
                step=1.0,
                help="Maximum rotation angle"
            )
    
    # Subdivision Parameters
    with st.expander("📐 Lot Subdivision", expanded=True):
        st.markdown("**Lot Width (meters):**")
        c1, c2, c3 = st.columns(3)
        with c1:
            min_lot_width = st.number_input(
                "Min", 
                min_value=10.0, 
                max_value=40.0, 
                value=20.0, 
                step=1.0,
                help="Minimum lot width"
            )
        with c2:
            target_lot_width = st.number_input(
                "Target", 
                min_value=20.0, 
                max_value=100.0, 
                value=40.0, 
                step=5.0,
                help="Target lot width"
            )
        with c3:
            max_lot_width = st.number_input(
                "Max", 
                min_value=40.0, 
                max_value=120.0, 
                value=80.0, 
                step=5.0,
                help="Maximum lot width"
            )
    
    # Optimization Parameters
    with st.expander("⚡ Optimization", expanded=False):
        st.markdown("**NSGA-II Genetic Algorithm:**")
        c1, c2 = st.columns(2)
        with c1:
            population_size = st.number_input(
                "Population Size", 
                min_value=20, 
                max_value=200, 
                value=default_pop, 
                step=10,
                help="Number of solutions per generation"
            )
        with c2:
            generations = st.number_input(
                "Generations", 
                min_value=50, 
                max_value=500, 
                value=default_gen, 
                step=10,
                help="Number of evolution iterations"
            )
        
        st.markdown("**OR-Tools Solver:**")
        ortools_time_limit = st.number_input(
            "Time per Block (seconds)", 
            min_value=0.1, 
            max_value=60.0, 
            value=default_ort, 
            step=0.1,
            help="Maximum time for solving each block"
        )
        
        # Show time estimate
        est_time = (population_size * generations) / 50
        if est_time > 60:
            st.info(f"⏱️ Estimated time: ~{est_time//60:.0f} minutes")
        else:
            st.info(f"⏱️ Estimated time: ~{est_time:.0f} seconds")
        
        if est_time > 600:
            st.warning("⚠️ May timeout (>10 min). Consider reducing parameters.")
    
    # Infrastructure Parameters
    with st.expander("🏗️ Infrastructure", expanded=False):
        road_width = st.number_input(
            "Road Width (m)", 
            min_value=3.0, 
            max_value=10.0, 
            value=6.0, 
            step=0.5,
            help="Width of roads between blocks"
        )
        block_depth = st.number_input(
            "Block Depth (m)", 
            min_value=30.0, 
            max_value=100.0, 
            value=50.0, 
            step=5.0,
            help="Depth of each block"
        )

# ==================== COLUMN 2: Input & Action ====================
with col_action:
    st.markdown("### 📍 Land Plot")
    
    # Input method selection
    input_method = st.radio(
        "Input method:",
        ["Sample", "DXF Upload", "GeoJSON Upload", "Manual"],
        horizontal=False
    )
    
    if input_method == "Sample":
        # Predefined sample
        sample_type = st.selectbox(
            "Sample type:",
            ["Rectangle 100x100", "L-Shape", "Irregular", "Large Site"]
        )
        
        if sample_type == "Rectangle 100x100":
            coords = [[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]]
        elif sample_type == "L-Shape":
            coords = [[[0, 0], [60, 0], [60, 40], [40, 40], [40, 100], [0, 100], [0, 0]]]
        elif sample_type == "Irregular":
            coords = [[[0, 0], [80, 10], [100, 50], [90, 100], [20, 90], [0, 0]]]
        else:  # Large Site
            coords = [[
                [0, 0], [950, 50], [1000, 800], [400, 1100], 
                [100, 900], [-50, 400], [0, 0]
            ]]
        
        st.session_state.land_plot = {
            "type": "Polygon",
            "coordinates": coords,
            "properties": {"name": sample_type}
        }
    
    elif input_method == "DXF Upload":
        st.info("📐 Upload DXF file containing site boundary (closed polyline)")
        uploaded = st.file_uploader(
            "DXF file", 
            type=['dxf'], 
            key="dxf_upload",
            help="File should contain closed LWPOLYLINE or POLYLINE for site boundary"
        )
        
        if uploaded:
            with st.spinner("⏳ Parsing DXF..."):
                try:
                    # Upload to backend API
                    files = {"file": (uploaded.name, uploaded.getvalue(), "application/dxf")}
                    response = requests.post(f"{API_URL}/api/upload-dxf", files=files)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.land_plot = data['polygon']
                        st.success(f"✅ {data['message']}")
                        st.info(f"📊 Area: {data['area']:.2f} m²")
                    else:
                        st.error(f"Failed to parse DXF: {response.text}")
                        st.session_state.land_plot = None
                        
                except Exception as e:
                    st.error(f"Error uploading DXF: {str(e)}")
                    st.session_state.land_plot = None
        
    elif input_method == "GeoJSON Upload":
        uploaded = st.file_uploader("GeoJSON file", type=['json', 'geojson'], key="geojson_upload")
        if uploaded:
            try:
                data = json.load(uploaded)
                if data['type'] == 'FeatureCollection':
                    st.session_state.land_plot = data['features'][0]['geometry']
                else:
                    st.session_state.land_plot = data
                st.success(f"✅ Loaded {uploaded.name}")
            except Exception as e:
                st.error(f"Invalid file: {e}")
                st.session_state.land_plot = None
                
    else:  # Manual
        coords_input = st.text_area(
            "Coordinates (JSON):",
            '''[
  [0, 0], 
  [950, 50], 
  [1000, 800], 
  [400, 1100], 
  [100, 900],
  [-50, 400], 
  [0, 0]
]''',
            height=150
        )
        try:
            coords = json.loads(coords_input)
            st.session_state.land_plot = {
                "type": "Polygon",
                "coordinates": [coords],
                "properties": {}
            }
        except:
            st.error("Invalid JSON")
    
    # Preview
    if st.session_state.land_plot:
        with st.expander("📋 Preview", expanded=False):
            st.json(st.session_state.land_plot, expanded=False)
    
    st.markdown("---")
    
    # Status & Action
    st.markdown("### 🚀 Execute")
    
    # Status indicator
    status = st.session_state.status
    if status == 'ready':
        st.success("✅ Ready to optimize")
    elif status == 'running':
        st.warning("⏳ Processing...")
    elif status == 'complete':
        st.success("✅ Complete!")
    else:
        st.error("❌ Error occurred")
    
    # Run button
    if st.button("🚀 Run Optimization", type="primary", use_container_width=True, 
                 disabled=st.session_state.land_plot is None):
        
        st.session_state.status = 'running'
        
        config = {
            "spacing_min": spacing_min,
            "spacing_max": spacing_max,
            "angle_min": angle_min,
            "angle_max": angle_max,
            "min_lot_width": min_lot_width,
            "max_lot_width": max_lot_width,
            "target_lot_width": target_lot_width,
            "road_width": road_width,
            "block_depth": block_depth,
            "population_size": population_size,
            "generations": generations,
            "ortools_time_limit": ortools_time_limit
        }
        
        with st.spinner("Running NSGA-II + OR-Tools..."):
            try:
                # Show progress information
                progress_text = st.empty()
                progress_text.info(f"🔄 Starting optimization with {population_size} population × {generations} generations...")
                
                response = requests.post(
                    f"{API_URL}/api/optimize",
                    json={
                        "config": config,
                        "land_plots": [st.session_state.land_plot]
                    },
                    timeout=600  # Increased to 10 minutes
                )
                
                progress_text.empty()
                
                if response.status_code == 200:
                    st.session_state.result = response.json()
                    st.session_state.status = 'complete'
                    st.rerun()
                else:
                    st.session_state.status = 'error'
                    st.error(f"API Error: {response.text[:200]}")
                    
            except requests.exceptions.Timeout:
                st.session_state.status = 'error'
                st.error(f"⏱️ Optimization timed out after 10 minutes. Try reducing Population ({population_size}) or Generations ({generations}).")
            except requests.exceptions.ConnectionError:
                st.session_state.status = 'error'
                st.error("Cannot connect to API. Is backend running on port 8000?")
            except Exception as e:
                st.session_state.status = 'error'
                st.error(f"Error: {str(e)}")
    
    # Reset button
    if st.session_state.result:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.result = None
            st.session_state.status = 'ready'
            st.rerun()

# ==================== COLUMN 3: Results ====================
with col_result:
    st.markdown("### 📊 Results")
    
    if st.session_state.result is None:
        # Show placeholder with input preview
        st.info("Run optimization to see results here")
        
        # Show input polygon preview
        if st.session_state.land_plot:
            coords = st.session_state.land_plot['coordinates'][0]
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=xs, y=ys,
                fill='toself',
                fillcolor='rgba(100, 126, 234, 0.2)',
                line=dict(color='#667eea', width=2),
                name='Input Land'
            ))
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                title="Input Land Plot",
                showlegend=False
            )
            fig.update_yaxes(scaleanchor="x", scaleratio=1)
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        result = st.session_state.result
        stats = result.get('statistics', {})
        
        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("🔲 Blocks", stats.get('total_blocks', 0))
        with m2:
            st.metric("🏠 Lots", stats.get('total_lots', 0))
        with m3:
            st.metric("🌳 Parks", stats.get('total_parks', 0))
        with m4:
            st.metric("📏 Avg Width", f"{stats.get('avg_lot_width', 0):.1f}m")
        
        # Optimized parameters
        st.markdown("**Optimized Parameters:**")
        p1, p2 = st.columns(2)
        with p1:
            st.info(f"🔲 Spacing: **{stats.get('optimal_spacing', 0):.1f}m**")
        with p2:
            st.info(f"📐 Angle: **{stats.get('optimal_angle', 0):.1f}°**")
        
        # === Advanced Interactive Visualization (Plotly) ===
        st.markdown("### 🗺️ Master Plan Visualization")
        
        def plot_master_plan_plotly(result_data):
            """
            CAD-Style Master Plan Visualization.
            Professional engineering drawing with:
            - Hatching patterns on lots (like AutoCAD)
            - Tree symbols in parks
            - Road centerlines and edges
            - Building-style thick borders
            - Engineering grid background
            """
            import random
            from shapely.geometry import Point
            
            try:
                features = result_data.get('final_layout', {}).get('features', [])
                fig = go.Figure()
                
                # Collect bounds for auto-fit
                all_x, all_y = [], []
                
                # --- HELPER FUNCTIONS ---
                def get_poly_coords(geom):
                    if geom.geom_type == 'Polygon':
                        return [geom.exterior.xy]
                    elif geom.geom_type == 'MultiPolygon':
                        return [poly.exterior.xy for poly in geom.geoms]
                    return []

                def get_line_coords(geom):
                    if geom.geom_type == 'LineString':
                        return [geom.xy]
                    elif geom.geom_type == 'MultiLineString':
                        return [line.xy for line in geom.geoms]
                    return []
                
                def generate_trees_in_polygon(polygon, count=8):
                    """Generate tree positions within a polygon"""
                    minx, miny, maxx, maxy = polygon.bounds
                    trees = []
                    attempts = 0
                    while len(trees) < count and attempts < 100:
                        px = random.uniform(minx, maxx)
                        py = random.uniform(miny, maxy)
                        if polygon.contains(Point(px, py)):
                            trees.append((px, py))
                        attempts += 1
                    return trees
                
                def generate_hatch_lines(polygon, spacing=15, angle=45):
                    """Generate hatching lines for a polygon"""
                    import math
                    minx, miny, maxx, maxy = polygon.bounds
                    lines_x, lines_y = [], []
                    
                    # Extend bounds to ensure coverage
                    diag = math.sqrt((maxx-minx)**2 + (maxy-miny)**2)
                    cx, cy = (minx+maxx)/2, (miny+maxy)/2
                    
                    rad = math.radians(angle)
                    cos_a, sin_a = math.cos(rad), math.sin(rad)
                    
                    # Generate parallel lines
                    for offset in range(-int(diag/2), int(diag/2), spacing):
                        # Line perpendicular to angle
                        x1 = cx + offset * cos_a - diag * sin_a
                        y1 = cy + offset * sin_a + diag * cos_a
                        x2 = cx + offset * cos_a + diag * sin_a
                        y2 = cy + offset * sin_a - diag * cos_a
                        
                        # Clip to polygon
                        from shapely.geometry import LineString
                        line = LineString([(x1, y1), (x2, y2)])
                        clipped = polygon.intersection(line)
                        
                        if clipped.is_empty:
                            continue
                        if clipped.geom_type == 'LineString':
                            coords = list(clipped.coords)
                            if len(coords) >= 2:
                                lines_x.extend([coords[0][0], coords[-1][0], None])
                                lines_y.extend([coords[0][1], coords[-1][1], None])
                        elif clipped.geom_type == 'MultiLineString':
                            for seg in clipped.geoms:
                                coords = list(seg.coords)
                                if len(coords) >= 2:
                                    lines_x.extend([coords[0][0], coords[-1][0], None])
                                    lines_y.extend([coords[0][1], coords[-1][1], None])
                    
                    return lines_x, lines_y

                # --- CAD COLOR PALETTE ---
                CAD_COLORS = {
                    'lot_fill': 'rgba(255, 248, 220, 0.6)',      # Cream/Beige
                    'lot_hatch': '#cd853f',                       # Peru/Brown
                    'lot_border': '#8b4513',                      # Saddle Brown
                    'park_fill': 'rgba(144, 238, 144, 0.4)',     # Light Green
                    'park_border': '#228b22',                     # Forest Green
                    'tree': '#228b22',                            # Forest Green
                    'tree_outline': '#006400',                    # Dark Green
                    'xlnt_fill': 'rgba(0, 206, 209, 0.4)',       # Cyan
                    'xlnt_border': '#008b8b',                     # Dark Cyan
                    'service_fill': 'rgba(221, 160, 221, 0.5)',  # Plum
                    'service_border': '#8b008b',                  # Dark Magenta
                    'electric': '#0000cd',                        # Medium Blue
                    'transformer': '#ff0000',                     # Red
                    'drainage': '#00ced1',                        # Dark Turquoise
                    'road_center': '#8b0000',                     # Dark Red
                    'road_edge': '#2f4f4f',                       # Dark Slate Gray
                }

                # === LAYER 0: ROAD NETWORK (Background) ===
                # Draw road areas as white/beige with edge lines
                road_legend_shown = False
                road_centerlines_x, road_centerlines_y = [], []
                
                for f in features:
                    props = f['properties']
                    if props.get('type') == 'road_network':
                        geom = shape(f['geometry'])
                        # Check if this is a reasonably sized road (not the huge bounding box)
                        if geom.area < 100000:  # Only draw if < 100,000 m²
                            coords_list = get_poly_coords(geom)
                            for xs, ys in coords_list:
                                # Draw road polygon
                                fig.add_trace(go.Scatter(
                                    x=list(xs), y=list(ys),
                                    fill='toself',
                                    fillcolor='rgba(245, 245, 220, 0.8)',  # Beige
                                    line=dict(color=CAD_COLORS['road_edge'], width=2),
                                    name='🛣️ Đường Giao Thông',
                                    legendgroup='roads',
                                    showlegend=not road_legend_shown,
                                    hoverinfo='text',
                                    text='Road Network'
                                ))
                                road_legend_shown = True
                            
                            # Generate centerline from polygon centroid
                            if geom.geom_type == 'Polygon':
                                # Get bounding box for centerline
                                minx, miny, maxx, maxy = geom.bounds
                                cx, cy = geom.centroid.x, geom.centroid.y
                                
                                # Determine if road is more horizontal or vertical
                                if (maxx - minx) > (maxy - miny):
                                    # Horizontal road
                                    road_centerlines_x.extend([minx, maxx, None])
                                    road_centerlines_y.extend([cy, cy, None])
                                else:
                                    # Vertical road
                                    road_centerlines_x.extend([cx, cx, None])
                                    road_centerlines_y.extend([miny, maxy, None])
                
                # Draw all road centerlines
                if road_centerlines_x:
                    fig.add_trace(go.Scatter(
                        x=road_centerlines_x, y=road_centerlines_y,
                        mode='lines',
                        line=dict(color=CAD_COLORS['road_center'], width=2, dash='dash'),
                        name='Road Centerline',
                        legendgroup='roads',
                        showlegend=False,
                        hoverinfo='skip'
                    ))

                # === LAYER 1: LOTS WITH DOUBLE-LINE BORDERS (CAD STYLE) ===
                lot_legend_shown = False
                hatch_legend_shown = False
                
                for f in features:
                    props = f['properties']
                    ftype = props.get('type')
                    
                    if ftype == 'lot':
                        geom = shape(f['geometry'])
                        coords_list = get_poly_coords(geom)
                        area = props.get('area', 0)
                        lot_id = props.get('id', 'N/A')
                        
                        for xs, ys in coords_list:
                            all_x.extend(list(xs))
                            all_y.extend(list(ys))
                            
                            # OUTER BORDER (thick dark - like building wall)
                            fig.add_trace(go.Scatter(
                                x=list(xs), y=list(ys),
                                fill=None,
                                mode='lines',
                                line=dict(color='#5d4037', width=5),  # Dark brown outer
                                legendgroup='lots',
                                showlegend=False,
                                hoverinfo='skip'
                            ))
                            
                            # FILL with inner border
                            fig.add_trace(go.Scatter(
                                x=list(xs), y=list(ys),
                                fill='toself',
                                fillcolor=CAD_COLORS['lot_fill'],
                                line=dict(color=CAD_COLORS['lot_border'], width=2),
                                name='🏭 Lô Đất',
                                legendgroup='lots',
                                showlegend=not lot_legend_shown,
                                hovertemplate=f"<b>🏭 Lô {lot_id}</b><br>Diện tích: {area:.0f} m²<br><extra></extra>"
                            ))
                            lot_legend_shown = True
                        
                        # Add lot ID label in center
                        cx, cy = geom.centroid.x, geom.centroid.y
                        fig.add_annotation(
                            x=cx, y=cy,
                            text=f"<b>L{lot_id}</b>",
                            font=dict(size=9, color='#5d4037', family='Arial'),
                            showarrow=False,
                            bgcolor='rgba(255,255,255,0.7)',
                            borderpad=2
                        )
                        
                        # Add hatching lines (increased spacing for less density)
                        try:
                            hatch_x, hatch_y = generate_hatch_lines(geom, spacing=30, angle=45)
                            if hatch_x:
                                fig.add_trace(go.Scatter(
                                    x=hatch_x, y=hatch_y,
                                    mode='lines',
                                    line=dict(color=CAD_COLORS['lot_hatch'], width=0.8),
                                    name='Hatching',
                                    legendgroup='lots',
                                    showlegend=False,
                                    hoverinfo='skip'
                                ))
                        except:
                            pass  # Skip hatching if it fails

                # === LAYER 2: PARKS WITH TREES ===
                park_legend_shown = False
                all_star_trees_x, all_star_trees_y = [], []  # Star-shaped trees
                all_circle_trees_x, all_circle_trees_y = [], []  # Circle trees
                all_palm_x, all_palm_y = [], []  # Palm/shrub trees
                
                for f in features:
                    props = f['properties']
                    ftype = props.get('type')
                    
                    if ftype == 'park':
                        geom = shape(f['geometry'])
                        coords_list = get_poly_coords(geom)
                        
                        for xs, ys in coords_list:
                            all_x.extend(list(xs))
                            all_y.extend(list(ys))
                            
                            # OUTER BORDER for parks (dark green)
                            fig.add_trace(go.Scatter(
                                x=list(xs), y=list(ys),
                                fill=None,
                                mode='lines',
                                line=dict(color='#1b5e20', width=4),  # Dark green outer
                                legendgroup='parks',
                                showlegend=False,
                                hoverinfo='skip'
                            ))
                            
                            # Draw park fill with inner border
                            fig.add_trace(go.Scatter(
                                x=list(xs), y=list(ys),
                                fill='toself',
                                fillcolor=CAD_COLORS['park_fill'],
                                line=dict(color=CAD_COLORS['park_border'], width=2),
                                name='🌳 Cây Xanh',
                                legendgroup='parks',
                                showlegend=not park_legend_shown,
                                hoverinfo='text',
                                text='🌳 Park / Green Space'
                            ))
                            park_legend_shown = True
                        
                        # Generate star-shaped trees (main trees)
                        tree_count = max(5, int(geom.area / 300))
                        trees = generate_trees_in_polygon(geom, min(tree_count, 25))
                        for i, (tx, ty) in enumerate(trees):
                            if i % 3 == 0:
                                all_star_trees_x.append(tx)
                                all_star_trees_y.append(ty)
                            elif i % 3 == 1:
                                all_circle_trees_x.append(tx)
                                all_circle_trees_y.append(ty)
                            else:
                                all_palm_x.append(tx)
                                all_palm_y.append(ty)
                
                # Also add trees along lot boundaries (like CAD drawing)
                for f in features:
                    props = f['properties']
                    if props.get('type') == 'lot':
                        geom = shape(f['geometry'])
                        if geom.geom_type == 'Polygon':
                            # Add trees at polygon vertices/corners
                            coords = list(geom.exterior.coords)
                            step = max(1, len(coords) // 4)  # ~4 trees per lot boundary
                            for i in range(0, len(coords), step):
                                px, py = coords[i]
                                # Offset slightly into the lot
                                cx, cy = geom.centroid.x, geom.centroid.y
                                offset_x = (cx - px) * 0.05
                                offset_y = (cy - py) * 0.05
                                all_circle_trees_x.append(px + offset_x)
                                all_circle_trees_y.append(py + offset_y)
                
                # Draw star-shaped trees (CAD style - like asterisks)
                if all_star_trees_x:
                    fig.add_trace(go.Scatter(
                        x=all_star_trees_x, y=all_star_trees_y,
                        mode='markers',
                        marker=dict(
                            symbol='asterisk',
                            size=14,
                            color='#2e8b57',  # Sea green
                            line=dict(width=2, color='#006400'),
                        ),
                        name='🌲 Cây Lớn',
                        legendgroup='trees',
                        hoverinfo='text',
                        text='🌲 Large Tree'
                    ))
                
                # Draw circle trees
                if all_circle_trees_x:
                    fig.add_trace(go.Scatter(
                        x=all_circle_trees_x, y=all_circle_trees_y,
                        mode='markers',
                        marker=dict(
                            symbol='circle',
                            size=10,
                            color='#32cd32',  # Lime green
                            line=dict(width=1.5, color='#228b22'),
                            opacity=0.85
                        ),
                        name='🌳 Cây Trung',
                        legendgroup='trees',
                        showlegend=False,
                        hoverinfo='text',
                        text='🌳 Medium Tree'
                    ))
                
                # Draw palm/shrub markers
                if all_palm_x:
                    fig.add_trace(go.Scatter(
                        x=all_palm_x, y=all_palm_y,
                        mode='markers',
                        marker=dict(
                            symbol='hexagram',
                            size=8,
                            color='#90ee90',  # Light green
                            line=dict(width=1, color='#228b22'),
                            opacity=0.8
                        ),
                        name='🌴 Cây Nhỏ',
                        legendgroup='trees',
                        showlegend=False,
                        hoverinfo='text',
                        text='🌴 Small Plant'
                    ))

                # === LAYER 3: SERVICE & TECHNICAL AREAS ===
                legend_xlnt = False
                legend_service = False
                
                for f in features:
                    props = f['properties']
                    ftype = props.get('type')
                    
                    if ftype == 'xlnt':
                        geom = shape(f['geometry'])
                        coords_list = get_poly_coords(geom)
                        for xs, ys in coords_list:
                            all_x.extend(list(xs))
                            all_y.extend(list(ys))
                            fig.add_trace(go.Scatter(
                                x=list(xs), y=list(ys),
                                fill='toself',
                                fillcolor=CAD_COLORS['xlnt_fill'],
                                line=dict(color=CAD_COLORS['xlnt_border'], width=2.5),
                                name='💧 XLNT',
                                legendgroup='xlnt',
                                showlegend=not legend_xlnt,
                                hoverinfo='text',
                                text='💧 Xử Lý Nước Thải'
                            ))
                            legend_xlnt = True
                    
                    elif ftype == 'service':
                        geom = shape(f['geometry'])
                        coords_list = get_poly_coords(geom)
                        for xs, ys in coords_list:
                            all_x.extend(list(xs))
                            all_y.extend(list(ys))
                            fig.add_trace(go.Scatter(
                                x=list(xs), y=list(ys),
                                fill='toself',
                                fillcolor=CAD_COLORS['service_fill'],
                                line=dict(color=CAD_COLORS['service_border'], width=2.5),
                                name='🏢 Điều Hành',
                                legendgroup='service',
                                showlegend=not legend_service,
                                hoverinfo='text',
                                text='🏢 Service / Admin'
                            ))
                            legend_service = True

                # === LAYER 4: ELECTRIC NETWORK ===
                electric_legend_shown = False
                for f in features:
                    if f['properties'].get('type') == 'connection':
                        geom = shape(f['geometry'])
                        coords_list = get_line_coords(geom)
                        for xs, ys in coords_list:
                            all_x.extend(list(xs))
                            all_y.extend(list(ys))
                            
                            # Draw as dashed line
                            fig.add_trace(go.Scatter(
                                x=list(xs), y=list(ys),
                                mode='lines',
                                line=dict(color=CAD_COLORS['electric'], width=2, dash='dashdot'),
                                name='⚡ Điện Ngầm',
                                legendgroup='electric',
                                showlegend=not electric_legend_shown,
                                hoverinfo='text',
                                text='⚡ Underground Cable'
                            ))
                            electric_legend_shown = True

                # === LAYER 5: TRANSFORMERS ===
                t_x, t_y = [], []
                for f in features:
                    if f['properties'].get('type') == 'transformer':
                        pt = shape(f['geometry'])
                        t_x.append(pt.x)
                        t_y.append(pt.y)
                        all_x.append(pt.x)
                        all_y.append(pt.y)
                
                if t_x:
                    fig.add_trace(go.Scatter(
                        x=t_x, y=t_y,
                        mode='markers+text',
                        marker=dict(
                            symbol='square',
                            size=14,
                            color=CAD_COLORS['transformer'],
                            line=dict(width=2, color='white')
                        ),
                        text=['T'] * len(t_x),
                        textposition='middle center',
                        textfont=dict(size=8, color='white', family='Arial Black'),
                        name='🔴 Trạm Biến Áp',
                        legendgroup='transformer',
                        hoverinfo='text',
                        hovertext='🔴 Transformer Station'
                    ))

                # === LAYER 6: DRAINAGE ===
                drain_features = [f for f in features if f['properties'].get('type') == 'drainage']
                if len(drain_features) > 25:
                    drain_features = drain_features[::2]
                    
                for f in drain_features:
                    geom = shape(f['geometry'])
                    if geom.geom_type == 'LineString':
                        coords = list(geom.coords)
                        if len(coords) >= 2:
                            fig.add_annotation(
                                x=coords[-1][0], y=coords[-1][1],
                                ax=coords[0][0], ay=coords[0][1],
                                xref='x', yref='y', axref='x', ayref='y',
                                showarrow=True,
                                arrowhead=3,
                                arrowsize=1.5,
                                arrowwidth=2,
                                arrowcolor=CAD_COLORS['drainage']
                            )

                # Dummy trace for Drainage Legend
                fig.add_trace(go.Scatter(
                    x=[None], y=[None],
                    mode='lines+markers',
                    marker=dict(symbol='arrow', color=CAD_COLORS['drainage'], size=8),
                    line=dict(color=CAD_COLORS['drainage'], width=2),
                    name='💧 Thoát Nước',
                    legendgroup='drainage'
                ))

                # === AUTO-FIT BOUNDS ===
                if all_x and all_y:
                    x_min, x_max = min(all_x), max(all_x)
                    y_min, y_max = min(all_y), max(all_y)
                    x_pad = (x_max - x_min) * 0.08
                    y_pad = (y_max - y_min) * 0.08
                    x_range = [x_min - x_pad, x_max + x_pad]
                    y_range = [y_min - y_pad, y_max + y_pad]
                else:
                    x_range = None
                    y_range = None

                # === CAD-STYLE LAYOUT ===
                fig.update_layout(
                    title=dict(
                        text="<b>📐 QUY HOẠCH CHI TIẾT 1/500</b>",
                        y=0.98,
                        x=0.5,
                        xanchor='center',
                        yanchor='top',
                        font=dict(size=18, color='#1a1a1a', family='Arial Black')
                    ),
                    height=1000,  # Taller for more space
                    xaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(200, 200, 200, 0.3)',
                        gridwidth=1,
                        zeroline=False,
                        scaleanchor="y",
                        scaleratio=1,
                        title=dict(text="X (meters)", font=dict(size=11, color='#333')),
                        range=x_range,
                        showspikes=True,
                        spikecolor='#666',
                        spikethickness=1,
                        tickfont=dict(size=10),
                        side='bottom'
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(200, 200, 200, 0.3)',
                        gridwidth=1,
                        zeroline=False,
                        title=dict(text="Y (meters)", font=dict(size=11, color='#333')),
                        range=y_range,
                        showspikes=True,
                        spikecolor='#666',
                        spikethickness=1,
                        tickfont=dict(size=10)
                    ),
                    plot_bgcolor='rgba(255, 255, 252, 1)',  # Warm white like paper
                    paper_bgcolor='white',
                    hovermode='closest',
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.08,  # Below the chart
                        xanchor="center",
                        x=0.5,
                        bgcolor='rgba(255,255,255,0.95)',
                        bordercolor='rgba(0,0,0,0.1)',
                        borderwidth=1,
                        font=dict(size=9, family='Arial'),
                        itemsizing='constant',
                        tracegroupgap=5
                    ),
                    margin=dict(l=60, r=60, t=60, b=100)  # More space at bottom for legend
                )
                
                # === CAD-STYLE ANNOTATIONS ===
                # North Arrow (top-right corner)
                fig.add_annotation(
                    x=0.97, y=0.97,
                    xref='paper', yref='paper',
                    text='<b>⬆ N</b>',
                    font=dict(size=16, color='#333', family='Arial Black'),
                    showarrow=False,
                    bgcolor='rgba(255,255,255,0.9)',
                    bordercolor='#333',
                    borderwidth=1,
                    borderpad=4
                )
                
                # Scale Bar (calculate based on data range)
                if x_range and y_range:
                    plot_width = x_range[1] - x_range[0]
                    # Determine appropriate scale bar length
                    if plot_width > 1000:
                        scale_len = 200
                        scale_text = '200m'
                    elif plot_width > 500:
                        scale_len = 100
                        scale_text = '100m'
                    else:
                        scale_len = 50
                        scale_text = '50m'
                    
                    # Scale bar position (bottom-left)
                    sb_x = x_range[0] + (x_range[1] - x_range[0]) * 0.05
                    sb_y = y_range[0] + (y_range[1] - y_range[0]) * 0.03
                    
                    # Draw scale bar line
                    fig.add_trace(go.Scatter(
                        x=[sb_x, sb_x + scale_len],
                        y=[sb_y, sb_y],
                        mode='lines',
                        line=dict(color='black', width=3),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                    
                    # Scale bar end caps
                    fig.add_trace(go.Scatter(
                        x=[sb_x, sb_x],
                        y=[sb_y - 5, sb_y + 5],
                        mode='lines',
                        line=dict(color='black', width=2),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                    fig.add_trace(go.Scatter(
                        x=[sb_x + scale_len, sb_x + scale_len],
                        y=[sb_y - 5, sb_y + 5],
                        mode='lines',
                        line=dict(color='black', width=2),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                    
                    # Scale bar label
                    fig.add_annotation(
                        x=sb_x + scale_len / 2, y=sb_y + 15,
                        text=f'<b>{scale_text}</b>',
                        font=dict(size=10, color='#333'),
                        showarrow=False,
                        bgcolor='rgba(255,255,255,0.8)'
                    )

                return fig

            except Exception as e:
                st.error(f"Plotting error: {e}")
                return None

        # Display Plot
        fig = plot_master_plan_plotly(result)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        
        # Visualization (Plotly)
        stages = result.get('stages', [])
        if len(stages) >= 2:
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=('Stage 1: Grid Optimization', 'Stage 2: Subdivision'),
                horizontal_spacing=0.05
            )
            
            # Stage 1: Grid blocks
            for feature in stages[0]['geometry']['features']:
                coords = feature['geometry']['coordinates'][0]
                xs = [c[0] for c in coords]
                ys = [c[1] for c in coords]
                
                fig.add_trace(go.Scatter(
                    x=xs, y=ys,
                    fill='toself',
                    fillcolor='rgba(100, 126, 234, 0.5)',
                    line=dict(color='#667eea', width=1),
                    showlegend=False,
                    hoverinfo='skip'
                ), row=1, col=1)
            
            # Stage 2: Lots and parks
            for feature in stages[1]['geometry']['features']:
                coords = feature['geometry']['coordinates'][0]
                xs = [c[0] for c in coords]
                ys = [c[1] for c in coords]
                
                ftype = feature['properties'].get('type', 'lot')
                color = 'rgba(255, 152, 0, 0.7)' if ftype == 'lot' else 'rgba(76, 175, 80, 0.7)'
                line_color = '#ff9800' if ftype == 'lot' else '#4caf50'
                
                fig.add_trace(go.Scatter(
                    x=xs, y=ys,
                    fill='toself',
                    fillcolor=color,
                    line=dict(color=line_color, width=1),
                    showlegend=False,
                    hoverinfo='text',
                    text=ftype.title()
                ), row=1, col=2)
            
            fig.update_layout(
                height=450,
                margin=dict(l=20, r=20, t=40, b=20),
                showlegend=False
            )
            fig.update_xaxes(scaleanchor="y", scaleratio=1)
            fig.update_yaxes(scaleanchor="x", scaleratio=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Legend
            st.markdown("""
            <div style="display: flex; gap: 2rem; justify-content: center; padding: 0.5rem;">
                <span style="display: flex; align-items: center; gap: 0.5rem;">
                    <div style="width: 20px; height: 20px; background: rgba(100, 126, 234, 0.5); border: 1px solid #667eea;"></div>
                    Grid Blocks
                </span>
                <span style="display: flex; align-items: center; gap: 0.5rem;">
                    <div style="width: 20px; height: 20px; background: rgba(255, 152, 0, 0.7); border: 1px solid #ff9800;"></div>
                    Residential Lots
                </span>
                <span style="display: flex; align-items: center; gap: 0.5rem;">
                    <div style="width: 20px; height: 20px; background: rgba(76, 175, 80, 0.7); border: 1px solid #4caf50;"></div>
                    Parks
                </span>
            </div>
            """, unsafe_allow_html=True)
        
        # Download section
        st.markdown("---")
        st.markdown("**📥 Download Results:**")
        
        d1, d2, d3 = st.columns(3)
        
        with d1:
            if result.get('final_layout'):
                st.download_button(
                    "📄 GeoJSON",
                    data=json.dumps(result['final_layout'], indent=2),
                    file_name="layout.geojson",
                    mime="application/json",
                    use_container_width=True
                )
        
        with d2:
            st.download_button(
                "📊 Full Report",
                data=json.dumps(result, indent=2),
                file_name="report.json",
                mime="application/json",
                use_container_width=True
            )
        
        with d3:
            # DXF Export button
            if st.button("📐 Export DXF", use_container_width=True, key="export_dxf"):
                with st.spinner("Generating DXF..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/api/export-dxf",
                            json={"result": result}
                        )
                        
                        if response.status_code == 200:
                            st.download_button(
                                "⬇️ Download DXF",
                                data=response.content,
                                file_name="land_redistribution.dxf",
                                mime="application/dxf",
                                use_container_width=True,
                                key="download_dxf"
                            )
                        else:
                            st.error("Failed to generate DXF")
                    except Exception as e:
                        st.error(f"DXF export error: {str(e)}")
