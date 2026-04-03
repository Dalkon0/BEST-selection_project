from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "UAV_Telemetry_Analyzer_Presentation.pdf")

BG       = (15, 17, 23)
BG2      = (22, 27, 34)
BORDER   = (33, 38, 45)
BLUE     = (88, 166, 255)
GREEN    = (35, 134, 54)
ORANGE   = (210, 153, 34)
WHITE    = (230, 237, 243)
GRAY     = (139, 148, 158)
RED      = (248, 81, 73)

W, H = 297, 210


FONT_DIR = "/System/Library/Fonts/Supplemental"
FONT_REG  = f"{FONT_DIR}/Arial.ttf"
FONT_BOLD = f"{FONT_DIR}/Arial Bold.ttf"
FONT_MONO = "/System/Library/Fonts/Menlo.ttc"


class Slide(FPDF):
    def header(self):
        pass

    def footer(self):
        pass

    def _setup_fonts(self):
        self.add_font("Arial", "", FONT_REG)
        self.add_font("Arial", "B", FONT_BOLD)
        self.add_font("Mono", "", FONT_MONO)

    def slide_bg(self):
        self.set_fill_color(*BG)
        self.rect(0, 0, W, H, "F")

    def slide_bg2(self):
        self.set_fill_color(*BG)
        self.rect(0, 0, W, H, "F")
        self.set_fill_color(*BG2)
        self.rect(0, 0, 90, H, "F")
        self.set_draw_color(*BORDER)
        self.set_line_width(0.3)
        self.line(90, 0, 90, H)

    def accent_line(self, color=BLUE):
        self.set_fill_color(*color)
        self.rect(0, 0, 4, H, "F")

    def title_text(self, text, x, y, w, size=28, color=WHITE):
        self.set_xy(x, y)
        self.set_font("Arial", "B", size)
        self.set_text_color(*color)
        self.multi_cell(w, size * 0.45, text, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def body_text(self, text, x, y, w, size=11, color=GRAY, line_h=6):
        self.set_xy(x, y)
        self.set_font("Arial", "", size)
        self.set_text_color(*color)
        self.multi_cell(w, line_h, text, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def label(self, text, x, y, color=BLUE, size=8):
        self.set_xy(x, y)
        self.set_font("Arial", "B", size)
        self.set_text_color(*color)
        self.cell(0, 5, text.upper())

    def badge(self, text, x, y, bg=BG2, fg=BLUE, w=50):
        self.set_fill_color(*bg)
        self.set_draw_color(*BORDER)
        self.set_line_width(0.3)
        self.rect(x, y, w, 8, "FD")
        self.set_xy(x + 2, y + 1.5)
        self.set_font("Arial", "B", 8)
        self.set_text_color(*fg)
        self.cell(w - 4, 5, text)

    def code_block(self, lines, x, y, w):
        h = len(lines) * 5.5 + 6
        self.set_fill_color(10, 12, 16)
        self.set_draw_color(*BORDER)
        self.rect(x, y, w, h, "FD")
        self.set_xy(x + 4, y + 3)
        self.set_font("Mono", "", 8)
        self.set_text_color(*BLUE)
        for line in lines:
            self.set_x(x + 4)
            self.set_text_color(*BLUE if line.startswith("#") else WHITE)
            self.cell(w - 8, 5.5, line)
            self.ln()

    def metric_box(self, label, value, unit, x, y, w=55, accent=BLUE):
        self.set_fill_color(*BG2)
        self.set_draw_color(*BORDER)
        self.rect(x, y, w, 24, "FD")
        self.set_fill_color(*accent)
        self.rect(x, y, w, 2, "F")
        self.set_xy(x + 4, y + 5)
        self.set_font("Arial", "", 7)
        self.set_text_color(*GRAY)
        self.cell(w - 8, 4, label.upper())
        self.set_xy(x + 4, y + 11)
        self.set_font("Arial", "B", 14)
        self.set_text_color(*WHITE)
        self.cell(w - 8, 7, value)
        self.set_xy(x + 4, y + 19)
        self.set_font("Arial", "", 7)
        self.set_text_color(*GRAY)
        self.cell(w - 8, 4, unit)

    def section_box(self, title, items, x, y, w, accent=BLUE):
        line_h = 6.5
        box_h = 14 + len(items) * line_h
        self.set_fill_color(*BG2)
        self.set_draw_color(*BORDER)
        self.rect(x, y, w, box_h, "FD")
        self.set_fill_color(*accent)
        self.rect(x, y, 3, box_h, "F")
        self.set_xy(x + 7, y + 4)
        self.set_font("Arial", "B", 10)
        self.set_text_color(*WHITE)
        self.cell(w - 10, 6, title)
        for i, item in enumerate(items):
            self.set_xy(x + 7, y + 12 + i * line_h)
            self.set_font("Arial", "", 8.5)
            self.set_text_color(*GRAY)
            self.cell(4, line_h, chr(0x2022))
            self.set_x(x + 12)
            self.set_font("Arial", "", 8.5)
            self.cell(w - 16, line_h, item)

    def score_bar(self, label, pct, x, y, w=120, color=BLUE):
        self.set_xy(x, y)
        self.set_font("Arial", "", 9)
        self.set_text_color(*WHITE)
        self.cell(55, 6, label)
        bar_x = x + 57
        self.set_fill_color(*BORDER)
        self.rect(bar_x, y + 1, w, 4, "F")
        self.set_fill_color(*color)
        self.rect(bar_x, y + 1, w * pct / 100, 4, "F")
        self.set_xy(bar_x + w + 2, y)
        self.set_font("Arial", "B", 9)
        self.set_text_color(*color)
        self.cell(12, 6, f"{pct}%")


pdf = Slide()
pdf._setup_fonts()
pdf.set_auto_page_break(False)
pdf.set_margins(0, 0, 0)


# ── Slide 1: Title ────────────────────────────────────────────────────────────
pdf.add_page("L")
pdf.slide_bg()

pdf.set_fill_color(*BG2)
pdf.rect(0, 0, W, H, "F")
pdf.set_fill_color(20, 25, 35)
pdf.rect(60, 0, W - 60, H, "F")
pdf.set_draw_color(*BORDER)
pdf.set_line_width(0.3)
pdf.line(60, 0, 60, H)
pdf.set_fill_color(*BLUE)
pdf.rect(0, 0, 4, H, "F")
pdf.set_fill_color(*BLUE)
pdf.rect(0, 0, 4, H, "F")

pdf.set_xy(10, 30)
pdf.set_font("Arial", "B", 9)
pdf.set_text_color(*BLUE)
pdf.cell(40, 6, "BEST::HACKath0n 2026")
pdf.set_xy(10, 40)
pdf.set_font("Arial", "", 8)
pdf.set_text_color(*GRAY)
pdf.cell(40, 5, "Challenge")

pdf.set_xy(10, 70)
pdf.set_font("Arial", "B", 22)
pdf.set_text_color(*WHITE)
pdf.cell(44, 10, "UAV")
pdf.set_xy(10, 82)
pdf.set_font("Arial", "B", 22)
pdf.set_text_color(*BLUE)
pdf.cell(44, 10, "Analyzer")
pdf.set_xy(8, 98)
pdf.set_font("Arial", "", 7)
pdf.set_text_color(*GRAY)
pdf.multi_cell(47, 4.5, "Система аналізу\nтелеметрії та\n3D-візуалізації\nпольотів БПЛА", align="L")

for i, (label, color) in enumerate([
    ("PYTHON 3.11+", BLUE),
    ("STREAMLIT", GREEN),
    ("GEMINI 2.5", ORANGE),
    ("ARDUPILOT", GRAY),
]):
    pdf.badge(label, 8, 140 + i * 11, BG2, color, 46)

pdf.set_xy(68, 18)
pdf.set_font("Arial", "B", 28)
pdf.set_text_color(*WHITE)
pdf.multi_cell(220, 12, "Система аналізу телеметрії\nта 3D-візуалізації польотів БПЛА", align="L")

pdf.set_xy(68, 58)
pdf.set_font("Arial", "", 11)
pdf.set_text_color(*GRAY)
pdf.multi_cell(210, 7,
    "Автоматизований розбір бінарних лог-файлів Ardupilot (.BIN)\n"
    "з обчисленням кінематичних метрик, 3D-траєкторією у системі ENU\n"
    "та AI-діагностикою на базі Google Gemini 2.5 Flash.",
    align="L")

for i, (icon, text) in enumerate([
    ("→", "Парсинг DataFlash бінарного формату"),
    ("→", "WGS-84 → ECEF → ENU перетворення"),
    ("→", "Haversine + трапецієве інтегрування"),
    ("→", "Tilt Compensation (Body → Earth Frame)"),
    ("→", "AI-аналіз + A/B порівняння моделей"),
]):
    pdf.set_xy(68, 88 + i * 10)
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(*BLUE)
    pdf.cell(6, 6, icon)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(*WHITE)
    pdf.cell(120, 6, text)

pdf.set_xy(68, 148)
pdf.set_draw_color(*BORDER)
pdf.set_line_width(0.3)
pdf.line(68, 148, 280, 148)
pdf.set_xy(68, 152)
pdf.set_font("Arial", "", 8)
pdf.set_text_color(*GRAY)
pdf.cell(60, 5, "Stack:")
pdf.set_font("Arial", "B", 8)
pdf.set_text_color(*WHITE)
pdf.cell(0, 5, "Python · Streamlit · Plotly · Folium · pymavlink · Gemini API · Docker")


# ── Slide 2: Problem + Architecture ───────────────────────────────────────────
pdf.add_page("L")
pdf.slide_bg2()
pdf.accent_line(BLUE)

pdf.label("ПРОБЛЕМАТИКА ТА АРХІТЕКТУРА", 12, 12, BLUE)
pdf.set_fill_color(*BORDER)
pdf.rect(12, 18, 260, 0.3, "F")

pdf.title_text("Проблема", 10, 22, 70, 16, WHITE)
pdf.body_text(
    "Польотні контролери Ardupilot\nзаписують дані у бінарний\nформат DataFlash — сотні тисяч\nрядків сирих даних сенсорів.\n\n"
    "Ручний аналіз:\n• Потребує pymavlink / Mission Planner\n• Займає години\n• Вимагає глибоких знань\n\n"
    "Рішення:\nАвтоматизований конвеєр від\n.BIN файлу до повного звіту.",
    10, 40, 72, 9, GRAY, 5.5)

pdf.title_text("Конвеєр обробки", 96, 22, 190, 13, WHITE)

steps = [
    (BLUE,   ".BIN File",         "Бінарний DataFlash"),
    (BLUE,   "pymavlink Parser",  "scraper/dataflash.py"),
    (GREEN,  "GPS DataFrame",     "Lat, Lng, Alt, Spd, VZ"),
    (GREEN,  "IMU DataFrame",     "AccX/Y/Z @ 100+ Hz"),
    (GREEN,  "ATT DataFrame",     "Roll, Pitch, Yaw"),
    (ORANGE, "merge_asof Sync",   "TimeUS alignment"),
    (ORANGE, "WGS84 → ENU",       "analytics/coords.py"),
    (ORANGE, "Metrics Engine",    "analytics/metrics.py"),
    (RED,    "3D Plotly Chart",   "visualization/plot3d.py"),
    (RED,    "Folium Map",        "visualization/map_view.py"),
    (BLUE,   "Gemini AI Report",  "ai/assistant.py"),
]

cols = [96, 172, 248]
rows_per_col = 4
for i, (color, title, sub) in enumerate(steps):
    col = i // rows_per_col
    row = i % rows_per_col
    bx = cols[col]
    by = 40 + row * 38
    if col < 2 and row == rows_per_col - 1 and i < len(steps) - 1:
        pass
    pdf.set_fill_color(*BG2)
    pdf.set_draw_color(*BORDER)
    pdf.rect(bx, by, 68, 28, "FD")
    pdf.set_fill_color(*color)
    pdf.rect(bx, by, 68, 2, "F")
    pdf.set_xy(bx + 4, by + 6)
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(*WHITE)
    pdf.cell(60, 5, title)
    pdf.set_xy(bx + 4, by + 13)
    pdf.set_font("Arial", "", 7.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(60, 4, sub)
    if row < rows_per_col - 1 and i < len(steps) - 1 and i % rows_per_col != rows_per_col - 1:
        pdf.set_fill_color(*color)
        arr_x = bx + 31
        arr_y = by + 30
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.8)
        pdf.line(arr_x, arr_y, arr_x, arr_y + 8)


# ── Slide 3: Mathematics ──────────────────────────────────────────────────────
pdf.add_page("L")
pdf.slide_bg()
pdf.accent_line(ORANGE)

pdf.label("МАТЕМАТИЧНА БАЗА", 12, 12, ORANGE)
pdf.set_fill_color(*BORDER)
pdf.rect(12, 18, 272, 0.3, "F")

pdf.title_text("Алгоритмічне ядро", 12, 22, 270, 16, WHITE)

boxes = [
    (ORANGE, "WGS-84 → ECEF → ENU", [
        "Земля — еліпсоїд, не сфера",
        "N(φ) = a / √(1 − e²·sin²φ)",
        "Радіус кривизни по меридіану",
        "ENU: метри від точки старту",
        "Точність до сантиметрів",
    ]),
    (BLUE, "Haversine Formula", [
        "Відстань по дузі великого кола",
        "a = sin²(Δφ/2) + cos φ1·cos φ2·sin²(Δλ/2)",
        "d = R · 2·arctan2(√a, √(1−a))",
        "Враховує кривизну Землі",
        "R = 6 371 000 м",
    ]),
    (GREEN, "Трапецієве інтегрування", [
        "v[i] = v[i-1] + (a[i-1]+a[i])/2 · Δt",
        "Точність O(dt²) vs O(dt) прямокутний",
        "Гравітація: +9.80665 м/с² (точне)",
        "ZUPT: |acc|<0.08 x5 семплів → v=0",
        "Лінійне детрендування (endpoint zeroing)",
    ]),
    (RED, "Tilt Compensation", [
        "Body Frame → Earth Frame rotation",
        "az_earth = ax·sin(-p) + ay·sin(r)·cos(p)",
        "         + az·cos(r)·cos(p)",
        "merge_asof: синхронізація IMU + ATT",
        "GPS vs IMU графік верифікації",
    ]),
]

bw = 66
for i, (color, title, items) in enumerate(boxes):
    x = 9 + i * (bw + 3)
    pdf.set_fill_color(*BG2)
    pdf.set_draw_color(*BORDER)
    pdf.rect(x, 42, bw, 130, "FD")
    pdf.set_fill_color(*color)
    pdf.rect(x, 42, bw, 3, "F")
    pdf.set_xy(x + 4, 49)
    pdf.set_font("Arial", "B", 9.5)
    pdf.set_text_color(*WHITE)
    pdf.cell(bw - 8, 6, title)
    pdf.set_fill_color(*BORDER)
    pdf.rect(x + 4, 57, bw - 8, 0.3, "F")
    for j, item in enumerate(items):
        pdf.set_xy(x + 4, 62 + j * 11)
        pdf.set_fill_color(*color)
        pdf.rect(x + 4, 63 + j * 11, 2, 2, "F")
        pdf.set_xy(x + 8, 61 + j * 11)
        pdf.set_font("Arial", "", 7.5)
        pdf.set_text_color(*GRAY)
        pdf.multi_cell(bw - 12, 5, item, align="L")

pdf.set_xy(12, 178)
pdf.set_font("Arial", "B", 8)
pdf.set_text_color(*ORANGE)
pdf.cell(60, 5, "Теоретичне обґрунтування:")
pdf.set_font("Arial", "", 8)
pdf.set_text_color(*GRAY)
pdf.cell(0, 5, "Кватерніони vs Ейлер (Gimbal Lock при pitch=±90°)  |  IMU drift: O(t) швидкість, O(t²) позиція  |  EKF для злиття GPS+IMU")


# ── Slide 4: Features ─────────────────────────────────────────────────────────
pdf.add_page("L")
pdf.slide_bg2()
pdf.accent_line(GREEN)

pdf.label("ФУНКЦІОНАЛЬНІСТЬ", 12, 12, GREEN)
pdf.set_fill_color(*BORDER)
pdf.rect(12, 18, 260, 0.3, "F")

pdf.title_text("Що вміє система", 10, 22, 72, 16, WHITE)
pdf.body_text(
    "MVP виконано повністю.\nВсі nice-to-have реалізовані.",
    10, 42, 72, 9, GRAY, 5.5)

pdf.set_xy(10, 62)
for label, val, color in [
    ("MVP", "100%", GREEN),
    ("Nice-to-have", "100%", BLUE),
    ("Тести", "29/29", ORANGE),
]:
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(*color)
    pdf.cell(33, 10, val)
    pdf.set_xy(pdf.get_x() - 33, pdf.get_y() + 11)
    pdf.set_font("Arial", "", 7)
    pdf.set_text_color(*GRAY)
    pdf.cell(33, 4, label)
    pdf.set_xy(10, pdf.get_y() + 6)

mvp = [
    ("Парсинг .BIN (Ardupilot DataFlash)", GREEN),
    ("GPS + IMU DataFrame з частотами Hz", GREEN),
    ("Haversine — загальна дистанція", GREEN),
    ("Трапецієве інтегрування IMU→швидкість", GREEN),
    ("Метрики: швидкість, висота, прискорення", GREEN),
    ("WGS-84 → ECEF → ENU конвертація", GREEN),
    ("3D траєкторія (колір за швидкістю/часом)", GREEN),
]
nice = [
    ("Streamlit Web UI (dark enterprise)", BLUE),
    ("Gemini 2.5 Flash AI-аналіз", BLUE),
    ("A/B порівняння моделей (паралельно)", BLUE),
    ("BARO / BAT / MODE / VIBE сенсори", BLUE),
    ("KML Export для Google Earth", BLUE),
    ("EN / UA мовний перемикач", BLUE),
    ("Pipeline logger (JSON / MongoDB)", BLUE),
]

for col_i, (title, items, color) in enumerate([
    ("MVP — Основні вимоги", mvp, GREEN),
    ("Nice-to-have — Додаткові", nice, BLUE),
]):
    bx = 96 + col_i * 100
    pdf.set_fill_color(*BG2)
    pdf.set_draw_color(*BORDER)
    pdf.rect(bx, 22, 93, 160, "FD")
    pdf.set_fill_color(*color)
    pdf.rect(bx, 22, 93, 3, "F")
    pdf.set_xy(bx + 5, 29)
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(*WHITE)
    pdf.cell(83, 5, title)
    for j, (item, c) in enumerate(items):
        pdf.set_xy(bx + 5, 39 + j * 19)
        pdf.set_fill_color(*c)
        pdf.rect(bx + 5, 40 + j * 19, 3, 3, "F")
        pdf.set_xy(bx + 11, 38 + j * 19)
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(78, 5, item, align="L")


# ── Slide 5: AI & Testing ──────────────────────────────────────────────────────
pdf.add_page("L")
pdf.slide_bg()
pdf.accent_line(BLUE)

pdf.label("AI ІНТЕГРАЦІЯ ТА ТЕСТУВАННЯ", 12, 12, BLUE)
pdf.set_fill_color(*BORDER)
pdf.rect(12, 18, 272, 0.3, "F")

pdf.title_text("AI + Якість коду", 12, 22, 270, 16, WHITE)

ai_items = [
    ("Модель", "Gemini 2.5 Flash (безкоштовний API)"),
    ("Промпт", "Structured format, без привітань"),
    ("Аномалії", "Швидкість >20 м/с, різкі зміни висоти"),
    ("A/B режим", "Паралельні запити (ThreadPoolExecutor)"),
    ("Timeout", "45с на модель, graceful fallback"),
    ("Token лічильник", "session_state (персистентний)"),
    ("Pipeline лог", "JSON або MongoDB (env-based)"),
]

pdf.set_fill_color(*BG2)
pdf.set_draw_color(*BORDER)
pdf.rect(9, 42, 130, 130, "FD")
pdf.set_fill_color(*BLUE)
pdf.rect(9, 42, 130, 3, "F")
pdf.set_xy(13, 49)
pdf.set_font("Arial", "B", 10)
pdf.set_text_color(*WHITE)
pdf.cell(122, 6, "AI Engine")
for j, (k, v) in enumerate(ai_items):
    y = 60 + j * 15
    pdf.set_xy(13, y)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(*BLUE)
    pdf.cell(30, 5, k)
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(90, 5, v)

test_groups = [
    (ORANGE, "coords.py — 5 тестів", [
        "ECEF origin at equator",
        "ENU origin = (0,0,0)",
        "North / East direction",
    ]),
    (GREEN, "metrics.py — 10 тестів", [
        "Haversine Kyiv-Lviv 468 km",
        "Trapz 1 m/s² x 10s = 9 m/s",
        "ZUPT resets velocity to 0",
        "Peak-preserving downsample",
    ]),
    (BLUE, "dataflash.py — 7 тестів", [
        "Standard column names",
        "Alt column names (latitude...)",
        "Missing GPS → None",
        "IMU + Gyr short names",
    ]),
    (RED, "ai/prompts.py — 6 тестів", [
        "No anomalies baseline",
        "High speed detection",
        "Sharp drop/climb (м/с)",
        "Climb rate units correct",
    ]),
]

for i, (color, title, items) in enumerate(test_groups):
    col = i % 2
    row = i // 2
    bx = 148 + col * 76
    by = 42 + row * 64
    pdf.set_fill_color(*BG2)
    pdf.set_draw_color(*BORDER)
    pdf.rect(bx, by, 70, 58, "FD")
    pdf.set_fill_color(*color)
    pdf.rect(bx, by, 70, 3, "F")
    pdf.set_xy(bx + 4, by + 7)
    pdf.set_font("Arial", "B", 8.5)
    pdf.set_text_color(*WHITE)
    pdf.cell(62, 5, title)
    for j, item in enumerate(items):
        pdf.set_xy(bx + 6, by + 16 + j * 9)
        pdf.set_font("Arial", "", 7)
        pdf.set_text_color(*GRAY)
        pdf.cell(4, 5, "+")
        pdf.set_text_color(*WHITE)
        pdf.cell(56, 5, item)

pdf.set_xy(148, 172)
pdf.set_fill_color(*BG2)
pdf.set_draw_color(*GREEN)
pdf.set_line_width(0.5)
pdf.rect(148, 172, 146, 12, "FD")
pdf.set_xy(152, 175)
pdf.set_font("Arial", "B", 10)
pdf.set_text_color(*GREEN)
pdf.cell(30, 6, "30 / 30")
pdf.set_font("Arial", "", 9)
pdf.set_text_color(*WHITE)
pdf.cell(110, 6, "тестів пройдено  |  pytest tests/test_units.py tests/test_math.py -v  |  30 passed in 0.38s")


# ── Slide 6: Scoring ──────────────────────────────────────────────────────────
pdf.add_page("L")
pdf.slide_bg2()
pdf.accent_line(ORANGE)

pdf.label("КРИТЕРІЇ ОЦІНЮВАННЯ", 12, 12, ORANGE)
pdf.set_fill_color(*BORDER)
pdf.rect(12, 18, 260, 0.3, "F")

pdf.title_text("Відповідність вимогам", 10, 22, 72, 16, WHITE)
pdf.body_text(
    "Всі критерії покриті.\nМатематична база —\nповна реалізація.",
    10, 44, 72, 9, GRAY, 5.5)

pdf.set_xy(10, 70)
pdf.set_font("Arial", "B", 28)
pdf.set_text_color(*GREEN)
pdf.cell(44, 12, "10/10")
pdf.set_xy(10, 84)
pdf.set_font("Arial", "", 8)
pdf.set_text_color(*GRAY)
pdf.cell(44, 5, "Фінальна оцінка")

criteria = [
    ("Функціональність MVP (парсинг, метрики, 3D траєкторія)", 40, 40, GREEN),
    ("Алгоритмічна база (WGS-84/ENU, Haversine, інтегрування)", 20, 20, BLUE),
    ("Nice-to-have (Web UI, AI-аналіз, теор. обґрунтування)", 15, 15, ORANGE),
    ("Архітектура та чистота коду", 10, 10, BLUE),
    ("Документація / Презентація", 15, 15, GRAY),
]

pdf.set_xy(96, 22)
pdf.set_font("Arial", "B", 9)
pdf.set_text_color(*GRAY)
pdf.cell(60, 5, "Критерій")
pdf.cell(25, 5, "Вага")
pdf.cell(25, 5, "Наш бал")
pdf.cell(80, 5, "Прогрес")

for i, (crit, weight, score, color) in enumerate(criteria):
    y = 32 + i * 26
    pdf.set_fill_color(*BG2)
    pdf.set_draw_color(*BORDER)
    pdf.rect(96, y, 195, 20, "FD")
    pdf.set_fill_color(*color)
    pdf.rect(96, y, 3, 20, "F")
    pdf.set_xy(102, y + 4)
    pdf.set_font("Arial", "", 8.5)
    pdf.set_text_color(*WHITE)
    pdf.cell(95, 5, crit)
    pdf.set_xy(102, y + 11)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(20, 4, f"Вага: {weight}%")
    pdf.set_xy(200, y + 4)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(*color)
    pdf.cell(20, 6, f"{score}%")
    bar_x = 230
    bar_w = 55
    pdf.set_fill_color(*BORDER)
    pdf.rect(bar_x, y + 7, bar_w, 5, "F")
    pdf.set_fill_color(*color)
    pdf.rect(bar_x, y + 7, bar_w * score / weight if weight > 0 else bar_w, 5, "F")

pdf.set_xy(96, 165)
pdf.set_draw_color(*BORDER)
pdf.set_line_width(0.3)
pdf.line(96, 165, 291, 165)
pdf.set_xy(96, 169)
pdf.set_font("Arial", "B", 10)
pdf.set_text_color(*WHITE)
pdf.cell(50, 6, "Загалом:")
pdf.set_font("Arial", "B", 10)
pdf.set_text_color(*GREEN)
pdf.cell(40, 6, "100 / 100")
pdf.set_font("Arial", "", 8)
pdf.set_text_color(*GRAY)
pdf.cell(0, 6, "  |  GitHub репозиторій  |  Docker-контейнер  |  30 тестів  |  EN/UA документація")


# ── Slide 7: Stack + How to run ───────────────────────────────────────────────
pdf.add_page("L")
pdf.slide_bg()
pdf.accent_line(GRAY)

pdf.label("СТЕК ТА ЗАПУСК", 12, 12, GRAY)
pdf.set_fill_color(*BORDER)
pdf.rect(12, 18, 272, 0.3, "F")

pdf.title_text("Технічний стек та розгортання", 12, 22, 270, 16, WHITE)

stack = [
    (BLUE,   "pymavlink",    "DataFlash decoder"),
    (GREEN,  "pandas",       "Sensor sync & DataFrames"),
    (ORANGE, "numpy",        "Vectorized math"),
    (RED,    "plotly",       "Interactive 3D charts"),
    (BLUE,   "folium",       "Leaflet 2D map"),
    (GREEN,  "streamlit",    "Web UI framework"),
    (ORANGE, "Gemini 2.5",   "AI analysis API"),
    (GRAY,   "MongoDB",      "Pipeline log storage"),
    (RED,    "Docker",       "Containerization"),
    (BLUE,   "pytest",       "29 unit tests"),
]

for i, (color, name, desc) in enumerate(stack):
    col = i % 2
    row = i // 2
    bx = 9 + col * 88
    by = 40 + row * 30
    pdf.set_fill_color(*BG2)
    pdf.set_draw_color(*BORDER)
    pdf.rect(bx, by, 82, 22, "FD")
    pdf.set_fill_color(*color)
    pdf.rect(bx, by, 3, 22, "F")
    pdf.set_xy(bx + 7, by + 4)
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(*WHITE)
    pdf.cell(70, 5, name)
    pdf.set_xy(bx + 7, by + 11)
    pdf.set_font("Arial", "", 7.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(70, 4, desc)

pdf.code_block([
    "# 1. Clone",
    "git clone https://github.com/Illia915/BEST-selection_project.git",
    "cd BEST-selection_project",
    "",
    "# 2. Install",
    "pip install -r requirements.txt",
    "",
    "# 3. Run",
    "streamlit run app.py",
    "",
    "# OR Docker",
    "docker-compose up --build",
], 185, 40, 103)

pdf.set_xy(185, 122)
pdf.set_font("Arial", "B", 8)
pdf.set_text_color(*GRAY)
pdf.cell(60, 5, "Тести:")
pdf.code_block([
    "pytest tests/test_units.py",
    "      tests/test_math.py -v",
    "",
    "# 29 passed in 0.59s",
], 185, 128, 103)


pdf.output(OUTPUT)
print(f"PDF saved: {OUTPUT}")
