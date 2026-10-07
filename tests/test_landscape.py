"""AI-assisted test generation and revision: OpenAI Codex (OpenAI, n.d.-b).

See ``AI_ASSISTANCE.md`` for scope, prompts and references.
"""

from services.landscape import (
    AGRICULTURAL_URL,
    LandscapeService,
    _is_active_feature,
    _reference_years,
    _forage_value,
)


class PagedHttp:
    """Minimal fake reproducing the OGC ``next`` pagination contract."""

    def __init__(self):
        self.calls = []

    def get_json(self, url, params=None):
        self.calls.append((url, params))
        if url == AGRICULTURAL_URL:
            return {
                "numberMatched": 2,
                "features": [{"id": "first"}],
                "links": [{"rel": "next", "href": "https://example.test/page-2"}],
            }
        return {
            "numberMatched": 2,
            "features": [{"id": "second"}],
            "links": [],
        }


def test_landscape_reads_all_ogc_pages():
    http = PagedHttp()
    features, number_matched = LandscapeService(http)._features(46.95, 7.45)

    assert [feature["id"] for feature in features] == ["first", "second"]
    assert number_matched == 2
    assert len(http.calls) == 2
    assert http.calls[0][1]["limit"] == 1000
    assert http.calls[1] == ("https://example.test/page-2", None)


def test_mixed_current_land_use_years_are_all_reported():
    features = [
        {"properties": {"kanton": "SG", "bezugsjahr": 2025}},
        {"properties": {"kanton": "AI", "bezugsjahr": 2026}},
    ]
    years = _reference_years(features)

    assert years == [2025, 2026]
    assert _is_active_feature(features[0]["properties"])
    assert _is_active_feature(features[1]["properties"])


def test_inactive_or_non_definitive_land_use_is_rejected():
    assert not _is_active_feature(
        {"kanton": "SG", "bezugsjahr": 2026, "ist_definitiv": False}
    )
    assert not _is_active_feature(
        {"kanton": "SG", "bezugsjahr": 2026, "nutzung_im_beitragsjahr": False}
    )


def test_extensive_pastures_are_not_misclassified_as_meadows():
    assert _forage_value("Extensiv genutzte Weiden")[1] == "Pastures"
    assert _forage_value("Waldweiden")[1] == "Pastures"
    assert _forage_value("Extensiv genutzte Wiesen")[1] == "Meadows"
    assert _forage_value("Luzernewiese")[1] == "Clover and lucerne"


def test_missing_geometry_outside_rings_and_partial_pages_cannot_raise_rank():
    class Http:
        def __init__(self, coordinates, matched=1):
            self.coordinates, self.matched = coordinates, matched

        def get_json(self, *args, **kwargs):
            return {
                "numberMatched": self.matched,
                "features": [
                    {
                        "properties": {"flaeche_m2": 100000, "nutzung": "Raps"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": self.coordinates,
                        },
                    }
                ],
            }

    outside = [
        [
            [2603100, 1200000],
            [2603200, 1200000],
            [2603200, 1200100],
            [2603100, 1200100],
            [2603100, 1200000],
        ]
    ]
    for coordinates in ([], outside):
        result = LandscapeService(Http(coordinates)).analyse(
            46.95, 7.45, 2600000, 1200000
        )
        assert not result["available"]
        assert result["diversity_score"] == 0
    inside = [
        [
            [2600000, 1200000],
            [2600100, 1200000],
            [2600100, 1200100],
            [2600000, 1200100],
            [2600000, 1200000],
        ]
    ]
    partial = LandscapeService(Http(inside, matched=2)).analyse(
        46.95, 7.45, 2600000, 1200000
    )
    assert partial["truncated"]
    assert not partial["available"]


def test_disconnected_fields_contribute_only_their_local_area():
    import pytest
    from shapely.geometry import MultiPolygon, box, mapping

    geometry = MultiPolygon(
        [
            box(2600000, 1200000, 2600100, 1200100),
            box(2610000, 1200000, 2610100, 1200100),
        ]
    )

    class Http:
        def get_json(self, *args, **kwargs):
            return {
                "numberMatched": 1,
                "features": [
                    {
                        "properties": {"flaeche_m2": 20000, "nutzung": "Raps"},
                        "geometry": mapping(geometry),
                    }
                ],
            }

    result = LandscapeService(Http()).analyse(46.95, 7.45, 2600050, 1200050)
    assert result["available"]
    assert result["mapped_hectares"] == pytest.approx(1)
    assert result["forage_hectares_equivalent"] == pytest.approx(1)
