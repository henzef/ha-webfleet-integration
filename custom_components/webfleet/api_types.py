from datetime import datetime
from typing import TypedDict


class ShowObjectReportExternResult(TypedDict):
    objectno: str | None  # 10 characters; Identifying number of an object. Unique within an account, case-sensitive.
    objectname: str | None  # Display name of an object.
    objectclassname: str | None
    objecttype: str | None  # Can be empty or contain the valid values listed in vehicletype, see updateVehicle API documentation.
    description: str | None  # 500 characters; Vehicle description
    lastmsgid: str | None
    deleted: bool | None
    msgtime: str | None
    longitude: str | None
    latitude: str | None
    postext: str | None
    postext_short: str | None
    pos_time: datetime | None
    speed: str | None
    course: int | None  # 0 .. 360°
    direction: int | None
    quality: str | None
    satellite: str | None
    status: str | None
    dest_latitude: int | None
    dest_longitude: int | None
    dest_text: str | None
    dest_eta: datetime | None
    orderno: str | None
    driver: str | None
    drivername: str | None
    drivertelmobile: str | None
    codriver: str | None
    codrivername: str | None
    codrivertelmobile: str | None
    driver_currentworkstate: str | None
    codriver_currentworkstate: str | None
    rll_btaddress: str | None
    odometer: str | None
    ignition: int | None
    ignition_time: str | None
    dest_distance: str | None
    tripmode: int | None
    standstill: int | None
    pndconn: int | None
    latitude_mdeg: int | None
    longitude_mdeg: int | None
    objectuid: str
    fuellevel: int | None
    externalid: str | None
    driveruid: str | None
    codriveruid: str | None
    driverkey_deviceaddress: str | None
    fuellevel_milliliters: str | None
    engine_operation_time: int | None
    odometer_long: int | None
