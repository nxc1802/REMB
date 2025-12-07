# Land Redistribution Algorithm Tester

Test land subdivision and redistribution algorithms with FastAPI backend and Streamlit frontend.

## Features

- **Algorithm Implementation**: 100% equivalent logic from `algo.ipynb`
  - **Stage 1: Grid Optimization**: Uses NSGA-II (Genetic Algorithm) to find the optimal grid orientation and spacing.
- **Stage 2: Subdivision**: Uses OR-Tools (Constraint Programming) to subdivide blocks into individual lots, optimizing for target dimensions.
- **Stage 3: Infrastructure**: Generates technical networks (electricity/water MST) and drainage plans.
- **Zoning**: Automatically classifies lands into Residential, Service (Operations/Parking), and Wastewater Treatment (XLNT).
- **Visualization**: Interactive maps (Folium) and static notebook-style architectural plots (Matplotlib).
- **DXF Support**: Import site boundaries from DXF files and export results.ing and visualization
- **No Database**: In-memory processing for algorithm testing

## Project Structure

```
algorithms/
├── backend/
│   ├── main.py           # FastAPI app entry point
│   ├── models.py         # Pydantic models
│   ├── algorithm.py      # Core algorithm implementation
│   ├── routes.py         # API endpoints
│   └── requirements.txt
├── frontend/
│   ├── app.py           # Streamlit frontend
│   └── requirements.txt
├── .env.example
└── README.md
```

## Installation

### Backend

```bash
cd algorithms/backend
pip install -r requirements.txt
```

### Frontend

```bash
cd algorithms/frontend
pip install -r requirements.txt
```

## Running the Application

### Start Backend Server

```bash
cd algorithms/backend
uvicorn main:app --reload --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

### Start Frontend Application

In a new terminal:

```bash
cd algorithms/frontend
streamlit run app.py
```

The Streamlit app will open in your browser at http://localhost:8501

## Usage

1. **Configure Parameters** (in sidebar):
   - Grid spacing range (20-30m)
   - Rotation angle range (0-90°)
   - Lot width constraints (5-8m)
   - Population size and generations for NSGA-II

2. **Input Land Plots**:
   - Use sample rectangular plot
   - Upload GeoJSON file
   - Enter coordinates manually

3. **Run Optimization**:
   - Click "Run Full Pipeline"
   - Wait for results (typically 30-60 seconds)

4. **View Results**:
   - Summary statistics (blocks, lots, parks)
   - Stage-by-stage visualizations
   - Download GeoJSON or JSON results

## API Endpoints

### `POST /api/optimize`
Run complete optimization pipeline (all stages)

**Request**:
```json
{
  "config": {
    "spacing_min": 20.0,
    "spacing_max": 30.0,
    "angle_min": 0.0,
    "angle_max": 90.0,
    "min_lot_width": 5.0,
    "max_lot_width": 8.0,
    "target_lot_width": 6.0,
    "road_width": 6.0,
    "block_depth": 50.0,
    "population_size": 50,
    "generations": 100
  },
  "land_plots": [{
    "type": "Polygon",
    "coordinates": [[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]],
    "properties": {}
  }]
}
```

**Response**: Results with stages, metrics, and final GeoJSON layout

### `POST /api/stage1`
Run only grid optimization stage

### `GET /health`
Health check endpoint

## Algorithm Details

### Stage 1: Grid Optimization (NSGA-II)
- Multi-objective genetic algorithm
- Objectives:
  1. Maximize residential area
  2. Minimize fragmented blocks
- Uses DEAP library for evolutionary computation

### Stage 2: Block Subdivision (OR-Tools)
- Constraint programming for optimal lot widths
- Minimizes deviation from target width
- Respects min/max constraints
- Classifies blocks as residential or parks

## Example GeoJSON

```json
{
  "type": "Polygon",
  "coordinates": [
    [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]
  ],
  "properties": {"name": "Sample Plot"}
}
```

## Dependencies

### Backend
- FastAPI 0.104.1
- Shapely 2.0.2
- DEAP 1.4.1 (genetic algorithms)
- OR-Tools 9.8.3296 (constraint programming)
- NumPy 1.26.2

### Frontend
- Streamlit 1.29.0
- Plotly 5.18.0 (interactive charts)
- Requests 2.31.0

## Development

To modify the algorithm logic, edit `backend/algorithm.py`. The implementation is designed to match the notebook exactly.

## Troubleshooting

**Backend won't start**: Make sure port 8000 is not in use
```bash
lsof -i :8000
```

**Frontend can't connect**: Verify backend is running and API_URL is correct

**Optimization takes too long**: Reduce `generations` or `population_size` in the configuration

## License

MIT
