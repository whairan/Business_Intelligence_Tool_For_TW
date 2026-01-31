# Clark County Real Estate Intelligence Platform

**A Geospatial Business Intelligence tool for real estate investment analysis in Clark County.**

This platform combines interactive mapping with predictive AI to assist investors in identifying high-value land and property opportunities. It features a lasso-based search interface, granular analytics dashboards, and an automated "Go/No-Go" investment scoring engine.

---

## 🏗 Architecture Overview

The system follows a **Hybrid Microservices Architecture**, decoupling the resource-intensive geospatial/AI processing from the user interface.

* **Frontend:** Next.js (React) hosted on **Vercel** (Edge Network).
* **Backend:** Python (FastAPI) running in **Docker** containers (Fly.io / Railway).
* **Database:** **PostgreSQL** with **PostGIS** for spatial indexing.
* **AI Engine:** **XGBoost** for valuation scoring & **LangChain** for textual summaries.

---

## 🚀 Key Features

* **Interactive Geospatial Map:** High-performance vector tile rendering of 50,000+ Clark County parcels using **Mapbox GL JS**.
* **The Lasso Tool:** Freehand polygon selection to instantly analyze clusters of properties.
* **Multi-Input Search:** Robust search via Address, Parcel Number (APN), or Legal Description.
* **AI Investment Scout:**
* **Go/No-Go Scoring:** A 0-100 probability score for investment viability based on zoning, assessment history, and market comps.
* **Generative Summaries:** LLM-generated briefings on zoning constraints and neighborhood trends.


* **Granular Dashboard:** Dynamic visualizations (charts/graphs) that update based on the current map view or lasso selection.

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| **Frontend** | Next.js 15 (App Router) | UI Framework & SSR |
|  | Mapbox GL JS | Vector Mapping & Draw Tools |
|  | Zustand | Client-side State Management |
|  | Tailwind CSS / Shadcn | Styling & Components |
| **Backend** | Python 3.11 | Runtime Environment |
|  | FastAPI | Asynchronous API Framework |
|  | GeoPandas / Shapely | Spatial Analysis & Geometry Math |
|  | SQLAlchemy / Pydantic | ORM & Data Validation |
| **AI / ML** | XGBoost | Predictive Valuation Model |
|  | LangChain + OpenAI | Natural Language Summarization |
| **Data** | PostgreSQL 16 + PostGIS | Primary Spatial Database |
|  | Redis | Caching Hot Queries |
| **Infra** | Docker | Containerization |

---

## 💻 Local Development Setup

### Prerequisites

* **Docker Desktop** (Required for PostGIS database)
* **Node.js 20+** (For Frontend)
* **Python 3.11** (For Backend)
* **Mapbox API Key**
* **OpenAI API Key**

### 1. Database Setup (Docker)

Start the PostGIS database locally.

```bash
# Navigate to the database directory
cd infrastructure

# Spin up Postgres with PostGIS extension pre-loaded
docker-compose up -d db

```

*The database is now accessible at `localhost:5432`.*

### 2. Backend Setup (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies (including heavy GIS libs)
pip install -r requirements.txt

# Run the API Server
uvicorn app.main:app --reload --port 8000

```

*Access the API docs at: `http://localhost:8000/docs*`

### 3. Frontend Setup (Next.js)

```bash
cd frontend

# Install dependencies
npm install

# Run the Development Server
npm run dev

```

*Open the app at: `http://localhost:3000*`

---

## ⚙️ Configuration (.env)

Create a `.env` file in both `backend/` and `frontend/` directories.

**Backend `.env**`

```ini
DATABASE_URL=postgresql://user:password@localhost:5432/clark_county_db
OPENAI_API_KEY=sk-proj-...
REDIS_URL=redis://localhost:6379
CLARK_COUNTY_GIS_SOURCE_URL=https://gis.clark.wa.gov/gishome/

```

**Frontend `.env.local**`

```ini
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ...
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

```

---

## 🔄 Data Pipeline (ETL)

The system relies on up-to-date data from Clark County.

**To run the initial ingest:**

```bash
# From the backend directory
python -m scripts.etl.ingest_parcels

```

**This script performs the following:**

1. Fetches the latest Shapefiles (`.shp`) from Clark County GIS Open Data.
2. Normalizes coordinate systems (NAD83 -> WGS84).
3. Cleans invalid geometries (self-intersecting polygons).
4. Bulk inserts into the `parcels` table in PostGIS.
5. Refreshes the Vector Tiles cache.

---

## 🚢 Deployment

### Frontend (Vercel)

Connect your GitHub repository to Vercel.

* **Build Command:** `npm run build`
* **Output Directory:** `.next`
* Ensure environment variables (`NEXT_PUBLIC_API_URL`) point to your production backend.

### Backend (Fly.io / Railway)

The backend is containerized.

```bash
# Build the Docker image
docker build -t clark-bi-backend .

# Deploy to Fly.io
fly deploy

```

---

## 📜 License

Proprietary - Internal Business Use Only.
