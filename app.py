import streamlit as st
import os
import pandas as pd
import numpy as np
from scraper.dataflash import parse_log, get_gps_dataframe, get_imu_dataframe, get_attitude_dataframe, get_vibe_dataframe, get_baro_dataframe, get_battery_dataframe, get_mode_dataframe
from analytics.metrics import compute_metrics, compare_metrics
from analytics.coords import gps_to_enu
from visualization.plot3d import build_3d_track, build_3d_track_animation, build_comparison_3d, build_altitude_chart, build_speed_comparison_chart, build_attitude_tracking_chart, build_vibration_chart, build_baro_vs_gps_chart, build_battery_chart
from visualization.map_view import build_map, generate_kml
from analytics.pdf_report import generate_pdf_report
from ai.assistant import analyze_flight, analyze_flight_ab, AVAILABLE_MODELS, DEFAULT_MODEL
from ai.token_counter import get_session_usage
from ai.pipeline_logger import get_recent_logs
from i18n import t

st.set_page_config(page_title='UAV Telemetry Analyzer', page_icon='🛸', layout='wide')

lang = st.sidebar.selectbox('Language / Мова', ['en', 'uk'], index=1, label_visibility='collapsed')

st.markdown("""
<style>
    .stApp { background-color: #0f1117; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #21262d; }
    [data-testid="stSidebarContent"] { padding-top: 0rem !important; }
    [data-testid="stSidebarNav"] { display: none; }
    [data-testid="stMetric"] {
        background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px 16px;
    }
    [data-testid="stMetricValue"] { color: #58a6ff; font-weight: 700; font-size: 24px; }
    [data-testid="stMetricLabel"] { color: #8b949e; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
    .section-label { color: #8b949e; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; margin-top: 24px; }
    .status-badge { display: flex; align-items:center; gap: 6px; background: rgba(35, 134, 54, 0.15); color: #3fb950; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(63, 185, 80, 0.3); }
    .status-dot { width: 6px; height: 6px; background: #3fb950; border-radius: 50%; box-shadow: 0 0 8px #3fb950; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 40px; background-color: #161b22; border-radius: 6px 6px 0 0; border: 1px solid #30363d; border-bottom: none; color: #8b949e; padding: 0 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #1f2937 !important; color: #58a6ff !important; border-top: 2px solid #58a6ff !important; }
    .model-badge { background: #21262d; color: #58a6ff; font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; border: 1px solid #30363d; margin-right: 6px; }
    .token-info { font-family: monospace; font-size: 10px; color: #8b949e; }
    .ai-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
    .ai-card-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; padding-bottom: 12px; margin-bottom: 16px; }
    .token-bar { display: flex; gap: 16px; background: #0d1117; padding: 10px 16px; border-radius: 6px; border: 1px solid #21262d; margin-top: 24px; }
    .token-stat { font-size: 11px; color: #8b949e; }
    .token-stat span { color: #c9d1d9; font-weight: 600; margin-left: 4px; }
    .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 40px; }
    .feature-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; transition: transform 0.2s, border-color 0.2s; }
    .feature-card:hover { border-color: #58a6ff; transform: translateY(-2px); }
    .feature-card-title { color: #e6edf3; font-weight: 600; margin-bottom: 8px; }
    .feature-card-desc { color: #8b949e; font-size: 13px; line-height: 1.5; }
    div[data-testid="stExpander"] { background: #161b22; border: 1px solid #30363d; border-radius: 6px; }
</style>

<div style="display:flex; align-items:center; justify-content:space-between; padding: 10px 0 20px; border-bottom: 1px solid #21262d; margin-bottom: 24px;">
    <div>
        <h1 style="font-size: 24px; font-weight: 700; margin:0; color: #e6edf3;">{t('page_title', lang)}</h1>
        <p style="font-size: 13px; color: #8b949e; margin: 4px 0 0;">{t('app_subtitle', lang)}</p>
    </div>
    <div class="status-badge"><div class="status-dot"></div>{t('status_online', lang)}</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f'<div class="section-label">{t("sidebar_data_source", lang)}</div>', unsafe_allow_html=True)
compare_mode = st.sidebar.toggle(t('sidebar_compare_mode', lang), value=False)

if compare_mode:
    uploaded = st.sidebar.file_uploader(t('sidebar_upload_multi', lang), type=['BIN', 'bin'], accept_multiple_files=True, label_visibility='collapsed')
else:
    uploaded = st.sidebar.file_uploader(t('sidebar_upload_label', lang), type=['BIN', 'bin'], label_visibility='collapsed')

if uploaded is not None: st.session_state.pop('demo_path', None)
demo_path = st.session_state.get('demo_path')

if not uploaded and not demo_path:
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
color_by = st.sidebar.radio(t('sidebar_color_label', lang), ['speed', 'time'], format_func=lambda x: t('sidebar_color_speed', lang) if x == 'speed' else t('sidebar_color_time', lang), label_visibility='collapsed')
show_anoms = st.sidebar.toggle(t('sidebar_show_anomalies', lang), value=True)
animate_mode = st.sidebar.toggle(t('sidebar_animate', lang), value=False)

st.sidebar.markdown(f'<div class="section-label" style="margin-top:16px">{t("sidebar_ai_engine", lang)}</div>', unsafe_allow_html=True)
default_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
gemini_key = st.sidebar.text_input('Gemini API Key', value=default_key, type='password', placeholder=t('sidebar_api_key_placeholder', lang), help=t('sidebar_api_key_help', lang))
ai_mode = st.sidebar.radio('Mode', ['single', 'ab'], format_func=lambda x: t('sidebar_mode_single', lang) if x == 'single' else t('sidebar_mode_ab', lang), label_visibility='collapsed')

if ai_mode == 'single':
    selected_model = st.sidebar.selectbox('Model', list(AVAILABLE_MODELS.keys()), format_func=lambda x: AVAILABLE_MODELS[x], index=list(AVAILABLE_MODELS.keys()).index(DEFAULT_MODEL), label_visibility='collapsed')
    ab_models = None
else:
    model_options = list(AVAILABLE_MODELS.keys())
    ab_models = st.sidebar.multiselect(t('sidebar_models_label', lang), model_options, default=model_options[:2], format_func=lambda x: AVAILABLE_MODELS[x], label_visibility='collapsed')
    selected_model = None

@st.cache_data(show_spinner=True)
def load_log_data(file_bytes_or_path):
    if isinstance(file_bytes_or_path, str): return parse_log(file_bytes_or_path)
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.BIN') as tmp:
        tmp.write(file_bytes_or_path)
        tmp_path = tmp.name
    result = parse_log(tmp_path)
    os.unlink(tmp_path)
    return result

def process_single_log(data):
    gps_df = get_gps_dataframe(data)
    if gps_df is None or len(gps_df) < 2: return None
    imu_df = get_imu_dataframe(data)
    att_df = get_attitude_dataframe(data)
    vibe_df = get_vibe_dataframe(data)
    baro_df = get_baro_dataframe(data)
    bat_df = get_battery_dataframe(data)
    mode_df = get_mode_dataframe(data)
    
    metrics = compute_metrics(gps_df, imu_df, att_df, vibe_df)
    gps_enu = gps_to_enu(gps_df)
    
    return {
        'gps_df': gps_df, 'imu_df': imu_df, 'att_df': att_df,
        'vibe_df': vibe_df, 'baro_df': baro_df, 'bat_df': bat_df,
        'mode_df': mode_df, 'metrics': metrics, 'gps_enu': gps_enu
    }

if uploaded or demo_path:
    logs_data = []
    filenames = []
    
    if compare_mode and isinstance(uploaded, list):
        for up in uploaded[:2]:
            d = load_log_data(up.read())
            p = process_single_log(d)
            if p:
                logs_data.append(p)
                filenames.append(up.name)
    elif demo_path:
        d = load_log_data(str(demo_path))
        p = process_single_log(d)
        if p:
            logs_data.append(p)
            filenames.append(os.path.basename(demo_path))
    elif uploaded:
        d = load_log_data(uploaded.read())
        p = process_single_log(d)
        if p:
            logs_data.append(p)
            filenames.append(uploaded.name)

    if not logs_data:
        st.error(t('error_no_gps', lang))
        st.stop()

    # --- Header Metrics ---
    if len(logs_data) == 1:
        m = logs_data[0]['metrics']
        st.sidebar.success(f' {filenames[0]}')
        
        badges = []
        if m.get('gps_sampling_hz'): badges.append(f'GPS {m["gps_sampling_hz"]} Hz')
        if m.get('imu_sampling_hz'): badges.append(f'IMU {m["imu_sampling_hz"]} Hz')
        badges.append(f'Points {len(logs_data[0]["gps_df"])}')
        st.markdown(f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px"><div class="section-label" style="margin-bottom:0">{t("section_metrics", lang)}</div><div style="font-size:12px;color:#8b949e">{" · ".join(badges)}</div></div>', unsafe_allow_html=True)
        
        c1, c2, c3, col4 = st.columns(4)
        with c1:
            st.metric(t('metric_distance', lang), f"{m['total_distance_m']:,.0f} m" if m['total_distance_m'] else '—')
            st.metric(t('metric_duration', lang), f"{m['total_duration_s']:.0f} s" if m['total_duration_s'] else '—')
        with c2:
            st.metric(t('metric_horiz_speed', lang), f"{m['max_horiz_speed_ms']} m/s" if m['max_horiz_speed_ms'] else '—')
            st.metric(t('metric_vert_speed', lang), f"{m['max_vert_speed_ms']} m/s" if m['max_vert_speed_ms'] else '—')
        with c3:
            st.metric(t('metric_max_alt', lang), f"{m['max_alt_m']} m" if m['max_alt_m'] else '—')
            st.metric(t('metric_vibration', lang), f"{m.get('max_vibration')} m/s²" if m.get('max_vibration') is not None else '—')
        with col4:
            st.metric(t('metric_acceleration', lang), f"{m['max_acceleration']} m/s²" if m['max_acceleration'] else '—')
            st.metric(t('metric_imu_vz', lang), f"{m['imu_max_vz_ms']} m/s" if m['imu_max_vz_ms'] else '—')
    else:
        # Comparison Header Table
        st.sidebar.success(f' {filenames[0]} vs {filenames[1]}')
        st.markdown(f'<div class="section-label">{t("compare_header", lang)}</div>', unsafe_allow_html=True)
        comp = compare_metrics(logs_data[0]['metrics'], logs_data[1]['metrics'])
        
        rows = []
        for k, v in comp.items():
            diff_str = f"{v['diff']:+.1f} ({v['pct']:+.1f}%)"
            rows.append({
                t('compare_metric', lang): k.replace('_', ' ').title(),
                t('compare_log_a', lang): f"{v['a']:.1f}",
                t('compare_log_b', lang): f"{v['b']:.1f}",
                t('compare_delta', lang): diff_str
            })
        st.table(pd.DataFrame(rows))

    # --- Tabs ---
    tab_list = [t('tab_3d', lang)]
    if len(logs_data) > 1: tab_list.append(t('tab_compare', lang))
    tab_list.extend([t('tab_map', lang), t('tab_charts', lang), t('tab_ai', lang)])
    
    tabs = st.tabs(tab_list)
    
    with tabs[0]: # 3D Tab
        if animate_mode:
            st.plotly_chart(build_3d_track_animation(logs_data[0]['gps_enu']), use_container_width=True)
        else:
            st.plotly_chart(build_3d_track(logs_data[0]['gps_enu'], color_by=color_by, show_anomalies=show_anoms), use_container_width=True)

    curr_idx = 1
    if len(logs_data) > 1:
        with tabs[curr_idx]: # Compare Tab
            st.plotly_chart(build_comparison_3d(logs_data[0]['gps_enu'], logs_data[1]['gps_enu'], filenames[0], filenames[1]), use_container_width=True)
        curr_idx += 1
        
    with tabs[curr_idx]: # Map
        st_folium = None
        try: from streamlit_folium import st_folium
        except: st.warning(t('warn_folium', lang))
        if st_folium:
            st_folium(build_map(logs_data[0]['gps_df']), use_container_width=True, height=560)
        kml_data = generate_kml(logs_data[0]['gps_df'])
        st.download_button(label="Download KML", data=kml_data, file_name=f"{filenames[0]}_path.kml", mime="application/vnd.google-earth.kml+xml", use_container_width=True)
    
    curr_idx += 1
    with tabs[curr_idx]: # Charts
        d0 = logs_data[0]
        c1, c2 = st.columns(2)
        with c1:
            baro_fig = build_baro_vs_gps_chart(d0['baro_df'], d0['gps_df'])
            st.plotly_chart(baro_fig if baro_fig else build_altitude_chart(d0['gps_df']), use_container_width=True)
            track_fig = build_attitude_tracking_chart(d0['att_df'])
            if track_fig: st.plotly_chart(track_fig, use_container_width=True)
        with c2:
            comp_fig = build_speed_comparison_chart(d0['imu_df'], d0['att_df'], d0['gps_df'])
            if comp_fig: st.plotly_chart(comp_fig, use_container_width=True)
            vibe_fig = build_vibration_chart(d0['vibe_df'])
            if vibe_fig: st.plotly_chart(vibe_fig, use_container_width=True)
    
    curr_idx += 1
    with tabs[curr_idx]: # AI
        m, g, f = logs_data[0]['metrics'], logs_data[0]['gps_df'], filenames[0]
        mode_label = f'{t("ai_single_caption", lang)} · <span class="model-badge">{selected_model}</span>' if ai_mode == 'single' else f'{t("ai_ab_caption", lang)} · <span class="model-badge">{len(ab_models or [])} {t("ai_models_label", lang)}</span>'
        st.markdown(f'<div style="font-size:13px;color:#8b949e;margin-bottom:16px">{mode_label}</div>', unsafe_allow_html=True)
        col_btn, col_info = st.columns([1, 4])
        run_ai = col_btn.button(t('ai_run_button', lang), type='primary', use_container_width=True)
        col_info.markdown(f'<div style="font-size:12px;color:#8b949e;padding-top:8px">{t("ai_info", lang)}</div>', unsafe_allow_html=True)

        if run_ai:
            if not gemini_key: st.warning(t('ai_warn_no_key', lang))
            elif ai_mode == 'ab':
                if not ab_models: st.warning(t('ai_warn_no_models', lang))
                else:
                    with st.spinner(t('ai_spinner_ab', lang)): results = analyze_flight_ab(metrics=m, gps_df=g, api_key=gemini_key, models=ab_models)
                    cols = st.columns(len(results))
                    for col, res in zip(cols, results):
                        with col:
                            st.markdown(f'<div class="ai-card"><div class="ai-card-header"><span class="model-badge">{res["model"]}</span><span class="token-info">{res["prompt_tokens"]}↑ {res["completion_tokens"]}↓ tokens</span></div>', unsafe_allow_html=True)
                            st.markdown(res['text']); st.markdown('</div>', unsafe_allow_html=True)
            else:
                with st.spinner(t('ai_spinner', lang)): result = analyze_flight(metrics=m, gps_df=g, api_key=gemini_key, model=selected_model)
                st.markdown(f'<div class="ai-card"><div class="ai-card-header"><span class="model-badge">{result["model"]}</span><span class="token-info">{result["prompt_tokens"]}↑ &nbsp;{result["completion_tokens"]}↓ &nbsp;tokens</span></div>', unsafe_allow_html=True)
                st.markdown(result['text']); st.markdown('</div>', unsafe_allow_html=True)
                pdf_data = generate_pdf_report(f, m, result['text'])
                st.download_button(t('ai_export', lang) + " (PDF)", data=pdf_data, file_name=f"{f.split('.')[0]}_report.pdf", mime='application/pdf', use_container_width=True)
else:
    st.markdown(f'<div style="text-align:center; padding: 60px 20px 40px;"><div style="font-size:48px; margin-bottom:12px">🛸</div><div style="font-size:22px; font-weight:700; color:#e6edf3; margin-bottom:8px">{t("landing_title", lang)}</div><div style="font-size:14px; color:#8b949e; max-width:480px; margin: 0 auto 40px;">{t("landing_subtitle", lang)}</div></div><div class="feature-grid"><div class="feature-card"><div class="feature-card-title">{t("landing_feat_3d_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_3d_desc", lang)}</div></div><div class="feature-card"><div class="feature-card-title">{t("landing_feat_metrics_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_metrics_desc", lang)}</div></div><div class="feature-card"><div class="feature-card-title">{t("landing_feat_map_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_map_desc", lang)}</div></div><div class="feature-card"><div class="feature-card-title">{t("landing_feat_ai_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_ai_desc", lang)}</div></div><div class="feature-card"><div class="feature-card-title">{t("landing_feat_ab_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_ab_desc", lang)}</div></div><div class="feature-card"><div class="feature-card-title">{t("landing_feat_log_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_log_desc", lang)}</div></div></div>', unsafe_allow_html=True)
