import pytest
from datetime import datetime, timezone, timedelta
from arxi.modules.compliance.service import AuditService


@pytest.fixture
async def audit_svc(db):
    return AuditService(db)


@pytest.fixture
async def seeded_logs(audit_svc, db):
    """Seed 5 audit entries for filter testing."""
    await audit_svc.log(
        action="prescription.create", actor_id="agent-001", actor_role="agent",
        resource_type="prescription", resource_id="rx-001",
        detail={"source": "e-prescribe"},
    )
    await audit_svc.log(
        action="prescription.approve", actor_id="pharmacist-001", actor_role="pharmacist",
        resource_type="prescription", resource_id="rx-001",
        detail={"notes": "Looks good"},
        before_state={"status": "pending_review", "reviewed_by": None},
        after_state={"status": "approved", "reviewed_by": "pharmacist-001"},
    )
    await audit_svc.log(
        action="prescription.reject", actor_id="pharmacist-001", actor_role="pharmacist",
        resource_type="prescription", resource_id="rx-002",
        detail={"notes": "Bad NDC"},
        before_state={"status": "pending_review"},
        after_state={"status": "rejected"},
    )
    await audit_svc.log(
        action="prescription.create", actor_id="agent-002", actor_role="agent",
        resource_type="prescription", resource_id="rx-003",
    )
    await audit_svc.log(
        action="prescription.validate", actor_id="pipeline-worker", actor_role="system",
        resource_type="prescription", resource_id="rx-003",
        before_state={"status": "parsed"},
        after_state={"status": "validated"},
    )
    await db.commit()


async def test_query_filter_by_action(audit_svc, seeded_logs):
    logs, total = await audit_svc.query_filtered(action="prescription.approve")
    assert total == 1
    assert logs[0].action == "prescription.approve"


async def test_query_filter_by_actor(audit_svc, seeded_logs):
    logs, total = await audit_svc.query_filtered(actor_id="pharmacist-001")
    assert total == 2


async def test_query_filter_by_resource_type(audit_svc, seeded_logs):
    logs, total = await audit_svc.query_filtered(resource_type="prescription")
    assert total == 5


async def test_query_pagination(audit_svc, seeded_logs):
    logs, total = await audit_svc.query_filtered(limit=2, offset=0)
    assert len(logs) == 2
    assert total == 5

    logs2, total2 = await audit_svc.query_filtered(limit=2, offset=2)
    assert len(logs2) == 2
    assert total2 == 5


async def test_query_search_detail(audit_svc, seeded_logs):
    logs, total = await audit_svc.query_filtered(search="Bad NDC")
    assert total == 1
    assert logs[0].resource_id == "rx-002"
