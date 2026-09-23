"""Nationwide routing for Swiss hive-movement compliance information.

AI assistance citation: OpenAI Codex helped draft this module on 21 September
2026. Contacts come from the official FSVO/BLV cantonal veterinary directory
and must be rechecked before a real submission because cantonal details change.
"""

from __future__ import annotations

VETERINARY_DIRECTORY_URL = (
    "https://www.blv.admin.ch/dam/blv/de/dokumente/import-export/import/"
    "adressliste-kantonalen-veterinaeraemter-db.pdf.download.pdf/"
    "Adressliste%20der%20kantonalen%20Veterinaeraemter.pdf"
)
FSVO_BEES_URL = "https://www.blv.admin.ch/de/bienen"
FSVO_STOCK_CONTROL_TEMPLATE_URL = (
    "https://www.blv.admin.ch/dam/de/sd-web/keeNTCMwOYVC/"
    "vorlage-bestandeskontrolle-bienenvoelker-de.docx"
)
FSVO_STOCK_CONTROL_GUIDE_URL = (
    "https://www.blv.admin.ch/dam/de/sd-web/dQWh4Q6Qxpng/"
    "anleitung-fuehren-bestandeskontrolle-bienen-de.pdf"
)
LAND_AGREEMENT_SOURCE_URL = (
    "https://bienen.ch/wp-content/uploads/2022/11/"
    "Mustervereinbarung_fuer_Platz_fuer_Bienenhaltung_Formular.pdf"
)

# Several cantons share one veterinary service. Keeping the compact official
# grouping makes the mapping easier to audit than 26 repeated records.
_GROUPS = {
    "AG": ("Veterinärdienst Kanton Aargau", "veterinaerdienst@ag.ch"),
    "AR": ("Veterinäramt beider Appenzell", "veterinaeramt@ar.ch"),
    "AI": ("Veterinäramt beider Appenzell", "veterinaeramt@ar.ch"),
    "BE": ("Amt für Veterinärwesen Kanton Bern", "info.avet@be.ch"),
    "BL": ("Veterinärdienst Kanton Basel-Landschaft", "veterinaerdienst@bl.ch"),
    "BS": ("Veterinäramt Kanton Basel-Stadt", "kanzlei.vetamt@bs.ch"),
    "FR": ("Service de la sécurité alimentaire et des affaires vétérinaires", "saav-vc@fr.ch"),
    "GE": ("Service de la consommation et des affaires vétérinaires", "scav@etat.ge.ch"),
    "GR": ("Amt für Lebensmittelsicherheit und Tiergesundheit GR/GL", "info@alt.gr.ch"),
    "GL": ("Amt für Lebensmittelsicherheit und Tiergesundheit GR/GL", "info@alt.gr.ch"),
    "JU": ("Service de la consommation et des affaires vétérinaires", "secr.vet@jura.ch"),
    "LU": ("Veterinärdienst Kanton Luzern", "veterinaerdienst@lu.ch"),
    "NE": ("Service de la consommation et des affaires vétérinaires", "scav@ne.ch"),
    "NW": ("Laboratorium der Urkantone", "kt@laburk.ch"),
    "OW": ("Laboratorium der Urkantone", "kt@laburk.ch"),
    "SZ": ("Laboratorium der Urkantone", "kt@laburk.ch"),
    "UR": ("Laboratorium der Urkantone", "kt@laburk.ch"),
    "SG": ("Amt für Verbraucherschutz und Veterinärwesen", "info.avsv@sg.ch"),
    "SH": ("Veterinäramt Kanton Schaffhausen", "veterinaeramt@sh.ch"),
    "SO": ("Veterinärdienst Kanton Solothurn", "vetd@vd.so.ch"),
    "TG": ("Veterinäramt Kanton Thurgau", "veterinaeramt@tg.ch"),
    "TI": ("Ufficio del veterinario cantonale", "dss-uvc@ti.ch"),
    "VD": ("Direction générale de l'agriculture, de la viticulture et des affaires vétérinaires", "info.svet@vd.ch"),
    "VS": ("Office vétérinaire cantonal", "ovet@admin.vs.ch"),
    "ZG": ("Veterinärdienst Kanton Zug", "info.vetd@zg.ch"),
    "ZH": ("Veterinäramt Kanton Zürich", "kanzlei@veta.zh.ch"),
}


def veterinary_office(canton_code: str | None) -> dict:
    """Return a verified-directory contact and a mandatory verification link."""
    code = (canton_code or "").upper()
    office, email = _GROUPS.get(
        code, ("Cantonal veterinary service", "See the official BLV directory")
    )
    return {
        "canton": code or "Unknown",
        "office": office,
        "email": email,
        "directory_url": VETERINARY_DIRECTORY_URL,
        "source_date": "2024-07-30",
        "link_checked_on": "2026-09-21",
        "verification_note": "Verify the current office and cantonal form before sending.",
    }


def movement_steps(origin_canton: str | None, destination_canton: str | None) -> list[str]:
    """Return guidance without pretending to grant regulatory clearance."""
    different = origin_canton and destination_canton and origin_canton != destination_canton
    steps = [
        "Confirm that the beekeeper and every apiary are registered and visibly identified.",
        "Check current disease restriction zones at both origin and destination using the official cantonal source.",
        "Update the official BLV stock-control record for every colony moved.",
    ]
    if different:
        steps.insert(
            2,
            "Contact the competent inspectors or veterinary services at both origin and destination before moving the colonies.",
        )
    else:
        steps.insert(
            2,
            "Confirm with the competent cantonal service whether the move crosses an inspection district and which notice is required.",
        )
    steps.append("Use the canton-specific official form where one is required.")
    return steps


def notification_copy(data: dict, canton: str) -> tuple[str, str]:
    """Create a reviewable movement notice in the canton's main language."""
    origin = _place_with_canton(data["origin_name"], data["origin_canton"])
    destination = _place_with_canton(data["destination_name"], data["destination_canton"])
    common = {
        "beekeeper": data["beekeeper"],
        "beekeeper_number": data["beekeeper_number"] or "-",
        "origin": origin,
        "origin_number": data["origin_apiary_number"] or "-",
        "destination": destination,
        "destination_number": data["apiary_number"] or "-",
        "coordinates": data["coordinates"],
        "date": data["move_date"].strftime("%d.%m.%Y"),
        "colonies": data["colonies"],
        "phone": data["phone"],
        "email": data["email"],
    }
    if canton in {"FR", "GE", "JU", "NE", "VD", "VS"}:
        subject = f"Annonce de déplacement de colonies: {origin} – {destination}"
        body = (
            "Bonjour,\n\nJe vous annonce le déplacement prévu de colonies d'abeilles.\n\n"
            "Apiculteur/trice: {beekeeper}\nN° d'exploitation: {beekeeper_number}\n"
            "Rucher de départ: {origin}, n° {origin_number}\n"
            "Rucher de destination: {destination}, n° {destination_number}\n"
            "Coordonnées de destination: {coordinates}\nDate: {date}\nNombre de colonies: {colonies}\n\n"
            "Merci de m'indiquer si un contrôle, une autre annonce ou un formulaire cantonal est nécessaire. "
            "Je peux joindre le contrôle d'effectif rempli sur demande.\n\nMeilleures salutations\n"
            "{beekeeper}\n{phone}\n{email}"
        ).format(**common)
    elif canton == "TI":
        subject = f"Notifica spostamento di colonie: {origin} – {destination}"
        body = (
            "Buongiorno,\n\nCon la presente notifico lo spostamento previsto di colonie di api.\n\n"
            "Apicoltore/trice: {beekeeper}\nN. azienda: {beekeeper_number}\n"
            "Apiario di partenza: {origin}, n. {origin_number}\n"
            "Apiario di destinazione: {destination}, n. {destination_number}\n"
            "Coordinate della destinazione: {coordinates}\nData: {date}\nNumero di colonie: {colonies}\n\n"
            "Vi prego di comunicarmi se sono necessari un controllo, un'ulteriore notifica o un modulo cantonale. "
            "Su richiesta posso allegare il controllo dell'effettivo compilato.\n\nCordiali saluti\n"
            "{beekeeper}\n{phone}\n{email}"
        ).format(**common)
    else:
        subject = f"Meldung Bienenverstellung: {origin} – {destination}"
        body = (
            "Guten Tag\n\nHiermit melde ich die geplante Verstellung von Bienenvölkern.\n\n"
            "Imker/in: {beekeeper}\nBetriebs-Nr.: {beekeeper_number}\n"
            "Ausgangsstand: {origin}, Stand-Nr. {origin_number}\n"
            "Zielstand: {destination}, Stand-Nr. {destination_number}\n"
            "Koordinaten Ziel: {coordinates}\nDatum: {date}\nAnzahl Bienenvölker: {colonies}\n\n"
            "Bitte teilen Sie mir mit, ob eine Kontrolle, weitere Meldung oder ein kantonales Formular erforderlich ist. "
            "Die ausgefüllte Bestandeskontrolle kann ich auf Anfrage beilegen.\n\nFreundliche Grüsse\n"
            "{beekeeper}\n{phone}\n{email}"
        ).format(**common)
    return subject, body


def _place_with_canton(name: str, canton: str) -> str:
    suffix = f"({canton})" if canton else ""
    return name if not suffix or suffix in name else f"{name} {suffix}"
