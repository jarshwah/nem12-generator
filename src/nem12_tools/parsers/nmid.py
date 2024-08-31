"""
Parse NMI Discovery details required for NEM12 file generation.
"""

import dataclasses

from lxml import etree


@dataclasses.dataclass()
class Register:
    register_id: str
    uom: str
    suffix: str


@dataclasses.dataclass()
class Meter:
    serial_number: str

    registers: list[Register]


@dataclasses.dataclass()
class MeterPoint:
    """
    NMI details required for NEM12 file generation.
    """

    nmi: str
    role_mdp: str
    role_rp: str

    meters: list[Meter]


def from_nmidiscovery(xml_doc: str) -> MeterPoint:
    """
    Parse NMI Discovery XML document and return a list of MeterPoint objects.
    """

    root = etree.fromstring(xml_doc)

    return MeterPoint(
        nmi=root.findtext(".//NMI"),
        role_mdp=_get_participant(root, "MDP"),
        role_rp=_get_participant(root, "RP"),
        meters=_get_meters(root),
    )


def _get_meters(root: etree.Element) -> list[Meter]:
    """
    Get the list of meters from the XML root element.
    """
    meters = []
    for meter in root.findall(".//Meter"):
        status = meter.find(".//Status").text
        if status == "C":
            serial_number = meter.find(".//SerialNumber").text

            registers = []
            for register in meter.findall(".//Register"):
                register_status = register.find(".//Status").text
                if register_status == "C":
                    register_id = register.find(".//RegisterID").text
                    uom = register.find(".//UnitOfMeasure").text
                    suffix = register.find(".//Suffix").text

                    registers.append(Register(register_id, uom, suffix))

            if registers:  # Check if there are any current registers
                meters.append(Meter(serial_number, registers))

    return meters


def _get_participant(root: etree.Element, role: str) -> str:
    """
    Get the participant from the XML root element.
    """
    for participants in root.findall(".//RoleAssignment"):
        if participants.findtext(".//Role") == role:
            return participants.findtext(".//Party")
    raise ValueError(f"Participant with role {role} not found.")
