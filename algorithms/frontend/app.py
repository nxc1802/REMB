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

# Configuration
API_URL = "http://localhost:8000"

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
                min_value=10.0, 
                max_value=50.0, 
                value=20.0, 
                step=0.5,
                help="Minimum grid spacing"
            )
        with c2:
            spacing_max = st.number_input(
                "Max", 
                min_value=10.0, 
                max_value=50.0, 
                value=30.0, 
                step=0.5,
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
        
        p1, p2 = st.columns(2)
        with p1:
            st.info(f"🔲 Spacing: **{stats.get('optimal_spacing', 0):.1f}m**")
        with p2:
            st.info(f"📐 Angle: **{stats.get('optimal_angle', 0):.1f}°**")
        
        # === Notebook-Style Visualization (Matplotlib) ===
        st.markdown("### 🗺️ Master Plan Visualization")
        
        def plot_notebook_style(result_data):
            """
            Replicate the Detailed 1/500 Planning Plot.
            Includes: Roads, Setbacks, Zoning, Loop Network, Transformers, Drainage.
            """
            try:
                # Setup figure
                fig, ax = plt.subplots(figsize=(12, 12))
                ax.set_aspect('equal')
                ax.set_facecolor('#f0f0f0')
                
                # Retrieve features from final layout (Stage 3 includes everything)
                features = result_data.get('final_layout', {}).get('features', [])
                
                # 1. Draw Roads & Sidewalks (Layer 0)
                # We specifically look for type='road_network' or we draw the inverse using plot background if needed
                # But our backend now sends 'road_network' feature
                for f in features:
                    if f['properties'].get('type') == 'road_network':
                        geom = shape(f['geometry'])
                        if geom.is_empty: continue
                        if geom.geom_type == 'Polygon':
                            xs, ys = geom.exterior.xy
                            ax.fill(xs, ys, color='#607d8b', alpha=0.3, label='Hạ tầng giao thông')
                        elif geom.geom_type == 'MultiPolygon':
                            for poly in geom.geoms:
                                xs, ys = poly.exterior.xy
                                ax.fill(xs, ys, color='#607d8b', alpha=0.3)

                # 2. Draw Commercial Lots & Setbacks (Layer 1)
                for f in features:
                    props = f['properties']
                    ftype = props.get('type')
                    
                    if ftype == 'lot':
                        poly = shape(f['geometry'])
                        xs, ys = poly.exterior.xy
                        ax.plot(xs, ys, color='black', linewidth=0.5)
                        ax.fill(xs, ys, color='#fff9c4', alpha=0.5) # Yellow
                    
                    elif ftype == 'setback':
                        poly = shape(f['geometry'])
                        xs, ys = poly.exterior.xy
                        ax.plot(xs, ys, color='red', linestyle='--', linewidth=0.8, alpha=0.7)

                # 3. Draw Service / Technical Areas (Layer 2)
                for f in features:
                    props = f['properties']
                    ftype = props.get('type')
                    poly = shape(f['geometry'])
                    
                    if ftype == 'xlnt':
                        xs, ys = poly.exterior.xy
                        ax.fill(xs, ys, color='#b2dfdb', alpha=0.9) # Cyan/Blue
                        ax.text(poly.centroid.x, poly.centroid.y, "XLNT", ha='center', fontsize=8, color='black', weight='bold')
                    elif ftype == 'service':
                        xs, ys = poly.exterior.xy
                        ax.fill(xs, ys, color='#d1c4e9', alpha=0.9) # Purple
                        ax.text(poly.centroid.x, poly.centroid.y, "Điều hành", ha='center', fontsize=8, color='black', weight='bold')
                    elif ftype == 'park':
                        xs, ys = poly.exterior.xy
                        ax.fill(xs, ys, color='#f6ffed', alpha=0.5) # Green
                        ax.plot(xs, ys, color='green', linewidth=0.5, linestyle=':')

                # 4. Draw Electrical Infrastructure (Loop)
                for f in features:
                    if f['properties'].get('type') == 'connection':
                        line = shape(f['geometry'])
                        xs, ys = line.xy
                        ax.plot(xs, ys, color='blue', linestyle='-', linewidth=0.5, alpha=0.4)

                # 5. Draw Transformers
                for f in features:
                    if f['properties'].get('type') == 'transformer':
                        pt = shape(f['geometry'])
                        ax.scatter(pt.x, pt.y, c='red', marker='^', s=100, zorder=10)

                # 6. Draw Drainage (Arrows)
                for i, f in enumerate([feat for feat in features if feat['properties'].get('type') == 'drainage']):
                    if i % 3 == 0: # Sample to avoid clutter
                        line = shape(f['geometry'])
                        # Shapely LineString to Arrow
                        start = line.coords[0]
                        end = line.coords[1]
                        dx = end[0] - start[0]
                        dy = end[1] - start[1]
                        ax.arrow(start[0], start[1], dx, dy, head_width=5, head_length=5, fc='cyan', ec='cyan', alpha=0.6)

                # Title
                ax.set_title("QUY HOẠCH CHI TIẾT 1/500 (PRODUCTION READY)\n"
                          "Bao gồm: Đường phân cấp, Vạt góc, Chỉ giới XD, Điện mạch vòng, Thoát nước tự chảy", fontsize=14)

                # Custom Legend
                from matplotlib.lines import Line2D
                custom_lines = [Line2D([0], [0], color='#fff9c4', lw=4),
                                Line2D([0], [0], color='red', linestyle='--', lw=1),
                                Line2D([0], [0], color='#607d8b', lw=4),
                                Line2D([0], [0], color='blue', lw=1),
                                Line2D([0], [0], marker='^', color='w', markerfacecolor='red', markersize=10),
                                Line2D([0], [0], color='cyan', lw=1, marker='>')]

                ax.legend(custom_lines, ['Đất CN', 'Chỉ giới XD (Setback)', 'Đường giao thông', 'Cáp điện ngầm (Loop)', 'Trạm biến áp', 'Hướng thoát nước'], loc='lower right')

                plt.tight_layout()
                return fig
            except Exception as e:
                st.error(f"Plotting error: {e}")
                return None

        # Display Plot
        fig = plot_notebook_style(result)
        if fig:
            st.pyplot(fig)
        
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
