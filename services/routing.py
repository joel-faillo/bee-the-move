"""Optional openrouteservice adapter for road logistics.

When an API key is configured, road distance replaces straight-line distance
in the visible travel context. It never changes biological suitability because
driving convenience does not improve forage available to the colony.

AI assistance: OpenAI Codex supported drafting and review. See
``AI_ASSISTANCE.md`` for scope, prompts and the full citation.
"""

from __future__ import annotations

from services.http import HttpClient

# Public endpoint currently documented for the openrouteservice instance
# hosted by HeiGIT.
ORS_URL = "https://api.heigit.org/openrouteservice/v2/directions/driving-car/geojson"
SNAP_RADIUS_METRES = 2_000


class RoutingService:
    """Fetch driving distance and duration for shortlisted destinations."""

    def __init__(self, http: HttpClient, api_key: str) -> None:
        self.http = http
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def route(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> dict | None:
        """Return a compact route summary, or ``None`` when ORS is disabled."""
        if not self.enabled:
            return None
        data = self.http.post_json(
            ORS_URL,
            {
                "coordinates": [[origin[1], origin[0]], [destination[1], destination[0]]],
                # GeoAdmin place labels and MeteoSwiss forecast points are
                # geographic reference points, not guaranteed road addresses.
                # The public API permits up to 2 km for snapping them to the
                # nearest drivable segment; without this, valid Ticino and
                # Alpine searches can fail even though a road route exists.
                "radiuses": [SNAP_RADIUS_METRES, SNAP_RADIUS_METRES],
            },
            headers={"Authorization": self.api_key},
        )
        summary = data["features"][0]["properties"]["summary"]
        return {
            "distance_km": round(summary["distance"] / 1000, 1),
            "duration_minutes": round(summary["duration"] / 60),
        }
