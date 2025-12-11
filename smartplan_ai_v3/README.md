# SmartPlan AI v3.0

🏗️ **Automated Industrial Park Planning Engine** - LLM-driven spatial design with validation

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SmartPlan AI v3.0                         │
├─────────────────┬──────────────────┬──────────────────┬─────────┤
│  Pre-processing │ Generative Engine│   Validation     │Infra    │
│  (DXF→Blocks)   │ (Gemini 2.5)     │   (Gatekeeper)   │Routing  │
└─────────────────┴──────────────────┴──────────────────┴─────────┘
```

## Quick Start

### Backend

```bash
cd smartplan_ai_v3/backend
pip install -r requirements.txt
export GOOGLE_API_KEY="your-key"
uvicorn main:app --reload --port 8003
```

## Features

### 🎯 Core Modules

| Module | Description |
|--------|-------------|
| **Geometry Core** | DXF parsing, Block extraction, Shapely operations |
| **Generative Engine** | Gemini 2.5 Flash for spatial asset placement |
| **Validation** | Gatekeeper function for collision/boundary checks |
| **Infrastructure** | MST/Steiner Tree for utility routing |

### 📦 Asset Keywords

```json
["factory_standard", "warehouse_cold", "office_hq", 
 "parking_lot", "green_buffer", "utility_station"]
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload-dxf` | POST | Upload DXF, extract blocks |
| `/api/blocks` | GET | List all blocks |
| `/api/blocks/{id}/generate` | POST | Generate assets for block |
| `/api/validate` | POST | Validate proposed assets |
| `/api/finalize` | POST | Run infrastructure routing |

## Processing Pipeline

1. **Pre-processing**: DXF → GeoJSON, Block = Boundary - Roads
2. **Generative Design**: User selects block → LLM generates assets
3. **Validation**: Gatekeeper checks collisions & boundaries
4. **Infrastructure**: MST routing for utilities

## Environment Variables

```bash
GOOGLE_API_KEY=your-gemini-key  # For LLM
```
