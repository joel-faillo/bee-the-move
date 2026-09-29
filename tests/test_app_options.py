from streamlit.testing.v1 import AppTest

from app import (
    COMPENSATION_PERIOD_OPTIONS,
    DOCUMENT_LANGUAGE_OPTIONS,
    DURATION_OPTIONS,
    ELEVATION_OPTIONS,
    FORAGE_OPTIONS,
    INSTALLATION_OPTIONS,
    NOTICE_PERIOD_OPTIONS,
    NOTICE_TIMING_OPTIONS,
    RADIUS_OPTIONS,
    SITE_PLAN_OPTIONS,
    _candidate_summary,
    _location_suggestions,
    _document_language_for_canton,
    _postcode_and_town,
    _safe_canton,
    _source_timestamp,
)


def _form_app():
    import app

    class Geo:
        def canton(self, lat, lon):
            return {"code": "SG", "name": "St. Gallen"}

    class Analysis:
        geo = Geo()

    destination = {
        "name": "Appenzell",
        "postal_code": "9050",
        "lat": 47.331,
        "lon": 9.409,
    }
    result = {
        "origin": {"name": "St. Gallen", "lat": 47.4245, "lon": 9.3767},
    }
    app._move_preparation(Analysis(), result, destination)


def _by_label(elements, label):
    return next(element for element in elements if element.label == label)


def test_initial_page_exposes_every_search_option_without_errors():
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception
    assert _by_label(at.selectbox, "Maximum search radius").options == [
        f"{value} km" for value in RADIUS_OPTIONS
    ]
    assert _by_label(at.selectbox, "Forage focus").options == list(FORAGE_OPTIONS)
    assert _by_label(at.selectbox, "Elevation band").options == list(ELEVATION_OPTIONS)
    assert _by_label(at.button, "Compare nearby areas").disabled


def test_every_search_selector_value_can_be_selected():
    at = AppTest.from_file("app.py", default_timeout=30).run()
    for value in RADIUS_OPTIONS:
        _by_label(at.selectbox, "Maximum search radius").set_value(value).run()
        assert not at.exception
    for value in FORAGE_OPTIONS:
        _by_label(at.selectbox, "Forage focus").set_value(value).run()
        assert not at.exception
    for value in ELEVATION_OPTIONS:
        _by_label(at.selectbox, "Elevation band").set_value(value).run()
        assert not at.exception


def test_form_exposes_every_original_document_choice_without_errors():
    at = AppTest.from_function(_form_app, default_timeout=30).run()
    assert not at.exception
    assert _by_label(at.radio, "Installation on the site").options == list(
        INSTALLATION_OPTIONS
    )
    assert _by_label(
        at.radio, "Will a plan showing the site and access be attached?"
    ).options == list(SITE_PLAN_OPTIONS)
    assert _by_label(at.radio, "Duration").options == list(DURATION_OPTIONS)
    assert _by_label(at.selectbox, "Notice period").options == list(
        NOTICE_PERIOD_OPTIONS
    )
    assert _by_label(at.selectbox, "Notice can end").options == list(
        NOTICE_TIMING_OPTIONS
    )
    assert _by_label(at.radio, "Compensation period").options == list(
        COMPENSATION_PERIOD_OPTIONS
    )
    assert _by_label(
        at.selectbox, "Official BLV stock-control language"
    ).options == list(DOCUMENT_LANGUAGE_OPTIONS)
    assert _by_label(at.text_input, "Destination postcode and town").value == (
        "9050 Appenzell"
    )
    assert _by_label(at.date_input, "Use begins *").value is None
    assert _by_label(at.date_input, "Planned move date *").value is None


def test_conditional_form_options_show_their_matching_fields():
    at = AppTest.from_function(_form_app, default_timeout=30).run()

    _by_label(at.radio, "Installation on the site").set_value("Other").run()
    assert _by_label(at.text_input, "Describe the installation")

    _by_label(at.selectbox, "Notice can end").set_value(
        "Only on a specified date"
    ).run()
    assert _by_label(at.text_input, "Specified notice date or rule")

    _by_label(at.radio, "Duration").set_value("Open-ended").run()
    assert all(item.label != "Fixed term ends *" for item in at.date_input)


def test_every_form_selector_value_can_be_selected():
    at = AppTest.from_function(_form_app, default_timeout=30).run()
    groups = (
        (at.radio, "Installation on the site", INSTALLATION_OPTIONS),
        (at.radio, "Will a plan showing the site and access be attached?", SITE_PLAN_OPTIONS),
        (at.radio, "Duration", DURATION_OPTIONS),
        (at.selectbox, "Notice period", NOTICE_PERIOD_OPTIONS),
        (at.selectbox, "Notice can end", NOTICE_TIMING_OPTIONS),
        (at.radio, "Compensation period", COMPENSATION_PERIOD_OPTIONS),
        (at.selectbox, "Official BLV stock-control language", DOCUMENT_LANGUAGE_OPTIONS),
    )
    for _elements, label, options in groups:
        for value in options:
            current_elements = at.radio if label in {
                "Installation on the site",
                "Will a plan showing the site and access be attached?",
                "Duration",
                "Compensation period",
            } else at.selectbox
            _by_label(current_elements, label).set_value(value).run()
            assert not at.exception


def test_location_autocomplete_formats_verified_choices_and_fails_closed():
    class Geo:
        def suggest(self, query):
            assert query == "9000"
            return [{
                "label": "9000 - St. Gallen",
                "kind": "Postal code (CAP)",
                "postal_code": "9000",
                "lat": 47.425,
                "lon": 9.376,
            }]

    class Analysis:
        geo = Geo()

    choices = _location_suggestions(Analysis(), " 9000 ")
    assert choices == [
        (
            "9000 - St. Gallen · Postal code (CAP)",
            {
                "label": "9000 - St. Gallen",
                "kind": "Postal code (CAP)",
                "postal_code": "9000",
                "lat": 47.425,
                "lon": 9.376,
            },
        )
    ]
    assert _location_suggestions(Analysis(), "9") == []

    class BrokenGeo:
        def suggest(self, query):
            raise ConnectionError("temporary failure")

    class BrokenAnalysis:
        geo = BrokenGeo()

    assert _location_suggestions(BrokenAnalysis(), "9000") == []


def test_destination_address_and_document_language_defaults_are_explicit():
    assert _postcode_and_town({"name": "Appenzell", "postal_code": "9050"}) == (
        "9050 Appenzell"
    )
    assert _postcode_and_town({"name": "9000 - St. Gallen", "postal_code": "9000"}) == (
        "9000 St. Gallen"
    )
    assert _postcode_and_town({"name": "Appenzell"}) == "Appenzell"
    assert _document_language_for_canton("TI") == "Italiano"
    assert _document_language_for_canton("VD") == "Français"
    assert _document_language_for_canton("SG") == "Deutsch"


def test_candidate_summary_distinguishes_road_and_direct_distance():
    base = {
        "best_period": {"from": "2026-09-30", "to": "2026-10-02"},
        "flowering": {"score": 60},
    }
    direct = _candidate_summary({**base, "route": None})
    routed = _candidate_summary(
        {**base, "route": {"distance_km": 12.4, "duration_minutes": 19}}
    )

    assert "direct (Haversine)" in direct
    assert "nearest routable road: 12.4 km, 19 min" in routed
    assert "Best relative period within the next seven days" in direct


def test_candidate_summary_warns_when_flowering_signal_is_low():
    summary = _candidate_summary(
        {
            "best_period": {"from": "2026-09-30", "to": "2026-10-02"},
            "flowering": {"score": 12},
            "route": None,
        }
    )
    assert "Flowering signal remains low" in summary


def test_source_timestamp_is_compact_and_explicitly_utc():
    assert _source_timestamp("2026-09-29T08:04:04.878211Z") == "2026-09-29 08:04 UTC"


def test_canton_lookup_fails_without_inventing_a_result():
    class Geo:
        def canton(self, lat, lon):
            raise ConnectionError("temporary failure")

    class Analysis:
        geo = Geo()

    assert _safe_canton(Analysis(), {"lat": 47.4, "lon": 9.3}) is None
