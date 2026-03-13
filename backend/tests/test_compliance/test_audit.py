from arxi.modules.compliance.service import AuditService
from arxi.modules.compliance.models import AuditLog  # noqa: F401


async def test_create_audit_entry(db):
    svc = AuditService(db)
    entry = await svc.log(
        action="prescription.create",
        actor_id="user-123",
        actor_role="technician",
        resource_type="prescription",
        resource_id="rx-456",
        detail={"drug": "Amoxicillin 500mg", "qty": 30},
        before_state=None,
        after_state={"status": "parsed"},
    )
    await db.commit()
    assert entry.id is not None
    assert entry.action == "prescription.create"
    assert entry.actor_id == "user-123"
    assert entry.after_state == {"status": "parsed"}


async def test_audit_log_query(db):
    svc = AuditService(db)
    entry = await svc.log(
        action="prescription.create",
        actor_id="user-123",
        actor_role="pharmacist",
        resource_type="prescription",
        resource_id="rx-789",
    )
    await db.commit()
    entries = await svc.query(resource_id="rx-789")
    assert len(entries) == 1
    assert entries[0].id == entry.id


async def test_audit_service_has_no_update_or_delete(db):
    """AuditService enforces append-only at the application level."""
    svc = AuditService(db)
    assert not hasattr(svc, "update")
    assert not hasattr(svc, "delete")
