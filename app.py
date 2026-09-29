"""Bee the Move - one guided Streamlit workflow.

AI assistance citation: OpenAI Codex helped draft and revise this interface
between 21 and 29 September 2026. The project team must review the code and
describe that use in the submitted video and list of aids. See
``AI_ASSISTANCE.md`` for prompts, scope and the full reference.
"""

from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from streamlit_searchbox import st_searchbox

from analysis import BeeMoveAnalysis
from config import Config
from ml.flowering_model import FloweringModel
from services.compliance import (
    FSVO_BEES_URL,
    FSVO_STOCK_CONTROL_GUIDE_URL,
    FSVO_STOCK_CONTROL_TEMPLATE_URLS,
    LAND_AGREEMENT_SOURCE_URL,
    VETERINARY_DIRECTORY_URL,
    movement_steps,
    notification_copy,
    veterinary_office,
)
from services.geo import GeoAdminService
from services.http import HttpClient
from services.landscape import FORAGE_CATEGORIES, LandscapeService
from services.meteoswiss import MeteoSwissForecastService
from services.official_documents import fill_land_agreement, fill_stock_control
from services.phenology import PhenologyService
from services.pollen import PollenService
from services.routing import RoutingService
from ui.map import map_html

load_dotenv()
st.set_page_config(page_title="Bee the Move", page_icon="🐝", layout="wide")

RADIUS_OPTIONS = (2, 5, 10, 15, 20, 30, 50)
FORAGE_OPTIONS = ("Balanced mix", *FORAGE_CATEGORIES)
ELEVATION_OPTIONS = (
    "Any elevation",
    "Below 600 m",
    "600–1,000 m",
    "Above 1,000 m",
)
INSTALLATION_OPTIONS = ("Bee house", "Hives without a bee house", "Other")
SITE_PLAN_OPTIONS = ("Yes", "No")
DURATION_OPTIONS = ("Fixed term", "Open-ended")
NOTICE_PERIOD_OPTIONS = ("Not selected", "3 months", "6 months", "9 months", "12 months")
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


@st.cache_resource
def build_analysis() -> BeeMoveAnalysis:
    """Create one cached adapter per source for the Streamlit process."""
    http = HttpClient(Config.HTTP_TIMEOUT, Config.CACHE_TTL_SECONDS)
    return BeeMoveAnalysis(
        geo=GeoAdminService(http),
        forecast=MeteoSwissForecastService(http),
        phenology=PhenologyService(http),
        landscape=LandscapeService(http),
        pollen=PollenService(http),
        routing=RoutingService(http, Config.OPENROUTESERVICE_API_KEY),
        flowering_model=FloweringModel.load(Config.FLOWERING_MODEL_PATH),
        max_candidates=Config.MAX_CANDIDATES,
    )


def main() -> None:
    _style()
    analysis = build_analysis()
    _header()
    _intro()
    _search(analysis)
    result = st.session_state.get("analysis_result")
    if result:
        selected = _results(result)
        _move_preparation(analysis, result, selected)
    else:
        _empty_state()
    _method_and_sources(analysis)


def _style() -> None:
    """A restrained visual system; Streamlit remains responsible for layout."""
    st.markdown(
        """
        <style>
        :root { --bee-green:#143f35; --bee-yellow:#f5c344; }
        .block-container { max-width: 1220px; padding-top: 2rem; }
        h1, h2, h3 { color: var(--bee-green); letter-spacing: -0.025em; }
        [data-testid="stMetric"] { border:1px solid #e5e7e6; border-radius:10px; padding:.75rem 1rem; }
        [data-testid="stMetricValue"] { font-size:2rem; }
        .hero-copy { font-size:1.08rem; color:#4b5563; max-width:760px; margin-top:-.4rem; }
        .step { border-left:4px solid var(--bee-yellow); padding:.25rem 0 .25rem .8rem; min-height:68px; }
        .source-note { color:#647067; font-size:.86rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _header() -> None:
    mark, copy = st.columns([1, 8], vertical_alignment="center")
    with mark:
        logo = Path("static/img/logo.svg")
        if logo.exists():
            st.image(str(logo), width=86)
        else:
            st.write("🐝")
    with copy:
        st.title("Bee the Move")
        st.markdown(
            '<p class="hero-copy">Find a promising area, understand the evidence, '
            "and prepare the same hive move without leaving the page.</p>",
            unsafe_allow_html=True,
        )


def _intro() -> None:
    with st.expander("New here? See how it works"):
        a, b, c = st.columns(3)
        a.markdown('<div class="step"><b>1 · Search</b><br>Choose a Swiss place or postcode from official suggestions.</div>', unsafe_allow_html=True)
        b.markdown('<div class="step"><b>2 · Compare</b><br>Understand flowering, forage, flight weather and distance.</div>', unsafe_allow_html=True)
        c.markdown('<div class="step"><b>3 · Prepare</b><br>Fill your details once and download prefilled source documents.</div>', unsafe_allow_html=True)
        st.caption("Decision support is not a field inspection, land permission or health clearance.")


def _search(analysis: BeeMoveAnalysis) -> None:
    st.subheader("Where are your hives now?")
    place_col, radius_col = st.columns([3, 1])
    with place_col:
        selected = st_searchbox(
            lambda searchterm: _location_suggestions(analysis, searchterm),
            key="location_search",
            label="Swiss place or postcode",
            placeholder="Start typing, for example St. Gallen or 9000",
            debounce=250,
            clear_on_submit=False,
            edit_after_submit="option",
        )
        st.caption("Type at least two characters and select one official place or postcode.")
    with radius_col:
        radius = st.selectbox(
            "Maximum search radius", RADIUS_OPTIONS, index=2,
            format_func=lambda value: f"{value} km",
        )
        st.caption("Straight-line search radius; the calculated road route can be longer.")
    with st.expander("Search preferences", expanded=False):
        forage_col, elevation_col = st.columns(2)
        with forage_col:
            forage_choice = st.selectbox(
                "Forage focus", FORAGE_OPTIONS,
                help="Optional ranking preference based on mapped agricultural land use. It is not a nectar measurement.",
            )
        with elevation_col:
            elevation_choice = st.selectbox(
                "Elevation band",
                ELEVATION_OPTIONS,
                help="Optional eligibility filter based on GeoAdmin terrain height. It does not add BeeScore points.",
            )

    if selected:
        st.caption(f"Selected: **{selected['label']}** · {selected['kind']}")

    if st.button("Compare nearby areas", type="primary", width="stretch", disabled=selected is None):
        try:
            with st.spinner("Comparing current weather with official Swiss datasets…"):
                result = analysis.run(
                    selected, float(radius),
                    None if forage_choice == "Balanced mix" else forage_choice,
                    elevation_choice,
                )
            st.session_state["analysis_result"] = result
            st.session_state["selected_destination"] = result["results"][0]["name"]
            st.session_state.pop("prepared_documents", None)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("One or more public sources are temporarily unavailable. Please retry.")


def _location_suggestions(analysis: BeeMoveAnalysis, searchterm: str) -> list[tuple[str, dict]]:
    """Return live GeoAdmin choices for the single autocomplete field."""
    if len(searchterm.strip()) < 2:
        return []
    try:
        return [
            (f"{item['label']} · {item['kind']}", item)
            for item in analysis.geo.suggest(searchterm.strip())
        ]
    except Exception:
        # A temporary GeoAdmin failure leaves the search empty instead of
        # offering an unverified free-text location.
        return []


def _empty_state() -> None:
    st.divider()
    st.subheader("One search, one complete decision path")
    left, middle, right = st.columns(3)
    left.markdown("**Official data context**\n\nCurrent MeteoSwiss weather and pollen, historical phenology and annually mapped agricultural resources.")
    middle.markdown("**Explainable recommendation**\n\nEvery result shows its score components; your searched place is always retained.")
    right.markdown("**Practical next step**\n\nThe selected destination flows into the land agreement, stock record and notification draft.")


def _results(result: dict) -> dict:
    st.divider()
    st.header("Recommendation")
    st.caption(
        f"Origin: {result['origin']['name']} · radius: {result['radius_km']:.0f} km · "
        f"forage focus: {result.get('forage_preference') or 'balanced mix'} · "
        f"elevation: {result.get('elevation_preference', 'Any elevation')}"
    )
    candidates = result["results"]
    if len(candidates) == 1 and result.get("elevation_preference") != "Any elevation":
        st.warning(
            "No nearby MeteoSwiss candidate matched the selected elevation band. "
            "The searched area is still shown for comparison."
        )
    labels = [
        f"{item['name']} · {item['score']}/100" +
        (" · searched area" if item["is_origin_area"] else "")
        for item in candidates
    ]
    current = st.session_state.get("selected_destination", candidates[0]["name"])
    current_index = next((i for i, item in enumerate(candidates) if item["name"] == current), 0)
    chosen = st.radio("Choose an area", labels, index=current_index, horizontal=True, label_visibility="collapsed")
    selected = candidates[labels.index(chosen)]
    if selected["name"] != current:
        st.session_state.pop("prepared_documents", None)
    st.session_state["selected_destination"] = selected["name"]

    map_column, detail_column = st.columns([1.65, 1])
    with map_column:
        encoded = base64.b64encode(map_html(result, selected["name"]).encode()).decode()
        st.iframe(f"data:text/html;base64,{encoded}", height=540)
        st.caption(
            "Map controls switch each evidence layer on or off. Small pale-green dots are centroids of mapped "
            "agricultural parcels near the searched place; they are not flowering observations."
        )
    with detail_column:
        st.subheader(selected["name"])
        a, b = st.columns(2)
        a.metric("BeeScore", f"{selected['score']}/100")
        route = selected.get("route")
        if selected["is_origin_area"]:
            distance_label, distance_value = "Distance", "Searched area"
        elif route:
            distance_label, distance_value = "Road distance", f"{route['distance_km']:.1f} km"
        else:
            distance_label, distance_value = "Direct distance", f"{selected['distance_km']:.1f} km"
        b.metric(distance_label, distance_value)
        st.caption("The searched area stays visible even when it is not among the three best scores.")
        for key, title in (
            ("forage", "Flowering & mapped forage"),
            ("flight_weather", "Bee-flight weather"),
            ("continuity", "Seven-day continuity"),
            ("logistics", "Travel practicality"),
        ):
            value = selected["components"][key]
            st.progress(int(value), text=f"{title}: {value:.0f}/100")
        st.info(_candidate_summary(selected))

    weather = pd.DataFrame(selected["weather"]["days"])
    flowering = pd.DataFrame(selected["flowering"].get("daily", []))
    left, right = st.columns(2)
    with left:
        st.markdown("**Seven-day flight conditions**")
        if not weather.empty:
            st.line_chart(weather.set_index("date")[["flight_score"]], y_label="score")
        else:
            st.caption("No forecast series available.")
    with right:
        st.markdown("**Modelled flowering signal**")
        if not flowering.empty:
            st.line_chart(flowering.set_index("date")[["score"]], y_label="score")
        else:
            st.caption("No flowering series available.")

    with st.expander("More evidence for this area"):
        a, b, c = st.columns(3)
        a.metric("Elevation", f"{selected['height_m']:.0f} m" if selected["height_m"] is not None else "Not available")
        a.caption("Context and model feature; no direct BeeScore points.")
        b.metric("Mapped forage", f"{selected['landscape'].get('forage_hectares_equivalent', 0):.1f} ha eq.")
        b.caption(", ".join(selected["landscape"].get("top_resources", [])) or "No mapped categories returned.")
        pollen = result.get("pollen", {})
        if pollen.get("available"):
            c.metric("Pollen station near searched place", pollen.get("station", "Available"))
            c.caption(f"{pollen.get('station_distance_km')} km from the searched place · {pollen.get('timestamp')} · context only.")
        else:
            c.metric("Pollen context", "Not available")
            c.caption("Pollen is never used as a proxy for nectar.")
        predictions = selected["flowering"].get("predictions", [])
        station = result.get("phenology_station")
        if station:
            st.caption(
                f"Purple map marker: nearest MeteoSwiss phenology station, "
                f"{station['name']} ({station['distance_km']} km from the searched place). "
                "It is a reference station; the trained model uses the national historical network."
            )
        if predictions:
            st.dataframe(pd.DataFrame(predictions), hide_index=True, width="stretch")
            st.caption(
                f"Held-out model MAE: {selected['flowering'].get('model_mae_days')} days; "
                f"historical-median baseline: {selected['flowering'].get('baseline_mae_days')} days."
            )
        freshness = []
        forecast_updated = result.get("sources", {}).get("meteoswiss_forecast", {}).get("updated")
        if forecast_updated:
            freshness.append(f"forecast updated {_source_timestamp(forecast_updated)}")
        reference_year = selected.get("landscape", {}).get("reference_year")
        if reference_year:
            freshness.append(f"agricultural land use {reference_year}")
        model_source = selected.get("flowering", {}).get("source_updated")
        if model_source:
            freshness.append(f"flowering-model source snapshot {_source_timestamp(model_source)}")
        if freshness:
            st.caption("Data freshness · " + " · ".join(freshness))
    return selected


def _move_preparation(analysis: BeeMoveAnalysis, result: dict, destination: dict) -> None:
    st.divider()
    st.header("Prepare this hive move")
    st.write(
        f"Selected destination: **{destination['name']}**. Complete the guided fields once; "
        "Bee the Move inserts them into copies of the original source documents."
    )
    origin_canton = _safe_canton(analysis, result["origin"])
    destination_canton = _safe_canton(analysis, destination)
    origin_code = origin_canton.get("code", "") if origin_canton else ""
    destination_code = destination_canton.get("code", "") if destination_canton else ""
    origin_office = veterinary_office(origin_code)
    office = veterinary_office(destination_code)
    default_language = _document_language_for_canton(destination_code)

    with st.container():
        st.subheader("1 · Beekeeper")
        a, b, c = st.columns(3)
        beekeeper = a.text_input("Name and surname *", placeholder="e.g. Anna Keller")
        beekeeper_number = b.text_input(
            "Beekeeper / business number",
            placeholder="e.g. SG-12345",
            help="Official cantonal Betriebs-Nr.; leave blank if it has not been assigned.",
        )
        section = c.text_input("Beekeeping section", placeholder="e.g. Imkerverein St. Gallen")
        a, b = st.columns(2)
        beekeeper_street = a.text_input("Street and number", placeholder="e.g. Rosenbergstrasse 10")
        beekeeper_city = b.text_input("Postcode and town", placeholder="e.g. 9000 St. Gallen")
        a, b = st.columns(2)
        phone = a.text_input("Phone", placeholder="e.g. +41 79 123 45 67")
        email = b.text_input("Email", placeholder="e.g. anna@example.ch")

        st.subheader("2 · Site agreement")
        st.caption(
            "These choices match the original German BienenSchweiz sample agreement; "
            "signatures stay blank."
        )
        a, b, c = st.columns(3)
        landowner = a.text_input(
            "Landowner name and address *",
            placeholder="e.g. Peter Muster, Dorfstrasse 4, 9050 Appenzell",
            help="Official PDF field: Eigentümer. Include the postal address.",
        )
        parcel = b.text_input(
            "Property / parcel *",
            value=destination["name"],
            placeholder="e.g. parcel 123 / field name",
            help="Official PDF field: Liegenschaft / Parzelle.",
        )
        area_m2 = c.number_input(
            "Area (m²)", min_value=0, step=1,
            help="Official PDF field: surface of land made available for the apiary.",
        )
        installation = st.radio(
            "Installation on the site",
            INSTALLATION_OPTIONS, horizontal=True,
            help="Choose the wording that the official agreement should tick.",
        )
        other_installation = st.text_input(
            "Describe the installation", placeholder="e.g. four magazine hives"
        ) if installation == "Other" else ""
        site_plan = st.radio(
            "Will a plan showing the site and access be attached?", SITE_PLAN_OPTIONS, horizontal=True,
        )
        a, b, c = st.columns(3)
        start_date = a.date_input("Use begins *", value=None, format="DD/MM/YYYY")
        duration = b.radio("Duration", DURATION_OPTIONS, horizontal=True)
        if duration == "Fixed term":
            end_date = c.date_input(
                "Fixed term ends *", value=None, format="DD/MM/YYYY"
            )
        else:
            end_date = None
            c.caption("No end date is inserted for an open-ended agreement.")
        a, b = st.columns(2)
        notice_period = a.selectbox("Notice period", NOTICE_PERIOD_OPTIONS)
        notice_timing = b.selectbox("Notice can end", NOTICE_TIMING_OPTIONS)
        specified_notice_date = st.text_input(
            "Specified notice date or rule", placeholder="e.g. 31 October each year"
        ) if notice_timing == "Only on a specified date" else ""
        other_notice_rule = st.text_input(
            "Other notice timing (optional)",
            placeholder="e.g. after the honey harvest",
            help="Fills the additional blank option under Kündigungstermin in the official form.",
        )
        additional_duty = st.text_input(
            "Additional beekeeper duty or agreed condition (optional)",
            placeholder="e.g. keep the access path clear",
            help="Fills the extra bullet under the beekeeper's duties in the official form.",
        )
        a, b = st.columns(2)
        compensation = a.text_input(
            "Compensation amount / description (optional)", placeholder="e.g. CHF 100"
        )
        compensation_period = b.radio("Compensation period", COMPENSATION_PERIOD_OPTIONS, horizontal=True)

        st.subheader("3 · Apiary and movement record")
        language_labels = list(DOCUMENT_LANGUAGE_OPTIONS)
        document_language_label = st.selectbox(
            "Official BLV stock-control language",
            language_labels,
            index=language_labels.index(default_language),
            help=(
                "The BLV publishes separate original templates in German, French and Italian. "
                "This choice changes only the BLV record; the BienenSchweiz sample agreement remains German."
            ),
        )
        document_language = DOCUMENT_LANGUAGE_OPTIONS[document_language_label]
        a, b, c = st.columns(3)
        apiary_number = a.text_input(
            "Destination apiary number", placeholder="e.g. SG-456",
            help="Official BLV field: Stand-Nr. / Flurname.",
        )
        site_street = b.text_input(
            "Destination street / field address", placeholder="e.g. parcel 123, Feldweg",
            help="Official BLV field: Strasse, Nr.",
        )
        site_city = c.text_input(
            "Destination postcode and town",
            value=_postcode_and_town(destination),
            key=f"site_city_{destination['lat']:.5f}_{destination['lon']:.5f}",
            placeholder="e.g. 9050 Appenzell", help="Official BLV field: PLZ / Ort.",
        )
        a, b, c = st.columns(3)
        move_date = a.date_input(
            "Planned move date *", value=None, format="DD/MM/YYYY"
        )
        colonies = b.number_input("Colonies moved", min_value=1, value=1, step=1)
        origin_apiary_number = c.text_input(
            "Origin apiary number", placeholder="e.g. SG-111",
            help="Official BLV movement field: incoming from apiary number.",
        )
        a, b = st.columns(2)
        movement_reason = a.text_input(
            "Movement reason", value="Verstellen",
            placeholder="e.g. Verstellen",
            help="Official BLV field: Ursache / Begründung.",
        )
        inspector = b.text_input(
            "Competent bee inspector (if known)", placeholder="e.g. Max Muster"
        )
        st.caption(f"Destination coordinates filled automatically: {destination['lat']:.6f}, {destination['lon']:.6f}")

        confirmation = st.checkbox(
            "I understand that I must review and sign the documents and complete any required cantonal notification."
        )
        submitted = st.button("Prepare documents", type="primary", width="stretch")

    if submitted:
        if not beekeeper or not landowner or not parcel:
            st.error("Complete the three fields marked with *.")
        elif start_date is None or move_date is None:
            st.error("Choose the agreement start date and planned move date.")
        elif duration == "Fixed term" and end_date is None:
            st.error("Choose an end date or select an open-ended agreement.")
        elif not confirmation:
            st.error("Confirm that official checks, notification and signatures are still required.")
        else:
            data = {
                "beekeeper": beekeeper, "beekeeper_number": beekeeper_number,
                "beekeeper_street": beekeeper_street, "beekeeper_city": beekeeper_city,
                "phone": phone, "email": email, "section": section,
                "landowner": landowner, "parcel": parcel, "area_m2": area_m2,
                "installation": installation, "other_installation": other_installation,
                "site_plan_attached": site_plan == "Yes", "start_date": start_date,
                "fixed_term": duration == "Fixed term", "end_date": end_date,
                "notice_period": notice_period, "notice_timing": notice_timing,
                "specified_notice_date": specified_notice_date,
                "other_notice_rule": other_notice_rule, "additional_duty": additional_duty,
                "compensation": compensation, "compensation_period": compensation_period,
                "apiary_number": apiary_number, "site_street": site_street,
                "site_city": site_city, "move_date": move_date, "colonies": colonies,
                "origin_apiary_number": origin_apiary_number, "bee_inspector": inspector,
                "movement_reason": movement_reason,
                "veterinary_office": office["office"],
                "coordinates": f"{destination['lat']:.4f}/{destination['lon']:.4f}",
                "year": move_date.year,
                "origin_name": result["origin"]["name"],
                "destination_name": destination["name"],
                "origin_canton": origin_code, "destination_canton": destination_code,
            }
            st.session_state["prepared_documents"] = {
                "destination": destination["name"], "language": document_language,
                "data": data,
                "agreement": fill_land_agreement(data),
                "stock_control": fill_stock_control(data, document_language),
            }

    prepared = st.session_state.get("prepared_documents")
    if (
        prepared
        and prepared.get("destination") == destination["name"]
        and prepared.get("language") == document_language
    ):
        st.success("Ready for review: the original source templates have been prefilled.")
        left, right = st.columns(2)
        left.download_button(
            "Download filled BienenSchweiz agreement", prepared["agreement"],
            file_name="bienenschweiz-site-agreement-filled.pdf", mime="application/pdf", width="stretch",
        )
        right.download_button(
            "Download filled BLV stock-control form", prepared["stock_control"],
            file_name="blv-stock-control-filled.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", width="stretch",
        )
        _health_notification(prepared["data"], origin_office, office)

    with st.expander("Official checks before moving"):
        st.caption(f"Detected cantons: {origin_code or 'not available'} → {destination_code or 'not available'}")
        for index, step in enumerate(movement_steps(origin_code, destination_code)):
            st.checkbox(step, key=f"move-step-{index}-{origin_code}-{destination_code}")
        contact_rows = [origin_office]
        if (office["canton"], office["email"]) != (origin_office["canton"], origin_office["email"]):
            contact_rows.append(office)
        for item in contact_rows:
            st.markdown(f"**{item['canton']} · {item['office']}**")
            if item["email"]:
                st.caption(f"Contact: {item['email']}")
            for note in item["notes"]:
                st.write(f"- {note}")
            st.link_button(
                f"Open official {item['canton']} guidance",
                item["source_url"],
            )
        st.caption(
            "Cantonal pages were checked on 28 September 2026. Temporary restriction zones and contacts can change, "
            "so the official page remains the deciding source."
        )
        links = st.columns(4)
        links[0].link_button("BLV bee rules", FSVO_BEES_URL, width="stretch")
        links[1].link_button("Cantonal directory", VETERINARY_DIRECTORY_URL, width="stretch")
        links[2].link_button(
            f"Blank BLV form ({document_language.upper()})",
            FSVO_STOCK_CONTROL_TEMPLATE_URLS[document_language],
            width="stretch",
        )
        links[3].link_button("BLV instructions", FSVO_STOCK_CONTROL_GUIDE_URL, width="stretch")


def _health_notification(data: dict, origin_office: dict, destination_office: dict) -> None:
    """Prepare—not send—a review request for the competent authority."""
    st.subheader("4 · Movement review request")
    st.write(
        "Switzerland has no single nationwide clearance form for every move. The app prepares an email draft so the competent authority can confirm the current procedure. It is not an official submission or permit."
    )
    offices = [origin_office]
    if (destination_office["canton"], destination_office["email"]) != (
        origin_office["canton"], origin_office["email"]
    ):
        offices.append(destination_office)
    valid = False
    for item in offices:
        subject, body = notification_copy(data, item["canton"])
        st.text_area(
            f"Draft request for {item['canton']} — review before sending",
            body, height=300, key=f"health-message-{item['canton']}",
        )
        if "@" in item["email"]:
            valid = True
            mailto = f"mailto:{item['email']}?subject={quote(subject)}&body={quote(body)}"
            st.link_button(
                f"Open email for {item['canton']} · {item['email']}", mailto,
                type="primary", width="stretch",
            )
    if not valid:
        st.warning("The competent email could not be resolved. Use the official cantonal directory above.")
    st.caption(
        "The BLV requires notification to the bee inspector of the old and new inspection districts. "
        "The linked canton-specific rule can be stricter. Bee the Move does not send the message or confirm clearance."
    )


def _method_and_sources(analysis: BeeMoveAnalysis) -> None:
    st.divider()
    with st.expander("Method, limitations and official sources"):
        st.markdown(
            "**BeeScore:** flowering and mapped forage 45% · flight weather 30% · "
            "continuity 15% · logistics 10%. Pollen and elevation are context, not extra points."
        )
        if analysis.flowering_model:
            metrics = analysis.flowering_model.metrics
            a, b, c = st.columns(3)
            a.metric("Held-out model MAE", f"{metrics['model_mae_days']} days")
            b.metric("Baseline MAE", f"{metrics['baseline_mae_days']} days")
            c.metric("Training observations", f"{metrics['training_rows']:,}")
        sources = [
            ("GeoAdmin Search", "Place and postcode suggestions", "https://docs.geo.admin.ch/access-data/search.html"),
            ("GeoAdmin Height", "Terrain elevation", "https://docs.geo.admin.ch/access-data/get-point-height.html"),
            ("GeoAdmin Identify", "Origin and destination canton", "https://docs.geo.admin.ch/access-data/identify-features.html"),
            ("MeteoSwiss Local Forecast", "Bee-flight weather", "https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data"),
            ("MeteoSwiss Phenology", "ML training observations", "https://opendatadocs.meteoswiss.ch/a-data-groundbased/a9-phenological-observations"),
            ("MeteoSwiss Pollen", "Regional context only", "https://opendatadocs.meteoswiss.ch/a-data-groundbased/a7-pollen-stations"),
            ("Agricultural land use", "Annual parcels used by the app's forage heuristic", "https://opendata.swiss/en/dataset/landwirtschaftliche-nutzungsflachen-schweiz"),
            ("swisstopo Vector Tiles", "Official map", "https://docs.geo.admin.ch/visualize-data/vector-tiles.html"),
            ("BLV", "Federal stock-control form and movement guidance", FSVO_BEES_URL),
            ("BienenSchweiz", "Original association sample agreement", LAND_AGREEMENT_SOURCE_URL),
            ("openrouteservice / HeiGIT", "Optional road distance", "https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/"),
        ]
        st.dataframe(
            pd.DataFrame(sources, columns=["Source", "Contribution", "Official link"]),
            hide_index=True, width="stretch",
            column_config={"Official link": st.column_config.LinkColumn()},
        )
        st.warning(
            "A high BeeScore is not proof of current nectar, flowering on a specific parcel, land permission or legal clearance. Check the site and competent authorities."
        )
        st.markdown(
            '<p class="source-note">Official BLV templates: German downloaded 22 September 2026; French and Italian downloaded 29 September 2026. BienenSchweiz German sample agreement downloaded 22 September 2026. Online sources reverified 29 September 2026. Source: MeteoSwiss for MeteoSwiss data.</p>',
            unsafe_allow_html=True,
        )


def _safe_canton(analysis: BeeMoveAnalysis, place: dict) -> dict | None:
    try:
        return analysis.geo.canton(place["lat"], place["lon"])
    except Exception:
        return None


def _postcode_and_town(place: dict) -> str:
    """Format a destination without inventing a postcode that GeoAdmin omitted."""
    name = str(place.get("name") or place.get("label") or "").strip()
    postcode = str(place.get("postal_code") or "").strip()
    if postcode and name.startswith(f"{postcode} - "):
        return f"{postcode} {name.removeprefix(f'{postcode} - ').strip()}"
    if postcode and postcode not in name.split():
        return f"{postcode} {name}".strip()
    return name


def _document_language_for_canton(canton_code: str | None) -> str:
    """Choose a practical default; the user can always select another language."""
    code = (canton_code or "").upper()
    if code == "TI":
        return "Italiano"
    if code in {"FR", "GE", "JU", "NE", "VD", "VS"}:
        return "Français"
    return "Deutsch"


def _candidate_summary(candidate: dict) -> str:
    period = candidate.get("best_period")
    dates = f"{period['from']} to {period['to']}" if period else "not available"
    route = candidate.get("route")
    distance = (
        f"Road route to the nearest routable road: {route['distance_km']} km, "
        f"{route['duration_minutes']} min"
        if route else "Distance shown is direct (Haversine)"
    )
    flowering_score = candidate.get("flowering", {}).get("score")
    low_signal = (
        " Flowering signal remains low throughout this window."
        if flowering_score is not None and flowering_score < 25
        else ""
    )
    return f"Best relative period within the next seven days: {dates}. {distance}.{low_signal}"


def _source_timestamp(value: str) -> str:
    """Turn an ISO source timestamp into a compact, readable UTC label."""
    return value.replace("T", " ")[:16] + " UTC"


if __name__ == "__main__":
    main()
