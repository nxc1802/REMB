# Procedural Generation

> Generative Design / Micro Design for CAD-Ready Layouts

Generate detailed site plans using procedural techniques: L-Systems, Skeletonization, OBB Trees, Shape Grammars, and Wave Function Collapse.

## Features

- **Road Network Generation**
  - Skeletonization (medial axis) for central main roads
  - L-Systems for organic branching patterns
  - Automatic corner filleting (R=12m for trucks)

- **Lot Subdivision**
  - OBB Tree for hierarchical division
  - Shape Grammar for rule-based generation
  - Quality validation with automatic green space conversion

- **Post-Processing**
  - Sidewalk generation
  - Green buffer zones
  - Corner smoothing

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
cd procedural_gen

# Install backend dependencies
cd backend && pip install -r requirements.txt && cd ..

# Install frontend dependencies
cd frontend && pip install -r requirements.txt && cd ..
```

### Running Locally

**Option 1: Using Makefile**

```bash
# Start both backend and frontend
make dev
```

**Option 2: Manual**

```bash
# Terminal 1: Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
streamlit run app.py
```

**Option 3: Docker**

```bash
make build
make up
```

### Access

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend UI**: http://localhost:8501

## Project Structure

```
procedural_gen/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── api/                       # Routes and schemas
│   ├── core/                      # Core algorithms
│   │   ├── road_network/          # L-Systems, Skeleton
│   │   ├── subdivision/           # OBB Tree, Shape Grammar
│   │   ├── tile_system/           # WFC (coming soon)
│   │   ├── post_processing/       # Buffers, corners
│   │   └── geometry/              # Shared utilities
│   └── pipeline/                  # Orchestration
├── frontend/
│   └── app.py                     # Streamlit UI
├── docker-compose.yml
└── Makefile
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate/roads` | POST | Generate road network |
| `/api/generate/subdivision` | POST | Subdivide into lots |
| `/api/generate/full` | POST | Run complete pipeline |
| `/api/upload-dxf` | POST | Upload DXF boundary |
| `/health` | GET | Health check |

## Configuration

All settings can be configured via API request or environment variables.

### Road Network
- `algorithm`: `skeleton`, `l_systems`, or `hybrid`
- `fillet_radius`: Corner radius (default: 12m)

### Subdivision
- `min_lot_area`: Minimum lot size (default: 1000 m²)
- `max_lot_area`: Maximum lot size (default: 10000 m²)
- `target_lot_width`: Target width (default: 40m)

### Post-Processing
- `sidewalk_width`: Sidewalk width (default: 2m)
- `green_buffer_width`: Buffer around lots (default: 5m)

## Development Phases

- [x] Phase 1: Project Setup
- [ ] Phase 2: Road Network (L-Systems, Skeleton)
- [ ] Phase 3: Subdivision (OBB Tree, Shape Grammar)
- [ ] Phase 4: Tile System (WFC)
- [ ] Phase 5: Post-Processing
- [ ] Phase 6: Integration & Polish

## Related

- [algorithms/](../algorithms/) - Original land redistribution with NSGA-II + OR-Tools
- [docs/Procedural Generation.md](../docs/Procedural%20Generation.md) - Design requirements

## License

MIT
