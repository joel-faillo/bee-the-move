# Bee the Move

Bee the Move is a one-page Streamlit application for planning hive moves in
Switzerland. It compares nearby areas with current Swiss public data, explains
the ranking, and carries the selected destination into the practical movement
documents.

The recommendation is decision support. It is not an official flowering
forecast, health clearance, land permission or guarantee of nectar.

## What the application does — and why

Bee the Move deliberately stops at **regional screening**. It combines public
Swiss data to create a shortlist, shows the evidence behind every result and
then guides the beekeeper through the field, legal and document checks that
cannot be automated honestly. A candidate is therefore a promising area to
inspect, never an automatically approved apiary site.

The current design separates three decisions that use different evidence:

1. **Where:** a biological regional index compares modelled flowering, mapped
   agricultural forage and continuity over the complete planned stay.
2. **When:** the live MeteoSwiss forecast identifies short-term bee-flight
   conditions and a possible three-day movement window.
3. **Whether the exact parcel is usable:** the field checklist, exact
   coordinates, owner agreement and cantonal procedure remain explicit human
   checks.

This separation is intentional. Combining all available numbers into one score
would make changing weather, driving convenience or a nearby monitoring station
look like biological qualities of the land.

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
   By default, up to eight reference points are evaluated, spread by distance
   across the radius and deduplicated by place name. The shortlist is the best
   among this sample, not an exhaustive assessment of every possible location.
5. Inspect two decision horizons separately. Site suitability uses flowering
   and mapped forage across the complete planned stay. Short-term bee-flight
   conditions use up to seven available days from MeteoSwiss's current
   nine-day forecast, but never change the regional ranking. Monthly
   1991–2020 climate normals describe typical temperature, precipitation and
   relative sunshine for the selected calendar period, and are labelled as
   historical context rather than a forecast. Map switches show the search
   radius, recommended candidates, nearest phenology station, representative
   agricultural points, FOEN–WSL habitat context and nearest pollen station. The
   denser context layers start hidden to keep the map readable.
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
The planned colony count carries into the movement form and remains editable.
Edited enquiry text is used by the email link; regenerating documents resets
the enquiry to the current form details.

Dates up to one year ahead can be planned. Historical observations and climate
normals describe seasonal suitability, but the app never presents them as a
weather forecast for a future date.

## Regional suitability index

| Component | Weight | Inputs |
|---|---:|---|
| Flowering and mapped forage | 75% | 65% modelled flowering timing across the stay + 35% agricultural score (80% weighted abundance + 20% category diversity) |
| Continuity | 25% | 70% stable flowering across the stay + 30% mapped forage-category diversity |

The resulting effective contributions are 48.75% flowering timing, 26.25%
mapped agricultural score, and 25% continuity. Expanded fully, they are 48.75%
flowering timing, 21% mapped abundance, 17.5% flowering stability and 12.75%
category diversity. Diversity enters both agricultural context and continuity;
these are the combined weights, not four independently validated measures.
All inputs are bounded to 0–100 before weighting. A result is ranked
only when both flowering and agricultural-land evidence are available; missing
evidence is not silently replaced or reweighted.

These weights are **project heuristics**, not official MeteoSwiss, FOEN or
apicultural thresholds. Flowering receives the largest share because mapped
land use alone does not show whether a resource is blooming during the planned
stay. Continuity is kept separate so that one brief peak cannot dominate an
otherwise weak period. The weights make the prototype understandable and
testable; they have not been calibrated against measured colony productivity or
honey yield.

Short-term bee-flight weather and travel practicality are displayed separately
and never change the biological regional ranking. This keeps the same place
comparable across planning dates and avoids treating a shorter drive as better
for the colony. The search radius is only a filter.

| Evidence kept outside the index | Reason |
|---|---|
| Short-term weather | It changes daily and covers only the beginning of a longer stay. It is timing evidence, not permanent site quality. |
| Direct or road distance | It affects transport practicality, not forage available to bees. |
| Pollen monitoring | A nearby station measures airborne pollen for human-allergy monitoring; it is not a local nectar or bee-forage measurement. |
| Elevation | It can be a user-selected eligibility filter, but the project has no validated universal elevation bonus for Swiss apiaries. |
| Climate normals | They describe typical 1991–2020 monthly conditions, not the weather or flowering of the planned stay. |
| FOEN–WSL Habitat Map | The public WMS is a visual classification layer; rendered colours do not provide bee-specific nectar values or candidate-area totals. |

The agricultural source supplies parcel area and land-use labels, not nectar
yield. Category coefficients, 1/2/3 km distance rings and saturation thresholds
are documented prototype assumptions. Pale-green map dots are representative
points on locally clipped parcels,
not bees, pollen counts, flowering observations or reconstructed boundaries.
Shapely clips official LV95 Polygon/MultiPolygon records to the 1/2/3 km
rings. Declared crop area is allocated proportionally to the geometry inside
each ring, so disconnected or large parcels cannot contribute distant fields.
This single geometry dependency avoids handwritten polygon algorithms.

If flowering or agricultural evidence fails, the interface marks the result as
partial and does not present a comparable regional index.
Climate normals are context rather than a score component because MeteoSwiss
does not publish an official threshold that turns monthly normals into apiary
quality. This avoids presenting a project assumption as an official rule.

The “best period” is a separate three-day window inside the available live
forecast. It combines 55% bee-flight weather and 45% modelled flowering to help
time the move. It neither changes the regional index nor proves that conditions
will remain suitable for the colony's complete stay.
Only consecutive forecast dates form a window; fewer than three available
consecutive days produce an explicitly shorter window. Missing hourly weather
inputs are not substituted with calm wind or dry conditions.
Charts keep actual date values in chronological order and format axes and
tooltips as DD/MM/YYYY, including stays crossing a month or year boundary.

## Limits and correct interpretation

- **Regional, not parcel-level:** candidate coordinates are representative
  MeteoSwiss forecast points. Exact access, exposure, water, shade, spraying,
  mowing, stocking pressure and safety distances require an on-site check.
- **Flowering is modelled:** the machine-learning model estimates the timing of
  MeteoSwiss 50% flowering observations. It does not measure current flowers,
  nectar secretion, honey yield or colony demand at the destination.
- **Agricultural land is a proxy:** the map does not cover every garden, urban
  plant, forest resource or small wild-flower patch and does not say whether a
  mapped crop is accessible, flowering or treated at the relevant moment.
  Coverage and publication years can differ between cantons. Incomplete OGC
  pagination does not produce a comparable index, and resources outside the
  3 km forage radius do not increase abundance or diversity.
- **Forecast horizon is short:** the interface shows up to seven available days
  from a MeteoSwiss source horizon of up to nine full days. Later parts of the
  stay use seasonal flowering estimates and climate context, not invented daily
  weather.
- **Historical climate is not a forecast:** 1991–2020 normals support seasonal
  interpretation but cannot describe the selected year's actual conditions.
- **Monitoring stations are spatial proxies:** phenology and pollen stations may
  be kilometres away and are labelled as references rather than field sensors.
- **Legal and health status changes:** cantonal procedures and restriction zones
  can change after deployment. The app links to the competent official source
  and prepares a request for confirmation; it never claims clearance.
- **No biological guarantee:** colony strength, diseases, competition from other
  colonies and management decisions are outside the available public APIs.

For these reasons, a high regional index means “worth inspecting first”, not
“safe to move”, “officially authorised” or “guaranteed productive”.

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
The model does not use current-season weather inputs, so it cannot directly
capture the selected year's weather-driven shifts in flowering.
If both GeoAdmin height and MeteoSwiss point-height metadata are unavailable,
the model uses 600 m as a last-resort prototype imputation. This is not an
observed elevation; the result remains flagged as missing elevation context.
Displayed date ranges are the 10th–90th percentiles across individual trees,
not calibrated confidence intervals or guaranteed flowering windows.
The general signal is limited to phenological species with a documented nectar
or pollen role; wind-pollinated birch and cocksfoot are not treated as forage.
The validation is chronological rather than a fully independent spatial field
trial, so the model must remain a prototype planning signal.
If the model file is missing or prediction fails, the observational fallback uses three nearby
stations, current-season flowering dates when present, otherwise the median
of the last ten valid observations per parameter. It is a general phenological
signal: it does not apply the model's bee-species or forage-category selection.
The interface identifies this fallback instead of presenting it as an ML result.

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
| [FOEN–WSL Habitat Map v1.2](https://opendata.swiss/en/dataset/lebensraumkarte-der-schweiz) | Optional official habitat context on the map; no nectar or score is inferred |
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
reviewed on 7 October 2026 and are listed directly in
`services/compliance.py`. Important differences include advance-notice periods
in Basel-Landschaft, Fribourg and Graubünden, the permit regime in Glarus, the
internal-canton exception in Neuchâtel, and clearance requirements in Ticino.
Temporary restriction zones can change at any time, so the app always links to
the deciding official source instead of claiming automatic legal clearance.
The Graubünden checklist uses the accessible cantonal accompanying document
(three working days, not the previously encoded ten days). Zug's webpage still
states a ten-working-day registration deadline, conflicting with the federal
three-working-day rule; the app explicitly flags this and follows the shorter
federal deadline pending clarification by the authority.

The three BLV official language forms and the German BienenSchweiz sample
agreement are bundled unchanged in `static/forms/` so downloads remain
reliable. The German files were downloaded on 22 September 2026; the French
and Italian BLV files were downloaded from the official pages on 29 September
2026. All four bundled templates were compared byte for byte with the official
downloads on 7 October 2026 and matched. The app only
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

Settings live in `config.py`; `.env.example` mirrors the default eight-candidate
limit. `.env` or environment variables can override runtime settings without
changing scientific weights. HTTP GET responses have a one-hour cache by
default, so source timestamps indicate the data actually used, not a guarantee
of an immediate refresh on every click. GeoAdmin autocomplete bypasses this cache.
MapLibre 5.24.0 is retained because it was tested inside Streamlit's iframe;
the prior v6 worker-loading issue is documented beside the embedded script.

## Tests

```bash
python -m pytest -q
```

Tests cover every search and form selector value, the score, distance,
elevation bounds, origin retention, canton detection, every map evidence
control, model inference, all 26 official cantonal sources and key local
differences, multilingual request drafts, and preservation of the original
PDF/Word source files and structures while filling copies.

Verification on 7 October 2026: 827 automated tests passed, including all 676
origin/destination canton pairs, the document workflow for each of the 26
cantons, and every declared search/form selector value. Separate live checks
covered 26 postcodes, 26 place-name searches and 26 road routes. Browser checks
covered the map switches/category filters and desktop/mobile layout; all pages
of the three language stock-control copies and the site agreement were rendered
and inspected. The climate-normal STAC item still reported the same 30 June
2026 update as the bundled snapshot.

These are defined test cases, not every possible location or combination.
Seven returned areas lacked usable agricultural evidence and correctly remained
non-comparable. The Basel-Landschaft source blocked automated HTTP requests
with 403; its published guidance was reviewed through the official indexed page,
not treated as a successful live fetch. Temporary orders and actual inspector
approval remain checks for the beekeeper before each move.

## Course submission checklist

- Complete the five members' actual roles in `CONTRIBUTIONS.md`; no work is
  attributed automatically.
- Review `AI_ASSISTANCE.md`, retain relevant prompts and include ChatGPT and Codex in
  the declaration of aids and the video reflection.
- Include the bundled official declaration of authorship with the submission;
  its text states that submission itself confirms the declaration.
- Demonstrate the working app, interaction, visualisations and ML model in a
  human-narrated video of no more than four minutes.
- Upload the actual deliverables, not only external links.
- The supplied assignment sets the Canvas deadline at 10 December 2026,
  23:59, and requires the video/Q&A session on 11 December. Verify later course
  announcements before submission.

Source attribution for MeteoSwiss data: **Source: MeteoSwiss**.

## AI assistance

ChatGPT supported early project discussions, prototype work and proposal wording;
Codex supported code generation, revision, testing and documentation. Their
scope, genuine prompt excerpts, human verification responsibilities and
provisional tool references are recorded in [`AI_ASSISTANCE.md`](AI_ASSISTANCE.md).
AI was used as an aid, not as a source for scientific or regulatory claims.
The supplied project slides require source-code attribution when AI generates
code, plus the video's list of aids and reflection. The AI record is a working
disclosure, not confirmation of final academic compliance: the group must
review the code, record its real contributions and complete verified model/version
details requested by the tutor. Tool names and access dates are not model releases;
missing version information is disclosed rather than invented.
