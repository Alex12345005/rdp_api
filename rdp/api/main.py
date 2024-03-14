from typing import Union, List, Optional

from fastapi import FastAPI, HTTPException, Depends

from rdp.sensor import Reader
from rdp.crud import create_engine, Crud
from . import api_types as ApiTypes

import logging

logger = logging.getLogger("rdp.api")
app = FastAPI()

@app.get("/")
def read_root() -> ApiTypes.ApiDescription:
    """This url returns a simple description of the api

    Returns:
        ApiTypes.ApiDescription: the Api description in json format 
    """    
    return ApiTypes.ApiDescription()

@app.get("/type/")
def read_types() -> List[ApiTypes.ValueType]:
    """Implements the get of all value types

    Returns:
        List[ApiTypes.ValueType]: list of available valuetypes. 
    """    
    global crud
    return crud.get_value_types()

@app.get("/type/{id}/")
def read_type(id: int) -> ApiTypes.ValueType:
    """returns an explicit value type identified by id

    Args:
        id (int): primary key of the desired value type

    Raises:
        HTTPException: Thrown if a value type with the given id cannot be accessed

    Returns:
        ApiTypes.ValueType: the desired value type 
    """
    global crud
    try:
         return crud.get_value_type(id)
    except crud.NoResultFound:
        raise HTTPException(status_code=404, detail="Item not found") 
    return value_type 

@app.put("/type/{id}/")
def put_type(id, value_type: ApiTypes.ValueTypeNoID) -> ApiTypes.ValueType:
    """PUT request to a special valuetype. This api call is used to change a value type object.

    Args:
        id (int): primary key of the requested value type
        value_type (ApiTypes.ValueTypeNoID): json object representing the new state of the value type. 

    Raises:
        HTTPException: Thrown if a value type with the given id cannot be accessed 

    Returns:
        ApiTypes.ValueType: the requested value type after persisted in the database. 
    """
    global crud
    try:
        crud.add_or_update_value_type(id, value_type_name=value_type.type_name, value_type_unit=value_type.type_unit)
        return read_type(id)
    except crud.NoResultFound:
        raise HTTPException(status_code=404, detail="Item not found")

@app.get("/value/")
def get_values(type_id:int=None, start:int=None, end:int=None) -> List[ApiTypes.Value]:
    """Get values from the database. The default is to return all available values. This result can be filtered.

    Args:
        type_id (int, optional): If set, only values of this type are returned. Defaults to None.
        start (int, optional): If set, only values at least as new are returned. Defaults to None.
        end (int, optional): If set, only values not newer than this are returned. Defaults to None.

    Raises:
        HTTPException: _description_

    Returns:
        List[ApiTypes.Value]: _description_
    """
    global crud
    try:
        values = crud.get_values(type_id, start, end)
        return values
    except crud.NoResultFound:
        raise HTTPException(status_code=404, deltail="Item not found")

@app.on_event("startup")
async def startup_event() -> None:
    """start the character device reader
    """    
    logger.info("STARTUP: Sensor reader!")
    global reader, crud
    engine = create_engine("sqlite:///rdb.test.db")
    crud = Crud(engine)
    reader = Reader(crud)
    reader.start()
    logger.debug("STARTUP: Sensor reader completed!")

@app.on_event("shutdown")
async def shutdown_event():
    """stop the character device reader
    """    
    global reader
    logger.debug("SHUTDOWN: Sensor reader!")
    reader.stop()
    logger.info("SHUTDOWN: Sensor reader completed!")

@app.post("/create_device/", response_model=ApiTypes.Device)
def create_device(device_data: ApiTypes.DeviceNoID) -> ApiTypes.Device:
    """Create a new device with the given name and description.

    Args:
        device_data (ApiTypes.DeviceCreate): The name and description of the new device.

    Returns:
        ApiTypes.Device: The created device with its ID, name, and description.
    """
    global crud
    try:
        new_device = crud.add_device(name=device_data.name, description=device_data.description, city_id=device_data.city_id)
        return ApiTypes.Device(id=new_device.id, name=new_device.name, description=new_device.description, city_id=new_device.city_id)
    except crud.IntegrityError as e:
        logger.error(f"Failed to create a new device: {e}")
        raise HTTPException(status_code=400, detail="Failed to create a new device due to a database error.")

@app.get("/get_devices/")
def get_devices():
    return crud.get_devices()

@app.get("/get_values/by_device_id_or_name/", response_model=List[ApiTypes.Value])
def read_values_by_device(device_id: Optional[int] = None, device_name: Optional[str] = None):
    if device_id is None and device_name is None:
        raise HTTPException(status_code=400, detail="Either device_id or device_name must be provided")
    try:
        values = crud.get_values_by_device(device_id=device_id, device_name=device_name)
        return values
    except crud.NoResultFound:
        raise HTTPException(status_code=404, detail="Device not found or no values for this device")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/create_location/", response_model=ApiTypes.Location)
def create_location(location_data: ApiTypes.LocationNoID):
    """Create a new location with the given name.

    Args:
        location_data (ApiTypes.LocationNoID): The name of the new location.

    Returns:
        ApiTypes.Location: The created location with its ID and name.
    """
    try:
        new_location = crud.create_location(name=location_data.name)
        return ApiTypes.Location(id=new_location.id, name=new_location.name)
    except crud.IntegrityError as e:
        logger.error(f"Failed to create a new location: {e}")
        raise HTTPException(status_code=400, detail="Failed to create a new location due to a database error.")

@app.post("/create_city/", response_model=ApiTypes.City)
def create_city(city_data: ApiTypes.CityNoID):
    """Create a new city with the given name and associated location.

    Args:
        city_data (ApiTypes.CityNoID): The name of the new city and the ID of its location.

    Returns:
        ApiTypes.City: The created city with its ID, name, and location ID.
    """
    try:
        new_city = crud.create_city(name=city_data.name, location_id=city_data.location_id)
        return ApiTypes.City(id=new_city.id, name=new_city.name, location_id=new_city.location_id)
    except crud.IntegrityError as e:
        logger.error(f"Failed to create a new city: {e}")
        raise HTTPException(status_code=400, detail="Failed to create a new city due to a database error.")

@app.get("/get_devices/by_city/{city_id}/", response_model=List[ApiTypes.Device])
def get_devices_by_city(city_id: int):
    """Get devices by city ID.

    Args:
        city_id (int): The ID of the city to retrieve devices for.

    Returns:
        List[ApiTypes.Device]: A list of devices associated with the city ID.
    """
    devices = crud.get_devices_by_city(city_id=city_id)
    return [ApiTypes.Device(id=device.id, name=device.name, description=device.description, city_id=device.city_id) for device in devices]

@app.get("/get_all_locations/", response_model=List[ApiTypes.Location])
def get_all_locations():
    """Get all locations.

    Returns:
        List[ApiTypes.Location]: A list of all locations.
    """
    locations = crud.get_all_locations()
    return [ApiTypes.Location(id=location.id, name=location.name) for location in locations]

@app.get("/get_all_cities/", response_model=List[ApiTypes.City])
def get_all_cities():
    """Get all cities.

    Returns:
        List[ApiTypes.City]: A list of all cities.
    """
    cities = crud.get_all_cities()
    return [ApiTypes.City(id=city.id, name=city.name, location_id=city.location_id) for city in cities]

@app.get("/get_cities_by_location_id/{location_id}/", response_model=List[ApiTypes.City])
def get_cities_by_location_id(location_id: int):
    """Get cities by location ID.

    Args:
        location_id (int): The ID of the location to get cities for.

    Returns:
        List[ApiTypes.City]: A list of cities belonging to the given location ID.
    """
    cities = crud.get_cities_by_location_id(location_id=location_id)
    return [ApiTypes.City(id=city.id, name=city.name, location_id=city.location_id) for city in cities]
