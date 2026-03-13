import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from arxi.database import Base


class Drug(Base):
    """Drug product — sourced from FDA NDC Directory."""

    __tablename__ = "drugs"
    __table_args__ = {"schema": "pharma"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ndc: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    drug_name: Mapped[str] = mapped_column(String(300), index=True)
    generic_name: Mapped[str] = mapped_column(String(300), default="")
    dosage_form: Mapped[str] = mapped_column(String(100), default="")
    strength: Mapped[str] = mapped_column(String(100), default="")
    route: Mapped[str] = mapped_column(String(100), default="")
    manufacturer: Mapped[str] = mapped_column(String(200), default="")
    dea_schedule: Mapped[str] = mapped_column(String(10), default="")  # "", "CII", "CIII", etc.
    package_description: Mapped[str] = mapped_column(Text, default="")
