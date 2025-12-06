"""
Test script for the Production-Ready Estate Optimizer
Tests all 4 fixes and exports a DXF file
"""
import sys
import os
sys.path.insert(0, '.')

from src.algorithms.production_optimizer import (
    ProductionReadyEstateOptimizer, 
    export_optimized_layout_to_dxf,
    OverlapValidator
)

def test_production_optimizer():
    """Test the production optimizer with all 4 fixes"""
    print("=" * 70)
    print("🧪 TESTING PRODUCTION-READY ESTATE OPTIMIZER")
    print("=" * 70)
    
    # Define boundary (500m x 400m site)
    boundary = {
        'min_x': 0,
        'min_y': 0,
        'max_x': 500,
        'max_y': 400
    }
    
    # Define plot configurations
    plots = [
        {'width': 60, 'height': 80, 'type': 'warehouse'},
        {'width': 50, 'height': 60, 'type': 'office'},
        {'width': 70, 'height': 90, 'type': 'factory'},
        {'width': 55, 'height': 70, 'type': 'storage'},
    ] * 5  # 20 plots
    
    # Create optimizer
    optimizer = ProductionReadyEstateOptimizer(
        boundary_coords=boundary,
        plot_configs=plots,
        road_width=24,
        road_spacing=200,
        setback=10,
        plot_spacing=10
    )
    
    # Run optimization
    result = optimizer.optimize()
    
    # Export to DXF
    os.makedirs('output', exist_ok=True)
    dxf_path = 'output/production_layout.dxf'
    export_optimized_layout_to_dxf(result, dxf_path)
    
    # Verification
    print("\n" + "=" * 70)
    print("✅ VERIFICATION RESULTS")
    print("=" * 70)
    
    metrics = result['metrics']
    
    print(f"\n📊 METRICS:")
    print(f"   Site area:        {metrics['site_area']:>12,.0f} m²")
    print(f"   Buildable area:   {metrics['buildable_area']:>12,.0f} m²")
    print(f"   Total plot area:  {metrics['total_plot_area']:>12,.0f} m²")
    print(f"   Plots placed:     {metrics['num_plots']:>12d} / {len(plots)}")
    print(f"   Utilization:      {metrics['utilization']*100:>11.1f}%")
    
    print(f"\n🔍 VALIDATION:")
    print(f"   Valid layout:     {'✅ YES' if result['is_valid'] else '❌ NO'}")
    print(f"   Violations:       {len(result['violations'])}")
    
    if result['violations']:
        print("\n   Violation details:")
        for v in result['violations'][:5]:
            print(f"     - {v['type']}: {v.get('plots', v.get('plot', 'N/A'))}")
    
    print(f"\n📄 OUTPUT:")
    print(f"   DXF file: {os.path.abspath(dxf_path)}")
    
    # Success criteria from Industrial_Estate_Complete_Fixes.md
    print("\n" + "=" * 70)
    print("📋 SUCCESS CRITERIA CHECK")
    print("=" * 70)
    
    success = True
    
    # Criterion 1: No overlaps
    overlaps = [v for v in result['violations'] if v['type'] == 'OVERLAP']
    if len(overlaps) == 0:
        print("   ✅ No plot overlaps")
    else:
        print(f"   ❌ Found {len(overlaps)} overlaps")
        success = False
    
    # Criterion 2: No road conflicts
    road_conflicts = [v for v in result['violations'] if v['type'] == 'ROAD_CONFLICT']
    if len(road_conflicts) == 0:
        print("   ✅ No road conflicts")
    else:
        print(f"   ❌ Found {len(road_conflicts)} road conflicts")
        success = False
    
    # Criterion 3: Utilization > 30% (improved from 15%)
    if metrics['utilization'] > 0.30:
        print(f"   ✅ Utilization {metrics['utilization']*100:.1f}% > 30%")
    else:
        print(f"   ❌ Utilization {metrics['utilization']*100:.1f}% is too low")
        success = False
    
    # Criterion 4: Valid layout
    if result['is_valid']:
        print("   ✅ Layout is valid")
    else:
        print("   ❌ Layout is invalid")
        success = False
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 ALL TESTS PASSED! Optimizer working correctly.")
    else:
        print("⚠️ Some tests failed. Review violations above.")
    print("=" * 70)
    
    return result


if __name__ == "__main__":
    test_production_optimizer()
