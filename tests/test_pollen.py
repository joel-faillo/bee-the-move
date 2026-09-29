from services.pollen import PollenService


class PollenHttp:
    def get_json(self, *_args, **_kwargs):
        return {
            "features": [
                {
                    "geometry": {"coordinates": [9.4, 47.4]},
                    "properties": {"title": "Test station"},
                    "assets": {
                        "test_h_now.csv": {"href": "https://example.test/pollen.csv"}
                    },
                }
            ]
        }

    def get_text(self, *_args, **_kwargs):
        return (
            "station_abbr;reference_timestamp;alder;birch\n"
            "TST;29.09.2026 10:00;2.0;3.5\n"
        )


def test_pollen_reports_observed_context_without_scoring_it():
    result = PollenService(PollenHttp()).latest_near(47.42, 9.37)

    assert result["available"]
    assert result["station"] == "Test station"
    assert result["timestamp"] == "29.09.2026 10:00"
    assert result["total_pollen_m3"] == 5.5
    assert "score" not in result


class EmptyPollenHttp(PollenHttp):
    def get_json(self, *_args, **_kwargs):
        return {"features": []}


def test_pollen_has_an_explicit_unavailable_state():
    result = PollenService(EmptyPollenHttp()).latest_near(47.42, 9.37)
    assert result == {"available": False, "reason": "Nessuna misura oraria corrente"}
