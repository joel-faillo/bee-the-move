"""AI-assisted test generation and revision: OpenAI Codex (OpenAI, n.d.-b).

See ``AI_ASSISTANCE.md`` for scope, prompts and references.
"""

from services.geo import GeoAdminService, wgs84_to_lv95


class FakeHttp:
    def get_json(self, *_args, **_kwargs):
        return {
            "results": [
                {
                    "attrs": {
                        "label": "<i>Building</i> <b>San Gian</b>",
                        "origin": "gazetteer",
                        "lat": 46.5,
                        "lon": 9.8,
                    }
                },
                {
                    "attrs": {
                        "label": "<b>San Gallo (SG)</b>",
                        "origin": "gg25",
                        "lat": 47.4236,
                        "lon": 9.3885,
                    }
                },
                {
                    "attrs": {
                        "label": "<b>9000 - St. Gallen</b>",
                        "origin": "zipcode",
                        "lat": 47.4237,
                        "lon": 9.3622,
                    }
                },
                {
                    "attrs": {
                        "label": "<b>St. Gallen</b>",
                        "origin": "district",
                        "lat": 47.4,
                        "lon": 9.3,
                    }
                },
                {
                    "attrs": {
                        "label": "<b>St. Gallen</b>",
                        "origin": "kantone",
                        "lat": 47.4,
                        "lon": 9.3,
                    }
                },
            ]
        }


class FakeCantonHttp:
    def get_json(self, *_args, **_kwargs):
        return {"results": [{"attributes": {"ak": "SG", "name": "St. Gallen"}}]}


def test_geocode_prefers_a_place_over_an_unrelated_gazetteer_result():
    result = GeoAdminService(FakeHttp()).geocode("San G")
    assert result["name"] == "San Gallo (SG)"


def test_suggestions_include_places_and_postal_codes_only():
    results = GeoAdminService(FakeHttp()).suggest("9000")
    assert [item["kind"] for item in results] == ["Place", "Postal code (CAP)"]
    assert results[1]["label"] == "9000 - St. Gallen"
    assert results[1]["postal_code"] == "9000"


def test_canton_is_resolved_from_official_boundary_layer():
    assert GeoAdminService(FakeCantonHttp()).canton(47.42, 9.37) == {
        "code": "SG",
        "name": "St. Gallen",
    }


def test_wgs84_to_lv95_matches_st_gallen():
    easting, northing = wgs84_to_lv95(47.4245, 9.3767)
    assert abs(easting - 2_746_000) < 2_000
    assert abs(northing - 1_254_000) < 2_000
