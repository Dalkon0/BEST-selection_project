import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scraper.dataflash import parse_log, get_gps_dataframe, get_imu_dataframe, get_attitude_dataframe, get_vibe_dataframe
from analytics.metrics import compute_metrics
from analytics.coords import gps_to_enu

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', '00000001.BIN')

if not os.path.exists(LOG_FILE):
    print(f'Файл не знайдено: {LOG_FILE}')
    exit(1)

print(f'Парсинг: {LOG_FILE}')
dataframes = parse_log(LOG_FILE)

print(f'\nЗнайдено {len(dataframes)} типів повідомлень:')
for name, df in sorted(dataframes.items()):
    print(f'   {name:8s} — {len(df):5d} рядків  |  колонки: {list(df.columns)[:6]}...')

print('\n── GPS ──────────────────────────────────────────────────')
gps_df = get_gps_dataframe(dataframes)

if gps_df is None:
    print('GPS-даних не знайдено')
    print('Доступні повідомлення:', list(dataframes.keys()))
else:
    print(f'GPS: {len(gps_df)} точок')
    print(gps_df.head(5))

    print('\n── ENU конвертація ─────────────────────────────────────')
    gps_enu = gps_to_enu(gps_df)
    print(f'Діапазон E: {gps_enu["E_m"].min():.1f} .. {gps_enu["E_m"].max():.1f} м')
    print(f'Діапазон N: {gps_enu["N_m"].min():.1f} .. {gps_enu["N_m"].max():.1f} м')
    print(f'Діапазон U: {gps_enu["U_m"].min():.1f} .. {gps_enu["U_m"].max():.1f} м')

    print('\n── Метрики польоту ─────────────────────────────────────')
    imu_df = get_imu_dataframe(dataframes)
    att_df = get_attitude_dataframe(dataframes)
    vibe_df = get_vibe_dataframe(dataframes)
    metrics = compute_metrics(gps_df, imu_df, att_df, vibe_df)

    units = {
        'total_distance_m': 'м', 'max_horiz_speed_ms': 'м/с',
        'max_vert_speed_ms': 'м/с', 'max_acceleration': 'м/с²',
        'alt_gain_m': 'м', 'total_duration_s': 'с',
        'start_alt_m': 'м', 'max_alt_m': 'м', 'imu_max_vz_ms': 'м/с',
    }
    for key, val in metrics.items():
        print(f'   {key:25s}: {val} {units.get(key, "")}')

print('\nГотово! Тепер запусти: streamlit run app.py')
