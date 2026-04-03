# UAV Telemetry Analyzer

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red?style=flat-square&logo=streamlit)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=flat-square&logo=google)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-streamlit.app-ff4b4b?style=flat-square&logo=streamlit)](https://uav-telemetry.streamlit.app)

Web application for automated analysis of Ardupilot flight controller binary logs (.BIN) with 3D trajectory visualization, flight metric computation and AI-powered diagnostics.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Project Structure](#project-structure)
5. [How It Works](#how-it-works)
   - [Log Parsing & Sensor Sync](#log-parsing--sensor-sync)
   - [Coordinate Systems](#coordinate-systems)
   - [Flight Metrics & Tilt Compensation](#flight-metrics--tilt-compensation)
   - [3D Visualization](#3d-visualization)
   - [AI Analysis](#ai-analysis)
6. [Theoretical Grounding](#theoretical-grounding)
7. [Stack & Rationale](#stack--rationale)
8. [Docker Deployment](#docker-deployment)
9. [Tests](#tests)

---

## Overview

Ardupilot flight controllers record every sensor reading into binary .BIN log files (DataFlash format). These files contain GPS coordinates, IMU accelerometer/gyroscope data, barometer readings, flight modes, and dozens of other message types — all timestamped in microseconds.

Manually analyzing these files requires specialized tools and deep domain knowledge. This application automates the entire pipeline:

```
.BIN file  →  Parse  →  Sync Sensors  →  Compute Metrics  →  3D Visualization  →  AI Report
```

The result is a web dashboard where you upload a log file and immediately get a full flight analysis — trajectory, metrics, charts, map and an AI-generated technical report.

---

## Quick Start

### Requirements

- Python 3.11+
- pip

### Local setup

```bash
# 1. Clone the repository
git clone https://github.com/Dalkon0/BEST-selection_project.git
cd BEST-selection_project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Open .env and add your GEMINI_API_KEY (see Configuration section)

# 4. Run
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

> **Live demo:** [https://uav-telemetry.streamlit.app](https://uav-telemetry.streamlit.app)

---

## Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and fill in the values:

```env
# AI
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash

# Logging
LOG_AI_PIPELINE=true
LOG_STORAGE=local

# MongoDB (optional)
MONGO_URI=mongodb://localhost:27017
MONGO_DB=uav_telemetry
```

---

## Project Structure

```
.
├── app.py                      # Streamlit entry point — layout, state, tab routing
├── Dockerfile                  # Container image
├── docker-compose.yml
├── i18n.py                     # Ukrainian / English string translations
├── ui/
│   └── components.py           # Reusable Streamlit render functions
├── scraper/
│   └── dataflash.py            # Ardupilot .BIN parser + sensor extraction
├── analytics/
│   ├── metrics.py              # Haversine, trapezoidal integration, tilt compensation
│   └── coords.py               # WGS-84 → ECEF → ENU coordinate conversion
├── visualization/
│   ├── plot3d.py               # 3D Plotly trajectory, cockpit, charts, animation
│   └── map_view.py             # Folium/Leaflet interactive 2D map + KML export
├── ai/                         # Gemini LLM diagnostics pipeline
├── tests/                      # 30 unit tests (pytest)
└── data/                       # Sample .BIN log files
```

### Module responsibilities

| Module | Responsibility |
|--------|----------------|
| `scraper/dataflash.py` | Parse binary DataFlash format; extract typed DataFrames for GPS, IMU, ATT, VIBE, BARO, BAT, MODE |
| `analytics/metrics.py` | Haversine distance, trapezoidal integration, ZUPT, tilt-compensated acceleration, sampling rate |
| `analytics/coords.py` | WGS-84 → ECEF → ENU vectorised conversion |
| `visualization/plot3d.py` | Interactive 3D Plotly charts, virtual cockpit, A/B animation |
| `visualization/map_view.py` | Folium map with multi-track support and KML export |
| `ui/components.py` | Stateless Streamlit render helpers (metrics grid, compare table, landing page) |
| `ai/assistant.py` | Gemini API integration, single and A/B parallel analysis |
| `analytics/pdf_report.py` | PDF report generation with full Unicode / font auto-selection |

---

## How It Works

### Log Parsing & Sensor Sync

Ardupilot saves flight data in DataFlash binary format. `scraper/dataflash.py` uses `pymavlink` to decode this format and extract typed DataFrames:

- **GPS** — Latitude, Longitude, Altitude, Ground Speed, Vertical Speed
- **IMU** — Raw acceleration (AccX/Y/Z) at ~100 Hz
- **ATT** — Vehicle attitude (Roll, Pitch, Yaw)
- **VIBE** — Vibration levels (VibeX/Y/Z)
- **BARO** — Barometric altitude and pressure
- **BAT** — Battery voltage and current
- **MODE** — Flight mode changes (AUTO, LOITER, LAND, …)

**Sensor Synchronization:** IMU and ATT are recorded at different rates. `merge_asof` performs a time-based join to align attitude data with every accelerometer sample for precise tilt compensation.

**Sampling rate** is computed as `1 / median(ΔTimeUS)` to be robust against occasional gaps.

### Coordinate Systems

The app works with three coordinate systems:

1. **WGS-84** — Global GPS standard (degrees, degrees, metres).
2. **ECEF** — Earth-Centred Earth-Fixed 3D Cartesian (metres).
3. **ENU** — Local East-North-Up Cartesian centred on the takeoff point (metres).

Full pipeline: GPS → WGS-84 → ECEF → ENU. The 3D plot uses ENU coordinates so all axes represent real metres from the start position.

```python
N = a / sqrt(1 - e² · sin²(φ))          # radius of curvature (WGS-84)
X = (N + h) · cos(φ) · cos(λ)           # ECEF
Y = (N + h) · cos(φ) · sin(λ)
Z = (N·(1−e²) + h) · sin(φ)
E = −sin(λ)·dX + cos(λ)·dY             # ENU rotation
N =  −sin(φ)·cos(λ)·dX − sin(φ)·sin(λ)·dY + cos(φ)·dZ
U =   cos(φ)·cos(λ)·dX + cos(φ)·sin(λ)·dY + sin(φ)·dZ
```

### Flight Metrics & Tilt Compensation

**Total distance** uses the Haversine formula, computing the great-circle distance between consecutive clean GPS points:

```
a = sin²(Δφ/2) + cos(φ₁)·cos(φ₂)·sin²(Δλ/2)
d = 2R · arctan2(√a, √(1−a))
```

**Vertical speed from IMU (tilt compensation):** Raw Z-axis integration is inaccurate when the drone tilts — gravity shifts between body axes. We rotate body-frame acceleration into Earth-frame before integrating:

```python
az_earth = ax·sin(−pitch) + ay·sin(roll)·cos(pitch) + az·cos(roll)·cos(pitch)
az_pure  = az_earth + 9.80665   # remove gravity
```

**Dynamic acceleration (gravity subtraction in body frame):**

```python
# g_body = Rᵀ · [0, 0, −g]_ENU
dyn_x = ax − g·sin(pitch)
dyn_y = ay + g·sin(roll)·cos(pitch)
dyn_z = az + g·cos(roll)·cos(pitch)
max_acceleration = 95th_percentile(‖dyn_x, dyn_y, dyn_z‖)
```

### 3D Visualization

- **Single mode** — trajectory coloured by speed, time, or flight mode. Anomalies (sharp altitude drop, speed spike) are highlighted.
- **Compare mode (A/B)** — two trajectories overlaid with distinct colorscales (blue family / red family). Side-by-side delta table.
- **Animation / Replay** — frame-by-frame playback; in compare mode both UAVs animate simultaneously, resampled to the same frame count.
- **Virtual Cockpit** — animated attitude indicator, airspeed, altimeter, heading gauge.
- **FFT Vibration Analysis** — frequency-domain diagnosis of structural resonances from VIBE or raw IMU data.

### AI Analysis

Gemini 2.5 Flash receives flight metrics and GPS summary. Two modes:
- **Single** — one model, narrative technical report
- **A/B** — two models run in parallel for cross-validation; results shown side by side

The report can be exported as a PDF with full Unicode support.

---

## Theoretical Grounding

### 1. Coordinate Transformations (WGS-84 → ENU)

Global coordinates are non-Cartesian. Converting to a local ENU system ensures that X/Y/Z axes represent real metres relative to the takeoff point, making distance and trajectory calculations geometrically correct.

### 2. IMU Integration (Trapezoidal Method)

To derive velocity from acceleration we use the trapezoidal rule:

```
v[i] = v[i−1] + (a[i−1] + a[i]) / 2 · Δt
```

This method is O(dt²) accurate — significantly smoother than the basic rectangular (Euler) method.

**ZUPT (Zero Velocity Update):** when the Earth-frame residual acceleration |acc| < 0.15 m/s² for 5 consecutive samples, the drone is considered stationary and velocity is reset to 0, preventing drift accumulation during hover phases.

### 3. Orientation: Euler Angles vs Quaternions

The system uses Roll/Pitch/Yaw (ATT messages) for tilt compensation.

**Euler angles** are intuitive but suffer from **Gimbal Lock**: when pitch reaches ±90°, roll and yaw axes align and one degree of freedom is lost — it becomes impossible to distinguish rotation around two axes.

**Quaternions** represent rotation as a 4D unit vector q = [w, x, y, z] with w²+x²+y²+z²=1. There are no singularities — any 3D rotation is uniquely represented. For a production system processing aerobatic or fixed-wing logs with extreme pitch angles, quaternion-based attitude data (from the `NKF` messages) would replace ATT Euler angles.

### 4. IMU Sensor Drift — Nature of Double Integration Errors

IMU velocity estimation is an open-loop integration process. Every error accumulates:

| Stage | Error growth |
|-------|-------------|
| Acceleration → Velocity (1× integral) | Linear — O(t) |
| Velocity → Position (2× integral) | Quadratic — O(t²) |

Root causes:
- **Bias** — every MEMS accelerometer has a small constant offset (≈ 0.01 m/s²). After 60 s: velocity error ≈ 0.6 m/s.
- **Noise** — high-frequency vibration accumulates as random walk.

This project addresses drift with:
1. **ZUPT** — velocity reset when |residual acc| < 0.15 m/s² for 5 samples
2. **Linear detrend** — assuming v_start = v_end = 0, subtract a linear ramp equal to accumulated drift

---

## Stack & Rationale

| Library | Why |
|---------|-----|
| **pymavlink** | Only library that correctly decodes all DataFlash format versions |
| **pandas** | High-speed sensor synchronisation via `merge_asof`; clean DataFrame API |
| **numpy** | Vectorised math for coordinate transforms and tilt compensation |
| **plotly** | Best library for interactive 3D charts and animation in the browser |
| **folium** | Leaflet maps in Python without an API key requirement |
| **streamlit** | Fastest path from Python analysis code to a working web UI; built-in caching |

---

## Docker Deployment

```bash
docker build -t uav-analyzer .
docker run -p 8501:8501 -e GEMINI_API_KEY=AIza... uav-analyzer
```

Or with docker-compose:

```bash
GEMINI_API_KEY=AIza... docker-compose up
```

Open `http://localhost:8501`.

---

## Tests

```bash
# Unit tests (30 tests — math, coordinates, parser helpers)
pytest tests/test_units.py tests/test_math.py -v

# Smoke test against a real .BIN file
python tests/test_parser.py
```

All 30 unit tests pass without a physical flight log.

---
