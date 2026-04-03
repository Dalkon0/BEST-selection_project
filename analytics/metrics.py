import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1-a))

# Alias used by tests and external callers
haversine = haversine_distance


def filter_gps(df):
    """Remove zero/invalid GPS coordinates and statistical outliers (> 3σ)."""
    if df is None or len(df) == 0:
        return df
    df = df[(df['Lat'] != 0) & (df['Lng'] != 0)].copy()
    for col in ['Lat', 'Lng']:
        if col in df.columns and len(df) > 3:
            mean, std = df[col].mean(), df[col].std()
            if std > 0:
                df = df[np.abs(df[col] - mean) <= 3 * std]
    return df.reset_index(drop=True)


def compute_sampling_rate(df):
    """Return median sampling rate in Hz from TimeUS column, or None if insufficient data."""
    if df is None or 'TimeUS' not in df.columns or len(df) < 2:
        return None
    t = pd.to_numeric(df['TimeUS'], errors='coerce').dropna().values
    if len(t) < 2:
        return None
    median_dt_us = np.median(np.diff(t))
    if median_dt_us <= 0:
        return None
    return round(1e6 / median_dt_us, 2)


def total_distance(df):
    """Compute total Haversine distance (metres) from a GPS DataFrame."""
    _gps = df[['Lat', 'Lng']].apply(pd.to_numeric, errors='coerce').dropna()
    if len(_gps) < 2:
        return 0.0
    return float(haversine_distance(
        _gps['Lat'].iloc[:-1].values, _gps['Lng'].iloc[:-1].values,
        _gps['Lat'].iloc[1:].values,  _gps['Lng'].iloc[1:].values
    ).sum())

def trapz_integrate(values, times_us, detrend=False):
    """Trapezoidal integration of acceleration → velocity.
    values must be Earth-frame acceleration with gravity already removed (i.e. az_earth + g).
    ZUPT: zero velocity when Earth-frame residual acceleration is near zero for a window.
    """
    values = np.asarray(values, dtype=np.float64)
    times_us = np.asarray(times_us, dtype=np.float64)
    if len(values) != len(times_us) or len(values) < 2:
        return np.zeros(len(values))
    dt = np.diff(times_us) / 1e6
    acc = values.copy()
    velocities = np.zeros(len(acc))
    # ZUPT: input is (az_earth + 9.81), so at rest it's near 0
    zupt_window, zupt_threshold = 5, 0.15
    for i in range(1, len(acc)):
        velocities[i] = velocities[i-1] + (acc[i-1] + acc[i]) / 2.0 * dt[i-1]
        if i >= zupt_window and np.all(np.abs(acc[i - zupt_window:i]) < zupt_threshold):
            velocities[i] = 0.0
    if detrend and len(velocities) > 2:
        velocities -= np.linspace(0, velocities[-1], len(velocities))
    return velocities

def downsample_df(df, target_points=3000):
    if df is None or len(df) <= target_points:
        return df
    n = len(df)
    step = max(1, n // target_points)
    idx = np.arange(0, n, step)
    extra = []
    for col in ['Alt', 'Spd', 'VZ', 'AccZ', 'VibeX', 'VibeY', 'VibeZ']:
        if col in df.columns:
            try:
                v = pd.to_numeric(df[col], errors='coerce').values
                extra.extend([np.nanargmax(v), np.nanargmin(v)])
            except Exception as e:
                logger.debug(f"downsample peak detection failed for {col}: {e}")
    all_idx = np.unique(np.concatenate([idx, extra]))
    return df.iloc[all_idx[all_idx < n]].sort_index()

def compute_metrics(gps_df, imu_df, att_df, vibe_df):
    m = {}
    if gps_df is None or len(gps_df) < 2: return m
    df = gps_df.copy()
    df['TimeUS'] = pd.to_numeric(df['TimeUS'], errors='coerce')
    m['total_duration_s'] = round((df['TimeUS'].iloc[-1] - df['TimeUS'].iloc[0]) / 1e6, 1)
    # Haversine: use consecutive clean pairs with aligned indices
    _gps = df[['Lat', 'Lng']].apply(pd.to_numeric, errors='coerce').dropna()
    if len(_gps) >= 2:
        m['total_distance_m'] = round(haversine_distance(
            _gps['Lat'].iloc[:-1].values, _gps['Lng'].iloc[:-1].values,
            _gps['Lat'].iloc[1:].values,  _gps['Lng'].iloc[1:].values
        ).sum(), 1)
    else:
        m['total_distance_m'] = 0.0
    if 'Alt' in df.columns:
        v = pd.to_numeric(df['Alt'], errors='coerce')
        m['max_alt_m'] = round(float(v.max()), 1)
        m['start_alt_m'] = round(float(v.iloc[0]), 1)
        m['alt_gain_m'] = round(m['max_alt_m'] - m['start_alt_m'], 1)
    if 'Spd' in df.columns:
        try:
            m['max_horiz_speed_ms'] = round(float(pd.to_numeric(df['Spd'], errors='coerce').max()), 2)
        except Exception as e:
            logger.warning(f"max_horiz_speed_ms failed: {e}")
    if 'VZ' in df.columns:
        try:
            m['max_vert_speed_ms'] = round(float(pd.to_numeric(df['VZ'], errors='coerce').abs().max()), 2)
        except Exception as e:
            logger.warning(f"max_vert_speed_ms failed: {e}")
    if imu_df is not None and all(c in imu_df.columns for c in ['AccX', 'AccY', 'AccZ']):
        try:
            ax, ay, az = [pd.to_numeric(imu_df[c], errors='coerce').values for c in ['AccX', 'AccY', 'AccZ']]
            if att_df is not None and 'Roll' in att_df.columns:
                merged = pd.merge_asof(
                    imu_df[['TimeUS', 'AccX', 'AccY', 'AccZ']].sort_values('TimeUS'),
                    att_df[['TimeUS', 'Roll', 'Pitch']].sort_values('TimeUS'),
                    on='TimeUS'
                )
                r, p = np.radians(merged['Roll'].values), np.radians(merged['Pitch'].values)
                ax_m = pd.to_numeric(merged['AccX'], errors='coerce').values
                ay_m = pd.to_numeric(merged['AccY'], errors='coerce').values
                az_m = pd.to_numeric(merged['AccZ'], errors='coerce').values
                # Earth-frame Up component (for vertical velocity integration)
                az_e = ax_m * np.sin(-p) + ay_m * np.sin(r) * np.cos(p) + az_m * np.cos(r) * np.cos(p)
                m['imu_max_vz_ms'] = round(float(np.abs(trapz_integrate(az_e + 9.80665, merged['TimeUS'].values)).max()), 2)
                # Correct dynamic acceleration: subtract gravity vector in body frame.
                # g_body = R^T * [0,0,-g]_ENU = [g*sin(p), -g*sin(r)*cos(p), -g*cos(r)*cos(p)]
                G = 9.80665
                dyn_x = ax_m - G * np.sin(p)
                dyn_y = ay_m + G * np.sin(r) * np.cos(p)
                dyn_z = az_m + G * np.cos(r) * np.cos(p)
                m['max_acceleration'] = round(float(np.nanpercentile(np.sqrt(dyn_x**2 + dyn_y**2 + dyn_z**2), 95)), 2)
            else:
                # No attitude data: scalar approximation (valid only for near-level flight)
                m['max_acceleration'] = round(float(np.nanpercentile(np.abs(np.sqrt(ax**2 + ay**2 + az**2) - 9.80665), 95)), 2)
        except Exception as e:
            logger.warning(f"IMU metrics failed: {e}")
    if vibe_df is not None and 'VibeX' in vibe_df.columns:
        try:
            # 95th percentile to reject noise spikes
            vals = np.concatenate([
                pd.to_numeric(vibe_df[c], errors='coerce').dropna().values
                for c in ['VibeX', 'VibeY', 'VibeZ'] if c in vibe_df.columns
            ])
            m['max_vibration'] = round(float(np.nanpercentile(vals, 95)), 2)
        except Exception as e:
            logger.warning(f"max_vibration failed: {e}")
    return m

def compare_metrics(ma, mb):
    res = {}
    keys = ['total_distance_m', 'total_duration_s', 'max_horiz_speed_ms', 'max_vert_speed_ms', 'max_alt_m', 'max_acceleration', 'imu_max_vz_ms', 'max_vibration']
    for k in keys:
        va, vb = ma.get(k, 0) or 0, mb.get(k, 0) or 0
        diff = vb - va
        pct = (diff / va * 100) if va != 0 else 0
        res[k] = {'a': va, 'b': vb, 'diff': diff, 'pct': pct}
    return res
