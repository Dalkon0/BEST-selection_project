import plotly.graph_objects as go
import pandas as pd
import numpy as np

def build_3d_track(gps_enu_df, color_by='speed', show_anomalies=True, mode_df=None):
    from analytics.metrics import downsample_df
    df = downsample_df(gps_enu_df, 3000).copy()
    colorbar_dict = dict(thickness=15, len=0.6, tickfont=dict(color='#ffffff'))
    if color_by == 'mode' and mode_df is not None:
        merged = pd.merge_asof(df.sort_values('TimeUS'), mode_df[['TimeUS', 'Mode']].sort_values('TimeUS'), on='TimeUS', direction='backward')
        modes = merged['Mode'].fillna('Unknown').values
        unique_modes = np.unique(modes)
        mode_map = {m: i for i, m in enumerate(unique_modes)}
        color_values = [mode_map[m] for m in modes]
        colorbar_title = 'Mode'
        colorscale = [[i/(max(1, len(unique_modes)-1)), f'hsl({i*360/max(1, len(unique_modes))}, 70%, 50%)'] for i in range(len(unique_modes))]
        hover_text = [f"Mode: {m}" for m in modes]
        colorbar_dict.update(tickvals=list(mode_map.values()), ticktext=list(mode_map.keys()))
    elif color_by == 'speed' and 'Spd' in df.columns:
        color_values = pd.to_numeric(df['Spd'], errors='coerce').fillna(0).values
        colorbar_title, colorscale = 'Speed (m/s)', 'Viridis'
        hover_text = [f"Spd: {v:.1f} m/s" for v in color_values]
    else:
        t = pd.to_numeric(df['TimeUS'], errors='coerce').values
        color_values = (t - t.min()) / (t.max() - t.min() + 1e-9)
        colorbar_title, colorscale = 'Time', 'Plasma'
        hover_text = [f"T: {(v-t.min())/1e6:.1f}s" for v in t]
    track = go.Scatter3d(x=df['E_m'], y=df['N_m'], z=df['U_m'], mode='lines', line=dict(color=color_values, colorscale=colorscale, width=5, colorbar=dict(title=colorbar_title, **colorbar_dict)), name='Track', hovertext=hover_text, hovertemplate='%{hovertext}<br>E: %{x:.1f}m<br>N: %{y:.1f}m<br>U: %{z:.1f}m<extra></extra>')
    start = go.Scatter3d(x=[df['E_m'].iloc[0]], y=[df['N_m'].iloc[0]], z=[df['U_m'].iloc[0]], mode='markers', marker=dict(size=8, color='green'), name='Start')
    finish = go.Scatter3d(x=[df['E_m'].iloc[-1]], y=[df['N_m'].iloc[-1]], z=[df['U_m'].iloc[-1]], mode='markers', marker=dict(size=8, color='red'), name='Finish')
    shadow = go.Scatter3d(x=df['E_m'], y=df['N_m'], z=np.zeros(len(df)), mode='lines', line=dict(color='gray', width=1, dash='dot'), name='Projection', opacity=0.3)
    data = [shadow, track, start, finish]
    if show_anomalies:
        if 'VZ' in df.columns:
            vz = df['VZ'].values
            idx = np.where(vz > 5.0)[0]
            if len(idx) > 0: data.append(go.Scatter3d(x=df['E_m'].iloc[idx], y=df['N_m'].iloc[idx], z=df['U_m'].iloc[idx], mode='markers', marker=dict(size=6, color='orange', symbol='diamond'), name='Climb'))
        if 'Spd' in df.columns:
            spd = df['Spd'].values
            idx = np.where(spd > 20.0)[0]
            if len(idx) > 0: data.append(go.Scatter3d(x=df['E_m'].iloc[idx], y=df['N_m'].iloc[idx], z=df['U_m'].iloc[idx], mode='markers', marker=dict(size=6, color='red', symbol='cross'), name='Overspeed'))
    fig = go.Figure(data=data)
    fig.update_layout(template='plotly_dark', title='3D Trajectory', scene=dict(xaxis_title='E (m)', yaxis_title='N (m)', zaxis_title='U (m)', aspectmode='cube', camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))), margin=dict(l=5, r=5, b=5, t=40), height=700)
    return fig

def build_3d_track_animation(gps_enu_df):
    from analytics.metrics import downsample_df
    df = downsample_df(gps_enu_df, 300).copy()
    fig = go.Figure(
        data=[
            go.Scatter3d(x=df['E_m'], y=df['N_m'], z=df['U_m'], mode='lines', line=dict(color='rgba(100,100,100,0.3)', width=2), name='Path'),
            go.Scatter3d(x=[df['E_m'].iloc[0]], y=[df['N_m'].iloc[0]], z=[df['U_m'].iloc[0]], mode='markers+text', marker=dict(size=8, color='yellow', symbol='circle'), text=["UAV"], name='UAV'),
            go.Scatter3d(x=[df['E_m'].iloc[0]], y=[df['N_m'].iloc[0]], z=[0], mode='markers', marker=dict(size=4, color='white', opacity=0.5), name='Projection')
        ],
        layout=go.Layout(
            template='plotly_dark', scene=dict(aspectmode='cube', camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))),
            updatemenus=[dict(type="buttons", bgcolor="green", font=dict(color="white"), buttons=[dict(label="▶ Play Replay", method="animate", args=[None, {"frame": {"duration": 40, "redraw": True}, "fromcurrent": True}])])],
            margin=dict(l=5, r=5, b=5, t=40), height=700, title='Flight Replay'
        ),
        frames=[go.Frame(data=[go.Scatter3d(x=[df['E_m'].iloc[i]], y=[df['N_m'].iloc[i]], z=[df['U_m'].iloc[i]]), go.Scatter3d(x=[df['E_m'].iloc[i]], y=[df['N_m'].iloc[i]], z=[0])], traces=[1, 2]) for i in range(len(df))]
    )
    return fig

def build_comparison_3d(enu_a, enu_b, name_a="Log A", name_b="Log B", color_by='speed', show_anomalies=True, mode_df_a=None, mode_df_b=None):
    from analytics.metrics import downsample_df
    dfa = downsample_df(enu_a, 2000).copy()
    dfb = downsample_df(enu_b, 2000).copy()

    def _color_values(df, mode_df):
        if color_by == 'speed' and 'Spd' in df.columns:
            return pd.to_numeric(df['Spd'], errors='coerce').fillna(0).values, 'Speed (m/s)', [f"Spd: {v:.1f} m/s" for v in pd.to_numeric(df['Spd'], errors='coerce').fillna(0).values]
        elif color_by == 'mode' and mode_df is not None:
            merged = pd.merge_asof(df.sort_values('TimeUS'), mode_df[['TimeUS', 'Mode']].sort_values('TimeUS'), on='TimeUS', direction='backward')
            modes = merged['Mode'].fillna('Unknown').values
            unique_modes = np.unique(modes)
            mode_map = {m: i for i, m in enumerate(unique_modes)}
            return [mode_map[m] for m in modes], 'Mode', [f"Mode: {m}" for m in modes]
        else:
            t = pd.to_numeric(df['TimeUS'], errors='coerce').values
            cv = (t - t.min()) / (t.max() - t.min() + 1e-9)
            return cv, 'Time', [f"T: {(v - t.min())/1e6:.1f}s" for v in t]

    cv_a, cbar_a, hover_a = _color_values(dfa, mode_df_a)
    cv_b, cbar_b, hover_b = _color_values(dfb, mode_df_b)

    # Dark-start colorscales — always visible on dark background
    cs_a = [[0, '#0d2b4a'], [0.5, '#1f6fbf'], [1, '#58a6ff']]
    cs_b = [[0, '#4a0d0d'], [0.5, '#bf3f3f'], [1, '#ff7b72']]

    fig = go.Figure()
    cb = dict(thickness=12, len=0.5, tickfont=dict(color='#ffffff'))

    # Track A
    fig.add_trace(go.Scatter3d(x=dfa['E_m'], y=dfa['N_m'], z=dfa['U_m'], mode='lines',
        line=dict(color=cv_a, colorscale=cs_a, width=5, colorbar=dict(title=f'{name_a} {cbar_a}', x=1.0, **cb)),
        name=name_a, hovertext=hover_a, hovertemplate='%{hovertext}<extra>' + name_a + '</extra>'))
    fig.add_trace(go.Scatter3d(x=dfa['E_m'], y=dfa['N_m'], z=np.zeros(len(dfa)), mode='lines',
        line=dict(color='#58a6ff', width=1), opacity=0.2, showlegend=False))
    fig.add_trace(go.Scatter3d(x=[dfa['E_m'].iloc[0]], y=[dfa['N_m'].iloc[0]], z=[dfa['U_m'].iloc[0]], mode='markers',
        marker=dict(size=8, color='#58a6ff'), name=f'{name_a} start'))
    fig.add_trace(go.Scatter3d(x=[dfa['E_m'].iloc[-1]], y=[dfa['N_m'].iloc[-1]], z=[dfa['U_m'].iloc[-1]], mode='markers',
        marker=dict(size=8, color='#58a6ff', symbol='square'), name=f'{name_a} end'))

    # Track B
    fig.add_trace(go.Scatter3d(x=dfb['E_m'], y=dfb['N_m'], z=dfb['U_m'], mode='lines',
        line=dict(color=cv_b, colorscale=cs_b, width=5, colorbar=dict(title=f'{name_b} {cbar_b}', x=1.08, **cb)),
        name=name_b, hovertext=hover_b, hovertemplate='%{hovertext}<extra>' + name_b + '</extra>'))
    fig.add_trace(go.Scatter3d(x=dfb['E_m'], y=dfb['N_m'], z=np.zeros(len(dfb)), mode='lines',
        line=dict(color='#ff7b72', width=1), opacity=0.2, showlegend=False))
    fig.add_trace(go.Scatter3d(x=[dfb['E_m'].iloc[0]], y=[dfb['N_m'].iloc[0]], z=[dfb['U_m'].iloc[0]], mode='markers',
        marker=dict(size=8, color='#ff7b72'), name=f'{name_b} start'))
    fig.add_trace(go.Scatter3d(x=[dfb['E_m'].iloc[-1]], y=[dfb['N_m'].iloc[-1]], z=[dfb['U_m'].iloc[-1]], mode='markers',
        marker=dict(size=8, color='#ff7b72', symbol='square'), name=f'{name_b} end'))

    # Anomalies
    if show_anomalies:
        for adf, label in [(dfa, name_a), (dfb, name_b)]:
            if 'VZ' in adf.columns:
                vz = pd.to_numeric(adf['VZ'], errors='coerce').fillna(0).values
                idx = np.where(vz > 5.0)[0]
                if len(idx): fig.add_trace(go.Scatter3d(x=adf['E_m'].iloc[idx], y=adf['N_m'].iloc[idx], z=adf['U_m'].iloc[idx], mode='markers', marker=dict(size=5, color='orange', symbol='diamond'), name=f'Climb {label}', showlegend=False))
            if 'Spd' in adf.columns:
                spd = pd.to_numeric(adf['Spd'], errors='coerce').fillna(0).values
                idx = np.where(spd > 20.0)[0]
                if len(idx): fig.add_trace(go.Scatter3d(x=adf['E_m'].iloc[idx], y=adf['N_m'].iloc[idx], z=adf['U_m'].iloc[idx], mode='markers', marker=dict(size=5, color='red', symbol='cross'), name=f'Overspeed {label}', showlegend=False))

    fig.update_layout(template='plotly_dark', title='Track Comparison',
        scene=dict(xaxis_title='E (m)', yaxis_title='N (m)', zaxis_title='U (m)', aspectmode='cube', camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))),
        margin=dict(l=5, r=5, b=5, t=40), height=700)
    return fig


def build_comparison_3d_animation(enu_a, enu_b, name_a="Log A", name_b="Log B"):
    from analytics.metrics import downsample_df
    dfa = downsample_df(enu_a, 300).copy()
    dfb = downsample_df(enu_b, 300).copy()

    # Normalize both to same number of frames via linear interpolation
    n = min(len(dfa), len(dfb))
    def resample(df, n):
        idx = np.linspace(0, len(df) - 1, n).astype(int)
        return df.iloc[idx].reset_index(drop=True)
    dfa, dfb = resample(dfa, n), resample(dfb, n)

    fig = go.Figure(
        data=[
            go.Scatter3d(x=dfa['E_m'], y=dfa['N_m'], z=dfa['U_m'], mode='lines', line=dict(color='rgba(88,166,255,0.25)', width=2), name=name_a),
            go.Scatter3d(x=dfb['E_m'], y=dfb['N_m'], z=dfb['U_m'], mode='lines', line=dict(color='rgba(255,123,114,0.25)', width=2), name=name_b),
            go.Scatter3d(x=[dfa['E_m'].iloc[0]], y=[dfa['N_m'].iloc[0]], z=[dfa['U_m'].iloc[0]], mode='markers+text', marker=dict(size=9, color='#58a6ff'), text=[name_a], name=f'{name_a} UAV'),
            go.Scatter3d(x=[dfb['E_m'].iloc[0]], y=[dfb['N_m'].iloc[0]], z=[dfb['U_m'].iloc[0]], mode='markers+text', marker=dict(size=9, color='#ff7b72'), text=[name_b], name=f'{name_b} UAV'),
            go.Scatter3d(x=[dfa['E_m'].iloc[0]], y=[dfa['N_m'].iloc[0]], z=[0], mode='markers', marker=dict(size=4, color='#58a6ff', opacity=0.4), showlegend=False),
            go.Scatter3d(x=[dfb['E_m'].iloc[0]], y=[dfb['N_m'].iloc[0]], z=[0], mode='markers', marker=dict(size=4, color='#ff7b72', opacity=0.4), showlegend=False),
        ],
        layout=go.Layout(
            template='plotly_dark',
            scene=dict(aspectmode='cube', camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))),
            updatemenus=[dict(type="buttons", bgcolor="#21262d", font=dict(color="white"),
                buttons=[dict(label="▶ Play Replay", method="animate", args=[None, {"frame": {"duration": 40, "redraw": True}, "fromcurrent": True}])])],
            margin=dict(l=5, r=5, b=5, t=40), height=700, title='Flight Replay — Comparison'
        ),
        frames=[go.Frame(data=[
            go.Scatter3d(x=[dfa['E_m'].iloc[i]], y=[dfa['N_m'].iloc[i]], z=[dfa['U_m'].iloc[i]]),
            go.Scatter3d(x=[dfb['E_m'].iloc[i]], y=[dfb['N_m'].iloc[i]], z=[dfb['U_m'].iloc[i]]),
            go.Scatter3d(x=[dfa['E_m'].iloc[i]], y=[dfa['N_m'].iloc[i]], z=[0]),
            go.Scatter3d(x=[dfb['E_m'].iloc[i]], y=[dfb['N_m'].iloc[i]], z=[0]),
        ], traces=[2, 3, 4, 5]) for i in range(n)]
    )
    return fig

def build_cockpit(roll, pitch, yaw, speed, alt, v_speed=0, lang='en'):
    from plotly.subplots import make_subplots
    from i18n import t
    fig = make_subplots(rows=1, cols=4, specs=[[{'type': 'indicator'}]*4], horizontal_spacing=0.1)
    nf = {'size': 16, 'color': '#ffffff'}
    tf = {'size': 10, 'color': '#ffffff'}
    def get_g(c, r, th=None, s=None):
        g = {'axis': {'range': r, 'tickwidth': 1, 'tickcolor': '#ffffff'}, 'bar': {'color': c, 'thickness': 0.25}, 'bgcolor': "rgba(0,0,0,0)", 'borderwidth': 1, 'bordercolor': "rgba(255,255,255,0.1)"}
        if th: g['threshold'] = th
        if s: g['steps'] = s
        return g
    fig.add_trace(go.Indicator(mode="gauge+number", value=roll, number={'suffix': "°", 'font': nf}, title={'text': f"PITCH: {pitch:+.1f}°<br>{t('cockpit_roll', lang)}", 'font': tf}, gauge=get_g("#00d4ff", [-45, 45])), 1, 1)
    fig.add_trace(go.Indicator(mode="gauge+number", value=speed, number={'suffix': " m/s", 'font': nf}, title={'text': t('cockpit_speed', lang), 'font': tf}, gauge=get_g("#3fb950", [0, 40], s=[{'range': [30, 40], 'color': "rgba(255,0,0,0.2)"}])), 1, 2)
    fig.add_trace(go.Indicator(mode="gauge+number", value=alt, number={'suffix': " m", 'font': nf}, title={'text': f"VSI: {v_speed:+.1f}<br>{t('cockpit_alt', lang)}", 'font': tf}, gauge=get_g("#f2cc60", [0, 300])), 1, 3)
    fig.add_trace(go.Indicator(mode="gauge+number", value=yaw%360, number={'suffix': "°", 'font': nf}, title={'text': t('cockpit_heading', lang), 'font': tf}, gauge=get_g("#ffffff", [0, 360], s=[{'range': [0, 360], 'color': "rgba(255,255,255,0.05)"}])), 1, 4)
    fig.update_layout(template='plotly_dark', height=220, margin=dict(l=40, r=40, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', transition={'duration': 300, 'easing': 'cubic-in-out'})
    return fig

def build_altitude_chart(gps_df):
    from analytics.metrics import downsample_df
    df = downsample_df(gps_df, 1000)
    t = (df['TimeUS'] - df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure(go.Scatter(x=t, y=df['Alt'], mode='lines', fill='tozeroy', name='Alt', line=dict(color='#58a6ff', width=2)))
    fig.update_layout(template='plotly_dark', title='GPS Altitude', xaxis_title='Time (s)', yaxis_title='Meters', height=300, margin=dict(l=40, r=20, t=40, b=40))
    return fig

def build_speed_comparison_chart(imu_df, att_df, gps_df):
    if imu_df is None or att_df is None or gps_df is None or 'VZ' not in gps_df.columns: return None
    from analytics.metrics import trapz_integrate, downsample_df
    merged = pd.merge_asof(imu_df[['TimeUS', 'AccX', 'AccY', 'AccZ']], att_df[['TimeUS', 'Roll', 'Pitch']], on='TimeUS')
    r, p = np.radians(merged['Roll'].values), np.radians(merged['Pitch'].values)
    az_e = merged['AccX'].values * np.sin(-p) + merged['AccY'].values * np.sin(r) * np.cos(p) + merged['AccZ'].values * np.cos(r) * np.cos(p)
    v_z_imu = trapz_integrate(az_e + 9.80665, merged['TimeUS'].values, detrend=True)
    m_ds = downsample_df(merged, 1000)
    v_df = pd.DataFrame({'v': np.abs(v_z_imu)})
    v_ds = downsample_df(pd.DataFrame({'v': v_df['v'].rolling(window=20, center=True).mean().values}), 1000)['v'].values
    g_ds = downsample_df(gps_df, 1000)
    t_imu = (m_ds['TimeUS'].values - gps_df['TimeUS'].iloc[0]) / 1e6
    t_gps = (g_ds['TimeUS'].values - gps_df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_gps, y=g_ds['VZ'].abs(), mode='lines', name='GPS VZ', line=dict(color='gray', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=t_imu, y=v_ds, mode='lines', name='IMU VZ', line=dict(color='#ff4b4b', width=2.5)))
    fig.update_layout(template='plotly_dark', title='Vertical Speed Accuracy', xaxis_title='Time (s)', yaxis_title='m/s', height=350, margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.1))
    return fig

def build_attitude_tracking_chart(att_df):
    if att_df is None or 'DesRoll' not in att_df.columns: return None
    from analytics.metrics import downsample_df
    df = downsample_df(att_df, 1500)
    t = (df['TimeUS'] - df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=df['DesRoll'], mode='lines', name='Desired', line=dict(color='rgba(255,255,255,0.3)', width=1, dash='dot')))
    fig.add_trace(go.Scatter(x=t, y=df['Roll'].rolling(window=10, center=True).mean(), mode='lines', name='Actual', line=dict(color='#00d4ff', width=2)))
    fig.update_layout(template='plotly_dark', title='Roll Tracking Quality', xaxis_title='Time (s)', yaxis_title='Deg', height=300, margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.1))
    return fig

def build_baro_vs_gps_chart(baro_df, gps_df):
    if baro_df is None or 'Alt' not in baro_df.columns: return None
    from analytics.metrics import downsample_df
    b, g = downsample_df(baro_df, 1000), downsample_df(gps_df, 1000)
    t0 = gps_df['TimeUS'].iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=(g['TimeUS']-t0)/1e6, y=g['Alt'], mode='lines', name='GPS Alt', line=dict(color='#58a6ff', width=1.5, dash='dash')))
    fig.add_trace(go.Scatter(x=(b['TimeUS']-t0)/1e6, y=b['Alt'], mode='lines', name='Baro Alt', line=dict(color='#ff9500', width=2)))
    fig.update_layout(template='plotly_dark', title='Altitude: GPS vs Baro', xaxis_title='Time (s)', yaxis_title='Meters', height=300, margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.1))
    return fig

def build_battery_chart(bat_df, gps_df):
    if bat_df is None or 'Volt' not in bat_df.columns: return None
    from analytics.metrics import downsample_df
    df = downsample_df(bat_df, 1000)
    t = (df['TimeUS'] - gps_df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=df['Volt'], mode='lines', name='Voltage', line=dict(color='#ffcc00', width=2)))
    if 'Curr' in df.columns: fig.add_trace(go.Scatter(x=t, y=df['Curr'], mode='lines', name='Current', line=dict(color='#ff4b4b', width=1.5), yaxis='y2'))
    fig.update_layout(template='plotly_dark', title='Battery Health', xaxis_title='Time (s)', yaxis_title='V', height=300, margin=dict(l=40, r=20, t=40, b=40), yaxis2=dict(title='A', overlaying='y', side='right', showgrid=False), legend=dict(orientation="h", y=1.1))
    return fig

def build_vibration_chart(vibe_df):
    if vibe_df is None or 'VibeX' not in vibe_df.columns: return None
    from analytics.metrics import downsample_df
    df = downsample_df(vibe_df, 1000)
    t = (df['TimeUS'] - df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure()
    for ax, c in zip(['VibeX', 'VibeY', 'VibeZ'], ['#ffcc00', '#ff00ff', '#00ffcc']): fig.add_trace(go.Scatter(x=t, y=df[ax], mode='lines', name=ax, line=dict(color=c, width=1.2)))
    fig.update_layout(template='plotly_dark', title='Structural Vibrations', xaxis_title='Time (s)', yaxis_title='m/s²', height=300, margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.1))
    return fig
