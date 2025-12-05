"""Quick MILP Solver test"""
import sys
sys.path.insert(0, '.')

from ortools.sat.python import cp_model
from shapely.geometry import box
import time

print("Testing CP-SAT solver directly...")

# Simple test
model = cp_model.CpModel()

# Create 3 plots that must not overlap
plot_size = 30
site_size = 400

plots = []
x_intervals = []
y_intervals = []

for i in range(3):
    x = model.NewIntVar(0, site_size - plot_size, f'x_{i}')
    y = model.NewIntVar(0, site_size - plot_size, f'y_{i}')
    
    x_interval = model.NewIntervalVar(x, plot_size, x + plot_size, f'x_int_{i}')
    y_interval = model.NewIntervalVar(y, plot_size, y + plot_size, f'y_int_{i}')
    
    plots.append({'x': x, 'y': y})
    x_intervals.append(x_interval)
    y_intervals.append(y_interval)

# No overlap
model.AddNoOverlap2D(x_intervals, y_intervals)

# Solve
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 5

start = time.time()
status = solver.Solve(model)
elapsed = time.time() - start

print(f"Status: {solver.StatusName(status)}")
print(f"Solve time: {elapsed:.3f}s")

if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    for i, p in enumerate(plots):
        print(f"  Plot {i}: x={solver.Value(p['x'])}, y={solver.Value(p['y'])}")
    print("\n✅ MILP/CP-SAT solver works!")
else:
    print("❌ No solution found")
