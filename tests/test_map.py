from ui.map import map_html
from services.landscape import FORAGE_CATEGORIES


def test_map_explains_and_controls_context_layers():
    result = {
        "origin": {"name": "St. Gallen", "lat": 47.424, "lon": 9.376},
        "radius_km": 50,
        "results": [],
        "forage_map": [
            {
                "name": category,
                "category": category,
                "lat": 47.43 + index / 10_000,
                "lon": 9.38 + index / 10_000,
            }
            for index, category in enumerate(FORAGE_CATEGORIES)
        ],
        "phenology_station": {
            "name": "St. Gallen",
            "lat": 47.432,
            "lon": 9.378,
            "distance_km": 1.0,
        },
        "pollen": {
            "available": True,
            "station": "Buchs",
            "lat": 47.17,
            "lon": 9.47,
            "station_distance_km": 30.0,
        },
    }

    html = map_html(result)

    assert "Phenology station" in html
    assert "Agricultural parcels near searched place" in html
    assert "Pollen station near searched place" in html
    assert "maplibre-gl@5.24.0" in html
    assert "All forage categories" in html
    for category in FORAGE_CATEGORIES:
        assert category in html
    for layer in ("radius-line,radius-fill", "candidates", "phenology", "pollen", "forage"):
        assert f'data-layer="{layer}"' in html
    assert 'class="layer-options" hidden' in html
    assert 'aria-expanded="false"' in html


def test_origin_is_not_duplicated_as_a_candidate_marker():
    result = {
        "origin": {"name": "St. Gallen", "lat": 47.424, "lon": 9.376},
        "radius_km": 20,
        "results": [
            {
                "name": "St. Gallen",
                "lat": 47.424,
                "lon": 9.376,
                "score": 50,
                "is_origin_area": True,
            }
        ],
        "forage_map": [],
        "phenology_station": None,
        "pollen": {"available": False},
    }

    html = map_html(result, "St. Gallen")

    assert '"candidates": {"type": "FeatureCollection", "features": []}' in html
