import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pytest
from analytics.metrics import haversine, trapz_integrate

def test_haversine():
    # Відстань між Києвом та Львовом приблизно 468 км
    lat1, lon1 = 50.4501, 30.5234
    lat2, lon2 = 49.8397, 24.0297
    dist = haversine(lat1, lon1, lat2, lon2)
    assert 460000 < dist < 480000

def test_trapz_integrate():
    # Стале прискорення 1 м/с2 протягом 10 секунд
    acc = np.ones(10)
    times = np.linspace(0, 9 * 1e6, 10) # 0 to 9 seconds in microseconds
    velocities = trapz_integrate(acc, times)
    # Кінцева швидкість має бути 9 м/с
    assert velocities[-1] == pytest.approx(9.0)

def test_trapz_integrate_zupt():
    # ZUPT: 10 samples з нульовим прискоренням — швидкість має скинутись до 0
    acc = np.zeros(10)
    times = np.arange(10) * 1e6
    velocities = trapz_integrate(acc, times)
    assert velocities[-1] == 0.0

def test_trapz_integrate_zupt_resets_after_drift():
    # Спочатку прискорення 1 м/с² (5 секунд), потім спокій (10 семплів)
    acc = np.concatenate([np.ones(5), np.zeros(10)])
    times = np.arange(15) * 1e6
    velocities = trapz_integrate(acc, times)
    # Після зони спокою швидкість має бути 0
    assert velocities[-1] == 0.0
