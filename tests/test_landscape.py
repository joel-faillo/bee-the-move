from services.landscape import AGRICULTURAL_URL, LandscapeService


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
