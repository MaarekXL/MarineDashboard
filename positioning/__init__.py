from .manual_position import create_manual_position

from .nmea_reader import (
    NMEAError,
    calculate_checksum,
    parse_rmc,
    validate_checksum,
)

from .serial_reader import (
    NMEASerialReader,
    SerialPortInfo,
    list_serial_ports,
)

from .nearest_station import (
    StationMatch,
    find_nearest_station,
    haversine_distance_km,
    load_station_catalog,
)

__all__ = [
    "NMEAError",
    "NMEASerialReader",
    "SerialPortInfo",
    "calculate_checksum",
    "create_manual_position",
    "list_serial_ports",
    "parse_rmc",
    "validate_checksum",
    "StationMatch",
    "find_nearest_station",
    "haversine_distance_km",
    "load_station_catalog",
]