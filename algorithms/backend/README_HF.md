---
title: Land Redistribution Algorithm API
emoji: 🏘️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Land Redistribution Algorithm API

API for industrial park land subdivision and redistribution using advanced optimization algorithms.

## Features

- **Multi-stage Optimization**: NSGA-II genetic algorithm + OR-Tools constraint programming
- **DXF Import**: Upload site boundaries from CAD files
- **Automated Layout**: Grid optimization, block subdivision, and infrastructure planning
- **Export Results**: Download results as GeoJSON

## API Endpoints

### Health Check
```bash
GET /health
```

### Full Optimization Pipeline
```bash
POST /api/optimize
```

Runs the complete 3-stage optimization:
1. Grid Optimization (NSGA-II)
2. Block Subdivision (OR-Tools)
3. Infrastructure Planning

### DXF Upload
```bash
POST /api/upload-dxf
```

Upload DXF file and extract boundary polygon.

## Usage

Visit the [interactive API documentation](/docs) for detailed endpoint specifications and to test the API directly.

### Quick Example

```python
import requests

url = "https://your-space-name.hf.space/api/optimize"
payload = {
    "config": {
        "spacing_min": 20.0,
        "spacing_max": 30.0,
        "population_size": 50,
        "generations": 100
    },
    "land_plots": [{
        "type": "Polygon",
        "coordinates": [[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]]
    }]
}

response = requests.post(url, json=payload)
result = response.json()
```

## Frontend

For a complete user interface, use the Streamlit frontend: [Link to your Streamlit app]

## Technology Stack

- **FastAPI**: High-performance Python web framework
- **DEAP**: Genetic algorithms (NSGA-II)
- **OR-Tools**: Constraint programming solver
- **Shapely**: Geometric operations
- **ezdxf**: DXF file parsing

## License

MIT
