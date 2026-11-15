# AgriNext 🌱🛰️
**NASA-Powered Climate-Resilient Crop Rotation Decision Support System**

AgriNext is a full-stack decision support system designed for farmers, agricultural advisors, and researchers in India. It leverages real NASA Earth observation datasets (POWER, SMAP, GPM), local soil conditions, and multi-season crop dynamics to recommend evidence-backed, climate-resilient crop rotation sequences.

---

## 📌 Critical Design Principles

1. **NASA Data as Computational Evidence**: NASA Earth observations (solar radiation, precipitation anomalies, soil moisture deficit) are not just decorative chart widgets; they are directly incorporated as computational evidence in scoring and agronomic suitability formulas.
2. **Strict Provenance & Traceability**: Every crop recommendation is traceable to its satellite source, temporal period, spatial grid resolution (e.g. 0.5° POWER, 9km SMAP), units, and mathematical formula.
3. **Zero Fabrication Policy**:
   - Never invent NASA observations.
   - Never label placeholder/mock data as real data.
   - Never fabricate soil moisture, pH, or NPK readings.
4. **Configuration-Driven Regional Extensibility**: Andhra Pradesh is our initial pilot region. The core recommendation engine is region-agnostic. New Indian states can be integrated purely by creating JSON configuration files under `backend/state_data/<state_id>/` without changing common engine code.

---

## 🏗️ Architecture & Project Structure

The project is structured into two clean standalone tiers:

```
agrinext/
├── backend/                        # FastAPI Python Engine
│   ├── api/                        # API route handlers & endpoints
│   │   ├── __init__.py
│   │   └── router.py               # Health, State Data, NASA status routes
│   ├── nasa/                       # NASA Earth Observation Services
│   │   ├── __init__.py
│   │   ├── power.py                # NASA POWER (Agroclimatology API)
│   │   ├── smap.py                 # NASA SMAP (Root-zone soil moisture)
│   │   └── gpm.py                  # NASA GPM (IMERG precipitation)
│   ├── geospatial/                 # Geospatial processing & polygon analysis
│   ├── data_processing/            # Ingestion, formatting & unit normalization
│   ├── crop_knowledge/             # Agronomic knowledge representation
│   ├── recommendation/             # Core Decision Engine
│   │   ├── __init__.py
│   │   ├── evidence_engine.py      # Mathematical evidence structuring
│   │   ├── rotation_engine.py      # 3 strategy sequence generation
│   │   ├── scoring.py              # Multi-attribute priority weighting
│   │   └── explanation.py          # Plain-language farmer explanations
│   ├── simulation/                 # Climate what-if scenario simulations
│   ├── reports/                    # PDF audit report generation
│   ├── state_data/                 # Multi-state configuration catalog
│   │   ├── registry.json           # Supported states registry
│   │   └── andhra_pradesh/         # Andhra Pradesh pilot dataset
│   │       ├── districts.json      # AP districts (Anantapur, Guntur, Krishna, etc.)
│   │       ├── mandals.json        # Mandals with centroid coordinates
│   │       ├── crops.json          # Crops (Paddy, Groundnut, Cotton, Pulses, etc.)
│   │       └── crop_rules.json     # Agronomic rotation & nitrogen constraints
│   ├── tests/                      # Automated test suite (pytest)
│   │   └── test_backend.py
│   ├── venv/                       # Isolated Python virtual environment
│   ├── main.py                     # FastAPI application entry point
│   └── requirements.txt            # Python dependencies
│
└── frontend/                       # React 19 + TypeScript + Vite + Tailwind CSS
    ├── src/
    │   ├── pages/                  # Top-level screen views (Dashboard.tsx)
    │   ├── components/             # Reusable UI components
    │   │   ├── Header.tsx          # NASA branding & system connectivity header
    │   │   ├── StatusCard.tsx      # Real-time backend & NASA service indicators
    │   │   ├── WorkflowStepper.tsx # Visual guide for the 11-step workflow
    │   │   ├── StateDataViewer.tsx # Interactive explorer for crops, districts & rules
    │   │   └── DeveloperGuide.tsx  # Beginner architecture cheatsheet
    │   ├── services/               # Typed API client (api.ts)
    │   ├── hooks/                  # Custom React hooks
    │   ├── types/                  # TypeScript interfaces & domain models
    │   ├── configuration/          # App settings & endpoint constants
    │   ├── App.tsx                 # Root application component
    │   ├── main.tsx                # React DOM mount point
    │   └── index.css               # Tailwind CSS v4 directives
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    └── vite.config.ts
```

---

## 🚀 Beginner-Friendly Quick Start Guide

### Prerequisites
- **Python 3.10+**
- **Node.js 20+**

### 1. Start the Backend API (FastAPI)

Open a terminal and navigate to the backend directory:

```powershell
cd backend

# On Windows (PowerShell):
.\venv\Scripts\uvicorn.exe main:app --reload --port 8000
```

- **Backend Health Endpoint**: `http://localhost:8000/api/health`
- **Interactive Swagger Documentation**: `http://localhost:8000/docs`

### 2. Start the Frontend (React + Vite)

Open a second terminal and navigate to the frontend directory:

```powershell
cd frontend

# Run the Vite development server:
npm run dev
```

- **Frontend Application**: Open your browser at `http://localhost:5173`

---

## 🧪 Automated Testing & Verification

To verify that the backend API, NASA Earth observation services, farmer profile processing, and ANGRAU crop knowledge contracts are working properly:

```powershell
cd backend
python -m pytest tests -v
```

All **53 automated tests** across 9 test suites pass:
1. `test_backend.py`: Health checks, state catalog loading, NASA metadata schema, recommendation archetypes.
2. `test_geospatial.py`: Geodesic acreage calculation, polygon centroid computation, discrepancy detection, farm profile persistence.
3. `test_nasa_power.py`: NASA POWER agroclimatology, missing value filtering, environmental evidence structuring, SQLite caching.
4. `test_nasa_smap.py`: NASA SMAP Version 6 SPL3SMP_E surface soil moisture, 9 km grid resolution, area sampling, quality flags, 14-day trend indicators, authentication integrity (no fake data).
5. `test_nasa_gpm.py`: NASA GPM IMERG Version 07 precipitation, GES DISC archive, ~10 km grid resolution, unit conversions, comparison with NASA POWER reanalysis, physical variance explanations.
6. `test_farmer_profile.py`: All 10 farmer inputs (Soil type, pH, N-P-K, OC, Current crop, Previous crops, Available crops, Irrigation source, Farming season, Preferred crops), Soil Health Card classification scales, benchmark fallbacks, SQLite persistence.
7. `test_crop_knowledge.py`: ANGRAU Vyavasaya Panchangam (2023-24) catalog, botanical families, water requirements, thermal/water stress, rotation compatibility (monoculture penalties, family pest breaks, legume BNF credits).
8. `test_evidence_engine.py`: Unified Environmental Evidence Dossier synthesis across NASA POWER, SMAP, and GPM.
9. `test_integrated_recommendations.py`: Multi-source recommendations synthesizing NASA macro-environmental observations, farmer ground-truth soil parameters, and ANGRAU agronomy with explicit provenance badges.

---

## 🗺️ The 11-Step Core Recommendation Workflow

1. **Select Location**: Pick district and mandal in Andhra Pradesh.
2. **Draw Boundary**: Interactively draw farm polygon on high-resolution satellite map.
3. **Calculate Acreage**: Geodesic area calculation in acres/hectares via Turf.js.
4. **Retrieve NASA Data**: Query NASA POWER, SMAP, and GPM for solar, rain, and soil moisture.
5. **Soil & Crop Profile**: Input soil texture, pH, NPK, and prior season crop history.
6. **Generate 3 Strategies**:
   - Strategy 1: *Maximum Climate Resilience* (low water footprint, drought tolerant).
   - Strategy 2: *Soil Health & Nutrient Regeneration* (legume nitrogen fixation, bio-mass).
   - Strategy 3: *Balanced Economic & Risk Diversification* (cash/staple balance).
7. **Compare Strategies**: Side-by-side radar and bar chart trade-off analysis.
8. **Customize Priorities**: Adjust weight sliders (water savings vs. profitability vs. soil health).
9. **Recalculate**: Real-time re-scoring based on updated weights.
10. **Climate What-If**: Simulate 20% rainfall drop or heatwave anomalies.
11. **Download PDF Report**: Full evidence-based dossier with satellite audit citations.

## Backend authentication configuration

- Public registration creates farmer accounts only; privileged roles must be provisioned by an administrator.
- Passwords are stored as PBKDF2-HMAC-SHA256 hashes. Session tokens are opaque, stored hashed in SQLite, and delivered in an HttpOnly cookie.
- Local development uses `AGRINEXT_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173` and `AGRINEXT_COOKIE_SECURE=false`.
- In production, set `AGRINEXT_ALLOWED_ORIGINS` to the exact HTTPS frontend origins and set `AGRINEXT_COOKIE_SECURE=true`. If frontend and API are on different sites, use `AGRINEXT_COOKIE_SAMESITE=none` (which requires Secure/HTTPS); same-site deployments can keep `lax`.
- Existing farms created before ownership migration retain a NULL owner and are intentionally hidden from authenticated farmer accounts. Recreate or administratively assign legacy farms after verifying their owner; do not automatically assign them to the first user.
- This is an initial authentication implementation. Before public production launch, add email verification, password reset, rate limiting, audit logging, CSRF defenses appropriate to the deployment topology, and an administrator account provisioning workflow.

## Environmental evidence requirements for recommendations

The crop recommendation endpoint now fails closed when its required environmental baseline is missing. It requires:

- Annual precipitation from NASA GPM IMERG or NASA POWER `PRECTOTCORR`.
- NASA POWER `T2M` mean temperature.
- NASA POWER maximum temperature, read from `T2M.statistics.extreme_max_c` (the native POWER evidence shape) or an explicit `T2M_MAX` evidence item.

If one or more required observations are unavailable or have zero valid source days, `POST /api/recommendations/generate` returns HTTP `422` with the missing inputs listed. It no longer substitutes fixed rainfall or temperature values. GPM is preferred when a valid annual total is available; POWER precipitation is the fallback. Optional SMAP, solar-radiation, and humidity evidence only influence the result when valid evidence is present.

The drought and waterlogging indicators in the unified dossier are explicitly identified as project heuristics derived from observed annual precipitation (and SMAP deficit status where available), not as NASA-published risk products. When no precipitation observation is available, those indices are `null` rather than fabricated defaults.
## Additional geospatial sources: Sentinel-2 and FAO GAEZ

AgriNext includes a protected **Satellite & GAEZ** page at `/earth-observation`. Sentinel-2 currently provides Copernicus STAC scene discovery (date/cloud filters and selected asset metadata), while FAO GAEZ provides v4 catalogue search and a link to the v5 portal. This is catalogue integration only: farm-level NDVI/NDWI processing and GAEZ raster suitability extraction are not yet implemented. See `SENTINEL2_GAEZ_INTEGRATION_REPORT.md` for scope and validation.

Database setup: see [DATABASE_INITIALIZATION.md](DATABASE_INITIALIZATION.md) for clean schema initialization and persistent database configuration.

## Phase 2 live integration checks

The backend includes opt-in live provider smoke tests. They are deliberately not
pytest-discovered and make real outbound requests only when explicitly run:

```powershell
cd backend
python scripts/smoke_test_integrations.py
python scripts/smoke_test_sentinel2_processing.py
```

The multi-provider script writes `backend/phase2_live_smoke_results.json`. It reports
authenticated integrations as blocked when credentials are missing; it does not
substitute mock or sample observations. Run it from a network-enabled environment
with the required credentials configured in `backend/.env`.
