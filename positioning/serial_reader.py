from dataclasses import dataclass

import serial
from serial.tools import list_ports

from models import Position

from .nmea_reader import NMEAError, parse_rmc


@dataclass(frozen=True, slots=True)
class SerialPortInfo:
    device: str
    description: str
    hwid: str


def list_serial_ports() -> list[SerialPortInfo]:
    """
    Retourne les ports série disponibles sur la machine.
    """
    ports: list[SerialPortInfo] = []

    for port in list_ports.comports():
        ports.append(
            SerialPortInfo(
                device=port.device,
                description=port.description or "",
                hwid=port.hwid or "",
            )
        )

    return ports


class NMEASerialReader:
    """
    Lecteur de trames NMEA depuis un port série.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 4800,
        timeout: float = 1.0,
    ) -> None:
        if not port:
            raise ValueError("Le port série est obligatoire.")

        if baudrate <= 0:
            raise ValueError("Baudrate invalide.")

        if timeout < 0:
            raise ValueError("Timeout invalide.")

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._serial: serial.Serial | None = None

    @property
    def is_open(self) -> bool:
        return (
            self._serial is not None
            and self._serial.is_open
        )

    def open(self) -> None:
        if self.is_open:
            return

        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )

    def close(self) -> None:
        if self._serial is None:
            return

        if self._serial.is_open:
            self._serial.close()

        self._serial = None

    def __enter__(self) -> "NMEASerialReader":
        self.open()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()

    def read_sentence(self) -> str | None:
        """
        Lit une ligne brute depuis le port série.

        Retourne None en cas de timeout ou si la ligne
        ne ressemble pas à une trame NMEA.
        """
        if self._serial is None:
            raise RuntimeError(
                "Le port série n'est pas ouvert."
            )

        raw = self._serial.readline()

        if not raw:
            return None

        sentence = raw.decode(
            "ascii",
            errors="ignore",
        ).strip()

        if not sentence.startswith("$"):
            return None

        return sentence

    def read_next_position(
        self,
        max_lines: int = 100,
    ) -> Position | None:
        """
        Cherche la prochaine position RMC valide.

        Les autres trames NMEA sont ignorées.
        Les trames corrompues sont ignorées.
        """
        if max_lines <= 0:
            raise ValueError(
                "max_lines doit être supérieur à zéro."
            )

        for _ in range(max_lines):
            sentence = self.read_sentence()

            if sentence is None:
                continue

            if not sentence.startswith(
                ("$GPRMC", "$GNRMC")
            ):
                continue

            try:
                position = parse_rmc(sentence)
            except NMEAError:
                continue

            if not position.valid:
                continue

            return position

        return None