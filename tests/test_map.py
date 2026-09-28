from ui.map import map_html


def test_map_explains_and_controls_context_layers():
    result = {
        "origin": {"name": "St. Gallen", "lat": 47.424, "lon": 9.376},
        "radius_km": 50,
        "results": [],
        "forage_map": [
            {
                "name": "Extensive meadow",
                "category": "Meadows",
                "lat": 47.43,
                "lon": 9.38,
            }
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
    assert "Agricultural forage points" in html
    assert "Pollen station" in html
    assert "All forage categories" in html
    assert "Meadows" in html
    assert 'class="layer-options" hidden' in html
    assert 'aria-expanded="false"' in html
