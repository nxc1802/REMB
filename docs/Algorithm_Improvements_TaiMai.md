# Industrial Estate Optimization - Complete Algorithm Documentation

## Author: TaiMai

## Date: December 6, 2025

## Status: In Progress

---

## 1. PROJECT OVERVIEW

This document logs all algorithm improvements made to the REMB (Real Estate Master Builder) industrial estate layout optimization system.

### Problem Statement

The original optimization algorithms had critical issues:

1. Plots placed OUTSIDE the cadastral boundary
2. Data loss in DXF export (449 KB → 22 KB = 95% loss)
3. No proper setback/buffer zones
4. No road network inside the land
5. Hardcoded test coordinates instead of reading real DXF

### Solution Summary

Implemented a professional industrial estate planning pipeline following best practices:

1. Extract boundary from real DXF file
2. Apply setback buffer INWARD
3. Create road network inside buildable area
4. Generate grid-aligned plots COMPLETELY INSIDE the usable area
5. Export with ALL original data preserved

---

## 2. FILES CREATED/MODIFIED

### New Algorithm Files

| File | Description |
|------|-------------|
| `src/algorithms/production_optimizer.py` | Production-ready optimizer with bin packing |
| `src/algorithms/polygon_optimizer.py` | NFP-grid optimizer for irregular polygons |
| `src/algorithms/cadastral_optimizer.py` | DXF reading and adaptive parameters |
| `src/algorithms/production_dxf_exporter.py` | Data-preserving DXF export |
| `src/algorithms/industrial_estate_planner.py` | Complete professional planner |
| `src/algorithms/advanced_estate_optimizer.py` | **NEW** Diagonal roads + rotated grid |

### Test Files

| File | Description |
|------|-------------|
| `test_production_optimizer.py` | Tests for production optimizer |
| `test_polygon_optimizer.py` | Tests for polygon optimizer |
| `test_real_bel_air.py` | Tests with real cadastral DXF |
| `debug_estate.py` | Debug script for estate planner |
| `test_estate_planner.py` | Tests for estate planner |

### Output Files

| File | Size | Description |
|------|------|-------------|
| `output/Bel_Air_DEBUG.dxf` | 430 KB | 9 plots inside boundary |
| `output/Bel_Air_FULL_PRESERVED.dxf` | 427 KB | Data-preserved export |

---

## 3. KEY ALGORITHMS

### 3.1 Boundary Extraction

```python
def extract_boundary(dxf_path):
    """Extract main boundary from DXF file"""
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    
    for entity in msp.query('LWPOLYLINE'):
        coords = [(p[0], p[1]) for p in entity.get_points('xy')]
        if len(coords) >= 3:
            poly = Polygon(coords)
            if poly.is_valid and poly.area > 1000:
                # Convert mm to m
                boundary_m = scale(poly, xfact=0.001, yfact=0.001, origin=(0,0))
                return boundary_m
    return None
```

### 3.2 Setback Buffer (CRITICAL FIX)

```python
def apply_setback(boundary, distance=1.0):
    """
    Apply setback by buffering INWARD (negative buffer).
    This creates the buildable zone INSIDE the boundary.
    
    CRITICAL: Use negative distance for inward buffer!
    """
    setback_zone = boundary.buffer(-distance)  # Negative = inward
    return setback_zone
```

### 3.3 Plot Containment Check (CRITICAL FIX)

```python
def generate_plots(usable_area, plot_w, plot_h, spacing):
    """
    Generate plots that are COMPLETELY INSIDE the usable area.
    
    CRITICAL: Use contains() not intersects()!
    """
    plots = []
    minx, miny, maxx, maxy = usable_area.bounds
    
    x = minx + spacing
    while x + plot_w < maxx - spacing:
        y = miny + spacing
        while y + plot_h < maxy - spacing:
            candidate = box(x, y, x + plot_w, y + plot_h)
            
            # CRITICAL: Check COMPLETELY inside
            if usable_area.contains(candidate):
                plots.append(candidate)
            
            y += plot_h + spacing
        x += plot_w + spacing
    
    return plots
```

### 3.4 Data-Preserving DXF Export (CRITICAL FIX)

```python
def export_with_preservation(input_dxf, output_path, plots):
    """
    Export optimization results while PRESERVING ALL original data.
    
    WRONG: doc = ezdxf.new('R2010')  # Creates empty file!
    CORRECT: doc = ezdxf.readfile(input_dxf)  # Loads existing!
    """
    # Load existing DXF (preserves all data)
    doc = ezdxf.readfile(input_dxf)
    msp = doc.modelspace()
    
    # Create new layer for optimization results
    doc.layers.add('OPTIMIZED_PLOTS', color=5)
    
    # Add plots to new layer
    for plot in plots:
        px, py, px2, py2 = plot.bounds
        points = [(px, py), (px2, py), (px2, py2), (px, py2)]
        msp.add_lwpolyline(points, close=True, 
                          dxfattribs={'layer': 'OPTIMIZED_PLOTS'})
    
    # Save with all original data + new plots
    doc.saveas(output_path)
```

---

## 4. CRITICAL FIXES APPLIED

### Fix 1: Plots Outside Boundary

**Problem:** Plots were placed outside the cadastral boundary
**Root Cause:** Using `intersects()` instead of `contains()`
**Solution:** Changed to `usable_area.contains(candidate)`

### Fix 2: Data Loss in Export

**Problem:** 449 KB input → 22 KB output (95% loss)
**Root Cause:** Creating new empty DXF instead of modifying existing
**Solution:** Changed from `ezdxf.new()` to `ezdxf.readfile()`

### Fix 3: Wrong Coordinate Scale

**Problem:** DXF in millimeters, optimizer expected meters
**Root Cause:** No unit detection/conversion
**Solution:** Added `scale(poly, xfact=0.001, yfact=0.001)` for mm→m

### Fix 4: No Setback Zone

**Problem:** Plots touching boundary edge
**Root Cause:** No buffer applied
**Solution:** Added `boundary.buffer(-setback_distance)` for inward buffer

---

## 5. TEST RESULTS

### Before Fixes

| Metric | Value | Status |
|--------|-------|--------|
| Plots inside boundary | 0/3 | ❌ FAIL |
| Data preservation | 5% | ❌ FAIL |
| Utilization | 5.4% | ❌ POOR |

### After Fixes

| Metric | Value | Status |
|--------|-------|--------|
| Plots inside boundary | 9/9 | ✅ PASS |
| Data preservation | 95%+ | ✅ PASS |
| Utilization | 30%+ | ✅ GOOD |

---

## 6. NEXT STEPS: ADVANCED OPTIMIZATION

Based on the reference images, need to implement:

1. **Diagonal Main Road** - Cut through the land for access
2. **Secondary Roads** - Grid pattern perpendicular to main road
3. **Zone Splitting** - Divide land into zones by road
4. **Rotated Plot Grid** - Align plots with road direction
5. **Higher Density** - More plots, better utilization

Target: Match the professional layout shown in reference images.

---

## 7. DEPENDENCIES

```bash
pip install shapely ezdxf numpy matplotlib
```

---

## 8. USAGE

```python
from src.algorithms.industrial_estate_planner import IndustrialEstatePlanner

planner = IndustrialEstatePlanner('cadastral.dxf')
result = planner.plan_estate('output.dxf')
```

---

*Documentation last updated: December 6, 2025 13:30 UTC+7*
