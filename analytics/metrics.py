import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlam = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def total_distance(gps_df):
    """Calculate total flight distance using Haversine formula.
    
    Args:
        gps_df: DataFrame with Lat and Lng columns
        
    Returns:
        Total distance in meters
        
    Raises:
        ValueError: If required columns are missing or empty
    """
    if gps_df is None or len(gps_df) < 2:
        return 0.0
    
    lats, lngs = gps_df['Lat'].values, gps_df['Lng'].values
    
    # Filter out invalid coordinates
    valid_mask = np.isfinite(lats) & np.isfinite(lngs)
    lats, lngs = lats[valid_mask], lngs[valid_mask]
    
    if len(lats) < 2:
        logger.warning("Insufficient valid GPS points for distance calculation")
        return 0.0
    
    dist = 0.0
    for i in range(1, len(lats)):
        dist += haversine(lats[i-1], lngs[i-1], lats[i], lngs[i])
    return dist

def trapz_integrate(values, times_us, detrend=False):
    """Integrate acceleration to velocity using trapezoidal rule.

    Args:
        values: Acceleration values (m/s²)
        times_us: Timestamps in microseconds
        detrend: If True, apply linear drift correction assuming v_start = v_end = 0
                 (valid when drone takes off and lands at rest)

    Returns:
        Velocity array (m/s)
    """
    values = np.asarray(values, dtype=np.float64)
    times_us = np.asarray(times_us, dtype=np.float64)

    if len(values) != len(times_us) or len(values) < 2:
        return np.zeros(len(values))

    dt = np.diff(times_us) / 1e6
    acc = values.copy()
    velocities = np.zeros(len(acc))

    zupt_window = 5
    zupt_threshold = 0.08

    for i in range(1, len(acc)):
        velocities[i] = velocities[i-1] + (acc[i-1] + acc[i]) / 2.0 * dt[i-1]
        # ZUPT: if acceleration has been near-zero for zupt_window consecutive samples,
        # the drone is stationary — reset velocity to 0
        if i >= zupt_window and np.all(np.abs(acc[i - zupt_window:i]) < zupt_threshold):
            velocities[i] = 0.0

    if detrend and len(velocities) > 2:
        drift = np.linspace(0, velocities[-1], len(velocities))
        velocities -= drift

    return velocities

def compute_sampling_rate(df, time_col='TimeUS'):
    if df is None or time_col not in df.columns or len(df) < 2: return None
    times = pd.to_numeric(df[time_col], errors='coerce').dropna().values
    if len(times) < 2: return None
    dt_mean = np.mean(np.diff(times)) / 1e6
    return round(1.0 / dt_mean, 1) if dt_mean > 0 else None

def filter_gps(gps_df):
    """Filter GPS data to remove noise and outliers.
    
    Args:
        gps_df: Raw GPS DataFrame
        
    Returns:
        Filtered GPS DataFrame
    """
    if gps_df is None or len(gps_df) == 0:
        return gps_df
    
    df = gps_df.copy()

    # Remove zero coordinates first
    if 'Lat' in df.columns and 'Lng' in df.columns:
        df = df[(df['Lat'] != 0) & (df['Lng'] != 0)]

    # Skip leading points while GPS is still acquiring (only if Spd available)
    if len(df) > 5 and 'Spd' in df.columns:
        moving = df['Spd'].fillna(0) > 0.1
        if moving.any():
            first_valid = moving.idxmax()
            if first_valid > df.index[0]:
                df = df.loc[first_valid:].reset_index(drop=True)
    
    # Remove outliers using median-based filtering
    if len(df) > 10 and 'Lat' in df.columns and 'Lng' in df.columns:
        lat_med, lng_med = df['Lat'].median(), df['Lng'].median()
        df = df[((df['Lat'] - lat_med).abs() < 0.1) & ((df['Lng'] - lng_med).abs() < 0.1)]
    
    return df.reset_index(drop=True)

def downsample_df(df, max_points=5000):
    if df is None or len(df) <= max_points: return df
    step = len(df) // max_points
    indices = list(range(0, len(df), step))
    # Preserve peaks: include index of max/min for key columns
    for col in ('Alt', 'Spd', 'VZ', 'AccZ'):
        if col in df.columns:
            indices.append(int(df[col].idxmax()))
            indices.append(int(df[col].idxmin()))
    return df.iloc[sorted(set(indices))].reset_index(drop=True)

def compute_metrics(gps_df, imu_df=None, att_df=None, vibe_df=None):
    """Compute comprehensive flight metrics.
    
    Args:
        gps_df: GPS dataframe with Lat, Lng, Alt, Spd, VZ, TimeUS
        imu_df: IMU dataframe with AccX, AccY, AccZ, TimeUS
        att_df: Attitude dataframe with Roll, Pitch, Yaw, TimeUS
        vibe_df: Vibration dataframe with VibeX, VibeY, VibeZ
        
    Returns:
        Dictionary of computed metrics
    """
    metrics = {}
    
    # Validate GPS data
    if gps_df is None or len(gps_df) < 2:
        logger.warning("Insufficient GPS data for metrics computation")
        return {
            'total_distance_m': 0,
            'total_duration_s': None,
            'gps_sampling_hz': None,
            'imu_sampling_hz': None,
        }
    
    df = filter_gps(gps_df)
    
    if len(df) < 2:
        logger.warning("No valid GPS points after filtering")
        return {
            'total_distance_m': 0,
            'total_duration_s': None,
            'gps_sampling_hz': None,
            'imu_sampling_hz': None,
        }
    
    try:
        metrics['total_distance_m'] = round(total_distance(df), 1)
    except Exception as e:
        logger.error(f"Failed to compute distance: {e}")
        metrics['total_distance_m'] = 0
    
    if 'TimeUS' in df.columns:
        try:
            metrics['total_duration_s'] = round((df['TimeUS'].iloc[-1] - df['TimeUS'].iloc[0]) / 1e6, 1)
        except Exception as e:
            logger.error(f"Failed to compute duration: {e}")
            metrics['total_duration_s'] = None
    else:
        metrics['total_duration_s'] = None
    
    metrics['gps_sampling_hz'] = compute_sampling_rate(df)
    metrics['imu_sampling_hz'] = compute_sampling_rate(imu_df)
    
    # Altitude metrics
    if 'Alt' in df.columns:
        try:
            alt_valid = df['Alt'].dropna()
            if len(alt_valid) > 0:
                metrics['start_alt_m'] = round(float(alt_valid.iloc[0]), 1)
                metrics['max_alt_m'] = round(float(alt_valid.max()), 1)
                metrics['max_alt_gain_m'] = round(float(alt_valid.max() - alt_valid.iloc[0]), 1)
        except Exception as e:
            logger.warning(f"Failed to compute altitude metrics: {e}")
    
    # Speed metrics
    if 'Spd' in df.columns:
        try:
            metrics['max_horiz_speed_ms'] = round(float(pd.to_numeric(df['Spd'], errors='coerce').max()), 2)
        except:
            metrics['max_horiz_speed_ms'] = None
    
    if 'VZ' in df.columns:
        try:
            metrics['max_vert_speed_ms'] = round(float(pd.to_numeric(df['VZ'], errors='coerce').abs().max()), 2)
        except:
            metrics['max_vert_speed_ms'] = None
    
    # IMU metrics
    if imu_df is not None and all(c in imu_df.columns for c in ['AccX', 'AccY', 'AccZ']):
        try:
            ax, ay, az = [pd.to_numeric(imu_df[c], errors='coerce').values for c in ['AccX', 'AccY', 'AccZ']]
            if att_df is not None and 'Roll' in att_df.columns:
                merged = pd.merge_asof(imu_df[['TimeUS', 'AccX', 'AccY', 'AccZ']], att_df[['TimeUS', 'Roll', 'Pitch', 'Yaw']], on='TimeUS')
                r, p = np.radians(merged['Roll'].values), np.radians(merged['Pitch'].values)
                acc_z_earth = merged['AccX'].values * np.sin(-p) + merged['AccY'].values * np.sin(r) * np.cos(p) + merged['AccZ'].values * np.cos(r) * np.cos(p)
                v_z_imu = trapz_integrate(acc_z_earth + 9.80665, merged['TimeUS'].values)
                metrics['imu_max_vz_ms'] = round(float(np.abs(v_z_imu).max()), 2)
                metrics['max_acceleration'] = round(float(np.nanpercentile(np.abs(np.sqrt(ax**2 + ay**2 + az**2) - 9.80665), 95)), 2)
            else:
                metrics['max_acceleration'] = round(float(np.nanpercentile(np.abs(np.sqrt(ax**2 + ay**2 + az**2) - 9.81), 95)), 2)
                if 'TimeUS' in imu_df.columns:
                    metrics['imu_max_vz_ms'] = round(float(np.abs(trapz_integrate(az - np.nanmean(az[:10]), imu_df['TimeUS'].values)).max()), 2)
        except Exception as e:
            logger.warning(f"Failed to compute IMU metrics: {e}")
    
    # Vibration metrics
    if vibe_df is not None and 'VibeX' in vibe_df.columns:
        try:
            v_max = max(vibe_df['VibeX'].max(), vibe_df['VibeY'].max(), vibe_df['VibeZ'].max())
            metrics['max_vibration'] = round(float(v_max), 2)
        except:
            metrics['max_vibration'] = None
    
    return metrics

def compare_metrics(metrics_a, metrics_b):
    """Compare two sets of metrics and return a combined dictionary with deltas."""
    comparison = {}
    keys = [
        'total_distance_m', 'total_duration_s', 'max_horiz_speed_ms', 
        'max_vert_speed_ms', 'max_alt_m', 'max_acceleration', 
        'imu_max_vz_ms', 'max_vibration'
    ]
    
    for k in keys:
        val_a = metrics_a.get(k, 0) or 0
        val_b = metrics_b.get(k, 0) or 0
        diff = val_b - val_a
        pct = (diff / val_a * 100) if val_a != 0 else 0
        comparison[k] = {
            'a': val_a,
            'b': val_b,
            'diff': diff,
            'pct': pct
        }
    return comparison
