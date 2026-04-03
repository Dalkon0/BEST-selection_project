# UAV Telemetry Analyzer

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red?style=flat-square&logo=streamlit)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=flat-square&logo=google)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

Web application for automated analysis of Ardupilot flight controller binary logs (`.BIN`) with 3D trajectory visualization, flight metric computation and AI-powered diagnostics.

---

## Recent Updates

- **Multi-Sensor Support:** Beyond the required GPS and IMU, the system automatically detects and visualizes **BARO** (barometric altitude vs GPS), **BAT/CURR** (battery voltage & current), **MODE** (flight mode timeline), **VIBE** (structural vibrations), **ATT** (roll tracking) — any sensor present in the log appears automatically.
- **Multi-Log Comparison (A/B Analysis):** Toggle "Compare Mode" to upload two `.BIN` files simultaneously. The system generates a side-by-side metric comparison table with delta (%) calculation and overlays both 3D trajectories for direct spatial comparison.
- **ZUPT (Zero Velocity Update):** IMU integration now uses a physically correct stationary detection — if 5 consecutive samples have `|acc| < 0.08 m/s²`, velocity resets to 0. This prevents linear drift accumulation during hover or before takeoff.

- **Peak-Preserving Downsampling:** `downsample_df` now guarantees that max/min values of Alt, Spd, VZ, AccZ are always included in the downsampled dataset — critical peaks are never lost during visualization.
- **Tilt Compensation + Linear Detrend:** Full Body→Earth Frame rotation for IMU vertical speed, with endpoint-zeroing drift correction for visualization.
- **KML Export:** One-click export to **Google Earth (.kml)** with 3D path extrusion.
- **Verification Dashboard:** GPS vs IMU vertical speed comparison chart — visually proves mathematical accuracy.
- **30 Unit Tests:** Full coverage of coordinate transforms, Haversine, trapz integration, ZUPT, GPS/IMU/ATT column mapping, and AI anomaly detection.
- **A/B Model Comparison:** Parallel Gemini model requests (ThreadPoolExecutor) with 45s per-model timeout and full exception handling.
- **EN/UA Interface:** Full language switcher with complete Ukrainian translation.

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
   - [Pipeline Logging](#pipeline-logging)
6. [Theoretical Grounding](#theoretical-grounding)
7. [Stack & Rationale](#stack--rationale)
8. [Docker Deployment](#docker-deployment)
9. [Tests](#tests)

---

## Overview

Ardupilot flight controllers record every sensor reading into binary `.BIN` log files (DataFlash format). These files contain GPS coordinates, IMU accelerometer/gyroscope data, barometer readings, flight modes, and dozens of other message types — all timestamped in microseconds.

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
git clone https://github.com/Illia915/BEST-selection_project.git
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

### Using the app

1. **Upload a log** — drag and drop a `.BIN` file into the sidebar uploader, or click "Load Sample File" to use one of the included test logs from the `data/` folder.
2. **Explore metrics** — the top panel shows 8 key flight metrics computed automatically.
3. **View trajectory** — the **3D Trajectory** tab shows the flight path in 3D space, colored by speed or time.
4. **View map** — the **Map** tab shows the flight on an OpenStreetMap tile layer with speed-based color coding.
5. **View charts** — the **Charts** tab shows altitude and speed over time, plus the raw GPS data table.
6. **Run AI analysis** — enter your Gemini API key in the sidebar, choose a model (or enable A/B comparison), and click **Run Analysis**.

---

## Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and fill in the values:

```env
# ── AI ──────────────────────────────────────────────────────────────────────
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_AI_PIPELINE=true
LOG_STORAGE=local

# ── MongoDB (optional) ───────────────────────────────────────────────────────
MONGO_URI=mongodb://localhost:27017
MONGO_DB=uav_telemetry
```

---

## Project Structure

```
.
├── app.py                      # Streamlit UI — layout, state, all tabs
├── Dockerfile                  # Container image for the app
├── scraper/
│   └── dataflash.py            # Ardupilot .BIN parser + sensor extraction
├── analytics/
│   ├── metrics.py              # Haversine, trapezoidal integration, tilt compensation
│   └── coords.py               # WGS-84 → ECEF → ENU coordinate conversion
├── visualization/
│   ├── plot3d.py               # 3D Plotly trajectory + charts
│   └── map_view.py             # Folium/Leaflet interactive 2D map
├── ai/                         # LLM diagnostics and pipeline logging
└── data/                       # Sample log files for testing
```

---

## How It Works

### Log Parsing & Sensor Sync

Ardupilot saves flight data in **DataFlash binary format**. `scraper/dataflash.py` uses **pymavlink** to decode this format:

- **GPS messages** — Latitude, Longitude, Altitude, Ground Speed.
- **IMU messages** — Raw acceleration (AccX/Y/Z) at high frequency (100+ Hz).
- **ATT messages** — Vehicle attitude (Roll, Pitch, Yaw) used for orientation.

**Sensor Synchronization:** Since IMU and Attitude are recorded at different rates, the system uses a **Time-based Join (`merge_asof`)** to align orientation data with every accelerometer reading for precise tilt compensation.

### Coordinate Systems

The app works with three coordinate systems:
1. **WGS-84**: Global GPS standard (degrees).
2. **ECEF**: Earth-Centered, Earth-Fixed 3D Cartesian system.
3. **ENU (East-North-Up)**: Local Cartesian system centered on the takeoff point.axes are in meters from the start position. 

The full pipeline: GPS point → WGS-84 → ECEF → ENU. The 3D plot uses ENU coordinates directly.

### Flight Metrics & Tilt Compensation

**Total distance** uses the **Haversine formula**, which calculates the great-circle distance between two points on a sphere, accounting for Earth's curvature.

**Ideal Vertical Speed (Tilt Compensation)**:
Standard IMU integration of the raw Z-axis is inaccurate because gravity ($g$) shifts between axes as the drone tilts. We implement **Body Frame to Earth Frame rotation**:
```python
acc_z_earth = ax*sin(-pitch) + ay*sin(roll)*cos(pitch) + az*cos(roll)*cos(pitch)
acc_z_pure = acc_z_earth + 9.80665
```
By rotating the acceleration vector back to the "global vertical" before integrating, we get a truer vertical velocity even during aggressive maneuvers.

**Dynamic Acceleration**:
Calculated as the magnitude of the 3D acceleration vector minus the gravity constant:
`dynamic_acc = |√(AccX² + AccY² + AccZ²) - 9.80665|`. We use the **95th percentile** to filter out single-sample noise spikes.

---

## Theoretical Grounding

### 1. Coordinate Transformations (WGS-84 → ENU)
Global coordinates are non-Cartesian. To visualize them in 3D and perform metric calculations, we convert them to a local **East-North-Up (ENU)** system. This ensures that X/Y/Z axes represent real meters relative to the takeoff point.

### 2. IMU Integration (Trapezoidal Method)
To derive velocity from acceleration, we implement the **trapezoidal rule**:
`v[i] = v[i−1] + (a[i−1] + a[i]) / 2 · Δt`
This method is $O(dt^2)$ accurate, providing a much smoother and more precise velocity curve compared to the basic rectangular method.

### 3. Orientation: Euler Angles vs Quaternions

The system uses **Attitude (Roll, Pitch, Yaw)** from the ATT message log to rotate acceleration vectors from the Body Frame into the Earth Frame.

**Euler angles** (Roll/Pitch/Yaw) are intuitive but have a critical mathematical flaw — **Gimbal Lock**. When pitch reaches ±90°, Roll and Yaw axes align, and the system loses one degree of freedom. It becomes impossible to distinguish rotation around two axes — the orientation representation degenerates. For a drone performing aggressive aerobatics or a flip maneuver, this means the attitude computation simply fails.

**Quaternions** solve this by representing rotation as a 4D unit vector `q = [w, x, y, z]` with the constraint `w² + x² + y² + z² = 1`. There are no singularities in quaternion space — any 3D rotation is uniquely represented without ambiguity. Additionally, quaternion multiplication is computationally cheaper than composing three Euler rotation matrices.

In this project we use Euler angles directly from the log (since that is what Ardupilot records in the ATT message), but in a full production flight controller, the internal attitude estimate uses quaternions, and they are only converted to Euler for logging and display purposes.

### 4. IMU Sensor Drift — Nature of Double Integration Errors

IMU velocity estimation is an **open-loop integration** process. Every error accumulates:

| Integration stage | Error growth |
|---|---|
| Acceleration → Velocity (1× integral) | Linear drift — `O(t)` |
| Velocity → Position (2× integral) | Quadratic drift — `O(t²)` |

The two root causes:
- **Bias**: Every MEMS accelerometer has a small constant offset (e.g., 0.01 m/s²). After 60 seconds: velocity error ≈ 0.6 m/s. After 60 more seconds: position error ≈ 36 m.
- **Noise**: High-frequency vibration noise does not cancel out during integration — it accumulates as a random walk.

This project addresses drift in two ways:
1. **ZUPT (Zero Velocity Update)** — when `|acc| < 0.08 m/s²` for 5 consecutive samples, the drone is considered stationary and velocity is reset to 0. This prevents linear drift accumulation during hover or before takeoff.
2. **Linear detrend** — for visualization, we apply endpoint-zeroing: assuming `v_start = v_end = 0` (drone at rest at takeoff and landing), we subtract a linear ramp equal to the accumulated drift. This is a standard post-processing technique in inertial navigation.

For long-term position accuracy, the correct solution is an **Extended Kalman Filter (EKF)** — the algorithm Ardupilot uses internally to fuse GPS position with IMU data, continuously correcting drift with an absolute reference.

---

## Stack & Rationale

| Library | Why this one |
|---|---|
| **pymavlink** | The only library that correctly decodes all DataFlash format versions. |
| **pandas** | Natural fit for tabular telemetry; used for high-speed sensor synchronization. |
| **numpy** | Vectorized math for coordinate transforms and tilt compensation. |
| **plotly** | Best Python library for interactive 3D charts in the browser. |
| **folium** | Leaflet maps in Python without an API key requirement. |
| **streamlit** | Fastest path from Python analysis code to a working web UI. |

---

## Docker Deployment

```bash
# Build and start
cp .env.example .env
docker-compose up --build
```
The `docker-compose.yml` spins up the **Streamlit app** and a **MongoDB** instance for AI pipeline logging.

---

## Tests

```bash
# Full metrics and coordinate conversion smoke test
python tests/test_parser.py
```
This test parses `data/00000001.BIN`, checks ENU ranges, and prints all computed metrics including the ideal IMU velocity and dynamic acceleration.

---

---

# UAV Telemetry Analyzer — Українська версія

Веб-застосунок для автоматизованого аналізу бінарних лог-файлів польотного контролера Ardupilot (`.BIN`) з 3D-візуалізацією траєкторії, обчисленням метрик польоту та AI-діагностикою.

---

## Нещодавні оновлення

- **Підтримка багатьох сенсорів:** Окрім обов'язкових GPS та IMU, система автоматично виявляє та візуалізує **BARO** (барометрична висота), **BAT/CURR** (напруга та струм), **MODE** (режими польоту), **VIBE** (вібрації), **ATT** (крен) — будь-який сенсор з логу відображається автоматично.
- **Порівняння двох польотів (A/B аналіз):** Увімкніть "Режим порівняння", щоб завантажити два `.BIN` файли одночасно. Система створить таблицю порівняння метрик із розрахунком дельти (%) та накладе обидві 3D-траєкторії для візуального порівняння.
- **ZUPT (Zero Velocity Update)** — коли `|acc| < 0.08 м/с²` для 5 послідовних семплів, апарат вважається нерухомим, і швидкість скидається до 0. Це запобігає накопиченню лінійного дрейфу під час зависання або перед зльотом.
- **Анімація польоту (Replay):** Можливість відтворити політ у 3D з регулюванням швидкості.
- **Авто-виявлення аномалій:** Візуальні маркери на 3D-траєкторії для небезпечних маневрів або вібрацій.
- **PDF-звіти:** Генерація професійних технічних звітів з результатами AI-аналізу.

---

## Зміст

1. [Огляд](#огляд)
2. [Швидкий старт](#швидкий-старт)
3. [Конфігурація](#конфігурація)
4. [Структура проєкту](#структура-проєкту)
5. [Як це працює](#як-це-працює)
6. [Теоретичне обґрунтування](#теоретичне-обґрунтування)
7. [Стек та обґрунтування вибору](#стек-та-обґрунтування-вибору)
8. [Запуск через Docker](#запуск-через-docker)
9. [Тести](#тести)

---

## Огляд

Польотні контролери Ardupilot записують кожне показання датчиків у бінарні лог-файли `.BIN` (формат DataFlash). Ці файли містять GPS-координати, дані акселерометра/гіроскопа IMU, барометра, режимів польоту та десятки інших типів повідомлень — усе з мітками часу в мікросекундах.

Ручний аналіз таких файлів вимагає спеціалізованих інструментів і глибоких знань. Цей застосунок автоматизує весь конвеєр:

```
.BIN файл → Парсинг → Синхронізація сенсорів → Метрики → 3D-візуалізація → AI-звіт
```

Результат — веб-дашборд, де після завантаження файлу одразу отримуєш повний аналіз польоту: траєкторію, метрики, графіки, карту та AI-технічний звіт.

---

## Швидкий старт

### Вимоги

- Python 3.11+
- pip

### Локальне розгортання

```bash
# 1. Клонувати репозиторій
git clone https://github.com/Illia915/BEST-selection_project.git
cd BEST-selection_project

# 2. Встановити залежності
pip install -r requirements.txt

# 3. Налаштувати середовище
cp .env.example .env
# Відкрити .env та вказати GEMINI_API_KEY

# 4. Запустити
streamlit run app.py
```

Відкрити `http://localhost:8501` у браузері.

### Використання застосунку

1. **Завантажити лог** — перетягнути `.BIN` файл у сайдбар або натиснути "Завантажити тестовий файл".
2. **Метрики** — верхня панель показує 8 ключових показників польоту.
3. **3D траєкторія** — вкладка показує траєкторію в 3D просторі, розфарбовану за швидкістю або часом.
4. **Карта** — вкладка показує маршрут на OpenStreetMap з кольоровим кодуванням швидкості.
5. **Графіки** — вкладка показує висоту і швидкість у часі, порівняння GPS vs IMU вертикальної швидкості.
6. **AI-аналіз** — ввести Gemini API ключ, обрати модель і натиснути **Запустити аналіз**.

---

## Конфігурація

```env
# ── AI ───────────────────────────────────────────────────────────────────────
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash

# ── Логування ────────────────────────────────────────────────────────────────
LOG_AI_PIPELINE=true
LOG_STORAGE=local

# ── MongoDB (опціонально) ─────────────────────────────────────────────────────
MONGO_URI=mongodb://localhost:27017
MONGO_DB=uav_telemetry
```

---

## Структура проєкту

```
.
├── app.py                      # Streamlit UI — розмітка, стан, всі вкладки
├── Dockerfile                  # Образ контейнера
├── scraper/
│   └── dataflash.py            # Парсер .BIN + витяг даних сенсорів
├── analytics/
│   ├── metrics.py              # Haversine, трапецієве інтегрування, tilt compensation
│   └── coords.py               # Перетворення WGS-84 → ECEF → ENU
├── visualization/
│   ├── plot3d.py               # 3D Plotly траєкторія + графіки
│   └── map_view.py             # Інтерактивна 2D карта (Folium/Leaflet)
├── ai/                         # LLM-діагностика та логування конвеєра
└── data/                       # Тестові лог-файли
```

---

## Як це працює

### Парсинг логів і синхронізація сенсорів

Ardupilot зберігає дані у **бінарному форматі DataFlash**. `scraper/dataflash.py` використовує **pymavlink** для декодування:

- **GPS** — широта, довгота, висота, горизонтальна швидкість.
- **IMU** — сирі прискорення AccX/Y/Z на частоті 100+ Гц.
- **ATT** — орієнтація апарату (Roll, Pitch, Yaw) для tilt compensation.

**Синхронізація сенсорів:** IMU і ATT записуються з різними частотами, тому система використовує **часове об'єднання (`merge_asof`)** для вирівнювання даних орієнтації з кожним вимірюванням акселерометра.

### Системи координат

Застосунок працює з трьома системами координат:
1. **WGS-84** — глобальний GPS стандарт (градуси).
2. **ECEF** — декартова система з початком у центрі Землі.
3. **ENU (East-North-Up)** — локальна декартова система з початком у точці старту (метри).

Повний конвеєр: GPS → WGS-84 → ECEF → ENU. 3D-графік використовує ENU безпосередньо.

### Метрики польоту та компенсація нахилу

**Загальна дистанція** — формула **Haversine**, яка обчислює відстань між двома точками по дузі великого кола з урахуванням кривизни Землі.

**Ідеальна вертикальна швидкість (Tilt Compensation):**
Просте інтегрування сирої осі Z IMU є неточним, бо гравітація ($g$) розподіляється між осями при нахилі. Реалізовано поворот **Body Frame → Earth Frame**:
```python
acc_z_earth = ax*sin(-pitch) + ay*sin(roll)*cos(pitch) + az*cos(roll)*cos(pitch)
acc_z_pure = acc_z_earth + 9.80665
```

---

## Теоретичне обґрунтування

### 1. Перетворення координат WGS-84 → ENU

Глобальні координати є не декартовими. Для 3D-візуалізації та метричних обчислень вони конвертуються у локальну систему **East-North-Up (ENU)**, де X/Y/Z відповідають реальним метрам відносно точки зльоту. Земля моделюється як еліпсоїд WGS-84 (не сфера), що дає точність до сантиметрів.

### 2. Інтегрування IMU (метод трапецій)

Для отримання швидкості з прискорення застосовано **правило трапецій**:

```
v[i] = v[i-1] + (a[i-1] + a[i]) / 2 · Δt
```

Метод має точність `O(dt²)` — значно точніший за прямокутний метод `O(dt)`.

### 3. Орієнтація: кути Ейлера vs кватерніони

Система використовує **Roll/Pitch/Yaw** з ATT-повідомлень для повороту вектора прискорення.

**Кути Ейлера** мають критичний математичний недолік — **Gimbal Lock**. Коли кут Pitch досягає ±90°, осі Roll і Yaw вирівнюються, і система втрачає один ступінь свободи. Стає неможливим розрізнити обертання навколо двох осей — представлення орієнтації виродиться. Для БПЛА, що виконує агресивний маневр або переворот, це означає повну відмову обчислення орієнтації.

**Кватерніони** вирішують цю проблему, представляючи поворот як 4D одиничний вектор `q = [w, x, y, z]` з умовою `w² + x² + y² + z² = 1`. У просторі кватерніонів немає сингулярностей — будь-яке 3D-обертання представлено однозначно. Множення кватерніонів також обчислювально дешевше за композицію трьох матриць Ейлера.

У цьому проєкті кути Ейлера використовуються безпосередньо з лога (саме їх записує Ardupilot у ATT), але всередині польотного контролера оцінка орієнтації ведеться у кватерніонах, і вони конвертуються в Ейлер лише для запису і відображення.

### 4. Природа похибок подвійного інтегрування IMU

Оцінка швидкості через IMU — це **інтегрування з відкритим контуром**. Кожна похибка накопичується:

| Стадія інтегрування | Зростання похибки |
|---|---|
| Прискорення → Швидкість (1× інтеграл) | Лінійний дрейф — `O(t)` |
| Швидкість → Позиція (2× інтеграл) | Квадратичний дрейф — `O(t²)` |

Два джерела проблеми:
- **Зміщення (Bias)**: Кожен MEMS-акселерометр має невелике постійне зміщення (наприклад, 0.01 м/с²). Через 60 секунд: похибка швидкості ≈ 0.6 м/с. Через ще 60 секунд: похибка позиції ≈ 36 м.
- **Шум**: Високочастотний шум вібрацій не компенсується при інтегруванні — він накопичується як випадкове блукання.

У цьому проєкті дрейф компенсується двома способами:
1. **ZUPT (Zero Velocity Update)** — коли `|acc| < 0.08 м/с²` для 5 послідовних семплів, апарат вважається нерухомим, і швидкість скидається до 0. Це запобігає накопиченню лінійного дрейфу під час зависання або перед зльотом.
2. **Лінійне детрендування** — для візуалізації застосовується корекція кінцевої точки: припускаючи `v_початок = v_кінець = 0` (апарат у спокої на зльоті та посадці), віднімається лінійний нахил, що дорівнює накопиченому дрейфу.

Правильне рішення для довгострокової точності позиції — **Розширений фільтр Калмана (EKF)**: саме цей алгоритм Ardupilot використовує всередині для злиття GPS-позиції з даними IMU, безперервно коригуючи дрейф абсолютним орієнтиром.

---

## Стек та обґрунтування вибору

| Бібліотека | Чому саме вона |
|---|---|
| **pymavlink** | Єдина бібліотека, що коректно декодує всі версії формату DataFlash. |
| **pandas** | Природне середовище для табличної телеметрії; використовується для швидкої синхронізації сенсорів. |
| **numpy** | Векторизована математика для перетворень координат і tilt compensation. |
| **plotly** | Найкраща Python-бібліотека для інтерактивних 3D-графіків у браузері. |
| **folium** | Leaflet-карти в Python без потреби у платному API-ключі. |
| **streamlit** | Найшвидший шлях від аналітичного Python-коду до робочого веб-інтерфейсу. |

---

## Запуск через Docker

```bash
# Зібрати та запустити
cp .env.example .env
docker-compose up --build
```

`docker-compose.yml` запускає **Streamlit-застосунок** та інстанс **MongoDB** для логування AI-конвеєра.

---

## Тести

```bash
# Повний smoke-тест метрик та конвертації координат
python tests/test_parser.py

# Unit-тести (29 тестів)
pytest tests/test_units.py tests/test_math.py -v
```

Unit-тести покривають: Haversine, трапецієве інтегрування, WGS-84/ENU перетворення, парсинг колонок GPS/IMU/ATT, фільтрацію GPS, виявлення аномалій AI.
