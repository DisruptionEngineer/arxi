import uuid

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from arxi.database import Base


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = {"schema": "arxi"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), index=True)
    gender: Mapped[str] = mapped_column(String(10))
    date_of_birth: Mapped[str] = mapped_column(String(10))
    address_line1: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    state: Mapped[str] = mapped_column(String(2), default="")
    postal_code: Mapped[str] = mapped_column(String(10), default="")

    # Clinical profile
    allergies: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    conditions: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    prescriptions: Mapped[list["Prescription"]] = relationship(
        "Prescription", back_populates="patient", lazy="selectin"
    )
