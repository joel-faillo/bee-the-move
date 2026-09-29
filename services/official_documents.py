"""Fill copies of the official Swiss beekeeping templates.

The bundled files in ``static/forms`` are unmodified originals downloaded from
BienenSchweiz and the FSVO/BLV.  These functions only insert data supplied by
the user.  They do not rewrite clauses, add permissions or replace signatures.

AI assistance citation: OpenAI Codex helped draft this module on 22 September
2026. The project team must review it and document that use in its submission.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.shared import Pt
from pypdf import PdfReader, PdfWriter

FORMS_DIRECTORY = Path(__file__).resolve().parents[1] / "static" / "forms"
LAND_AGREEMENT_TEMPLATE = FORMS_DIRECTORY / "bienenschweiz-land-agreement.pdf"
STOCK_CONTROL_TEMPLATE = FORMS_DIRECTORY / "blv-stock-control.docx"
AUTHORSHIP_DECLARATION = FORMS_DIRECTORY / "hsg-declaration-of-authorship.pdf"


def fill_land_agreement(data: dict) -> bytes:
    """Return a filled copy of the official BienenSchweiz PDF.

    Only unambiguous AcroForm fields are populated. Signature fields and
    contractual choices that need agreement between the parties stay open.
    """
    reader = PdfReader(LAND_AGREEMENT_TEMPLATE)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    values = {
        "Vereinbarung zwischen": data.get("landowner", ""),
        "Imkerin  Imker": _join(
            data.get("beekeeper"), data.get("beekeeper_street"), data.get("beekeeper_city")
        ),
        "Liegenschaft  Parzelle": data.get("parcel", ""),
        "m2 Boden nachfolgend Platz um darauf Bienen zu halten": str(
            data.get("area_m2", "")
        ),
        # The source field name describes the preceding label. Its position in
        # the official form is the "Beginn der Nutzung" line.
        "Lageplan worauf der Platz und der Zugang dazu ersichtlich sind liegt bei": _date(
            data.get("start_date")
        ),
        # This field sits beside "befristet bis" in the original form.
        "undefined_2": _date(data.get("end_date")),
        "undefined": data.get("other_installation", ""),
        "undefined_3": data.get("specified_notice_date", ""),
        "undefined_4": data.get("other_notice_rule", ""),
        "den Platz auf eigene Kosten in dem Zustand zu halten wie er ihn übernommen hat": data.get(
            "additional_duty", ""
        ),
        "Die Imkerinder Imker bezahlt für die Nutzung des Platzes dem Eigentümer pro": data.get(
            "compensation", ""
        ),
    }
    if data.get("site_plan_attached"):
        values["Ja empfohlen"] = "/On"
    else:
        values["Nein"] = "/On"
    installation_fields = {
        "Bee house": "ein Bienenhaus gestellt Fahrnisbaute Pläne oder Fotos liegen bei",
        "Hives without a bee house": "kein Bienenhaus gestellt Pläne oder Fotos von Bienenbeute liegen bei",
        "Other": "Check Box1",
    }
    if data.get("installation") in installation_fields:
        values[installation_fields[data["installation"]]] = (
            "/Ja" if data["installation"] == "Other" else "/On"
        )
    if data.get("fixed_term"):
        values["befristet bis"] = "/On"
    else:
        values["unbefristet"] = "/On"
        values["undefined_2"] = ""
    notice_periods = {
        "3 months": "3 Monate",
        "6 months": "6 Monate",
        "9 months": "9 Monate",
        "12 months": "12 Monate",
    }
    if data.get("notice_period") in notice_periods:
        values[notice_periods[data["notice_period"]]] = "/On"
    notice_timings = {
        "Any time": "beliebig",
        "At month end": "auf ein Monatsende",
        "Only on a specified date": "nur per",
    }
    if data.get("notice_timing") in notice_timings:
        values[notice_timings[data["notice_timing"]]] = "/On"
    if data.get("other_notice_rule"):
        values["Check Box2"] = "/Ja"
    if data.get("compensation_period") == "Year":
        values["Jahr"] = "/On"
    elif data.get("compensation_period") == "Month":
        values["Monat"] = "/On"

    writer.update_page_form_field_values(
        writer.pages[0], values, auto_regenerate=False
    )
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def fill_stock_control(data: dict) -> bytes:
    """Return a filled copy of the current official FSVO/BLV Word form."""
    document = Document(STOCK_CONTROL_TEMPLATE)
    year = str(data.get("year") or date.today().year)
    title = document.paragraphs[0]
    title.text = f"Bestandeskontrolle der Bienenvölker für das Jahr {year}"

    details = document.tables[0]
    office = data.get("veterinary_office", "")
    inspector = data.get("bee_inspector", "") or "____________________________"
    details.cell(0, 0).text = (
        f"Zuständiger Veterinärdienst: {office}\n\n"
        f"Zuständiger Bieneninspektor: {inspector}"
    )

    # Left side: beekeeper. Right side: the selected destination apiary.
    _set(details, 3, 1, data.get("beekeeper_number"))
    _set(details, 4, 1, data.get("beekeeper"))
    _set(details, 5, 1, data.get("beekeeper_street"))
    _set(details, 6, 1, data.get("beekeeper_city"))
    _set(details, 7, 1, data.get("phone"))
    _set(details, 8, 1, data.get("email"))
    _set(details, 9, 1, data.get("section"))
    _set(details, 3, 5, data.get("apiary_number"))
    _set(details, 4, 5, data.get("site_street"))
    _set(details, 5, 5, data.get("site_city"))
    _set(details, 6, 5, data.get("coordinates"), font_size=8)

    # The first free movement line records colonies arriving at the selected
    # destination. The remaining official table stays blank for later entries.
    movement = document.tables[1]
    _set(movement, 2, 0, _short_date(data.get("move_date")), font_size=8)
    _set(movement, 2, 1, data.get("origin_apiary_number"))
    _set(movement, 2, 3, data.get("movement_reason") or "Verstellen")
    _set(movement, 2, 4, data.get("colonies"))
    _set(movement, 2, 5, "Bienenvolk (V)")

    output = BytesIO()
    document.save(output)
    return output.getvalue()


def _set(table, row: int, column: int, value, font_size: float | None = None) -> None:
    if value not in (None, ""):
        cell = table.cell(row, column)
        cell.text = str(value)
        if font_size:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(font_size)


def _date(value) -> str:
    return value.strftime("%d.%m.%Y") if hasattr(value, "strftime") else str(value or "")


def _short_date(value) -> str:
    return (
        f"{value.day}.{value.month}.{str(value.year)[-2:]}"
        if hasattr(value, "strftime")
        else str(value or "")
    )


def _join(*parts) -> str:
    return ", ".join(str(part).strip() for part in parts if str(part or "").strip())
