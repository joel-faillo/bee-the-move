from datetime import date

from services.compliance import movement_steps, notification_copy, veterinary_office


def test_every_canton_has_an_official_directory_contact():
    cantons = {
        "AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR", "JU",
        "LU", "NE", "NW", "OW", "SG", "SH", "SO", "SZ", "TG", "TI", "UR",
        "VD", "VS", "ZG", "ZH",
    }

    for canton in cantons:
        office = veterinary_office(canton)
        assert office["canton"] == canton
        assert "@" in office["email"]
        assert office["directory_url"].startswith("https://www.blv.admin.ch/")


def test_cross_canton_move_requires_both_services():
    steps = movement_steps("SG", "TG")
    assert any("both origin and destination" in step for step in steps)


def test_same_canton_move_checks_inspection_district():
    steps = movement_steps("SG", "SG")
    assert any("inspection district" in step for step in steps)


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
    assert "Je vous annonce" in french
    assert "Bern (BE) (BE)" not in french

    _subject, italian = notification_copy(data, "TI")
    assert "Con la presente notifico" in italian
