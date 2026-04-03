import folium
import pandas as pd
import numpy as np

def build_map(gps_df, gps_df2=None, label1='Log A', label2='Log B'):
    lats, lngs = [pd.to_numeric(gps_df[c], errors='coerce').values for c in ['Lat', 'Lng']]
    m = folium.Map(location=[float(np.nanmean(lats)), float(np.nanmean(lngs))], zoom_start=16, tiles='OpenStreetMap')
    folium.TileLayer('CartoDB positron', name='Світла карта').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Темна карта').add_to(m)

    # First track — speed-colored
    if 'Spd' in gps_df.columns:
        speeds = pd.to_numeric(gps_df['Spd'], errors='coerce').fillna(0).values
        max_spd = speeds.max() if speeds.max() > 0 else 1.0
        for i in range(len(lats) - 1):
            folium.PolyLine(locations=[[lats[i], lngs[i]], [lats[i+1], lngs[i+1]]], color=_speed_to_color(speeds[i]/max_spd), weight=4, opacity=0.85, tooltip=label1).add_to(m)
    folium.Marker(location=[float(lats[0]), float(lngs[0])], icon=folium.Icon(color='green', icon='play', prefix='fa'), tooltip=f'{label1} start').add_to(m)
    folium.Marker(location=[float(lats[-1]), float(lngs[-1])], icon=folium.Icon(color='red', icon='stop', prefix='fa'), tooltip=f'{label1} end').add_to(m)

    # Second track — blue
    if gps_df2 is not None:
        lats2, lngs2 = [pd.to_numeric(gps_df2[c], errors='coerce').values for c in ['Lat', 'Lng']]
        folium.PolyLine(locations=list(zip(lats2.tolist(), lngs2.tolist())), color='#58a6ff', weight=4, opacity=0.8, tooltip=label2).add_to(m)
        folium.Marker(location=[float(lats2[0]), float(lngs2[0])], icon=folium.Icon(color='blue', icon='play', prefix='fa'), tooltip=f'{label2} start').add_to(m)
        folium.Marker(location=[float(lats2[-1]), float(lngs2[-1])], icon=folium.Icon(color='darkblue', icon='stop', prefix='fa'), tooltip=f'{label2} end').add_to(m)

    folium.LayerControl().add_to(m)
    return m

def _speed_to_color(norm):
    r = int(255 * min(1, norm * 2))
    g = int(255 * min(1, 2 - norm * 2))
    return f'#{r:02x}{g:02x}00'

def generate_kml(gps_df):
    df = gps_df.copy().dropna(subset=['Lat', 'Lng'])
    coords = df[['Lng', 'Lat', 'Alt']].astype(str).agg(','.join, axis=1)
    coords_str = '\n                '.join(coords)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Style id="s"><LineStyle><color>ff0000ff</color><width>4</width></LineStyle><PolyStyle><color>400000ff</color></PolyStyle></Style>
    <Placemark><styleUrl>#s</styleUrl><LineString><extrude>1</extrude><tessellate>1</tessellate><altitudeMode>absolute</altitudeMode><coordinates>{coords_str}</coordinates></LineString></Placemark>
  </Document>
</kml>"""
