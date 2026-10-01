from services.landscape import (
    AGRICULTURAL_URL,
    LandscapeService,
    _is_active_feature,
    _reference_years,
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
