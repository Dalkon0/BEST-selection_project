from fpdf import FPDF
from datetime import datetime
import os

class FlightReport(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unicode_font = None
        self._setup_fonts()
        
    def _setup_fonts(self):
        # Try to find DejaVu (standard in Linux with packages.txt)
        font_paths = [
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ("/usr/share/fonts/TTF/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
        ]
        
        for reg, bold in font_paths:
            if os.path.exists(reg):
                try:
                    self.add_font("DejaVu", "", reg)
                    self.unicode_font = "DejaVu"
                    if os.path.exists(bold):
                        self.add_font("DejaVu", "B", bold)
                    break
                except Exception:
                    continue

    def set_safe_font(self, style="", size=10):
        if self.unicode_font:
            # If we have DejaVu but didn't find the Bold file, fallback to regular
            try:
                self.set_font("DejaVu", style, size)
            except Exception:
                self.set_font("DejaVu", "", size)
        else:
            self.set_font("Arial", style, size)

    def header(self):
        self.set_fill_color(15, 17, 23)
        self.rect(0, 0, 210, 40, "F")
        self.set_xy(10, 15)
        self.set_safe_font("B", 24)
        self.set_text_color(230, 237, 243)
        self.cell(0, 10, "UAV FLIGHT REPORT", align="L")
        self.set_xy(10, 25)
        self.set_safe_font("", 10)
        self.set_text_color(139, 148, 158)
        self.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align="L")
        self.ln(25)

    def footer(self):
        self.set_y(-15)
        self.set_safe_font("I", 8)
        self.set_text_color(139, 148, 158)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def transliterate(text):
    ua_map = {
        'а':'a', 'б':'b', 'в':'v', 'г':'h', 'ґ':'g', 'д':'d', 'е':'e', 'є':'ye', 'ж':'zh', 'з':'z', 'и':'y', 
        'і':'i', 'ї':'yi', 'й':'y', 'к':'k', 'л':'l', 'м':'m', 'н':'n', 'о':'o', 'п':'p', 'р':'r', 'с':'s', 
        'т':'t', 'у':'u', 'ф':'f', 'х':'kh', 'ц':'ts', 'ч':'ch', 'ш':'sh', 'щ':'shch', 'ь':'', 'ю':'yu', 'я':'ya',
        'А':'A', 'Б':'B', 'В':'V', 'Г':'H', 'Ґ':'G', 'Д':'D', 'Е':'E', 'Є':'Ye', 'Ж':'Zh', 'З':'Z', 'И':'Y', 
        'І':'I', 'Ї':'Yi', 'Й':'Y', 'К':'K', 'Л':'L', 'М':'M', 'Н':'N', 'О':'O', 'П':'P', 'Р':'R', 'С':'S', 
        'Т':'T', 'У':'U', 'Ф':'F', 'Х':'Kh', 'Ц':'Ts', 'Ч':'Ch', 'Ш':'Sh', 'Щ':'Shch', 'Ь':'', 'Ю':'Yu', 'Я':'Ya'
    }
    for k, v in ua_map.items():
        text = text.replace(k, v)
    return text

def generate_pdf_report(filename, metrics, ai_report):
    pdf = FlightReport()
    pdf.add_page()
    
    # Summary Section
    pdf.set_safe_font("B", 16)
    pdf.set_text_color(88, 166, 255)
    pdf.cell(0, 10, f"Flight: {filename}", ln=True)
    pdf.ln(5)
    
    # Metrics Table
    pdf.set_safe_font("B", 12)
    pdf.set_text_color(230, 237, 243)
    pdf.set_fill_color(22, 27, 34)
    pdf.cell(190, 10, "Flight Metrics", ln=True, fill=True, align='C')
    pdf.ln(2)
    
    metric_labels = {
        'total_distance_m': ('Total Distance', 'm'),
        'total_duration_s': ('Flight Duration', 's'),
        'max_horiz_speed_ms': ('Max Horiz Speed', 'm/s'),
        'max_vert_speed_ms': ('Max Vert Speed', 'm/s'),
        'max_alt_m': ('Max Altitude', 'm'),
        'max_acceleration': ('Max Acceleration', 'm/s2'),
        'imu_max_vz_ms': ('IMU Max Vertical Speed', 'm/s'),
        'max_vibration': ('Max Vibration', 'm/s2'),
    }
    
    pdf.set_text_color(0, 0, 0)
    for key, (label, unit) in metric_labels.items():
        val = metrics.get(key)
        if val is not None:
            pdf.set_safe_font("B", 10)
            pdf.cell(80, 8, f"{label}:", border=0)
            pdf.set_safe_font("", 10)
            pdf.cell(110, 8, f"{val:.1f} {unit}", border=0, ln=True)
            
    pdf.ln(10)
    
    # AI Report Section
    pdf.set_safe_font("B", 16)
    pdf.set_text_color(88, 166, 255)
    pdf.cell(0, 10, "AI Analysis Report", ln=True)
    pdf.ln(2)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_safe_font("", 10)
    
    clean_report = ai_report.replace('```markdown', '').replace('```', '').strip()
    
    if not pdf.unicode_font:
        clean_report = transliterate(clean_report)
    
    try:
        pdf.multi_cell(0, 6, clean_report)
    except Exception:
        pdf.multi_cell(0, 6, transliterate(clean_report).encode('ascii', 'ignore').decode('ascii'))
    
    return bytes(pdf.output())
