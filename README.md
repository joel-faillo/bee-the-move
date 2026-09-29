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
   one official GeoAdmin suggestion.
2. Choose a direct geographic search radius up to 100 km and, optionally, one mapped forage category
   or elevation band. Elevation is an eligibility filter, not a hidden score
   bonus.
3. Compare the best areas. The searched area is always retained, even when it
   is not among the top three, and is shown at 0 km.
4. Inspect the map, four BeeScore components, seven-day forecast, flowering
   estimate and elevation. Map switches show the search radius, recommended
   areas, nearest phenology station, agricultural forage centroids and nearest
   pollen station; the last two context layers start hidden to keep the map
   readable.
5. Select a destination and enter the beekeeper, land, contract and movement
   details in the same page.
6. Download prefilled copies of the original BienenSchweiz sample site
   agreement and the official BLV stock-control form.
7. Review the official guidance for the detected origin and destination
   cantons. The app prepares a German, French or Italian email **requesting
   confirmation** of the procedure; it is not itself a notification or permit.

Signatures remain blank. The user must review the generated files, contact the
competent bee inspectors, check current restriction zones, and complete any
canton-specific procedure.

## BeeScore

| Component | Weight | Inputs |
|---|---:|---|
| Flowering and forage | 45% | ML flowering timing plus mapped agricultural resources |
| Flight weather | 30% | Hourly temperature, rain, wind, gust and radiation |
| Continuity | 15% | Seven-day flowering stability and forage diversity |
| Logistics | 10% | Direct distance, or road distance to the nearest routable road when openrouteservice is configured |

Pollen is shown as context and does not add points. Elevation can exclude
candidates only when the user deliberately chooses a band; it never adds score
points. Agricultural forage coefficients and normalisation thresholds are
transparent prototype assumptions, not official agronomic thresholds. The
pale-green map dots are agricultural-parcel centroids, not bees, pollen counts
or flowering observations.

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

## Data sources and source documents

| Source | Contribution |
|---|---|
| [GeoAdmin Search](https://docs.geo.admin.ch/access-data/search.html) | Place/postcode suggestions and coordinates |
| [GeoAdmin Height](https://docs.geo.admin.ch/access-data/get-point-height.html) | Candidate elevation |
| [GeoAdmin Identify](https://docs.geo.admin.ch/access-data/identify-features.html) | Origin and destination canton |
| [MeteoSwiss Local Forecast](https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data) | Hourly inputs summarised daily; seven days shown from a source horizon of up to nine full days |
| [MeteoSwiss Phenology](https://opendatadocs.meteoswiss.ch/a-data-groundbased/a9-phenological-observations) | ML target and observational fallback |
| [MeteoSwiss Pollen](https://opendatadocs.meteoswiss.ch/a-data-groundbased/a7-pollen-stations) | Regional context only |
| [Swiss agricultural land use](https://opendata.swiss/en/dataset/landwirtschaftliche-nutzungsflachen-schweiz) | Annual agricultural parcels used by the app's explicit forage heuristic |
| [swisstopo Vector Tiles](https://docs.geo.admin.ch/visualize-data/vector-tiles.html) | Official map |
| [BLV bee guidance](https://www.blv.admin.ch/de/bienen) | Registration, identification and movement rules |
| [BLV stock-control template](https://www.blv.admin.ch/dam/de/sd-web/keeNTCMwOYVC/vorlage-bestandeskontrolle-bienenvoelker-de.docx) | Original federal Word form, published 21 April 2026 |
| [BLV stock-control instructions](https://www.blv.admin.ch/dam/de/sd-web/dQWh4Q6Qxpng/anleitung-fuehren-bestandeskontrolle-bienen-de.pdf) | Official instructions, published 24 June 2026 |
| Official cantonal bee/veterinary pages | Current local procedure, contacts and restriction-zone entry points for all 26 cantons |
| [BienenSchweiz sample site agreement](https://bienen.ch/wp-content/uploads/2022/11/Mustervereinbarung_fuer_Platz_fuer_Bienenhaltung_Formular.pdf) | Original association sample agreement |
| [openrouteservice / HeiGIT](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/) | Optional road route through the hosted `api.heigit.org` endpoint |

The 26 official cantonal entry points and the encoded local differences were
checked on 28 September 2026 and are listed directly in
`services/compliance.py`. Important differences include advance-notice periods
in Basel-Landschaft, Fribourg and Graubünden, the permit regime in Glarus, the
internal-canton exception in Neuchâtel, and clearance requirements in Ticino.
Temporary restriction zones can change at any time, so the app always links to
the deciding official source instead of claiming automatic legal clearance.

The BLV official form and the BienenSchweiz sample agreement are bundled in
`static/forms/` so downloads remain reliable. They were downloaded on 22
September 2026, and both online source files were reverified byte-for-byte on
29 September 2026. The app only inserts user data into copies; it does not
alter the source clauses or create an authorisation.

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
services/geo.py                GeoAdmin search, height and canton
services/meteoswiss.py         hourly local forecast
services/phenology.py          observational flowering fallback
services/pollen.py             optional context, never BeeScore
services/landscape.py          mapped agricultural forage
services/compliance.py         canton routing and notification text
services/official_documents.py official PDF/DOCX filling
ui/map.py                      MapLibre and swisstopo map
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
