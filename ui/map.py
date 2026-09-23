"""MapLibre map embedded in Streamlit with the official swisstopo style."""

from __future__ import annotations

import json
import math

STYLE_URL = "https://vectortiles.geo.admin.ch/styles/ch.swisstopo.lightbasemap.vt/style.json"


def map_html(result: dict, selected_name: str | None = None) -> str:
    origin = result["origin"]
    candidates = []
    seen = set()
    for candidate in result.get("results", []):
        key = round(candidate["lat"], 5), round(candidate["lon"], 5)
        if key in seen or candidate.get("is_origin_area"):
            continue
        seen.add(key)
        candidates.append(
            {
                "type": "Feature",
                "properties": {
                    "name": candidate["name"],
                    "score": candidate["score"],
                    "selected": candidate["name"] == selected_name,
                },
                "geometry": {"type": "Point", "coordinates": [candidate["lon"], candidate["lat"]]},
            }
        )
    origin_feature = {
        "type": "Feature",
        "properties": {"name": origin["name"]},
        "geometry": {"type": "Point", "coordinates": [origin["lon"], origin["lat"]]},
    }
    circle = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [_circle(origin["lat"], origin["lon"], result["radius_km"])],
        },
    }
    forage = [
        {
            "type": "Feature",
            "properties": {"name": point["name"], "category": point["category"]},
            "geometry": {"type": "Point", "coordinates": [point["lon"], point["lat"]]},
        }
        for point in result.get("forage_map", [])[:400]
    ]
    phenology = result.get("phenology_station") or {}
    phenology_features = []
    if phenology.get("lat") is not None and phenology.get("lon") is not None:
        phenology_features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": phenology.get("name", "Phenology station"),
                    "detail": f"Nearest observation station · {phenology.get('distance_km', '?')} km",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [phenology["lon"], phenology["lat"]],
                },
            }
        )
    pollen = result.get("pollen") or {}
    pollen_features = []
    if pollen.get("available") and pollen.get("lat") is not None:
        pollen_features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": pollen.get("station", "Pollen station"),
                    "detail": f"Current pollen context · {pollen.get('station_distance_km', '?')} km",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [pollen["lon"], pollen["lat"]],
                },
            }
        )
    payload = json.dumps(
        {
            "origin": origin_feature,
            "candidates": {"type": "FeatureCollection", "features": candidates},
            "radius": circle,
            "forage": {"type": "FeatureCollection", "features": forage},
            "forageCategories": sorted({item["properties"]["category"] for item in forage}),
            "phenology": {"type": "FeatureCollection", "features": phenology_features},
            "pollen": {"type": "FeatureCollection", "features": pollen_features},
        }
    )
    return f"""
<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://unpkg.com/maplibre-gl@5.7.1/dist/maplibre-gl.css" rel="stylesheet">
<style>
html,body,#map{{height:100%;margin:0}}
.maplibregl-popup-content{{font:14px system-ui;padding:9px 12px}}
.layers{{font:13px system-ui;background:#fff;padding:10px 12px;border-radius:6px;box-shadow:0 1px 4px #0004;min-width:190px}}
.layers strong{{display:block;margin-bottom:6px}} .layers label{{display:block;margin:5px 0;cursor:pointer}}
.layers select{{width:100%;margin-top:5px;padding:4px;border:1px solid #cbd5ce;border-radius:4px}}
</style>
</head><body><div id="map"></div>
<script src="https://unpkg.com/maplibre-gl@5.7.1/dist/maplibre-gl.js"></script>
<script>
const data={payload};
const map=new maplibregl.Map({{container:'map',style:'{STYLE_URL}',center:[{origin['lon']},{origin['lat']}],zoom:8}});
map.addControl(new maplibregl.NavigationControl(),'top-right');
class LayerControl {{
  onAdd(map) {{
    this.map=map; this.container=document.createElement('div');
    this.container.className='maplibregl-ctrl layers';
    this.container.innerHTML=`<strong>Map layers</strong>
      <label><input type="checkbox" data-layer="candidates" checked> Recommended areas</label>
      <label><input type="checkbox" data-layer="radius-line,radius-fill" checked> Search radius</label>
      <label><input type="checkbox" data-layer="phenology" checked> Phenology station</label>
      <label><input type="checkbox" data-layer="forage"> Agricultural forage points</label>
      <label><input type="checkbox" data-layer="pollen"> Pollen station</label>
      <select id="forage-category"><option value="">All forage categories</option></select>`;
    const select=this.container.querySelector('#forage-category');
    for (const category of data.forageCategories) {{
      const option=document.createElement('option'); option.value=category; option.textContent=category; select.appendChild(option);
    }}
    this.container.querySelectorAll('input').forEach(input=>input.addEventListener('change',()=>{{
      for (const layer of input.dataset.layer.split(',')) if (map.getLayer(layer)) map.setLayoutProperty(layer,'visibility',input.checked?'visible':'none');
    }}));
    select.addEventListener('change',()=>map.setFilter('forage',select.value?['==',['get','category'],select.value]:null));
    return this.container;
  }}
  onRemove() {{this.container.remove(); this.map=undefined;}}
}}
map.on('load',()=>{{
  map.addSource('radius',{{type:'geojson',data:data.radius}});
  map.addLayer({{id:'radius-fill',type:'fill',source:'radius',paint:{{'fill-color':'#f2c230','fill-opacity':0.08}}}});
  map.addLayer({{id:'radius-line',type:'line',source:'radius',paint:{{'line-color':'#1b5e3a','line-width':2,'line-dasharray':[3,2]}}}});
  map.addSource('forage',{{type:'geojson',data:data.forage}});
  map.addLayer({{id:'forage',type:'circle',source:'forage',layout:{{visibility:'none'}},paint:{{'circle-radius':3,'circle-color':'#55a868','circle-opacity':0.5}}}});
  map.addSource('phenology',{{type:'geojson',data:data.phenology}});
  map.addLayer({{id:'phenology',type:'circle',source:'phenology',paint:{{'circle-radius':8,'circle-color':'#7c3aed','circle-stroke-color':'#fff','circle-stroke-width':2}}}});
  map.addSource('pollen',{{type:'geojson',data:data.pollen}});
  map.addLayer({{id:'pollen',type:'circle',source:'pollen',layout:{{visibility:'none'}},paint:{{'circle-radius':8,'circle-color':'#2389da','circle-stroke-color':'#fff','circle-stroke-width':2}}}});
  map.addSource('candidates',{{type:'geojson',data:data.candidates}});
  map.addLayer({{id:'candidates',type:'circle',source:'candidates',paint:{{'circle-radius':['case',['get','selected'],9,7],'circle-color':['case',['get','selected'],'#f2b705','#2d8a52'],'circle-stroke-color':'#ffffff','circle-stroke-width':2}}}});
  map.addSource('origin',{{type:'geojson',data:data.origin}});
  map.addLayer({{id:'origin',type:'circle',source:'origin',paint:{{'circle-radius':7,'circle-color':'#111111','circle-stroke-color':'#ffffff','circle-stroke-width':2}}}});
  for (const layer of ['origin','candidates','phenology','pollen','forage']) map.on('click',layer,e=>{{const p=e.features[0].properties; new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>${{p.name}}</b>${{p.score?`<br>BeeScore ${{p.score}}/100`:''}}${{p.detail?`<br>${{p.detail}}`:''}}${{p.category?`<br>${{p.category}}`:''}}`).addTo(map)}});
  // Add the control only after every layer exists, so its switches always
  // refer to a valid MapLibre layer.
  map.addControl(new LayerControl(),'top-left');
}});
</script></body></html>"""


def _circle(lat: float, lon: float, radius_km: float, points: int = 72) -> list[list[float]]:
    coordinates = []
    for index in range(points + 1):
        angle = 2 * math.pi * index / points
        dlat = radius_km * math.sin(angle) / 110.574
        dlon = radius_km * math.cos(angle) / (111.320 * math.cos(math.radians(lat)))
        coordinates.append([lon + dlon, lat + dlat])
    return coordinates
