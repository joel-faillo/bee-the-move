# Bee the Move

Bee the Move is a one-page Streamlit application for planning hive moves in
Switzerland. It compares nearby areas with current Swiss public data, explains
the ranking, and carries the selected destination into the practical movement
documents.

The recommendation is decision support. It is not an official flowering
forecast, health clearance, land permission or guarantee of nectar.

## Start locally

Python 3.11 or newer is required; the project is tested with Python 3.14.6.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local address printed by Streamlit, normally
<http://localhost:8501>. Do **not** use `python app.py`: Streamlit applications
must be launched with the command above.

Optional road distance requires an openrouteservice key:

```bash
export OPENROUTESERVICE_API_KEY="your-key"
python -m streamlit run app.py
```

Without a key, the app clearly uses direct Haversine distance.

## User flow

1. Type a Swiss place or postcode. Nothing is preselected; the user must choose
   one official GeoAdmin suggestion. The autocomplete excludes canton and
   district centroids because they are too broad for an apiary location.
2. Enter the planned arrival, the end of the period and the number of colonies.
   Four weeks is only an editable starting point; the application does not claim
   that every colony should remain for a standard duration. Also choose a direct
   geographic search radius from 2 to 50 km and, optionally, one mapped forage
   category or elevation band. Elevation is an eligibility filter, not a hidden
   score bonus.
3. The same planning period drives the historical flowering model and forage
   continuity. Orchard, meadow and pasture preferences also focus the
   phenology model on directly matching observed species. Other preferences
   still rank real mapped agricultural area, while the interface explains that
   no direct species match exists in the MeteoSwiss phenology dataset.
4. Compare regional candidates. These are representative MeteoSwiss
   place/postcode points, not approved parcels. The searched area is always
   retained as a benchmark and is shown at 0 km.
5. Inspect two decision horizons separately. Site suitability uses flowering
   and mapped forage across the complete planned stay. Short-term bee-flight
   conditions use up to seven available days from MeteoSwiss's current
   nine-day forecast, but never change the regional ranking. Monthly
   1991–2020 climate normals describe typical temperature, precipitation and
   relative sunshine for the selected calendar period, and are labelled as
   historical context rather than a forecast. Map switches show the search radius, recommended
   candidates, nearest phenology station, agricultural forage centroids and nearest
   pollen station; the last two context layers start hidden to keep the map
   readable.
6. If arrival lies beyond the live forecast, the regional index remains
   comparable and the user is told to return within nine days of the move to
   assess the first foraging days. Actual transport should be planned for a
   suitable early-morning, evening or night period.
7. Treat the selected result as a regional candidate. A field checklist covers
   water, microclimate, access, safety distances, permission and current health
   restrictions before paperwork begins.
8. Select a destination and enter the beekeeper, land, contract and movement
   details in the same page. The recommended-area centre is only a reference:
   enter the exact apiary or parcel coordinates for the official form. GeoAdmin
   verifies that point and determines the competent destination canton.
9. Enter dates in Swiss day/month/year order. The planned arrival date is
   proposed as the movement date but remains editable. Results, charts and
   source timestamps use the same order. Open-ended agreements do not request
   or insert a fixed-term end date.
10. Download a prefilled copy of the original German BienenSchweiz sample site
   agreement and the official German, French or Italian BLV stock-control form.
   Blank source links follow the selected BLV language where an official
   version exists.
11. Review the official guidance for the detected origin and destination
   cantons. The app prepares a German, French or Italian email **requesting
   confirmation** of the procedure; it is not itself a notification or permit.

Signatures remain blank. The user must review the generated files, contact the
competent bee inspectors, check current restriction zones, and complete any
canton-specific procedure.

Changing any form field invalidates the previous downloads, preventing an old
document from being mistaken for the revised version. The app also checks date
order and dependent contract fields before generation.

Personal and property details remain in the current Streamlit session for
document generation. They are not written to the repository or sent to the
public-data APIs used for the recommendation.

Dates up to one year ahead can be planned. Historical observations and climate
normals describe seasonal suitability, but the app never presents them as a
weather forecast for a future date.

## Regional suitability index

| Component | Weight | Inputs |
|---|---:|---|
| Flowering and forage | 70% | ML flowering timing across the planned stay plus mapped agricultural resources |
| Continuity | 20% | Flowering stability across the planned stay and forage diversity |
| Logistics | 10% | Fixed 0–50 km practicality scale using direct distance, or road distance when openrouteservice is configured |

Short-term bee-flight weather is displayed separately and never changes the
regional ranking. This keeps the same place comparable across planning dates.
The search radius is a filter and cannot change an unchanged destination's
logistics score. Pollen is shown as context and does not add points. Elevation can exclude
candidates only when the user deliberately chooses a band; it never adds score
points. Agricultural forage coefficients and normalisation thresholds are
transparent prototype assumptions, not official agronomic thresholds. The
pale-green map dots are agricultural-parcel centroids, not bees, pollen counts
or flowering observations.

If flowering or agricultural evidence fails, the interface marks the result as
partial and does not present a comparable regional index.
Climate normals are context rather than a score component because MeteoSwiss
does not publish an official threshold that turns monthly normals into apiary
quality. This avoids presenting a project assumption as an official rule.

## Flowering model

The included model is a `RandomForestRegressor` trained on MeteoSwiss
observations explicitly labelled **flowering (50%)**. The held-out evaluation
uses the newest five complete years, then the persisted model is refitted on all
complete years.

| Measure | Included model |
|---|---:|
| Training observations | 58,894 |
| Training years | 1951-2025 |
| Held-out years | 2021-2025 |
| Model mean absolute error | 9.45 days |
| Historical-median baseline error | 14.52 days |
| Retrained | 29 September 2026 |
| MeteoSwiss source snapshot | 25 September 2026 |

Retraining is optional:

```bash
python -m scripts.train_flowering_model
```

The output estimates seasonal timing, not field-level flowering or nectar.
The general signal is limited to phenological species with a documented nectar
or pollen role; wind-pollinated birch and cocksfoot are not treated as forage.
The validation is chronological rather than a fully independent spatial field
trial, so the model must remain a prototype planning signal.

## Data sources and source documents

| Source | Contribution |
|---|---|
| [GeoAdmin Search](https://docs.geo.admin.ch/access-data/search.html) | Place/postcode suggestions and coordinates |
| [GeoAdmin Height](https://docs.geo.admin.ch/access-data/get-point-height.html) | Candidate elevation |
| [GeoAdmin Identify](https://docs.geo.admin.ch/access-data/identify-features.html) | Origin and destination canton |
| [MeteoSwiss Local Forecast](https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data) | Hourly inputs summarised daily; seven days shown from a source horizon of up to nine full days |
| [MeteoSwiss Spatial Climate Normals](https://opendatadocs.meteoswiss.ch/c-climate-data/c7-spatial-climate-normals) | Typical monthly temperature, precipitation and relative sunshine for 1991–2020 on the 1 km grid |
| [MeteoSwiss Phenology](https://opendatadocs.meteoswiss.ch/a-data-groundbased/a9-phenological-observations) | ML target and observational fallback |
| [MeteoSwiss Pollen](https://opendatadocs.meteoswiss.ch/a-data-groundbased/a7-pollen-stations) | Regional context only |
| [Swiss agricultural land use](https://opendata.swiss/en/dataset/landwirtschaftliche-nutzungsflachen-schweiz) | Annual agricultural parcels used by the app's explicit forage heuristic |
| [swisstopo Vector Tiles](https://docs.geo.admin.ch/visualize-data/vector-tiles.html) | Official map |
| [BLV bee guidance](https://www.blv.admin.ch/de/bienen) | Registration, identification and movement rules |
| [BienenSchweiz site guidance](https://bienen.ch/wp-content/uploads/2023/04/4.9_standortwahl.pdf) | Water, microclimate, access, colony-count and field-verification guidance |
| [BienenSchweiz moving guidance](https://bienen.ch/wp-content/uploads/2022/11/4.9.1_wandern_mit_bienen.pdf) | Planning checks, safety distances and transport timing |
| [BLV stock-control template (German)](https://www.blv.admin.ch/dam/de/sd-web/keeNTCMwOYVC/vorlage-bestandeskontrolle-bienenvoelker-de.docx) | Original federal Word form, published 21 April 2026 |
| [BLV stock-control template (French)](https://www.blv.admin.ch/dam/fr/sd-web/keeNTCMwOYVC/vorlage-bestandeskontrolle-bienenvoelker-fr.docx) | Original federal Word form, published 21 April 2026 |
| [BLV stock-control template (Italian)](https://www.blv.admin.ch/dam/it/sd-web/keeNTCMwOYVC/vorlage-bestandeskontrolle-bienenvoelker-it.docx) | Original federal Word form, published 21 April 2026 |
| [BLV stock-control instructions](https://www.blv.admin.ch/dam/de/sd-web/dQWh4Q6Qxpng/anleitung-fuehren-bestandeskontrolle-bienen-de.pdf) | Official instructions, published 24 June 2026 |
| Official cantonal bee/veterinary pages | Current local procedure, contacts and restriction-zone entry points for all 26 cantons |
| [BienenSchweiz sample site agreement (German)](https://bienen.ch/wp-content/uploads/2022/11/Mustervereinbarung_fuer_Platz_fuer_Bienenhaltung_Formular.pdf) | Original association sample agreement used for the prefilled PDF |
| [SAR sample site agreement (French)](https://abeilles.ch/wp-content/uploads/sites/7/2023/03/Modele_de_convention_entre_proprietaire_terrien_et_apiculteur_version_imprimable.pdf) | Official French-language association version linked as a blank source |
| [openrouteservice / HeiGIT](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/) | Optional road route through the hosted `api.heigit.org` endpoint |

The 26 official cantonal entry points and the encoded local differences were
checked on 28 September 2026 and are listed directly in
`services/compliance.py`. Important differences include advance-notice periods
in Basel-Landschaft, Fribourg and Graubünden, the permit regime in Glarus, the
internal-canton exception in Neuchâtel, and clearance requirements in Ticino.
Temporary restriction zones can change at any time, so the app always links to
the deciding official source instead of claiming automatic legal clearance.

The three BLV official language forms and the German BienenSchweiz sample
agreement are bundled unchanged in `static/forms/` so downloads remain
reliable. The German files were downloaded on 22 September 2026; the French
and Italian BLV files were downloaded from the official pages on 29 September
2026. The online sources were reverified on 29 September 2026. The app only
inserts user data into copies; it does not alter the source clauses or create
an authorisation. No official Swiss Italian or English site-agreement template,
and no official English BLV stock-control template, was found; the app does not
invent either version.

The climate normals are a stable official historical reference, not live
measurements. To keep the deployed app responsive and reproducible, the three
required MeteoSwiss NetCDF grids were reduced to the displayed 0.1-unit
precision in `data/climate_normals_1991_2020.npz`. The snapshot was created on
30 September 2026 from the STAC item updated on 30 June 2026. It contains only
temperature, precipitation, relative sunshine and grid coordinates.

The official HSG Declaration of Authorship supplied with the assignment is
also included unchanged as `static/forms/hsg-declaration-of-authorship.pdf`.
It is a submission document, not part of the beekeeper-facing workflow.

## Project structure

```text
app.py                         one-page interface and guided workflow
analysis.py                    source orchestration and candidate selection
beescore.py                    pure score rules
ml/flowering_model.py          model training, evaluation and inference
model/flowering_model.joblib   included trained artifact
data/climate_normals_1991_2020.npz  compact official grid snapshot
services/geo.py                GeoAdmin search, height and canton
services/meteoswiss.py         hourly local forecast
services/climate_normals.py    historical 1991–2020 climate context
services/phenology.py          observational flowering fallback
services/pollen.py             optional context, never BeeScore
services/landscape.py          mapped agricultural forage
services/compliance.py         canton routing and notification text
services/official_documents.py official PDF/DOCX filling
ui/map.py                      MapLibre and swisstopo map
ui/move_form.py                movement-form options, validation and data mapping
static/forms/                  unmodified official source templates
tests/                         scoring, sources, documents and compliance
```

## Tests

```bash
python -m pytest -q
```

Tests cover every search and form selector value, the score, distance,
elevation bounds, origin retention, canton detection, every map evidence
control, model inference, all 26 official cantonal sources and key local
differences, multilingual request drafts, and preservation of the original
PDF/Word source files and structures while filling copies.

## Course submission checklist

- Replace the five placeholders in `CONTRIBUTIONS.md` with the real work.
- Review `AI_ASSISTANCE.md`, retain the relevant prompts and include Codex in
  the declaration of aids and the video reflection.
- Include the bundled official declaration of authorship with the submission;
  its text states that submission itself confirms the declaration.
- Demonstrate the working app, interaction, visualisations and ML model in a
  human-narrated video of no more than four minutes.
- Upload the actual deliverables, not only external links.

Source attribution for MeteoSwiss data: **Source: MeteoSwiss**.

## AI assistance

OpenAI Codex supported code drafting, review, testing and documentation. The
scope, representative prompts, human verification responsibilities and a
report-ready reference are recorded in [`AI_ASSISTANCE.md`](AI_ASSISTANCE.md).
AI was used as an aid, not as a source for scientific or regulatory claims.
