from typing import List
from typing import Optional
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy import String, Float, DateTime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.orm import sessionmaker

class Base(DeclarativeBase):
    pass

class Device(Base):
    __tablename__ = "device"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()

    values: Mapped[List["Value"]] = relationship("Value", back_populates="device")

    def __repr__(self) -> str:
        return f"Device(id={self.id!r}, name={self.name!r}, description={self.description!r})"

class Value(Base):
    __tablename__ = "value"
    id: Mapped[int] = mapped_column(primary_key=True)
    time: Mapped[int] = mapped_column()
    value: Mapped[float] = mapped_column()
    value_type_id: Mapped[int] = mapped_column(ForeignKey("value_type.id"))
    device_id: Mapped[int] = mapped_column(ForeignKey("device.id"))

    value_type: Mapped["ValueType"] = relationship("ValueType", back_populates="values")
    device: Mapped["Device"] = relationship("Device", back_populates="values")

    __table_args__ = (UniqueConstraint("time", "value_type_id", "device_id", name="value_integrity"),)

    def __repr__(self) -> str:
        return f"Value(id={self.id!r}, time={self.time!r}, value_type={self.value_type.type_name!r}, value={self.value}, device_id={self.device_id!r})"

class ValueType(Base):
    __tablename__ = "value_type"
    id: Mapped[int] = mapped_column(primary_key=True)
    type_name: Mapped[str]
    type_unit: Mapped[str]

    values: Mapped[List["Value"]] = relationship("Value", back_populates="value_type")

    def __repr__(self) -> str:
        return f"ValueType(id={self.id!r}, type_name={self.type_name!r}, type_unit={self.type_unit!r})"