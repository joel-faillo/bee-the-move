from services.routing import ORS_URL, RoutingService


class StubHttp:
    def __init__(self):
        self.request = None

    def post_json(self, url, payload, headers=None):
        self.request = (url, payload, headers)
        return {
            "features": [
                {"properties": {"summary": {"distance": 12_345, "duration": 1_506}}}
            ]
        }


def test_routing_uses_current_heigit_endpoint_and_converts_units():
    http = StubHttp()
    service = RoutingService(http, "secret-key")

    route = service.route((47.42, 9.37), (47.33, 9.41))

    assert ORS_URL.startswith("https://api.heigit.org/openrouteservice/")
    assert http.request == (
        ORS_URL,
        {"coordinates": [[9.37, 47.42], [9.41, 47.33]]},
        {"Authorization": "secret-key"},
    )
    assert route == {"distance_km": 12.3, "duration_minutes": 25}


def test_routing_is_disabled_without_a_key():
    service = RoutingService(StubHttp(), "")

    assert not service.enabled
    assert service.route((47.42, 9.37), (47.33, 9.41)) is None
