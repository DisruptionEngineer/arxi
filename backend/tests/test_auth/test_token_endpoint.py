async def test_get_token_returns_jwt(client):
    """GET /api/auth/token should return a JWT string for authenticated users."""
    resp = await client.get("/api/auth/token")
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert isinstance(body["token"], str)
    assert len(body["token"]) > 0
