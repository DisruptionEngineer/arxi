from arxi.main import app


async def test_ws_endpoint_registered():
    """The /ws/events route should be registered on the app."""
    routes = [r.path for r in app.routes]
    assert "/ws/events" in routes
