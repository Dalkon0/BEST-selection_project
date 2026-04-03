import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# WGS-84 ellipsoid constants
_A  = 6378137.0          # semi-major axis, metres
_E2 = 0.00669437999014   # eccentricity squared


def wgs84_to_ecef(lat, lon, alt):
    """Convert WGS-84 geodetic coordinates to ECEF (Earth-Centred Earth-Fixed).

    Parameters may be scalars or numpy arrays (degrees, degrees, metres).
    Returns (X, Y, Z) in metres.
    """
    phi = np.radians(lat)
    lam = np.radians(lon)
    N = _A / np.sqrt(1 - _E2 * np.sin(phi) ** 2)
    x = (N + alt) * np.cos(phi) * np.cos(lam)
    y = (N + alt) * np.cos(phi) * np.sin(lam)
    z = (N * (1 - _E2) + alt) * np.sin(phi)
    return x, y, z


def ecef_to_enu(x, y, z, lat0, lon0, alt0):
    """Rotate ECEF coordinates to a local ENU frame centred at (lat0, lon0, alt0).

    (x, y, z) may be arrays; reference point is scalar.
    Returns (E, N, U) in metres.
    """
    x0, y0, z0 = wgs84_to_ecef(lat0, lon0, alt0)
    phi = np.radians(lat0)
    lam = np.radians(lon0)
    dx, dy, dz = x - x0, y - y0, z - z0
    E = -np.sin(lam) * dx + np.cos(lam) * dy
    N = -np.sin(phi) * np.cos(lam) * dx - np.sin(phi) * np.sin(lam) * dy + np.cos(phi) * dz
    U =  np.cos(phi) * np.cos(lam) * dx + np.cos(phi) * np.sin(lam) * dy + np.sin(phi) * dz
    return E, N, U


def gps_to_enu(gps_df):
    """Convert GPS coordinates to local ENU (East-North-Up) system.

    Args:
        gps_df: DataFrame with Lat, Lng columns (and optionally Alt, TimeUS).

    Returns:
        DataFrame with added E_m, N_m, U_m columns (metres from first valid point).

    Raises:
        ValueError: If required columns are missing or no valid coordinates found.
    """
    df = gps_df.copy()

    for col in ('Lat', 'Lng'):
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    if len(df) == 0:
        logger.warning("Empty GPS dataframe, returning as-is")
        df['E_m'] = df['N_m'] = df['U_m'] = pd.Series(dtype=float)
        return df

    valid_mask = df['Lat'].notna() & df['Lng'].notna()
    if not valid_mask.any():
        raise ValueError("No valid GPS coordinates found")

    origin = df[valid_mask].iloc[0]
    lat0 = float(origin['Lat'])
    lon0 = float(origin['Lng'])
    alt0 = float(origin['Alt']) if 'Alt' in df.columns and pd.notna(origin.get('Alt')) else 0.0

    lats = df['Lat'].fillna(lat0).values.astype(float)
    lons = df['Lng'].fillna(lon0).values.astype(float)
    alts = df['Alt'].fillna(alt0).values.astype(float) if 'Alt' in df.columns else np.zeros(len(df))

    x, y, z = wgs84_to_ecef(lats, lons, alts)
    E, N, U = ecef_to_enu(x, y, z, lat0, lon0, alt0)

    df['E_m'] = E
    df['N_m'] = N
    df['U_m'] = U
    return df
