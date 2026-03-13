import pytest


async def test_non_admin_gets_403(client):
    """Pharmacist role should be denied access."""
    res = await client.get("/api/audit/logs")
    assert res.status_code == 403


async def test_admin_gets_logs(admin_client, db):
    """Admin should get empty list when no logs exist."""
    res = await admin_client.get("/api/audit/logs")
    assert res.status_code == 200
    data = res.json()
    assert data["logs"] == []
    assert data["total"] == 0


async def test_admin_gets_seeded_logs(admin_client, db):
    """Admin should see audit entries with computed changes."""
    from arxi.modules.compliance.service import AuditService

    svc = AuditService(db)
    await svc.log(
        action="prescription.approve", actor_id="pharm-1", actor_role="pharmacist",
        resource_type="prescription", resource_id="rx-100",
        before_state={"status": "pending_review"},
        after_state={"status": "approved"},
    )
    await db.commit()

    res = await admin_client.get("/api/audit/logs")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    entry = data["logs"][0]
    assert entry["action"] == "prescription.approve"
    assert len(entry["changes"]) == 1
    assert entry["changes"][0]["field"] == "status"
    assert entry["changes"][0]["from_value"] == "pending_review"
    assert entry["changes"][0]["to_value"] == "approved"


async def test_filter_by_action(admin_client, db):
    from arxi.modules.compliance.service import AuditService

    svc = AuditService(db)
    await svc.log(
        action="prescription.create", actor_id="a1", actor_role="agent",
        resource_type="prescription", resource_id="rx-1",
    )
    await svc.log(
        action="prescription.approve", actor_id="p1", actor_role="pharmacist",
        resource_type="prescription", resource_id="rx-1",
    )
    await db.commit()

    res = await admin_client.get("/api/audit/logs?action=prescription.create")
    data = res.json()
    assert data["total"] == 1
    assert data["logs"][0]["action"] == "prescription.create"


async def test_pagination(admin_client, db):
    from arxi.modules.compliance.service import AuditService

    svc = AuditService(db)
    for i in range(5):
        await svc.log(
            action="prescription.create", actor_id="a1", actor_role="agent",
            resource_type="prescription", resource_id=f"rx-{i}",
        )
    await db.commit()

    res = await admin_client.get("/api/audit/logs?limit=2&offset=0")
    data = res.json()
    assert len(data["logs"]) == 2
    assert data["total"] == 5
