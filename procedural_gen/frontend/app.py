"""Streamlit frontend for Procedural Generation.

Progressive generation UI with stage-by-stage preview.
"""

import streamlit as st
import requests
import json
import plotly.graph_objects as go
from shapely.geometry import shape, mapping
import os

# Page config
st.set_page_config(
    page_title="Procedural Generation",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --accent-color: #667eea;
    }
    
    .main-header {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #f093fb 50%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
    }
    
    .stage-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🏗️ Procedural Generation</h1>
    <p style="color: rgba(255,255,255,0.7); margin-top: 0.5rem;">
        Generative Design for CAD-Ready Layouts
    </p>
</div>
""", unsafe_allow_html=True)

# API URL
API_URL = os.environ.get("API_URL", "http://localhost:8001")

# Session state
if 'site_boundary' not in st.session_state:
    st.session_state.site_boundary = None
if 'result' not in st.session_state:
    st.session_state.result = None
if 'current_stage' not in st.session_state:
    st.session_state.current_stage = 0

# Sidebar - Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Road Network
    st.subheader("🛣️ Road Network")
    road_algorithm = st.selectbox(
        "Algorithm",
        ["skeleton", "l_systems", "hybrid"],
        help="skeleton: Medial axis, l_systems: Organic branching"
    )
    fillet_radius = st.slider("Fillet Radius (m)", 5.0, 20.0, 12.0)
    
    st.divider()
    
    # Subdivision
    st.subheader("📐 Subdivision")
    min_lot_area = st.number_input("Min Lot Area (m²)", 100, 5000, 1000)
    max_lot_area = st.number_input("Max Lot Area (m²)", 1000, 50000, 10000)
    target_lot_width = st.slider("Target Lot Width (m)", 20, 100, 40)
    
    st.divider()
    
    # Post-processing
    st.subheader("🌿 Post-processing")
    sidewalk_width = st.slider("Sidewalk Width (m)", 1.0, 5.0, 2.0)
    green_buffer = st.slider("Green Buffer (m)", 2.0, 10.0, 5.0)

# Main layout
col_input, col_result = st.columns([1, 2])

with col_input:
    st.header("📍 Site Input")
    
    # Input method tabs
    input_tab1, input_tab2, input_tab3 = st.tabs(["Sample", "GeoJSON", "DXF Upload"])
    
    with input_tab1:
        if st.button("Use Sample Plot (500x400m)", use_container_width=True):
            st.session_state.site_boundary = {
                "type": "Polygon",
                "coordinates": [[[0, 0], [500, 0], [500, 400], [0, 400], [0, 0]]]
            }
            st.success("Sample plot loaded!")
            
    with input_tab2:
        geojson_input = st.text_area(
            "Paste GeoJSON coordinates",
            height=150,
            placeholder='{"type": "Polygon", "coordinates": [[[0,0], [100,0], [100,100], [0,100], [0,0]]]}'
        )
        if st.button("Parse GeoJSON", use_container_width=True):
            try:
                parsed = json.loads(geojson_input)
                st.session_state.site_boundary = parsed
                st.success("GeoJSON parsed successfully!")
            except Exception as e:
                st.error(f"Invalid GeoJSON: {e}")
                
    with input_tab3:
        uploaded_file = st.file_uploader("Upload DXF file", type=['dxf'])
        if uploaded_file:
            try:
                files = {'file': (uploaded_file.name, uploaded_file.getvalue())}
                response = requests.post(f"{API_URL}/api/upload-dxf", files=files)
                if response.ok:
                    data = response.json()
                    if data.get('boundaries', {}).get('features'):
                        first_boundary = data['boundaries']['features'][0]['geometry']
                        st.session_state.site_boundary = first_boundary
                        st.success(f"Loaded {data['count']} boundaries from DXF")
                else:
                    st.error("Failed to parse DXF")
            except Exception as e:
                st.error(f"DXF upload error: {e}")
    
    st.divider()
    
    # Generate button
    if st.session_state.site_boundary:
        if st.button("🚀 Generate Full Plan", type="primary", use_container_width=True):
            with st.spinner("Generating..."):
                try:
                    payload = {
                        "site_boundary": st.session_state.site_boundary,
                        "road_config": {
                            "algorithm": road_algorithm,
                            "fillet_radius": fillet_radius
                        },
                        "subdivision_config": {
                            "min_lot_area": min_lot_area,
                            "max_lot_area": max_lot_area,
                            "target_lot_width": target_lot_width
                        },
                        "postprocess_config": {
                            "sidewalk_width": sidewalk_width,
                            "green_buffer_width": green_buffer
                        }
                    }
                    
                    response = requests.post(
                        f"{API_URL}/api/generate/full",
                        json=payload,
                        timeout=60
                    )
                    
                    if response.ok:
                        st.session_state.result = response.json()
                        st.success("Generation complete!")
                    else:
                        st.error(f"API Error: {response.text}")
                        
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to API. Make sure backend is running.")
                except Exception as e:
                    st.error(f"Error: {e}")

with col_result:
    st.header("📊 Results")
    
    if st.session_state.result:
        result = st.session_state.result
        
        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        
        if result.get('metadata', {}).get('stats'):
            stats = result['metadata']['stats']
            m1.metric("Roads", stats.get('road_count', 0))
            m2.metric("Lots", stats.get('lot_count', 0))
            m3.metric("Green Spaces", stats.get('green_count', 0))
            m4.metric("Duration", f"{result.get('total_duration_ms', 0):.0f}ms")
        
        # Visualization
        fig = go.Figure()
        
        # Plot site boundary
        if st.session_state.site_boundary:
            coords = st.session_state.site_boundary.get('coordinates', [[]])[0]
            if coords:
                x = [c[0] for c in coords]
                y = [c[1] for c in coords]
                fig.add_trace(go.Scatter(
                    x=x, y=y, mode='lines',
                    line=dict(color='white', width=2),
                    name='Site Boundary'
                ))
        
        # Plot lots
        if result.get('lots', {}).get('features'):
            for feature in result['lots']['features']:
                coords = feature['geometry']['coordinates'][0]
                x = [c[0] for c in coords]
                y = [c[1] for c in coords]
                fig.add_trace(go.Scatter(
                    x=x, y=y, mode='lines',
                    fill='toself',
                    fillcolor='rgba(102, 126, 234, 0.3)',
                    line=dict(color='#667eea', width=1),
                    name='Lot',
                    showlegend=False
                ))
                
        # Plot green spaces
        if result.get('green_spaces', {}).get('features'):
            for feature in result['green_spaces']['features']:
                coords = feature['geometry']['coordinates'][0]
                x = [c[0] for c in coords]
                y = [c[1] for c in coords]
                fig.add_trace(go.Scatter(
                    x=x, y=y, mode='lines',
                    fill='toself',
                    fillcolor='rgba(46, 204, 113, 0.3)',
                    line=dict(color='#2ecc71', width=1),
                    name='Green Space',
                    showlegend=False
                ))
                
        # Plot roads
        if result.get('roads', {}).get('features'):
            for feature in result['roads']['features']:
                coords = feature['geometry']['coordinates']
                x = [c[0] for c in coords]
                y = [c[1] for c in coords]
                fig.add_trace(go.Scatter(
                    x=x, y=y, mode='lines',
                    line=dict(color='#e74c3c', width=3),
                    name='Road',
                    showlegend=False
                ))
        
        fig.update_layout(
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                scaleanchor="y",
                scaleratio=1,
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)'
            ),
            margin=dict(l=20, r=20, t=20, b=20),
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Download options
        st.subheader("📥 Export")
        dcol1, dcol2 = st.columns(2)
        
        with dcol1:
            if st.button("Download GeoJSON", use_container_width=True):
                st.download_button(
                    "📄 GeoJSON",
                    json.dumps(result, indent=2),
                    "procedural_output.json",
                    "application/json"
                )
                
        with dcol2:
            if st.button("Download DXF (coming soon)", use_container_width=True, disabled=True):
                pass
                
    else:
        st.info("👈 Configure parameters and load a site boundary to begin")
        
        # Show sample visualization
        st.markdown("""
        ### Pipeline Stages
        
        1. **🛣️ Road Network** - Generate roads using L-Systems or Skeletonization
        2. **📐 Block Division** - Cut site by roads into buildable blocks  
        3. **🏗️ Lot Subdivision** - Divide blocks using OBB Tree + Shape Grammar
        4. **✅ Quality Filter** - Validate lot shapes, convert poor ones to green space
        5. **🌿 Post-Processing** - Add sidewalks and green buffers
        """)
