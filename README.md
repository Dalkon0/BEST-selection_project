# UAV Telemetry Analyzer 🛸

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red?style=flat-square&logo=streamlit)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=flat-square&logo=google)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**Professional Suite for Ardupilot DataFlash Analysis.**  
Web application for automated analysis of Ardupilot flight controller binary logs (`.BIN`) with 3D trajectory visualization, flight replay, multi-log comparison, and AI-powered diagnostics.

---

## 🚀 Key Features

- **🥇 3D Flight Replay:** Interactive flight animation with ground projection and custom camera controls. Relive the mission in a balanced isometric view.
- **🥈 Multi-Log Comparison:** Side-by-side analysis of two flight logs. Automatically computes metric deltas (%) and overlays 3D tracks for direct spatial comparison.
- **🥉 AI-Powered Diagnostics:** Integration with **Gemini 2.5 Flash** to detect technical anomalies and generate structured technical reports.
- **📊 Auto-Anomaly Markers:** Visual indicators directly on the 3D trajectory for sharp climbs, overspeeding, and high vibrations.
- **📄 One-Click PDF Export:** Generate professional technical reports with flight metrics and AI conclusions (Unicode/Cyrillic support included).
- **📡 Multi-Sensor Analytics:** Automatic detection of GPS, IMU, BARO, BAT/CURR, MODE, VIBE, and ATT messages.
- **📐 Physics-Correct Metrics:** 
  - **ZUPT (Zero Velocity Update):** Stationary detection logic to eliminate IMU drift.
  - **Tilt Compensation:** IMU vertical speed calculation using Body→Earth frame rotation.
  - **Haversine Distance:** Precise ground distance calculation.

---

## 🛠 Tech Stack

| Component | Technology |
|---|---|
| **Frontend** | Streamlit (Custom CSS, responsive layout) |
| **Parsing** | Pymavlink (DataFlash binary decoder) |
| **Math** | NumPy & Pandas (Vectorized telemetry processing) |
| **3D Engine** | Plotly (Interactive WebGL charts) |
| **AI Engine** | Google Generative AI (Gemini 2.5 Flash) |
| **PDF Engine** | FPDF2 (Unicode-ready with system font fallback) |
| **Deployment** | Streamlit Cloud / Docker |

---

## 📖 How It Works

1. **Parsing & Sync:** `scraper/dataflash.py` decodes `.BIN` files. IMU and Attitude data are synchronized using time-based joins (`merge_asof`).
2. **Coordinate Transform:** GPS points are converted from WGS-84 to ECEF and then to a local **East-North-Up (ENU)** Cartesian system for 3D plotting.
3. **IMU Integration:** Vertical speed is derived using the trapezoidal rule with linear detrending and ZUPT to suppress drift.
4. **AI Pipeline:** Telemetry metrics are fed into Gemini with a specialized technical prompt to identify structural or piloting issues.

---

## 📦 Installation & Run

### Local Setup
```bash
# 1. Clone
git clone https://github.com/Dalkon0/BEST-selection_project.git
cd BEST-selection_project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Environment
cp .env.example .env
# Add your GEMINI_API_KEY to .env

# 4. Run
streamlit run app.py
```

### Docker
```bash
docker-compose up --build
```

---

# UAV Telemetry Analyzer — Українська версія 🇺🇦

**Професійний комплекс для аналізу логів Ardupilot.**

## ✨ Ключові можливості

- **🥇 3D-анімація польоту (Replay):** Інтерактивне відтворення місії з проекцією на землю та ізометричним ракурсом.
- **🥈 Порівняння двох польотів:** Режим A/B аналізу двох логів одночасно з розрахунком різниці (Delta %) та накладанням траєкторій.
- **🥉 AI-діагностика:** Використання **Gemini 2.5 Flash** для пошуку аномалій та формування технічних висновків.
- **📊 Маркери аномалій:** Візуальні позначки "проблемних" зон прямо на 3D-траєкторії.
- **📄 Експорт у PDF:** Генерація звітів з підтримкою української мови та автоматичною транслітерацією (fallback).
- **📐 Точна математика:** Компенсація нахилу (Tilt Compensation) та алгоритм ZUPT для усунення дрейфу IMU.

---

## 🧪 Тестування
```bash
# Запуск 29 unit-тестів (Math, Parser, AI)
pytest tests/test_units.py tests/test_math.py -v
```

---
*Developed for BEST Selection Project.*
