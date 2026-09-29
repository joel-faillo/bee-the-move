from datetime import date

from services.compliance import (
    CANTON_RULES,
    VETERINARY_DIRECTORY_URL,
    cantonal_rule,
    movement_steps,
    notification_copy,
)


def test_current_cantonal_veterinary_directory_is_used():
    assert VETERINARY_DIRECTORY_URL == "https://www.kantonstieraerzte.ch/uber-uns.html"


def test_every_canton_has_an_audited_official_source():
    cantons = {
        "AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR", "JU",
        "LU", "NE", "NW", "OW", "SG", "SH", "SO", "SZ", "TG", "TI", "UR",
        "VD", "VS", "ZG", "ZH",
    }

    assert set(CANTON_RULES) == cantons
    for canton in cantons:
        rule = cantonal_rule(canton)
        assert rule["canton"] == canton
        assert rule["office"]
        assert rule["source_url"].startswith("https://")
        assert rule["checked_on"] == "2026-09-28"
        assert rule["notes"]
        steps = movement_steps(canton, canton)
        assert len(steps) >= 5
        assert any("official" in step.lower() or "inspection" in step.lower() for step in steps)


def test_cross_canton_move_requires_both_services():
    steps = movement_steps("SG", "TG")
    assert any("both the old and new locations" in step for step in steps)


def test_same_canton_move_checks_inspection_district():
    steps = movement_steps("SG", "SG")
    assert any("inspection district" in step for step in steps)


def test_verified_cantonal_differences_are_not_flattened():
    assert any("two days" in step for step in movement_steps("BL", "BL"))
    assert any("ten days" in step for step in movement_steps("FR", "FR"))
    assert any("permit" in step for step in movement_steps("GL", "GL"))
    assert any("need no notice" in step for step in movement_steps("NE", "NE"))
    assert any("clearance" in step for step in movement_steps("TI", "TI"))
    assert any("ten working days" in step for step in movement_steps("ZG", "ZG"))


def test_notice_uses_canton_language_without_repeating_canton():
    data = {
        "beekeeper": "Test Beekeeper",
        "beekeeper_number": "",
        "origin_name": "Bern (BE)",
        "origin_canton": "BE",
        "origin_apiary_number": "BE-1",
        "destination_name": "Lausanne",
        "destination_canton": "VD",
        "apiary_number": "VD-2",
        "coordinates": "46.5197 / 6.6323",
        "move_date": date(2026, 9, 25),
        "colonies": 4,
        "phone": "",
        "email": "",
    }

    _subject, french = notification_copy(data, "VD")
    assert "Je vous prie de vérifier" in french
    assert "non une autorisation" in french
    assert "Bern (BE) (BE)" not in french

    _subject, italian = notification_copy(data, "TI")
    assert "Vi chiedo di verificare" in italian
    assert "non un'autorizzazione" in italian


def test_every_canton_produces_a_non_authorising_request_in_its_language():
    data = {
        "beekeeper": "Test Beekeeper",
        "beekeeper_number": "CH-1",
        "origin_name": "Bern",
        "origin_canton": "BE",
        "origin_apiary_number": "BE-1",
        "destination_name": "Test destination",
        "destination_canton": "ZH",
        "apiary_number": "ZH-2",
        "coordinates": "47.0 / 8.0",
        "move_date": date(2026, 9, 29),
        "colonies": 2,
        "phone": "+41 79 000 00 00",
        "email": "test@example.ch",
    }
    french = {"FR", "GE", "JU", "NE", "VD", "VS"}
    for canton in CANTON_RULES:
        subject, body = notification_copy(data, canton)
        assert subject and body
        if canton in french:
            assert "non une autorisation" in body
        elif canton == "TI":
            assert "non un'autorizzazione" in body
        else:
            assert "keine Bewilligung" in body
