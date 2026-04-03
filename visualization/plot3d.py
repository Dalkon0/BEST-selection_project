import plotly.graph_objects as go
import pandas as pd
import numpy as np

def build_3d_track(gps_enu_df, color_by='speed', show_anomalies=True):
    from analytics.metrics import downsample_df
    df = downsample_df(gps_enu_df, 3000).copy()
    
    if color_by == 'speed' and 'Spd' in df.columns:
        color_values = pd.to_numeric(df['Spd'], errors='coerce').fillna(0).values
        colorbar_title, colorscale = 'Швидкість (м/с)', 'Viridis'
    else:
        t = pd.to_numeric(df['TimeUS'], errors='coerce').values
        color_values = (t - t.min()) / (t.max() - t.min() + 1e-9)
        colorbar_title, colorscale = 'Час польоту', 'Plasma'
        
    track = go.Scatter3d(
        x=df['E_m'], y=df['N_m'], z=df['U_m'],
        mode='lines',
        line=dict(color=color_values, colorscale=colorscale, width=5, 
                  colorbar=dict(title=colorbar_title, thickness=15, len=0.6)),
        name='Траєкторія',
        hovertemplate='E: %{x:.1f}m<br>N: %{y:.1f}m<br>U: %{z:.1f}m<extra></extra>'
    )
    
    start = go.Scatter3d(x=[df['E_m'].iloc[0]], y=[df['N_m'].iloc[0]], z=[df['U_m'].iloc[0]], 
                        mode='markers', marker=dict(size=8, color='green'), name='Старт')
    finish = go.Scatter3d(x=[df['E_m'].iloc[-1]], y=[df['N_m'].iloc[-1]], z=[df['U_m'].iloc[-1]], 
                         mode='markers', marker=dict(size=8, color='red'), name='Фініш')
    shadow = go.Scatter3d(x=df['E_m'], y=df['N_m'], z=np.zeros(len(df)), 
                         mode='lines', line=dict(color='gray', width=1, dash='dot'), 
                         name='Проекція', opacity=0.3)
    
    data = [shadow, track, start, finish]
    
    if show_anomalies:
        anomalies = []
        # Sharp climb detection
        if 'VZ' in df.columns:
            vz = df['VZ'].values
            sharp_climb_idx = np.where(vz > 5.0)[0]
            if len(sharp_climb_idx) > 0:
                anomalies.append(go.Scatter3d(
                    x=df['E_m'].iloc[sharp_climb_idx], y=df['N_m'].iloc[sharp_climb_idx], z=df['U_m'].iloc[sharp_climb_idx],
                    mode='markers', marker=dict(size=6, color='orange', symbol='diamond'),
                    name='Різкий набір', hovertext='Швидкий підйом > 5м/с'
                ))
        
        # High vibration detection (if vibe data available and synced)
        # Note: In a real scenario we'd need vibe synced to GPS ENU. 
        # For now, let's stick to GPS-derived anomalies or simple speed spikes.
        if 'Spd' in df.columns:
            spd = df['Spd'].values
            overspeed_idx = np.where(spd > 20.0)[0] # Example threshold 20m/s
            if len(overspeed_idx) > 0:
                anomalies.append(go.Scatter3d(
                    x=df['E_m'].iloc[overspeed_idx], y=df['N_m'].iloc[overspeed_idx], z=df['U_m'].iloc[overspeed_idx],
                    mode='markers', marker=dict(size=6, color='red', symbol='cross'),
                    name='Перевищення швидкості', hovertext='Швидкість > 20м/с'
                ))
        data.extend(anomalies)

    fig = go.Figure(data=data)
    fig.update_layout(
        template='plotly_dark', 
        title='3D-траєкторія БПЛА', 
        scene=dict(
            xaxis_title='E (m)', yaxis_title='N (m)', zaxis_title='U (m)', 
            aspectmode='auto',
            camera=dict(
                eye=dict(x=0.1, y=-2.5, z=0.1)
            )
        ), 
        margin=dict(l=5, r=5, b=5, t=40), 
        height=700,
        legend=dict(yanchor="top", y=0.95, xanchor="left", x=0.05)
    )
    return fig

def build_3d_track_animation(gps_enu_df):
    from analytics.metrics import downsample_df
    df = downsample_df(gps_enu_df, 300).copy()
    
    fig = go.Figure(
        data=[
            # Static path
            go.Scatter3d(x=df['E_m'], y=df['N_m'], z=df['U_m'], mode='lines', 
                        line=dict(color='rgba(100,100,100,0.3)', width=2), name='Шлях'),
            # Animated drone
            go.Scatter3d(x=[df['E_m'].iloc[0]], y=[df['N_m'].iloc[0]], z=[df['U_m'].iloc[0]], 
                        mode='markers+text', marker=dict(size=8, color='yellow', symbol='circle'), 
                        text=["БПЛА"], textposition="top center", name='БПЛА'),
            # Animated shadow
            go.Scatter3d(x=[df['E_m'].iloc[0]], y=[df['N_m'].iloc[0]], z=[0], 
                        mode='markers', marker=dict(size=4, color='white', opacity=0.5), name='Проекція')
        ],
        layout=go.Layout(
            template='plotly_dark',
            scene=dict(
                xaxis_title='E (m)', yaxis_title='N (m)', zaxis_title='U (m)', 
                aspectmode='auto',
                camera=dict(
                    eye=dict(x=0.1, y=-2.5, z=0.1)
                )
            ),
            updatemenus=[dict(type="buttons", buttons=[dict(label="Play Replay", method="animate", 
                         args=[None, {"frame": {"duration": 40, "redraw": True}, "fromcurrent": True}])])],
            margin=dict(l=5, r=5, b=5, t=40),
            height=700, title='Replay польоту'
        ),
        frames=[go.Frame(data=[
            go.Scatter3d(x=[df['E_m'].iloc[i]], y=[df['N_m'].iloc[i]], z=[df['U_m'].iloc[i]]),
            go.Scatter3d(x=[df['E_m'].iloc[i]], y=[df['N_m'].iloc[i]], z=[0])
        ], traces=[1, 2]) for i in range(len(df))]
    )
    return fig

def build_comparison_3d(enu_a, enu_b, name_a="Log A", name_b="Log B"):
    from analytics.metrics import downsample_df
    df_a = downsample_df(enu_a, 2000)
    df_b = downsample_df(enu_b, 2000)
    
    fig = go.Figure()
    # Track A
    fig.add_trace(go.Scatter3d(x=df_a['E_m'], y=df_a['N_m'], z=df_a['U_m'], mode='lines', line=dict(color='#58a6ff', width=4), name=name_a))
    fig.add_trace(go.Scatter3d(x=df_a['E_m'], y=df_a['N_m'], z=np.zeros(len(df_a)), mode='lines', line=dict(color='#58a6ff', width=1), opacity=0.2, showlegend=False))
    
    # Track B
    fig.add_trace(go.Scatter3d(x=df_b['E_m'], y=df_b['N_m'], z=df_b['U_m'], mode='lines', line=dict(color='#ff7b72', width=4), name=name_b))
    fig.add_trace(go.Scatter3d(x=df_b['E_m'], y=df_b['N_m'], z=np.zeros(len(df_b)), mode='lines', line=dict(color='#ff7b72', width=1), opacity=0.2, showlegend=False))
    
    fig.update_layout(
        template='plotly_dark', title='Порівняння траєкторій',
        scene=dict(
            xaxis_title='E (m)', yaxis_title='N (m)', zaxis_title='U (m)', 
            aspectmode='auto',
            camera=dict(
                eye=dict(x=0.1, y=-2.5, z=0.1)
            )
        ),
        margin=dict(l=5, r=5, b=5, t=40), height=700
    )
    return fig

def build_altitude_chart(gps_df):
    from analytics.metrics import downsample_df
    df = downsample_df(gps_df, 1000)
    t = (df['TimeUS'] - df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure(go.Scatter(x=t, y=df['Alt'], mode='lines', fill='tozeroy', name='Висота', line=dict(color='#58a6ff', width=2)))
    fig.update_layout(template='plotly_dark', title='Висота (GPS)', xaxis_title='Час (с)', yaxis_title='Метри', height=300, margin=dict(l=40, r=20, t=40, b=40))
    return fig

def build_speed_comparison_chart(imu_df, att_df, gps_df):
    if imu_df is None or att_df is None or 'VZ' not in gps_df.columns: return None
    from analytics.metrics import trapz_integrate, downsample_df
    merged = pd.merge_asof(imu_df[['TimeUS', 'AccX', 'AccY', 'AccZ']], att_df[['TimeUS', 'Roll', 'Pitch']], on='TimeUS')
    r, p = np.radians(merged['Roll'].values), np.radians(merged['Pitch'].values)
    acc_z_earth = merged['AccX'].values * np.sin(-p) + merged['AccY'].values * np.sin(r) * np.cos(p) + merged['AccZ'].values * np.cos(r) * np.cos(p)
    v_z_imu = trapz_integrate(acc_z_earth + 9.80665, merged['TimeUS'].values, detrend=True)
    m_ds = downsample_df(merged, 1000)
    v_df = pd.DataFrame({'v': np.abs(v_z_imu)})
    v_smooth = v_df['v'].rolling(window=20, center=True).mean().values
    v_ds = downsample_df(pd.DataFrame({'v': v_smooth}), 1000)['v'].values
    g_ds = downsample_df(gps_df, 1000)
    t_imu = (m_ds['TimeUS'].values - gps_df['TimeUS'].iloc[0]) / 1e6
    t_gps = (g_ds['TimeUS'].values - gps_df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_gps, y=g_ds['VZ'].abs(), mode='lines', name='GPS VZ', line=dict(color='gray', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=t_imu, y=v_ds, mode='lines', name='IMU VZ (Filtered)', line=dict(color='#ff4b4b', width=2.5)))
    fig.update_layout(template='plotly_dark', title='Accuracy Check: Vertical Speed', xaxis_title='Час (с)', yaxis_title='м/с', height=350, margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.1))
    return fig

def build_attitude_tracking_chart(att_df):
    if att_df is None or 'DesRoll' not in att_df.columns: return None
    from analytics.metrics import downsample_df
    df = downsample_df(att_df, 1500)
    t = (df['TimeUS'] - df['TimeUS'].iloc[0]) / 1e6
    roll_smooth = df['Roll'].rolling(window=10, center=True).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=df['DesRoll'], mode='lines', name='Desired', line=dict(color='rgba(255,255,255,0.3)', width=1, dash='dot')))
    fig.add_trace(go.Scatter(x=t, y=roll_smooth, mode='lines', name='Actual (Smooth)', line=dict(color='#00d4ff', width=2)))
    fig.update_layout(template='plotly_dark', title='Control Quality: Roll Tracking', xaxis_title='Час (с)', yaxis_title='Градуси', height=300, margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.1))
    return fig

def build_baro_vs_gps_chart(baro_df, gps_df):
    if baro_df is None or 'Alt' not in baro_df.columns: return None
    from analytics.metrics import downsample_df
    b = downsample_df(baro_df, 1000)
    t_baro = (b['TimeUS'] - gps_df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure()
    g = downsample_df(gps_df, 1000)
    t_gps = (g['TimeUS'] - gps_df['TimeUS'].iloc[0]) / 1e6
    fig.add_trace(go.Scatter(x=t_gps, y=g['Alt'], mode='lines', name='GPS Alt',
        line=dict(color='#58a6ff', width=1.5, dash='dash')))
    fig.add_trace(go.Scatter(x=t_baro, y=b['Alt'], mode='lines', name='Baro Alt',
        line=dict(color='#ff9500', width=2)))
    fig.update_layout(template='plotly_dark', title='Altitude: GPS vs Barometer',
        xaxis_title='Час (с)', yaxis_title='Метри', height=300,
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(orientation="h", y=1.1))
    return fig

def build_battery_chart(bat_df, gps_df):
    if bat_df is None or 'Volt' not in bat_df.columns: return None
    from analytics.metrics import downsample_df
    df = downsample_df(bat_df, 1000)
    t = (df['TimeUS'] - gps_df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=df['Volt'], mode='lines', name='Voltage (V)',
        line=dict(color='#ffcc00', width=2)))
    if 'Curr' in df.columns:
        fig.add_trace(go.Scatter(x=t, y=df['Curr'], mode='lines', name='Current (A)',
            line=dict(color='#ff4b4b', width=1.5), yaxis='y2'))
    fig.update_layout(template='plotly_dark', title='Battery: Voltage & Current',
        xaxis_title='Час (с)', yaxis_title='Вольти (V)', height=300,
        margin=dict(l=40, r=20, t=40, b=40),
        yaxis2=dict(title='Ампери (A)', overlaying='y', side='right', showgrid=False),
        legend=dict(orientation="h", y=1.1))
    return fig

def build_vibration_chart(vibe_df):
    if vibe_df is None or 'VibeX' not in vibe_df.columns: return None
    from analytics.metrics import downsample_df
    df = downsample_df(vibe_df, 1000)
    t = (df['TimeUS'] - df['TimeUS'].iloc[0]) / 1e6
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=df['VibeX'], mode='lines', name='Vibe X', line=dict(color='#ffcc00', width=1)))
    fig.add_trace(go.Scatter(x=t, y=df['VibeY'], mode='lines', name='Vibe Y', line=dict(color='#ff00ff', width=1)))
    fig.add_trace(go.Scatter(x=t, y=df['VibeZ'], mode='lines', name='Vibe Z', line=dict(color='#00ffcc', width=1.5)))
    fig.update_layout(template='plotly_dark', title='Structural Health: Vibrations', xaxis_title='Час (с)', yaxis_title='m/s²', height=300, margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.1))
    return fig
