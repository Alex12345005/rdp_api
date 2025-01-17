import logging

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from .model import Base, Value, ValueType, Device, Location, City


class Crud:
    def __init__(self, engine):
        self._engine = engine
        self.IntegrityError = IntegrityError
        self.NoResultFound = NoResultFound

        Base.metadata.create_all(self._engine)

    def add_or_update_value_type(
        self,
        value_type_id: int = None,
        value_type_name: str = None,
        value_type_unit: str = None,
    ) -> None:
        """update or add a value typ

        Args:
            value_type_id (int, optional): ValueType id to be modified (if None a new ValueType is added), Default to None.
            value_type_name (str, optional): Typename wich should be set or updated. Defaults to None.
            value_type_unit (str, optional): Unit of mesarument wich should be set or updated. Defaults to None.

        Returns:
            _type_: _description_
        """
        with Session(self._engine) as session:
            stmt = select(ValueType).where(ValueType.id == value_type_id)
            db_type = None
            for type in session.scalars(stmt):
                db_type = type
            if db_type is None:
                db_type = ValueType(id=value_type_id)
            if value_type_name:
                db_type.type_name = value_type_name
            elif not db_type.type_name:
                db_type.type_name = "TYPE_%d" % value_type_id
            if value_type_unit:
                db_type.type_unit = value_type_unit
            elif not db_type.type_unit:
                db_type.type_unit = "UNIT_%d" % value_type_id
            session.add_all([db_type])
            session.commit()
            return db_type

    def add_value(self, value_time: int, value_type: int, value_value: float, device_id: int) -> None:
        """Add a measurement point to the database.

        Args:
            value_time (int): unix time stamp of the value.
            value_type (int): Valuetype id of the given value. 
            value_value (float): The measurement value as float.
        """        
        with Session(self._engine) as session:
            stmt = select(ValueType).where(ValueType.id == value_type)
            db_type = self.add_or_update_value_type(value_type)
            db_value = Value(time=value_time, value=value_value, value_type=db_type, device_id=device_id)

            session.add_all([db_type, db_value])
            try:
                session.commit()
            except IntegrityError:
                logging.error("Integrity")
                raise

    def get_value_types(self) -> List[ValueType]:
        """Get all configured value types

        Returns:
            List[ValueType]: List of ValueType objects. 
        """
        with Session(self._engine) as session:
            stmt = select(ValueType)
            return session.scalars(stmt).all()

    def get_value_type(self, value_type_id: int) -> ValueType:
        """Get a special ValueType

        Args:
            value_type_id (int): the primary key of the ValueType

        Returns:
            ValueType: The ValueType object
        """
        with Session(self._engine) as session:
            stmt = select(ValueType).where(ValueType.id == value_type_id)
            return session.scalars(stmt).one()

    def get_values(
        self, value_type_id: int = None, start: int = None, end: int = None
    ) -> List[Value]:
        """Get Values from database.

        The result can be filtered by the following paramater:

        Args:
            value_type_id (int, optional): If set, only value of this given type will be returned. Defaults to None.
            start (int, optional): If set, only values with a timestamp as least as big as start are returned. Defaults to None.
            end (int, optional): If set, only values with a timestamp as most as big as end are returned. Defaults to None.

        Returns:
            List[Value]: _description_
        """
        with Session(self._engine) as session:
            stmt = select(Value)
            if value_type_id is not None:
                stmt = stmt.join(Value.value_type).where(ValueType.id == value_type_id)
            if start is not None:
                stmt = stmt.where(Value.time >= start)
            if end is not None:
                stmt = stmt.where(Value.time <= end)
            stmt = stmt.order_by(Value.time)
            logging.error(start)
            logging.error(stmt)

            return session.scalars(stmt).all()

    def add_device(self, name: str, description: str, city_id: int) -> Device:
        """Add a new device to the database.

        Args:
            name (str): The name of the device.
            description (str): The description of the device.

        Returns:
            Device: The newly created Device object.
        """
        with Session(self._engine) as session:
            new_device = Device(name=name, description=description, city_id=city_id)
            session.add(new_device)
            try:
                session.commit()
                device_id = new_device.id  
                device_name = new_device.name  
                device_description = new_device.description  
                device_city_id = new_device.city_id
            except IntegrityError:
                logging.error("IntegrityError while adding a new device.")
                session.rollback()
                raise
            return Device(id=device_id, name=device_name, description=device_description, city_id = city_id)

    def get_devices(self) -> List[Device]:
        """Retrieve all devices from the database."""
        with Session(self._engine) as session:
            return session.query(Device).all()

    def get_values_by_device(self, device_id: Optional[int] = None, device_name: Optional[str] = None) -> List[Value]:
        with Session(self._engine) as session:
            if device_id is not None:
                stmt = select(Value).where(Value.device_id == device_id)
            elif device_name is not None:
                device = session.query(Device).filter(Device.name == device_name).first()
                if device is None:
                    raise self.NoResultFound("Device not found")
                stmt = select(Value).where(Value.device_id == device.id)
            else:
                raise ValueError("Either device_id or device_name must be provided")
            
            return session.scalars(stmt).all()

    def create_location(self, name: str) -> Location:
        with Session(self._engine) as session:
            new_location = Location(name=name)
            session.add(new_location)
            session.commit()
            session.refresh(new_location)
            return new_location

    def create_city(self, name: str, location_id: int) -> City:
        with Session(self._engine) as session:
            new_city = City(name=name, location_id=location_id)
            session.add(new_city)
            session.commit()
            session.refresh(new_city)
            return new_city

    def get_devices_by_city(self, city_id: int) -> List[Device]:
        with Session(self._engine) as session:
            return session.query(Device).filter(Device.city_id == city_id).all()

    def get_all_locations(self) -> List[Location]:
        with Session(self._engine) as session:
            return session.query(Location).all()

    def get_all_cities(self) -> List[City]:
        with Session(self._engine) as session:
            return session.query(City).all()

    def get_cities_by_location_id(self, location_id: int) -> List[City]:
        with Session(self._engine) as session:
            return session.query(City).filter(City.location_id == location_id).all()
