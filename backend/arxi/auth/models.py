import uuid
from sqlalchemy import String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from arxi.database import Base
import enum


class Role(str, enum.Enum):
    ADMIN = "admin"
    PHARMACIST = "pharmacist"
    TECHNICIAN = "technician"
    AGENT = "agent"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}
    # Intentionally in public schema — users span all domain schemas

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(SAEnum(Role, values_callable=lambda e: [m.value for m in e]))
    is_active: Mapped[bool] = mapped_column(default=True)
