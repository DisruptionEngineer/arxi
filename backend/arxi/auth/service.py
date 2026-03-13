import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from arxi.auth.models import User, Role


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.TECHNICIAN: {"prescription.create", "prescription.read", "patient.read", "patient.create"},
    Role.PHARMACIST: {"prescription.create", "prescription.read", "prescription.verify",
                      "prescription.approve", "patient.read", "patient.create", "patient.update"},
    Role.ADMIN: {"*"},
    Role.AGENT: {"prescription.create", "prescription.read", "patient.read", "patient.create"},
}


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, *, username: str, password: str,
                          full_name: str, role: Role) -> User:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(username=username, password_hash=pw_hash, full_name=full_name, role=role)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, username: str, password: str) -> User | None:
        stmt = select(User).where(User.username == username, User.is_active == True)  # noqa: E712
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user and bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return user
        return None

    async def change_password(self, user: User, old_password: str, new_password: str) -> bool:
        if not bcrypt.checkpw(old_password.encode(), user.password_hash.encode()):
            return False
        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        await self.db.commit()
        return True

    @staticmethod
    def has_permission(role: Role, permission: str) -> bool:
        perms = ROLE_PERMISSIONS.get(role, set())
        return "*" in perms or permission in perms
