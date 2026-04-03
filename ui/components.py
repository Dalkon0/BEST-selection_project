"""Reusable Streamlit UI components for UAV Telemetry Analyzer."""
import pandas as pd
import streamlit as st
from i18n import t


def render_metrics_grid(m: dict, lang: str) -> None:
    """Render two-row flight metrics grid (5 cols × 2 rows)."""
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    with r1c1: st.metric(t('metric_distance', lang),   f"{m.get('total_distance_m', 0):,.0f} m")
    with r1c2: st.metric(t('metric_duration', lang),   f"{m.get('total_duration_s', 0):.0f} s")
    with r1c3: st.metric(t('metric_max_alt', lang),    f"{m.get('max_alt_m', '—')} m")
    with r1c4: st.metric(t('metric_start_alt', lang),  f"{m.get('start_alt_m', '—')} m")
    with r1c5: st.metric(t('metric_alt_gain', lang),   f"{m.get('alt_gain_m', '—')} m")

    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
    with r2c1: st.metric(t('metric_horiz_speed', lang),  f"{m.get('max_horiz_speed_ms', '—')} m/s")
    with r2c2: st.metric(t('metric_vert_speed', lang),   f"{m.get('max_vert_speed_ms', '—')} m/s")
    with r2c3: st.metric(t('metric_imu_vz', lang),       f"{m.get('imu_max_vz_ms', '—')} m/s")
    with r2c4: st.metric(t('metric_acceleration', lang), f"{m.get('max_acceleration', '—')} m/s²")
    with r2c5: st.metric(t('metric_vibration', lang),    f"{m.get('max_vibration', '—')} m/s²")


def render_compare_table(comp: dict, lang: str) -> None:
    """Render A/B comparison metrics table."""
    rows = []
    for k, v in comp.items():
        rows.append({
            t('compare_metric', lang): k.replace('_', ' ').title(),
            t('compare_log_a', lang): f"{v['a']:.1f}",
            t('compare_log_b', lang): f"{v['b']:.1f}",
            t('compare_delta', lang): f"{v['diff']:+.1f} ({v['pct']:+.1f}%)",
        })
    st.table(pd.DataFrame(rows))


def render_landing(lang: str) -> None:
    """Render the hero landing page with upload zone and feature cards."""
    st.markdown(f"""
    <div style="text-align:center; padding: 56px 20px 32px;">
        <div style="font-size: 10px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; color: #58a6ff; margin-bottom: 14px;">Ardupilot DataFlash</div>
        <h1 style="font-size: 34px; font-weight: 800; color: #e6edf3; margin: 0 0 12px; letter-spacing: -0.5px;">{t("landing_title", lang)}</h1>
        <p style="font-size: 15px; color: #6e7681; max-width: 480px; margin: 0 auto; line-height: 1.7;">{t("landing_subtitle", lang)}</p>
    </div>
    """, unsafe_allow_html=True)

    _, drop_col, _ = st.columns([1, 2, 1])
    with drop_col:
        main_up = st.file_uploader(
            t('sidebar_upload_multi', lang),
            type=['BIN', 'bin'],
            accept_multiple_files=True,
            key='main_uploader',
            help=t('sidebar_upload_help', lang),
        )
        if main_up:
            st.session_state['main_upload_files'] = [
                {'bytes': f.read(), 'name': f.name} for f in main_up
            ]
            st.rerun()

    st.markdown("""
    <div style="height:1px;background:linear-gradient(90deg,transparent,#21262d,transparent);margin:40px 0 32px;"></div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;">
    """ + _feature_card("3D Track",    "#58a6ff", t("landing_feat_3d_title", lang),      t("landing_feat_3d_desc", lang)) +
          _feature_card("Analytics",   "#3fb950", t("landing_feat_metrics_title", lang),  t("landing_feat_metrics_desc", lang)) +
          _feature_card("AI Engine",   "#f2cc60", t("landing_feat_ai_title", lang),       t("landing_feat_ai_desc", lang)) +
          _feature_card("Compare",     "#a371f7", t("landing_feat_ab_title", lang),       t("landing_feat_ab_desc", lang)) +
    """</div>""", unsafe_allow_html=True)


def _feature_card(label: str, color: str, title: str, desc: str) -> str:
    return f"""
    <div style="background:#161b22;border:1px solid #21262d;border-radius:10px;padding:20px;">
        <div style="font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{color};margin-bottom:10px;">{label}</div>
        <div style="color:#c9d1d9;font-size:14px;font-weight:600;margin-bottom:6px;">{title}</div>
        <div style="color:#6e7681;font-size:13px;line-height:1.6;">{desc}</div>
    </div>"""
