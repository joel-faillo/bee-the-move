# AI assistance record

## Tool and purpose

The team used **OpenAI Codex** as a programming aid between 21 and
28 September 2026. Codex helped restructure an earlier Flask prototype as a
Streamlit application, draft and review Python code, prepare tests, improve
documentation, and audit the interface and the official-source workflow.

AI was not treated as a factual source. Claims about MeteoSwiss, GeoAdmin,
federal forms and cantonal procedures were checked against the official links
recorded in the code and README. Generated suggestions were reviewed and
tested by the project team before inclusion.

## Representative prompts

The working conversation included instructions such as:

> Rebuild Bee the Move as a simple and readable Swiss-wide application. Use
> official, current APIs; train an explainable flowering model; distinguish
> observations, model output and heuristics; and keep the code modular.

> Add location autocomplete, useful filters, the nearest phenology station,
> official map layers, and a guided workflow that fills copies of the original
> forms without changing their clauses.

> Audit every canton using official sources, remove unnecessary complexity,
> test every relevant function, and document AI use according to the course
> requirements.

## Affected code

Substantial AI-assisted drafting or revision appears in `app.py`,
`analysis.py`, `beescore.py`, `ml/flowering_model.py`, `services/`, `ui/map.py`,
the automated tests, and the project documentation. Those modules point back
to this record in their source comments. The trained model uses official
MeteoSwiss observations; Codex did not supply its training values or results.

The team remains responsible for:

1. understanding and explaining every submitted file;
2. verifying source claims and correcting errors;
3. deciding which suggestions to accept, simplify or reject;
4. entering the real team contributions in `CONTRIBUTIONS.md`;
5. naming Codex in the declaration of aids and reflecting on its use in the
   human-narrated project video.

## Suggested in-text citation and reference

For an accompanying report or methods section, describe the use in prose and
cite it as **(OpenAI, 2026)** where AI-assisted content is reproduced.

> OpenAI. (2026). *Codex* (accessed 28 September 2026) [Large language model].
> https://openai.com/codex/

This record follows the course slides and the HSG “Writing with AI” guidance:
AI must be listed as an aid, AI-supported code must be identifiable, and the
team—not the model—must verify factual content and document its own work. This
file does not replace the required declaration of authorship.
