import streamlit as st
import os
from scraper.dataflash import parse_log, get_gps_dataframe, get_imu_dataframe, get_attitude_dataframe, get_vibe_dataframe, get_baro_dataframe, get_battery_dataframe, get_mode_dataframe
from analytics.metrics import compute_metrics
from analytics.coords import gps_to_enu
from visualization.plot3d import build_3d_track, build_3d_track_animation, build_altitude_chart, build_speed_comparison_chart, build_attitude_tracking_chart, build_vibration_chart, build_baro_vs_gps_chart, build_battery_chart
from visualization.map_view import build_map, generate_kml
from analytics.pdf_report import generate_pdf_report
from ai.assistant import analyze_flight, analyze_flight_ab, AVAILABLE_MODELS, DEFAULT_MODEL
from ai.token_counter import get_session_usage
from ai.pipeline_logger import get_recent_logs
from i18n import t

st.set_page_config(page_title='UAV Telemetry Analyzer', page_icon='🛸', layout='wide')

st.markdown("""
<style>
    .stApp { background-color: #0f1117; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #21262d; }
    [data-testid="stSidebarContent"] { padding-top: 0rem !important; }
    [data-testid="stSidebarNav"] { display: none; }
    [data-testid="stMetric"] {
        background: #161b22; border: 1px solid #21262d;
        border-radius: 8px; padding: 16px 20px;
    }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 0.08em; }
    [data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 22px !important; font-weight: 600; }
    .stTabs [data-baseweb="tab-list"] { background: #161b22; border-bottom: 1px solid #21262d; gap: 0; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; padding: 10px 20px; font-size: 13px; font-weight: 500; border-bottom: 2px solid transparent; }
    .stTabs [aria-selected="true"] { color: #58a6ff !important; border-bottom: 2px solid #58a6ff !important; background: transparent !important; }
    .stButton > button[kind="primary"] {
        background: #238636; border: 1px solid #2ea043; color: #fff;
        font-weight: 600; border-radius: 6px;
    }
    .stButton > button[kind="primary"]:hover { background: #2ea043; }
    .app-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 20px 0 16px; border-bottom: 1px solid #21262d; margin-bottom: 24px;
    }
    .app-title { font-size: 20px; font-weight: 700; color: #e6edf3; letter-spacing: -0.02em; }
    .app-subtitle { font-size: 12px; color: #8b949e; margin-top: 2px; }
    .status-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: #1f2937; border: 1px solid #374151;
        border-radius: 20px; padding: 4px 12px; font-size: 12px; color: #9ca3af;
    }
    .status-dot { width: 7px; height: 7px; border-radius: 50%; background: #22c55e; }
    .section-label {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.1em; color: #8b949e; margin-bottom: 12px;
    }
    .ai-card {
        background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 20px 24px;
    }
    .ai-card-header {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #21262d;
    }
    .model-badge {
        background: #1f2937; border: 1px solid #374151; border-radius: 4px;
        padding: 2px 8px; font-size: 11px; color: #58a6ff; font-family: monospace;
    }
    .token-info { font-size: 11px; color: #8b949e; }
    .token-bar {
        background: #161b22; border: 1px solid #21262d; border-radius: 6px;
        padding: 10px 16px; display: flex; gap: 24px; margin-top: 16px;
    }
    .token-stat { font-size: 12px; color: #8b949e; }
    .token-stat span { color: #e6edf3; font-weight: 600; }
    .feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 20px 0; }
    .feature-card {
        background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px 18px;
    }
    .feature-card-title { font-size: 13px; font-weight: 600; color: #e6edf3; margin-bottom: 4px; }
    .feature-card-desc { font-size: 12px; color: #8b949e; }
    [data-testid="stExpander"] { background: #161b22; border: 1px solid #21262d; border-radius: 6px; }
    div[data-testid="stCaption"] { color: #6e7681 !important; font-size: 11px !important; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-top: -35px; margin-bottom: 5px;">
        <span style="font-size: 34px;">🛸</span>
        <div style="font-weight: 700; font-size: 20px; color: #e6edf3; letter-spacing: -0.02em; line-height: 1.1;">
            UAV<br><span style="color: #58a6ff; font-size: 14px;">Analyzer</span>
        </div>
    </div>
""", unsafe_allow_html=True)

lang = st.sidebar.radio('', ['en', 'uk'], horizontal=True, key='lang', format_func=lambda x: 'EN' if x == 'en' else 'UA')
st.sidebar.markdown('<div style="margin-bottom:8px"></div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="app-header">
    <div>
        <div class="app-title">UAV Telemetry Analyzer</div>
        <div class="app-subtitle">{t('app_subtitle', lang)}</div>
    </div>
    <div class="status-badge"><div class="status-dot"></div>{t('status_online', lang)}</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f'<div class="section-label">{t("sidebar_data_source", lang)}</div>', unsafe_allow_html=True)
uploaded = st.sidebar.file_uploader(t('sidebar_upload_label', lang), type=['BIN', 'bin'], help=t('sidebar_upload_help', lang), label_visibility='collapsed')

if uploaded is not None: st.session_state.pop('demo_path', None)
demo_path = st.session_state.get('demo_path')

if uploaded is None:
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
def load_log(file_bytes_or_path):
    if isinstance(file_bytes_or_path, str): return parse_log(file_bytes_or_path)
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.BIN') as tmp:
        tmp.write(file_bytes_or_path)
        tmp_path = tmp.name
    result = parse_log(tmp_path)
    os.unlink(tmp_path)
    return result

if uploaded is not None or demo_path:
    if uploaded is not None:
        dataframes = load_log(uploaded.read())
        filename   = uploaded.name
    else:
        dataframes = load_log(str(demo_path))
        filename   = os.path.basename(demo_path)

    st.sidebar.success(f' {filename}')
    gps_df  = get_gps_dataframe(dataframes)
    imu_df  = get_imu_dataframe(dataframes)
    att_df  = get_attitude_dataframe(dataframes)
    vibe_df = get_vibe_dataframe(dataframes)
    baro_df = get_baro_dataframe(dataframes)
    bat_df  = get_battery_dataframe(dataframes)
    mode_df = get_mode_dataframe(dataframes)

    if gps_df is None or len(gps_df) < 2:
        st.error(t('error_no_gps', lang))
        st.stop()

    gps_enu = gps_to_enu(gps_df)
    metrics = compute_metrics(gps_df, imu_df, att_df, vibe_df)

    badges = []
    if metrics.get('gps_sampling_hz'): badges.append(f'GPS <span style="color:#e6edf3;font-weight:600">{metrics["gps_sampling_hz"]} Hz</span>')
    if metrics.get('imu_sampling_hz'): badges.append(f'IMU <span style="color:#e6edf3;font-weight:600">{metrics["imu_sampling_hz"]} Hz</span>')
    badges.append(f'Points <span style="color:#e6edf3;font-weight:600">{len(gps_df)}</span>')
    badges_html = ' &nbsp;·&nbsp; '.join(badges)

    st.markdown(f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px"><div class="section-label" style="margin-bottom:0">{t("section_metrics", lang)}</div><div style="font-size:12px;color:#8b949e">{badges_html}</div></div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t('metric_distance', lang), f"{metrics['total_distance_m']:,.0f} m" if metrics['total_distance_m'] else '—')
        st.metric(t('metric_duration', lang), f"{metrics['total_duration_s']:.0f} s" if metrics['total_duration_s'] else '—')
    with col2:
        st.metric(t('metric_horiz_speed', lang), f"{metrics['max_horiz_speed_ms']} m/s" if metrics['max_horiz_speed_ms'] else '—')
        st.metric(t('metric_vert_speed', lang), f"{metrics['max_vert_speed_ms']} m/s" if metrics['max_vert_speed_ms'] else '—')
    with col3:
        st.metric(t('metric_max_alt', lang), f"{metrics['max_alt_m']} m" if metrics['max_alt_m'] else '—')
        vib = metrics.get('max_vibration')
        st.metric(t('metric_vibration', lang), f"{vib} m/s²" if vib is not None else '—')
    with col4:
        st.metric(t('metric_acceleration', lang), f"{metrics['max_acceleration']} m/s²" if metrics['max_acceleration'] else '—')
        st.metric(t('metric_imu_vz', lang), f"{metrics['imu_max_vz_ms']} m/s" if metrics['imu_max_vz_ms'] else '—')

    tab_3d, tab_map, tab_charts, tab_ai = st.tabs([t('tab_3d', lang), t('tab_map', lang), t('tab_charts', lang), t('tab_ai', lang)])

    with tab_3d:
        if animate_mode:
            st.plotly_chart(build_3d_track_animation(gps_enu), use_container_width=True)
        else:
            st.plotly_chart(build_3d_track(gps_enu, color_by=color_by, show_anomalies=show_anoms), use_container_width=True)

    with tab_map:
        try:
            from streamlit_folium import st_folium
            st_folium(build_map(gps_df), use_container_width=True, height=560)
        except: st.warning(t('warn_folium', lang))
        st.markdown("<br>", unsafe_allow_html=True)
        kml_data = generate_kml(gps_df)
        st.download_button(label="Скачати траєкторію для Google Earth (.kml)", data=kml_data, file_name=f"{filename.split('.')[0]}_trajectory.kml", mime="application/vnd.google-earth.kml+xml", use_container_width=True, type="primary")

    with tab_charts:
        c1, c2 = st.columns(2)
        with c1:
            baro_fig = build_baro_vs_gps_chart(baro_df, gps_df)
            if baro_fig: st.plotly_chart(baro_fig, use_container_width=True)
            else: st.plotly_chart(build_altitude_chart(gps_df), use_container_width=True)
            track_fig = build_attitude_tracking_chart(att_df)
            if track_fig: st.plotly_chart(track_fig, use_container_width=True)
            bat_fig = build_battery_chart(bat_df, gps_df)
            if bat_fig: st.plotly_chart(bat_fig, use_container_width=True)
        with c2:
            comp_fig = build_speed_comparison_chart(imu_df, att_df, gps_df)
            if comp_fig: st.plotly_chart(comp_fig, use_container_width=True)
            vibe_fig = build_vibration_chart(vibe_df)
            if vibe_fig: st.plotly_chart(vibe_fig, use_container_width=True)
        if mode_df is not None and 'Mode' in mode_df.columns:
            with st.expander('Flight Mode Timeline'):
                st.dataframe(mode_df[['TimeUS', 'Mode'] + [c for c in mode_df.columns if c not in ('TimeUS', 'Mode')]].head(100), use_container_width=True)
        with st.expander(t('charts_raw_gps', lang)): st.dataframe(gps_df.head(200), use_container_width=True)

    with tab_ai:
        mode_label = f'{t("ai_single_caption", lang)} · <span class="model-badge">{selected_model}</span>' if ai_mode == 'single' else f'{t("ai_ab_caption", lang)} · <span class="model-badge">{len(ab_models or [])} {t("ai_models_label", lang)}</span>'
        st.markdown(f'<div style="font-size:13px;color:#8b949e;margin-bottom:16px">{mode_label}</div>', unsafe_allow_html=True)
        col_btn, col_info = st.columns([1, 4])
        with col_btn: run_ai = st.button(t('ai_run_button', lang), type='primary', use_container_width=True)
        with col_info: st.markdown(f'<div style="font-size:12px;color:#8b949e;padding-top:8px">{t("ai_info", lang)}</div>', unsafe_allow_html=True)

        if run_ai:
            if not gemini_key: st.warning(t('ai_warn_no_key', lang))
            elif ai_mode == 'ab':
                if not ab_models: st.warning(t('ai_warn_no_models', lang))
                else:
                    with st.spinner(t('ai_spinner_ab', lang)): results = analyze_flight_ab(metrics=metrics, gps_df=gps_df, api_key=gemini_key, models=ab_models)
                    cols = st.columns(len(results))
                    for col, res in zip(cols, results):
                        with col:
                            st.markdown(f'<div class="ai-card"><div class="ai-card-header"><span class="model-badge">{res["model"]}</span><span class="token-info">{res["prompt_tokens"]}↑ {res["completion_tokens"]}↓ tokens</span></div>', unsafe_allow_html=True)
                            st.markdown(res['text']); st.markdown('</div>', unsafe_allow_html=True)
                            c1, c2 = st.columns(2)
                            with c1: st.download_button(f'{t("ai_export_ab", lang)} (.txt)', data=res['text'], file_name=f'flight_analysis_{res["model"]}.txt', mime='text/plain', use_container_width=True)
                            with c2: 
                                pdf_data = generate_pdf_report(filename, metrics, res['text'])
                                st.download_button(f'{t("ai_export_ab", lang)} (PDF)', data=pdf_data, file_name=f'flight_analysis_{res["model"]}.pdf', mime='application/pdf', use_container_width=True)
            else:
                with st.spinner(t('ai_spinner', lang)): result = analyze_flight(metrics=metrics, gps_df=gps_df, api_key=gemini_key, model=selected_model)
                st.markdown(f'<div class="ai-card"><div class="ai-card-header"><span class="model-badge">{result["model"]}</span><span class="token-info">{result["prompt_tokens"]}↑ &nbsp;{result["completion_tokens"]}↓ &nbsp;tokens</span></div>', unsafe_allow_html=True)
                st.markdown(result['text']); st.markdown('</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1: st.download_button(t('ai_export', lang) + " (.txt)", data=result['text'], file_name='flight_analysis.txt', mime='text/plain', use_container_width=True)
                with c2:
                    pdf_data = generate_pdf_report(filename, metrics, result['text'])
                    st.download_button(t('ai_export', lang) + " (PDF)", data=pdf_data, file_name=f"{filename.split('.')[0]}_report.pdf", mime='application/pdf', use_container_width=True)

        usage = get_session_usage()
        if usage['requests'] > 0: st.markdown(f'<div class="token-bar"><div class="token-stat">{t("token_requests", lang)} <span>{usage["requests"]}</span></div><div class="token-stat">{t("token_total", lang)} <span>{usage["total_tokens"]}</span></div><div class="token-stat">{t("token_prompt", lang)} <span>{usage["prompt_tokens"]}</span></div><div class="token-stat">{t("token_completion", lang)} <span>{usage["completion_tokens"]}</span></div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("Історія аналізів (MongoDB / Local)"):
            history = get_recent_logs(5)
            if history:
                for h in history:
                    st.markdown(f"**{h['filename']}** ({h['model']}) — *{h['timestamp']}*")
                    st.caption(h['response'][:200] + "...")
            else: st.info("Історія поки порожня")
else:
    st.markdown(f'<div style="text-align:center; padding: 60px 20px 40px;"><div style="font-size:48px; margin-bottom:12px">🛸</div><div style="font-size:22px; font-weight:700; color:#e6edf3; margin-bottom:8px">{t("landing_title", lang)}</div><div style="font-size:14px; color:#8b949e; max-width:480px; margin: 0 auto 40px;">{t("landing_subtitle", lang)}</div></div><div class="feature-grid"><div class="feature-card"><div class="feature-card-title">{t("landing_feat_3d_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_3d_desc", lang)}</div></div><div class="feature-card"><div class="feature-card-title">{t("landing_feat_metrics_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_metrics_desc", lang)}</div></div><div class="feature-card"><div class="feature-card-title">{t("landing_feat_map_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_map_desc", lang)}</div></div><div class="feature-card"><div class="feature-card-title">{t("landing_feat_ai_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_ai_desc", lang)}</div></div><div class="feature-card"><div class="feature-card-title">{t("landing_feat_ab_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_ab_desc", lang)}</div></div><div class="feature-card"><div class="feature-card-title">{t("landing_feat_log_title", lang)}</div><div class="feature-card-desc">{t("landing_feat_log_desc", lang)}</div></div></div>', unsafe_allow_html=True)
