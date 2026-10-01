from datetime import date

from streamlit.testing.v1 import AppTest

from app import (
    ELEVATION_OPTIONS,
    FORAGE_OPTIONS,
    RADIUS_OPTIONS,
    _candidate_summary,
    _format_display_date,
    _location_suggestions,
    _missing_evidence,
    _postcode_and_town,
    _safe_canton,
    _source_timestamp,
)
from ui.move_form import (
    COMPENSATION_PERIOD_OPTIONS,
    DOCUMENT_LANGUAGE_OPTIONS,
    DURATION_OPTIONS,
    INSTALLATION_OPTIONS,
    NOTICE_PERIOD_OPTIONS,
    NOTICE_TIMING_OPTIONS,
    SITE_PLAN_OPTIONS,
    coordinates_in_swiss_bounds,
    document_language_for_canton,
    validate_move_form,
)


def _form_app():
    import app

    class Geo:
        def canton(self, lat, lon):
            if lat < 47:
                return {"code": "TI", "name": "Ticino"}
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


def _complete_form(at, latitude=47.33, longitude=9.41):
    agreement_values = {
        "Name and surname *": "Anna Test",
        "Street and number *": "Via 1",
        "Postcode and town *": "9000 St. Gallen",
        "Landowner name and address *": "Owner, Via 2",
        "Property / parcel *": "Parcel 123",
    }
    for label, value in agreement_values.items():
        _by_label(at.text_input, label).set_value(value).run()
    _by_label(at.number_input, "Area (m²) *").set_value(100).run()
    _by_label(at.number_input, "Exact destination latitude *").set_value(latitude).run()
    _by_label(at.number_input, "Exact destination longitude *").set_value(longitude).run()
    movement_values = {
        "Destination apiary number *": "SG-2",
        "Destination street / field address *": "Field 1",
        "Origin apiary number *": "SG-1",
    }
    for label, value in movement_values.items():
        _by_label(at.text_input, label).set_value(value).run()
    _by_label(at.radio, "Installation on the site *").set_value(
        "Hives without a bee house"
    ).run()
    _by_label(
        at.radio, "Will a plan showing the site and access be attached? *"
    ).set_value("No").run()
    _by_label(at.radio, "Duration *").set_value("Open-ended").run()
    _by_label(at.date_input, "Use begins *").set_value(date(2026, 10, 1)).run()
    _by_label(at.date_input, "Planned move date *").set_value(
        date(2026, 10, 2)
    ).run()
    _by_label(
        at.checkbox,
        "Required confirmation: I understand that I must review and sign the documents and complete any required cantonal notification.",
    ).check().run()
    return at


def test_initial_page_exposes_every_search_option_without_errors():
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception
    assert _by_label(at.date_input, "Planned arrival").value is not None
    assert _by_label(at.date_input, "Evaluate the site until").value is not None
    assert _by_label(at.number_input, "Colonies to move").value == 1
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
    assert _by_label(at.radio, "Installation on the site *").options == list(
        INSTALLATION_OPTIONS
    )
    assert _by_label(
        at.radio, "Will a plan showing the site and access be attached? *"
    ).options == list(SITE_PLAN_OPTIONS)
    assert _by_label(at.radio, "Duration *").options == list(DURATION_OPTIONS)
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
    assert _by_label(at.text_input, "Destination postcode and town *").value == (
        "9050 Appenzell"
    )
    assert _by_label(at.number_input, "Exact destination latitude *").value is None
    assert _by_label(at.number_input, "Exact destination longitude *").value is None
    assert _by_label(at.date_input, "Use begins *").value is None
    assert _by_label(at.date_input, "Planned move date *").value is None
    assert _by_label(at.text_input, "Property / parcel *").value == ""
    assert _by_label(at.text_input, "Movement reason *").value == "Verstellen"


def test_conditional_form_options_show_their_matching_fields():
    at = AppTest.from_function(_form_app, default_timeout=30).run()

    _by_label(at.radio, "Installation on the site *").set_value("Other").run()
    assert _by_label(at.text_input, "Describe the installation")

    _by_label(at.selectbox, "Notice can end").set_value(
        "Only on a specified date"
    ).run()
    assert _by_label(at.text_input, "Specified notice date or rule")

    _by_label(at.radio, "Duration *").set_value("Fixed term").run()
    assert _by_label(at.date_input, "Fixed term ends *").value is None

    _by_label(at.radio, "Duration *").set_value("Open-ended").run()
    assert all(item.label != "Fixed term ends *" for item in at.date_input)


def test_every_form_selector_value_can_be_selected():
    at = AppTest.from_function(_form_app, default_timeout=30).run()
    groups = (
        (at.radio, "Installation on the site *", INSTALLATION_OPTIONS),
        (at.radio, "Will a plan showing the site and access be attached? *", SITE_PLAN_OPTIONS),
        (at.radio, "Duration *", DURATION_OPTIONS),
        (at.selectbox, "Notice period", NOTICE_PERIOD_OPTIONS),
        (at.selectbox, "Notice can end", NOTICE_TIMING_OPTIONS),
        (at.radio, "Compensation period", COMPENSATION_PERIOD_OPTIONS),
        (at.selectbox, "Official BLV stock-control language", DOCUMENT_LANGUAGE_OPTIONS),
    )
    for _elements, label, options in groups:
        for value in options:
            current_elements = at.radio if label in {
                "Installation on the site *",
                "Will a plan showing the site and access be attached? *",
                "Duration *",
                "Compensation period",
            } else at.selectbox
            _by_label(current_elements, label).set_value(value).run()
            assert not at.exception


def test_later_arrival_keeps_the_planning_period_valid():
    at = AppTest.from_file("app.py", default_timeout=30).run()

    _by_label(at.date_input, "Planned arrival").set_value(date(2027, 3, 1)).run()

    assert _by_label(at.date_input, "Evaluate the site until").value == date(
        2027, 3, 28
    )
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
    assert document_language_for_canton("TI") == "Italiano"
    assert document_language_for_canton("VD") == "Français"
    assert document_language_for_canton("SG") == "Deutsch"


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
    assert "Best available initial foraging window" in direct
    assert "55% flight weather" in direct
    assert "30/09/2026 to 02/10/2026" in direct


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
    assert _source_timestamp("2026-09-29T08:04:04.878211Z") == "29/09/2026 08:04 UTC"
    assert _format_display_date("2026-10-02") == "02/10/2026"


def test_canton_lookup_fails_without_inventing_a_result():
    class Geo:
        def canton(self, lat, lon):
            raise ConnectionError("temporary failure")

    class Analysis:
        geo = Geo()

    assert _safe_canton(Analysis(), {"lat": 47.4, "lon": 9.3}) is None


def test_coordinate_bounds_and_partial_evidence_messages_are_explicit():
    assert coordinates_in_swiss_bounds(46.95, 8.25)
    assert not coordinates_in_swiss_bounds(0, 0)
    missing = _missing_evidence(
        {
            "flowering": {"available": False},
            "landscape": {"available": False},
            "height_m": None,
            "is_origin_area": False,
            "route": None,
        },
        {"sources": {"openrouteservice": {"configured": True}}},
    )
    assert len(missing) == 5
    assert any("flowering" in message for message in missing)
    assert not any("weather" in message for message in missing)
    assert any("climate normals" in message for message in missing)
    assert any("road route" in message for message in missing)

    forecast_missing = _missing_evidence(
        {
            "flowering": {"available": True},
            "weather": {"days": []},
            "landscape": {"available": True},
            "climate_normals": {"available": True},
            "height_m": 500,
            "is_origin_area": True,
            "route": None,
        },
        {
            "forecast_lead_days": 2,
            "sources": {"openrouteservice": {"configured": False}},
        },
    )
    assert forecast_missing == [
        "weather was unavailable inside the current forecast horizon"
    ]


def test_move_form_validation_catches_dependent_fields_and_date_order():
    form = {
        "beekeeper": "Anna",
        "beekeeper_street": "Via 1",
        "beekeeper_city": "9000 St. Gallen",
        "landowner": "Owner, Via 2",
        "parcel": "123",
        "apiary_number": "SG-2",
        "site_street": "Field 1",
        "site_city": "9050 Appenzell",
        "origin_apiary_number": "SG-1",
        "movement_reason": "Verstellen",
        "area_m2": 100,
        "installation": "Other",
        "other_installation": "",
        "site_plan": "No",
        "duration": "Fixed term",
        "exact_latitude": 47.33,
        "exact_longitude": 9.41,
        "start_date": date(2026, 10, 2),
        "end_date": date(2026, 10, 1),
        "move_date": date(2026, 10, 3),
        "notice_timing": "Any time",
        "specified_notice_date": "",
        "compensation": "",
        "compensation_period": "Not selected",
        "confirmation": True,
    }
    canton = {"code": "SG", "name": "St. Gallen"}

    assert validate_move_form(form, canton) == "Describe the installation selected as Other."
    form["other_installation"] = "Four hives"
    assert "end date" in validate_move_form(form, canton)
    form["end_date"] = date(2026, 10, 5)
    form["notice_timing"] = "Only on a specified date"
    assert validate_move_form(form, canton) == "Enter the specified notice date or rule."
    form["specified_notice_date"] = "31/10"
    form["compensation"] = "CHF 100"
    assert "per year or per month" in validate_move_form(form, canton)


def test_exact_coordinates_drive_canton_and_language_then_generate_documents():
    at = _complete_form(
        AppTest.from_function(_form_app, default_timeout=30).run(),
        latitude=46.04,
        longitude=8.95,
    )
    assert _by_label(
        at.selectbox, "Official BLV stock-control language"
    ).value == "Italiano"

    _by_label(at.button, "Prepare documents").click().run()

    assert not at.error
    assert at.session_state["prepared_documents"]["data"]["destination_canton"] == "TI"


def test_editing_a_field_invalidates_prepared_documents():
    at = _complete_form(AppTest.from_function(_form_app, default_timeout=30).run())
    _by_label(at.button, "Prepare documents").click().run()
    assert at.session_state["prepared_documents"]["data"]["parcel"] == "Parcel 123"

    _by_label(at.text_input, "Property / parcel *").set_value("Parcel changed").run()

    assert "prepared_documents" not in at.session_state
    assert any("Prepare the documents again" in message.value for message in at.info)
