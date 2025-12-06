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

# Configuration
API_URL = "http://localhost:8001"

# Page config - Wide layout for one-page design
st.set_page_config(
    page_title="Land Redistribution Optimizer",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding: 1rem 2rem;
        max-width: 100%;
    }
    
    /* Card-like sections */
    .stExpander {
        background-color: #f8f9fa;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.75rem 1rem;
    }
    
    /* Primary button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
    }
    
    /* Section headers */
    .section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    /* Status box */
    .status-ready { color: #28a745; font-weight: 600; }
    .status-running { color: #ffc107; font-weight: 600; }
    .status-error { color: #dc3545; font-weight: 600; }
    
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Responsive columns */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style="text-align: center; padding: 1rem 0 2rem;">
    <h1 style="margin: 0;">🏘️ Land Redistribution Optimizer</h1>
    <p style="color: #6c757d; margin-top: 0.5rem;">
        NSGA-II Grid Optimization + OR-Tools Block Subdivision
    </p>
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
    
    # Grid Optimization Parameters
    with st.expander("🔲 Grid Optimization", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            spacing_min = st.number_input("Min Spacing (m)", 10.0, 50.0, 20.0, 1.0)
            angle_min = st.number_input("Min Angle (°)", 0.0, 90.0, 0.0, 5.0)
        with c2:
            spacing_max = st.number_input("Max Spacing (m)", 10.0, 50.0, 30.0, 1.0)
            angle_max = st.number_input("Max Angle (°)", 0.0, 90.0, 90.0, 5.0)
    
    # Subdivision Parameters
    with st.expander("📐 Lot Subdivision", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            min_lot_width = st.number_input("Min Width", 3.0, 10.0, 5.0, 0.5)
        with c2:
            target_lot_width = st.number_input("Target", 4.0, 12.0, 6.0, 0.5)
        with c3:
            max_lot_width = st.number_input("Max Width", 5.0, 15.0, 8.0, 0.5)
    
    # Advanced Settings
    with st.expander("⚡ Advanced", expanded=False):
        road_width = st.slider("Road Width (m)", 3.0, 10.0, 6.0, 0.5)
        block_depth = st.slider("Block Depth (m)", 30.0, 100.0, 50.0, 5.0)
        population_size = st.slider("Population Size", 20, 200, 50, 10)
        generations = st.slider("Generations", 50, 500, 100, 50)
        ortools_time_limit = st.slider("OR-Tools Time/Block (s)", 1, 60, 5, 1)

# ==================== COLUMN 2: Input & Action ====================
with col_action:
    st.markdown("### 📍 Land Plot")
    
    # Input method selection
    input_method = st.radio(
        "Input method:",
        ["Sample", "Upload", "Manual"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if input_method == "Sample":
        # Predefined sample
        sample_type = st.selectbox(
            "Sample type:",
            ["Rectangle 100x100", "L-Shape", "Irregular"]
        )
        
        if sample_type == "Rectangle 100x100":
            coords = [[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]]
        elif sample_type == "L-Shape":
            coords = [[[0, 0], [60, 0], [60, 40], [40, 40], [40, 100], [0, 100], [0, 0]]]
        else:
            coords = [[[0, 0], [80, 10], [100, 50], [90, 100], [20, 90], [0, 0]]]
        
        st.session_state.land_plot = {
            "type": "Polygon",
            "coordinates": coords,
            "properties": {"name": sample_type}
        }
        
    elif input_method == "Upload":
        uploaded = st.file_uploader("GeoJSON file", type=['json', 'geojson'])
        if uploaded:
            try:
                data = json.load(uploaded)
                if data['type'] == 'FeatureCollection':
                    st.session_state.land_plot = data['features'][0]['geometry']
                else:
                    st.session_state.land_plot = data
            except Exception as e:
                st.error(f"Invalid file: {e}")
                
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
                response = requests.post(
                    f"{API_URL}/api/optimize",
                    json={
                        "config": config,
                        "land_plots": [st.session_state.land_plot]
                    },
                    timeout=300
                )
                
                if response.status_code == 200:
                    st.session_state.result = response.json()
                    st.session_state.status = 'complete'
                    st.rerun()
                else:
                    st.session_state.status = 'error'
                    st.error(f"API Error: {response.text[:200]}")
                    
            except requests.exceptions.ConnectionError:
                st.session_state.status = 'error'
                st.error("Cannot connect to API. Is backend running?")
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
        
        # Visualization
        stages = result.get('stages', [])
        
        if len(stages) >= 2:
            # Create side-by-side comparison
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
        d1, d2 = st.columns(2)
        with d1:
            if result.get('final_layout'):
                st.download_button(
                    "📥 Download GeoJSON",
                    data=json.dumps(result['final_layout'], indent=2),
                    file_name="layout.geojson",
                    mime="application/json",
                    use_container_width=True
                )
        with d2:
            st.download_button(
                "📥 Download Full Report",
                data=json.dumps(result, indent=2),
                file_name="report.json",
                mime="application/json",
                use_container_width=True
            )
