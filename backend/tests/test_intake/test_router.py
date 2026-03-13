from pathlib import Path

FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures"


async def test_ingest_newrx_endpoint(client):
    xml = (FIXTURE_DIR / "sample_newrx.xml").read_text()
    resp = await client.post(
        "/api/intake/newrx",
        content=xml,
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "parsed"
    assert data["drug_description"] == "Amoxicillin 500 MG Oral Capsule"


async def test_get_queue(client):
    resp = await client.get("/api/intake/queue")
    assert resp.status_code == 200
    assert "prescriptions" in resp.json()
