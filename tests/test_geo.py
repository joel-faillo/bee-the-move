from services.geo import GeoAdminService


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
            ]
        }


class FakeCantonHttp:
    def get_json(self, *_args, **_kwargs):
        return {
            "results": [
                {"attributes": {"ak": "SG", "name": "St. Gallen"}}
            ]
        }


def test_geocode_prefers_a_place_over_an_unrelated_gazetteer_result():
    result = GeoAdminService(FakeHttp()).geocode("San G")
    assert result["name"] == "San Gallo (SG)"


def test_suggestions_include_places_and_postal_codes_only():
    results = GeoAdminService(FakeHttp()).suggest("9000")
    assert [item["kind"] for item in results] == ["Place", "Postal code (CAP)"]
    assert results[1]["label"] == "9000 - St. Gallen"


def test_canton_is_resolved_from_official_boundary_layer():
    assert GeoAdminService(FakeCantonHttp()).canton(47.42, 9.37) == {
        "code": "SG",
        "name": "St. Gallen",
    }
