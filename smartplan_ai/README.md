# SmartPlan AI

🏗️ **Design by Conversation** - LLM-driven industrial park planning

## Quick Start

### Backend

```bash
cd smartplan_ai/backend
pip install -r requirements.txt
export GOOGLE_API_KEY="your-key"  # Optional, for Gemini
uvicorn main:app --reload --port 8002
```

### Frontend

```bash
cd smartplan_ai/frontend
pip install -r requirements.txt
streamlit run app.py --server.port 8502
```

## Features

### 🛣️ Road Templates

| Template | Description |
|----------|-------------|
| **Spine** 🦴 | Central axis with perpendicular branches |
| **Grid** 🔲 | Orthogonal grid pattern |
| **Loop** ⭕ | Ring road around boundary |
| **Cross** ✚ | Two main axes crossing at center |

### 💬 Chat Commands

- "Tạo lưới đường bàn cờ"
- "Xoay 15 độ"
- "Chia lô tự động"
- "Áp dụng template vành đai"

### 🤖 LLM Integration

Uses **Google Gemini 2.5 Flash** for natural language understanding.
Falls back to pattern matching if no API key.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/templates` | GET | List templates |
| `/api/set-boundary` | POST | Set site boundary |
| `/api/apply-template` | POST | Apply road template |
| `/api/rotate` | POST | Rotate roads |
| `/api/subdivide` | POST | Subdivide into lots |
| `/api/chat` | POST | Chat with AI agent |
| `/api/state` | GET | Get current design |

## Architecture

```
User ─────► Chat Message
              │
              ▼
        ┌──────────────┐
        │ Design Agent │ (Gemini 2.5 Flash)
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ Design Tools │ (Pre-defined functions)
        └──────┬───────┘
               │
        ┌──────┴───────┐
        │              │
        ▼              ▼
   Templates      Subdivision
   (spine/grid/   (OBB-aligned
    loop/cross)    grid)
        │              │
        └──────┬───────┘
               │
               ▼
         GeoJSON Output
```

## Environment Variables

```bash
GOOGLE_API_KEY=your-gemini-key  # For LLM
API_URL=http://localhost:8002   # For frontend
```
