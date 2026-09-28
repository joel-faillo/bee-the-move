"""Official guidance for moving bee colonies within Switzerland.

The federal baseline comes from the FSVO/BLV. ``CANTON_RULES`` adds only
requirements or procedures stated by an official cantonal source. The app
does not grant a permit and cannot know temporary disease restriction zones;
the beekeeper must open the linked source immediately before every move.

AI assistance: OpenAI Codex helped structure and review this module on
28 September 2026. The project team verified the encoded rules against the
official links below and remains responsible for the submitted code.
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

CHECKED_ON = "2026-09-28"
FEDERAL_MOVE_RULE = (
    "Before crossing an inspection district, notify the bee inspectors for "
    "both the old and new locations; mating units moved to mating stations are exempt."
)


def _rule(office: str, email: str, source_url: str, *notes: str) -> dict:
    return {
        "office": office,
        "email": email,
        "source_url": source_url,
        "checked_on": CHECKED_ON,
        "notes": list(notes),
    }


# All 26 cantons have an official destination. A note is canton-specific only
# when the linked authority publishes a local requirement or implementation.
CANTON_RULES = {
    "AG": _rule(
        "Veterinärdienst Kanton Aargau", "veterinaerdienst@ag.ch",
        "https://www.ag.ch/de/themen/landwirtschaft-tiere/heim-und-nutztiere/tiergesundheit-und-tierseuchen/bienen",
        "Use the published inspection-circle contacts and check current restriction zones.",
    ),
    "AI": _rule(
        "Veterinäramt beider Appenzell", "veterinaeramt@ar.ch",
        "https://ar.ch/verwaltung/departement-gesundheit-und-soziales/veterinaeramt/bienen/",
        "Notify the inspectors for the old and new inspection districts before the move.",
    ),
    "AR": _rule(
        "Veterinäramt beider Appenzell", "veterinaeramt@ar.ch",
        "https://ar.ch/verwaltung/departement-gesundheit-und-soziales/veterinaeramt/bienen/",
        "Notify the inspectors for the old and new inspection districts before the move.",
    ),
    "BE": _rule(
        "Amt für Veterinärwesen Kanton Bern", "info.avet@be.ch",
        "https://www.weu.be.ch/de/start/themen/veterinaerwesen/tierseuchen/bienenseuchen.html",
        "Check the current cantonal restriction-zone map before moving colonies.",
    ),
    "BL": _rule(
        "Amt für Lebensmittelsicherheit und Veterinärwesen", "veterinaerdienst@bl.ch",
        "https://www.baselland.ch/politik-und-behorden/direktionen/volkswirtschafts-und-gesundheitsdirektion/lebensmittelsicherheit-und-veterinarwesen/veterinaerwesen/test-tiergesundh",
        "Notify the inspectors for both locations at least two days in advance when crossing an inspection district.",
    ),
    "BS": _rule(
        "Veterinäramt Kanton Basel-Stadt", "kanzlei.vetamt@bs.ch",
        "https://www.bs.ch/gd/veterinaeramt/tiergesundheit/tierseuchen/bieneninspektorat",
        "Contact the inspector early and wait for the official decision before moving.",
    ),
    "FR": _rule(
        "Service de la sécurité alimentaire et des affaires vétérinaires", "saav-sa@fr.ch",
        "https://www.fr.ch/energie-agriculture-et-environnement/agriculture-et-animaux-de-rente/sante-animale/ruchers",
        "Send the movement notice in writing at least ten days in advance.",
    ),
    "GE": _rule(
        "Service de la consommation et des affaires vétérinaires", "scav@etat.ge.ch",
        "https://www.ge.ch/actualite/beetraffic-application-qui-facilite-annonces-officielles-deplacement-abeilles-25-02-2020",
        "Use the cantonal BeeTraffic procedure and wait for confirmation or authorisation.",
    ),
    "GL": _rule(
        "Amt für Lebensmittelsicherheit und Tiergesundheit GR/GL", "info@alt.gr.ch",
        "https://gesetze.gl.ch/api/de/versions/1571/pdf_file",
        "Seasonal migratory beekeeping requires a cantonal permit; Glarus also has protected native-bee areas.",
    ),
    "GR": _rule(
        "Amt für Lebensmittelsicherheit und Tiergesundheit GR/GL", "info@alt.gr.ch",
        "https://www.gr.ch/DE/institutionen/verwaltung/dvs/alt/aktuelles/tiergesundheit/bienenwesen/Seiten/Bienenwesen---was-ist-zui-beachten-beim-Verstellen-von-Bienenv%C3%B6lkern.aspx",
        "Notify both inspectors in writing at least ten days in advance; arrivals from another canton may require a health confirmation.",
    ),
    "JU": _rule(
        "Service de la consommation et des affaires vétérinaires", "secr.vet@jura.ch",
        "https://www.jura.ch/fr/Autorites/Administration/DES/SCAV/Section-affaires-veterinaires/Apiculture/Apiculture.html",
        "Announce moves between inspection circles to the competent inspectors.",
    ),
    "LU": _rule(
        "Veterinärdienst Kanton Luzern", "veterinaerdienst@lu.ch",
        "https://veterinaerdienst.lu.ch/tiergesundheit/tierseuchen/bekaempfung/bienenseuchen",
        "Notify the inspector when crossing an inspection district and check current restriction zones.",
    ),
    "NE": _rule(
        "Service de la consommation et des affaires vétérinaires", "scav@ne.ch",
        "https://www.ne.ch/themes/economie-et-emploi/agriculture-et-viticulture/detenteurs-danimaux",
        "Moves between existing apiaries inside Neuchâtel need no notice, but must be recorded and checked against restriction zones.",
        "For a move to another canton, notify both inspectors and wait for authorisation.",
    ),
    "NW": _rule(
        "Laboratorium der Urkantone", "sekretariat.kt@laburk.ch",
        "https://www.ur.ch/unterinstanzen/978",
        "The shared veterinary authority applies the federal inspection-district rule; confirm the current inspector with Laburk.",
    ),
    "OW": _rule(
        "Laboratorium der Urkantone", "sekretariat.kt@laburk.ch",
        "https://www.ur.ch/unterinstanzen/978",
        "The shared veterinary authority applies the federal inspection-district rule; confirm the current inspector with Laburk.",
    ),
    "SG": _rule(
        "Amt für Verbraucherschutz und Veterinärwesen", "info.avsv@sg.ch",
        "https://www.sg.ch/umwelt-natur/veterinaerwesen/tiergesundheit/bienenkrankheiten.html",
        "Notify both inspectors before crossing an inspection district; the canton supports BeeTraffic.",
    ),
    "SH": _rule(
        "Veterinäramt Kanton Schaffhausen", "veterinaeramt@sh.ch",
        "https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Verwaltung/Departement-des-Innern/Veterin-ramt/Tierhalter/Bienen-1746130-DE.html",
        "For moves into or out of the canton, notify both inspectors in advance and check restriction zones.",
    ),
    "SO": _rule(
        "Veterinärdienst Kanton Solothurn", "vetd@vd.so.ch",
        "https://wallierhof.so.ch/fachwissen-und-beratung/bienen/meldepflichten/",
        "Notify the inspectors for the old and new locations before crossing an inspection district.",
    ),
    "SZ": _rule(
        "Laboratorium der Urkantone", "sekretariat.kt@laburk.ch",
        "https://www.ur.ch/unterinstanzen/978",
        "The shared veterinary authority applies the federal inspection-district rule; confirm the current inspector with Laburk.",
    ),
    "TG": _rule(
        "Veterinäramt Kanton Thurgau", "veterinaeramt@tg.ch",
        "https://www.rechtsbuch.tg.ch/app/de/texts_of_law/819.11",
        "The cantonal bee-inspection service implements the federal rule; confirm the responsible district inspector before moving.",
    ),
    "TI": _rule(
        "Ufficio del veterinario cantonale", "dss-uvc@ti.ch",
        "https://www4.ti.ch/dss/dsp/uvc/temi/tenuta-di-animali/api/identificazione-apiari-notifiche-e-spostamenti",
        "Notify both inspectors and obtain their clearance before crossing an inspection district.",
        "For arrivals from another canton, the origin inspector may need to certify the health status.",
    ),
    "UR": _rule(
        "Laboratorium der Urkantone", "sekretariat.kt@laburk.ch",
        "https://www.ur.ch/unterinstanzen/978",
        "The shared veterinary authority applies the federal inspection-district rule; confirm the current inspector with Laburk.",
    ),
    "VD": _rule(
        "Direction générale de l'agriculture, de la viticulture et des affaires vétérinaires", "info.svet@vd.ch",
        "https://www.vd.ch/population/veterinaires-et-animaux/apiculture",
        "Notify the inspectors for both locations before crossing an inspection district.",
    ),
    "VS": _rule(
        "Office vétérinaire cantonal", "ovet@admin.vs.ch",
        "https://geo.vs.ch/web/scav/veterinaire/abeille",
        "Notify before crossing an inspection district or canton, and check current disease and seasonal plant-health restrictions.",
    ),
    "ZG": _rule(
        "Veterinärdienst Kanton Zug", "info.vetd@zg.ch",
        "https://zg.ch/de/natur-umwelt-tiere/veterinaerwesen/tiergesundheit/bieneninspektorat",
        "Zug has one cantonal inspector; register a new apiary or change within ten working days and record every movement.",
    ),
    "ZH": _rule(
        "Veterinäramt Kanton Zürich", "kanzlei@veta.zh.ch",
        "https://www.zh.ch/de/umwelt-tiere/tiere/tierseuchen.html",
        "Notify both inspectors before crossing an inspection district or canton and check restriction zones.",
    ),
}


def cantonal_rule(canton_code: str | None) -> dict:
    """Return the audited official entry point for one canton."""
    code = (canton_code or "").upper()
    rule = CANTON_RULES.get(code)
    if not rule:
        return {
            "canton": code or "Unknown",
            "office": "Cantonal veterinary service",
            "email": "",
            "source_url": VETERINARY_DIRECTORY_URL,
            "checked_on": CHECKED_ON,
            "notes": ["Resolve the competent inspector from the official BLV directory."],
        }
    return {"canton": code, **rule}


def veterinary_office(canton_code: str | None) -> dict:
    """Backward-compatible alias used by the document and email workflow."""
    return cantonal_rule(canton_code)


def movement_steps(origin_canton: str | None, destination_canton: str | None) -> list[str]:
    """Build a checklist from federal rules and the two relevant cantons."""
    origin = (origin_canton or "").upper()
    destination = (destination_canton or "").upper()
    steps = [
        "Confirm that the beekeeper and every apiary are registered and visibly identified.",
        "Check current disease restriction zones at origin and destination immediately before moving.",
        "Record the move in the official colony stock-control record and retain it for three years.",
    ]
    if origin and destination and origin != destination:
        steps.insert(2, FEDERAL_MOVE_RULE)
    elif destination == "NE":
        steps.insert(2, CANTON_RULES["NE"]["notes"][0])
    elif origin and destination:
        steps.insert(2, "Confirm whether the move crosses an inspection district; if it does, the federal notification rule applies.")
    else:
        steps.insert(2, "Resolve both cantons and the competent inspection districts before moving.")

    for code in dict.fromkeys((origin, destination)):
        for note in cantonal_rule(code)["notes"] if code else []:
            if note not in steps:
                steps.append(note)
    steps.append("Open the linked cantonal source again on the day of planning; temporary orders can change without notice.")
    return steps


def notification_copy(data: dict, canton: str) -> tuple[str, str]:
    """Create a draft inquiry, never an official clearance or submission."""
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
        subject = f"Demande concernant un déplacement de colonies: {origin} – {destination}"
        body = (
            "Bonjour,\n\nJe vous prie de vérifier le déplacement prévu de colonies d'abeilles.\n\n"
            "Apiculteur/trice: {beekeeper}\nN° d'exploitation: {beekeeper_number}\n"
            "Rucher de départ: {origin}, n° {origin_number}\n"
            "Rucher de destination: {destination}, n° {destination_number}\n"
            "Coordonnées de destination: {coordinates}\nDate: {date}\nNombre de colonies: {colonies}\n\n"
            "Merci de me confirmer la procédure officielle, le délai et l'autorisation éventuellement requise. "
            "Ce message est un projet préparé par Bee the Move et non une autorisation.\n\nMeilleures salutations\n"
            "{beekeeper}\n{phone}\n{email}"
        ).format(**common)
    elif canton == "TI":
        subject = f"Richiesta per spostamento di colonie: {origin} – {destination}"
        body = (
            "Buongiorno,\n\nVi chiedo di verificare il seguente spostamento previsto di colonie di api.\n\n"
            "Apicoltore/trice: {beekeeper}\nN. azienda: {beekeeper_number}\n"
            "Apiario di partenza: {origin}, n. {origin_number}\n"
            "Apiario di destinazione: {destination}, n. {destination_number}\n"
            "Coordinate della destinazione: {coordinates}\nData: {date}\nNumero di colonie: {colonies}\n\n"
            "Vi prego di confermare la procedura ufficiale, il termine e l'eventuale autorizzazione necessaria. "
            "Questo messaggio è una bozza preparata da Bee the Move e non un'autorizzazione.\n\nCordiali saluti\n"
            "{beekeeper}\n{phone}\n{email}"
        ).format(**common)
    else:
        subject = f"Anfrage zur Bienenverstellung: {origin} – {destination}"
        body = (
            "Guten Tag\n\nBitte prüfen Sie die folgende geplante Verstellung von Bienenvölkern.\n\n"
            "Imker/in: {beekeeper}\nBetriebs-Nr.: {beekeeper_number}\n"
            "Ausgangsstand: {origin}, Stand-Nr. {origin_number}\n"
            "Zielstand: {destination}, Stand-Nr. {destination_number}\n"
            "Koordinaten Ziel: {coordinates}\nDatum: {date}\nAnzahl Bienenvölker: {colonies}\n\n"
            "Bitte bestätigen Sie das offizielle Verfahren, die Frist und eine allenfalls erforderliche Bewilligung. "
            "Diese Nachricht ist ein von Bee the Move vorbereiteter Entwurf und keine Bewilligung.\n\nFreundliche Grüsse\n"
            "{beekeeper}\n{phone}\n{email}"
        ).format(**common)
    return subject, body


def _place_with_canton(name: str, canton: str) -> str:
    suffix = f"({canton})" if canton else ""
    return name if not suffix or suffix in name else f"{name} {suffix}"
