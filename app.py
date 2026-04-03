import streamlit as st
import os
from scraper.dataflash import parse_log, get_gps_dataframe, get_imu_dataframe, get_attitude_dataframe, get_vibe_dataframe, get_baro_dataframe, get_battery_dataframe, get_mode_dataframe
from analytics.metrics import compute_metrics, compare_metrics, compute_sampling_rate, filter_gps
from analytics.coords import gps_to_enu
from visualization.plot3d import build_3d_track, build_3d_track_animation, build_comparison_3d, build_comparison_3d_animation, build_altitude_chart, build_speed_comparison_chart, build_attitude_tracking_chart, build_vibration_chart, build_baro_vs_gps_chart, build_battery_chart, build_cockpit
from visualization.map_view import build_map, generate_kml
from analytics.pdf_report import generate_pdf_report
from ai.assistant import analyze_flight, analyze_flight_ab, AVAILABLE_MODELS, DEFAULT_MODEL
from i18n import t
from ui.components import render_metrics_grid, render_compare_table, render_landing

st.set_page_config(page_title='UAV Telemetry Analyzer', page_icon='🛸', layout='wide')

st.markdown(f"""
<style>
    .stApp {{ background-color: #0f1117; color: #e0e0e0; }}
    [data-testid="stHeader"] {{ background: rgba(0,0,0,0); height: 0px; }}
    .stMainBlockContainer {{ padding-top: 1rem !important; padding-bottom: 1rem !important; }}
    section[data-testid="stSidebar"] {{ background-color: #161b22; border-right: 1px solid #21262d; }}
    [data-testid="stSidebarContent"] {{ padding-top: 0rem !important; }}
    [data-testid="stMetric"] {{ background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px 16px; }}
    [data-testid="stMetricValue"] {{ color: #ffffff; font-weight: 700; font-size: 24px; }}
    [data-testid="stMetricLabel"] {{ color: #ffffff; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; }}
    .section-label {{ color: #8b949e; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; margin-top: 24px; }}
    .status-badge {{ display: flex; align-items:center; gap: 6px; background: rgba(35, 134, 54, 0.15); color: #3fb950; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(63, 185, 80, 0.3); }}
    .status-dot {{ width: 6px; height: 6px; background: #3fb950; border-radius: 50%; box-shadow: 0 0 8px #3fb950; }}
    .ai-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 16px; }}
    .feature-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }}
    .feature-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 24px; transition: all 0.3s ease; }}
    .feature-card:hover {{ border-color: #58a6ff; background: #1c2128; transform: translateY(-4px); }}
    .feature-card-title {{ color: #ffffff; font-size: 18px; font-weight: 600; margin-bottom: 10px; }}
    .feature-card-desc {{ color: #8b949e; font-size: 14px; line-height: 1.6; }}
    .category-label {{ font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px; }}
    
    /* LANGUAGE TOGGLE — neutral colors, full-zone clickable */
    div[data-testid="stCheckbox"],
    div[data-testid="stToggleSwitch"] {{
        width: 100%;
    }}
    div[data-testid="stCheckbox"] label,
    div[data-testid="stToggleSwitch"] label {{
        width: 100%;
        display: block;
        margin: 0;
        padding: 8px 10px;
        cursor: pointer;
        border-radius: 6px;
    }}
    div[data-testid="stCheckbox"] label:hover,
    div[data-testid="stToggleSwitch"] label:hover {{
        background: rgba(255,255,255,0.04);
    }}
    div[role="switch"] {{
        box-shadow: none !important;
        outline: none !important;
    }}
    div[role="switch"][aria-checked="false"] {{
        background-color: #21262d !important;
        border-color: #30363d !important;
        box-shadow: none !important;
    }}
    div[role="switch"][aria-checked="true"] {{
        background-color: #484f58 !important;
        border-color: #484f58 !important;
        box-shadow: none !important;
    }}
    div[role="switch"]:focus, div[role="switch"]:active {{
        box-shadow: none !important;
        outline: none !important;
        border-color: rgba(255,255,255,0.15) !important;
    }}
    /* Adjusting column behavior */
    div[data-testid="column"] {{
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    /* ALL BUTTONS — sky blue instead of red */
    button[kind="primary"], [data-testid="stBaseButton-primary"] {{
        background-color: #58a6ff !important;
        border-color: #58a6ff !important;
        color: #0f1117 !important;
    }}
    button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {{
        background-color: #79baff !important;
        border-color: #79baff !important;
        color: #0f1117 !important;
    }}
    button[kind="primary"]:active, [data-testid="stBaseButton-primary"]:active,
    button[kind="primary"]:focus, [data-testid="stBaseButton-primary"]:focus {{
        background-color: #388bfd !important;
        border-color: #388bfd !important;
        color: #0f1117 !important;
        box-shadow: none !important;
        outline: none !important;
    }}
    button[kind="secondary"], [data-testid="stBaseButton-secondary"] {{
        border-color: #30363d !important;
        color: #8b949e !important;
        background-color: transparent !important;
    }}
    button[kind="secondary"]:hover, [data-testid="stBaseButton-secondary"]:hover {{
        border-color: #58a6ff !important;
        color: #58a6ff !important;
        background-color: rgba(88,166,255,0.08) !important;
    }}
    [data-testid="stDownloadButton"] button,
    [data-testid="stBaseButton-downloadButton"] {{
        border-color: #30363d !important;
        color: #8b949e !important;
        background-color: transparent !important;
    }}
    [data-testid="stDownloadButton"] button:hover,
    [data-testid="stBaseButton-downloadButton"]:hover {{
        border-color: #58a6ff !important;
        color: #58a6ff !important;
        background-color: rgba(88,166,255,0.08) !important;
    }}
    /* Drop zone */
    [data-testid="stFileUploaderDropzone"] {{
        border: 2px dashed #30363d !important;
        border-radius: 12px !important;
        background: rgba(22,27,34,0.6) !important;
        transition: border-color 0.2s ease, background 0.2s ease !important;
        padding: 48px 24px !important;
    }}
    [data-testid="stFileUploaderDropzone"]:hover {{
        border-color: #58a6ff !important;
        background: rgba(88,166,255,0.04) !important;
    }}
    [data-testid="stFileUploaderDropzoneInstructions"] div span {{
        color: #8b949e !important;
        font-size: 14px !important;
    }}
    [data-testid="stFileUploaderDropzoneInstructions"] small {{
        color: #484f58 !important;
    }}
    [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {{
        border-color: #58a6ff !important;
        color: #58a6ff !important;
    }}
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div style="text-align: center; padding: 0 0 10px 0; margin-top: -50px;">
    <h2 style="color: #58a6ff; margin-bottom: 0; font-size: 20px;">UAV ANALYZER</h2>
    <p style="color: #ffffff; font-size: 10px; text-transform: uppercase; letter-spacing: 2px;">Professional Suite</p>
    <div style="height: 1px; background: linear-gradient(90deg, transparent, #21262d, transparent); margin-top: 10px;"></div>
</div>
""", unsafe_allow_html=True)

head_col1, head_col2 = st.columns([10, 2])
with head_col2:
    # Use a clear indicator for the toggle
    is_en = st.toggle("EN", value=False)
    lang = "en" if is_en else "uk"

with head_col1:
    st.markdown(f"""
    <div style="display:flex; align-items:center; justify-content:space-between; padding: 0px 0 10px; border-bottom: 1px solid #21262d; margin-bottom: 16px; margin-top: -10px;">
        <div>
            <h1 style="font-size: 24px; font-weight: 700; margin:0; color: #e6edf3;">{t('page_title', lang)}</h1>
            <p style="font-size: 13px; color: #8b949e; margin: 4px 0 0;">{t('app_subtitle', lang)}</p>
        </div>
        <div class="status-badge"><div class="status-dot"></div>{t('status_online', lang)}</div>
    </div>
    """, unsafe_allow_html=True)

main_files = st.session_state.get('main_upload_files', [])
compare_mode = len(main_files) >= 2
demo_path = st.session_state.get('demo_path')
if not main_files and not demo_path:
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if os.path.exists(data_dir):
        bin_files = [f for f in os.listdir(data_dir) if f.endswith('.BIN')]
        if bin_files:
            st.sidebar.markdown(f'<div class="section-label" style="margin-top:12px">{t("sidebar_sample_logs", lang)}</div>', unsafe_allow_html=True)
            chosen = st.sidebar.selectbox('', bin_files, label_visibility='collapsed')
            if st.sidebar.button(t('sidebar_load_sample', lang), use_container_width=True):
                st.session_state['demo_path'] = os.path.join(data_dir, chosen)
                demo_path = st.session_state['demo_path']

st.sidebar.markdown(f'<div class="section-label" style="margin-top:16px">{t("sidebar_visualization", lang)}</div>', unsafe_allow_html=True)
color_by = st.sidebar.radio(t('sidebar_color_label', lang), ['speed', 'time', 'mode'], format_func=lambda x: t(f'sidebar_color_{x}', lang), label_visibility='collapsed')
show_anoms = st.sidebar.toggle(t('sidebar_show_anomalies', lang), value=True)
animate_mode = st.sidebar.toggle(t('sidebar_animate', lang), value=False)

st.sidebar.markdown(f'<div class="section-label" style="margin-top:16px">{t("sidebar_ai_engine", lang)}</div>', unsafe_allow_html=True)
ai_mode = st.sidebar.radio('Mode', ['single', 'ab'], format_func=lambda x: t('sidebar_mode_single', lang) if x == 'single' else t('sidebar_mode_ab', lang), label_visibility='collapsed')
if ai_mode == 'single':
    selected_model = st.sidebar.selectbox('Model', list(AVAILABLE_MODELS.keys()), format_func=lambda x: AVAILABLE_MODELS[x], index=list(AVAILABLE_MODELS.keys()).index(DEFAULT_MODEL), label_visibility='collapsed')
    ab_models = None
else:
    ab_models = st.sidebar.multiselect(t('sidebar_models_label', lang), list(AVAILABLE_MODELS.keys()), default=list(AVAILABLE_MODELS.keys())[:2], format_func=lambda x: AVAILABLE_MODELS[x], label_visibility='collapsed')
default_key = ""
try:
    if "GEMINI_API_KEY" in st.secrets: default_key = st.secrets["GEMINI_API_KEY"]
    elif os.getenv("GEMINI_API_KEY"): default_key = os.getenv("GEMINI_API_KEY")
except Exception:
    pass
gemini_key = st.sidebar.text_input('Gemini API Key', value=default_key, type='password', placeholder=t('sidebar_api_key_placeholder', lang), help=t('sidebar_api_key_help', lang))

@st.cache_data(show_spinner=True)
def load_log_data(file_bytes_or_path):
    if isinstance(file_bytes_or_path, str): return parse_log(file_bytes_or_path)
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.BIN') as tmp:
        tmp.write(file_bytes_or_path); tmp_path = tmp.name
    res = parse_log(tmp_path); os.unlink(tmp_path)
    return res

def process_single_log(data):
    gps_df = get_gps_dataframe(data)
    if gps_df is None or len(gps_df) < 2: return None
    gps_df = filter_gps(gps_df)
    imu_df, att_df, vibe_df, baro_df, bat_df, mode_df = get_imu_dataframe(data), get_attitude_dataframe(data), get_vibe_dataframe(data), get_baro_dataframe(data), get_battery_dataframe(data), get_mode_dataframe(data)
    metrics = compute_metrics(gps_df, imu_df, att_df, vibe_df)
    gps_enu = gps_to_enu(gps_df)
    return {'gps_df': gps_df, 'imu_df': imu_df, 'att_df': att_df, 'vibe_df': vibe_df, 'baro_df': baro_df, 'bat_df': bat_df, 'mode_df': mode_df, 'metrics': metrics, 'gps_enu': gps_enu}

if main_files or demo_path:
    logs_data, fnames = [], []
    if main_files:
        for f_data in main_files[:2]:
            d = load_log_data(f_data['bytes']); p = process_single_log(d)
            if p: logs_data.append(p); fnames.append(f_data['name'])
    elif demo_path:
        d = load_log_data(str(demo_path)); p = process_single_log(d)
        if p: logs_data.append(p); fnames.append(os.path.basename(demo_path))

    if not logs_data: st.error(t('error_no_gps', lang)); st.stop()

    back_col, _ = st.columns([1, 11])
    with back_col:
        if st.button('←', help='Back' if lang == 'en' else 'Назад'):
            st.session_state.pop('demo_path', None)
            st.session_state.pop('main_upload_files', None)
            st.rerun()

    if len(logs_data) == 1:
        m, d0 = logs_data[0]['metrics'], logs_data[0]
        st.sidebar.success(f' {fnames[0]}')
        gps_hz = compute_sampling_rate(d0['gps_df'])
        imu_hz = compute_sampling_rate(d0['imu_df'])
        st.sidebar.markdown(
            f'<div style="font-size:11px;color:#8b949e;padding:4px 0 8px;">'
            f'GPS: <b style="color:#c9d1d9">{gps_hz or "—"} Hz</b> &nbsp;·&nbsp; '
            f'IMU: <b style="color:#c9d1d9">{imu_hz or "—"} Hz</b></div>',
            unsafe_allow_html=True
        )
        r, p, y = (float(d0['att_df']['Roll'].mean()), float(d0['att_df']['Pitch'].mean()), float(d0['att_df']['Yaw'].iloc[-1])) if d0['att_df'] is not None else (0,0,0)
        s = float(m.get('max_horiz_speed_ms') or 0)
        a = float(m.get('max_alt_m') or 0)
        vs = float(m.get('imu_max_vz_ms') or 0.0)
        st.plotly_chart(build_cockpit(r, p, y, s, a, vs, lang), use_container_width=True, key="stable_cockpit", config={'displayModeBar': False})
        render_metrics_grid(m, lang)
    else:
        st.sidebar.success(f' {fnames[0]} vs {fnames[1]}')
        comp = compare_metrics(logs_data[0]['metrics'], logs_data[1]['metrics'])
        render_compare_table(comp, lang)

    tabs = st.tabs([t('tab_3d', lang), t('tab_map', lang), t('tab_charts', lang), t('tab_ai', lang)])
    with tabs[0]:
        if compare_mode and len(logs_data) > 1:
            if animate_mode:
                st.plotly_chart(build_comparison_3d_animation(logs_data[0]['gps_enu'], logs_data[1]['gps_enu'], fnames[0], fnames[1]), use_container_width=True, key="compare_anim_3d")
            else:
                st.plotly_chart(build_comparison_3d(logs_data[0]['gps_enu'], logs_data[1]['gps_enu'], fnames[0], fnames[1], color_by=color_by, show_anomalies=show_anoms, mode_df_a=logs_data[0]['mode_df'], mode_df_b=logs_data[1]['mode_df']), use_container_width=True, key="compare_3d_main")
        elif animate_mode:
            st.plotly_chart(build_3d_track_animation(logs_data[0]['gps_enu']), use_container_width=True, key="anim_3d")
        else:
            st.plotly_chart(build_3d_track(logs_data[0]['gps_enu'], color_by=color_by, show_anomalies=show_anoms, mode_df=logs_data[0]['mode_df']), use_container_width=True, key="single_3d")

    cur = 1
    with tabs[cur]:
        try: from streamlit_folium import st_folium
        except Exception:
            st_folium = None
        if st_folium:
            map_obj = build_map(logs_data[0]['gps_df'], logs_data[1]['gps_df'] if compare_mode and len(logs_data) > 1 else None, fnames[0], fnames[1] if len(fnames) > 1 else '')
            st_folium(map_obj, use_container_width=True, height=560)
        st.download_button(label="Download KML", data=generate_kml(logs_data[0]['gps_df']), file_name=f"{fnames[0]}.kml", mime="application/vnd.google-earth.kml+xml", use_container_width=True)
    cur += 1
    with tabs[cur]:
        d0 = logs_data[0]; c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(build_baro_vs_gps_chart(d0['baro_df'], d0['gps_df']) or build_altitude_chart(d0['gps_df']), use_container_width=True)
            if d0['att_df'] is not None: st.plotly_chart(build_attitude_tracking_chart(d0['att_df']), use_container_width=True)
            bat_fig = build_battery_chart(d0['bat_df'], d0['gps_df'])
            if bat_fig is not None: st.plotly_chart(bat_fig, use_container_width=True)
        with c2:
            if d0['imu_df'] is not None: st.plotly_chart(build_speed_comparison_chart(d0['imu_df'], d0['att_df'], d0['gps_df']), use_container_width=True)
            if d0['vibe_df'] is not None: st.plotly_chart(build_vibration_chart(d0['vibe_df']), use_container_width=True)
    cur += 1
    with tabs[cur]:
        m, g, f = logs_data[0]['metrics'], logs_data[0]['gps_df'], fnames[0]
        if st.button(t('ai_run_button', lang), type='primary', use_container_width=True):
            if not gemini_key: st.warning("No API Key")
            elif ai_mode == 'ab':
                with st.spinner(t('ai_spinner_ab', lang)):
                    for r in analyze_flight_ab(metrics=m, gps_df=g, api_key=gemini_key, models=ab_models): st.markdown(f'<div class="ai-card"><b>{r["model"]}</b><br>{r["text"]}</div>', unsafe_allow_html=True)
            else:
                with st.spinner(t('ai_spinner', lang)):
                    r = analyze_flight(metrics=m, gps_df=g, api_key=gemini_key, model=selected_model)
                    st.markdown(f'<div class="ai-card">{r["text"]}</div>', unsafe_allow_html=True)
                    st.download_button(t('ai_export', lang) + " (PDF)", data=generate_pdf_report(f, m, r['text']), file_name=f"{f.split('.')[0]}_report.pdf", mime='application/pdf', use_container_width=True)
else:
    render_landing(lang)
