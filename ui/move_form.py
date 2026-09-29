"""Options, validation and data mapping for the guided movement form.

Keeping these pure rules outside ``app.py`` leaves the Streamlit page focused
on layout while making the document workflow independently testable.
"""

from __future__ import annotations

INSTALLATION_OPTIONS = (
    "Not selected",
    "Bee house",
    "Hives without a bee house",
    "Other",
)
SITE_PLAN_OPTIONS = ("Not selected", "Yes", "No")
DURATION_OPTIONS = ("Not selected", "Fixed term", "Open-ended")
NOTICE_PERIOD_OPTIONS = (
    "Not selected",
    "3 months",
    "6 months",
    "9 months",
    "12 months",
)
NOTICE_TIMING_OPTIONS = (
    "Not selected",
    "Any time",
    "At month end",
    "Only on a specified date",
)
COMPENSATION_PERIOD_OPTIONS = ("Not selected", "Year", "Month")
DOCUMENT_LANGUAGE_OPTIONS = {
    "Deutsch": "de",
    "Français": "fr",
    "Italiano": "it",
}
MOVEMENT_REASON_DEFAULTS = {
    "de": "Verstellen",
    "fr": "Déplacement",
    "it": "Trasferimento",
}
BLV_FIELD_LABELS = {
    "de": {
        "apiary": "Stand-Nr. / Flurname",
        "street": "Strasse, Nr.",
        "city": "PLZ / Ort",
        "origin": "Zugänge von Bienenstand Nummer",
        "reason": "Ursache / Begründung",
    },
    "fr": {
        "apiary": "N° du rucher / Nom local",
        "street": "Rue, numéro",
        "city": "NPA / lieu",
        "origin": "Entrées dans le rucher numéro",
        "reason": "Cause / motif",
    },
    "it": {
        "apiary": "N. apiario / Nome locale",
        "street": "Via / n.",
        "city": "NPA / località",
        "origin": "Aumenti numero di apiario",
        "reason": "Causa / Motivo",
    },
}


def document_language_for_canton(canton_code: str | None) -> str:
    """Choose a practical default; the user can select another language."""
    code = (canton_code or "").upper()
    if code == "TI":
        return "Italiano"
    if code in {"FR", "GE", "JU", "NE", "VD", "VS"}:
        return "Français"
    return "Deutsch"


def coordinates_in_swiss_bounds(latitude: float, longitude: float) -> bool:
    """Reject obvious non-Swiss coordinates before the GeoAdmin lookup."""
    return 45.7 <= float(latitude) <= 47.9 and 5.8 <= float(longitude) <= 10.7


def validate_move_form(form: dict, destination_canton: dict | None) -> str | None:
    """Return the first actionable inconsistency in the guided form."""
    required_text = (
        "beekeeper",
        "beekeeper_street",
        "beekeeper_city",
        "landowner",
        "parcel",
        "apiary_number",
        "site_street",
        "site_city",
        "origin_apiary_number",
        "movement_reason",
    )
    if not all(str(form.get(name) or "").strip() for name in required_text):
        return "Complete every text field marked with *."
    if form.get("area_m2", 0) <= 0:
        return "Enter the land area stated in the site agreement."
    if (
        form.get("installation") == "Not selected"
        or form.get("site_plan") == "Not selected"
    ):
        return "Choose the installation type and whether a site plan will be attached."
    if (
        form.get("installation") == "Other"
        and not str(form.get("other_installation") or "").strip()
    ):
        return "Describe the installation selected as Other."
    if form.get("duration") == "Not selected":
        return "Choose a fixed-term or open-ended agreement."

    latitude = form.get("exact_latitude")
    longitude = form.get("exact_longitude")
    if latitude is None or longitude is None:
        return "Enter the exact latitude and longitude of the destination apiary."
    if not coordinates_in_swiss_bounds(latitude, longitude):
        return "Enter coordinates inside Switzerland."
    if destination_canton is None:
        return "GeoAdmin could not verify the exact destination canton. Check the coordinates or retry."

    start_date = form.get("start_date")
    move_date = form.get("move_date")
    end_date = form.get("end_date")
    if start_date is None or move_date is None:
        return "Choose the agreement start date and planned move date."
    if form.get("duration") == "Fixed term" and end_date is None:
        return "Choose an end date or select an open-ended agreement."
    if end_date is not None and end_date < start_date:
        return "The fixed-term end date cannot be before the agreement start date."
    if move_date < start_date:
        return "The planned move cannot be before the agreement starts."
    if end_date is not None and move_date > end_date:
        return "The planned move cannot be after the fixed-term agreement ends."

    if (
        form.get("notice_timing") == "Only on a specified date"
        and not str(form.get("specified_notice_date") or "").strip()
    ):
        return "Enter the specified notice date or rule."
    compensation = str(form.get("compensation") or "").strip()
    compensation_period = form.get("compensation_period")
    if compensation and compensation_period == "Not selected":
        return "Choose whether the stated compensation applies per year or per month."
    if not compensation and compensation_period != "Not selected":
        return "Enter the compensation amount or leave its period unselected."
    if not form.get("confirmation"):
        return "Confirm that official checks, notification and signatures are still required."
    return None


def build_document_data(
    form: dict,
    origin_name: str,
    origin_canton: str,
    destination_canton: str,
    veterinary_office_name: str,
) -> dict:
    """Translate validated form state into fields used by both templates."""
    data = form.copy()
    for internal_name in (
        "destination_key",
        "document_language",
        "confirmation",
        "duration",
        "site_plan",
        "inspector",
        "exact_latitude",
        "exact_longitude",
    ):
        data.pop(internal_name, None)
    data.update(
        {
            "site_plan_attached": form["site_plan"] == "Yes",
            "fixed_term": form["duration"] == "Fixed term",
            "bee_inspector": form["inspector"],
            "veterinary_office": veterinary_office_name,
            "coordinates": (
                f"{form['exact_latitude']:.6f}° N, {form['exact_longitude']:.6f}° E"
            ),
            "year": form["move_date"].year,
            "origin_name": origin_name,
            "destination_name": form["site_city"],
            "origin_canton": origin_canton,
            "destination_canton": destination_canton,
        }
    )
    return data
