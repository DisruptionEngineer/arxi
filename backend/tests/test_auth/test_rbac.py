from arxi.auth.service import AuthService, Role


async def test_create_user(db):
    svc = AuthService(db)
    user = await svc.create_user(
        username="dr.smith", password="securepass123",
        full_name="Dr. Smith", role=Role.PHARMACIST,
    )
    assert user.username == "dr.smith"
    assert user.role == Role.PHARMACIST


async def test_authenticate_user(db):
    svc = AuthService(db)
    await svc.create_user(username="tech1", password="pass123",
                          full_name="Tech One", role=Role.TECHNICIAN)
    user = await svc.authenticate("tech1", "pass123")
    assert user is not None
    assert user.username == "tech1"


def test_role_hierarchy():
    """has_permission is a static method — no db or async needed."""
    assert AuthService.has_permission(Role.PHARMACIST, "prescription.verify")
    assert AuthService.has_permission(Role.TECHNICIAN, "prescription.create")
    assert not AuthService.has_permission(Role.TECHNICIAN, "prescription.verify")
    assert AuthService.has_permission(Role.ADMIN, "prescription.verify")
