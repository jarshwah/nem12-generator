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
    role_frmp: str

    meters: list[Meter]


def from_nmidiscovery(xml_doc: str) -> MeterPoint:
    """
    Parse NMI Discovery XML document and return a list of MeterPoint objects.
    """

    root = etree.fromstring(xml_doc)

    return MeterPoint(
        nmi=_get_nmi(root),
        role_mdp=_get_participant(root, "MDP"),
        role_frmp=_get_frmp(root),
        meters=_get_meters(root),
    )


def _get_nmi(root) -> str:
    nmi = root.findtext(".//NMI")
    if not nmi:
        raise ValueError("NMI not found in NMI Discovery XML.")
    return nmi


def _get_meters(root: etree._Element) -> list[Meter]:
    """
    Get the list of meters from the XML root element.
    """
    meters = []
    for meter in root.findall(".//Meter"):
        status = meter.findtext(".//Status")
        if status == "C":
            serial_number = meter.findtext(".//SerialNumber")
            if not serial_number:
                raise ValueError("Serial number not found in NMI Discovery XML.")

            registers = []
            for register in meter.findall(".//Register"):
                register_status = register.findtext(".//Status")
                if register_status == "C":
                    register_id = register.findtext(".//RegisterID")
                    uom = register.findtext(".//UnitOfMeasure")
                    suffix = register.findtext(".//Suffix")
                    if not register_id or not uom or not suffix:
                        raise ValueError("Register details not found in NMI Discovery XML.")

                    registers.append(Register(register_id, uom, suffix))

            if registers:  # Check if there are any current registers
                meters.append(Meter(serial_number, registers))

    return meters


def _get_participant(root: etree._Element, role: str) -> str:
    """
    Get the participant from the XML root element.
    """
    for participants in root.findall(".//RoleAssignment"):
        if participants.findtext(".//Role") == role:
            if party := participants.findtext(".//Party"):
                return party

    raise ValueError(f"Participant with role {role} not found.")


def _get_frmp(root: etree._Element) -> str:
    """
    Get the FRMP role from the XML root element.

    We extract the To participant from the header.
    """
    frmp = root.findtext("./Header/To")
    if not frmp:
        raise ValueError("FRMP not found in NMI Discovery XML.")
    return frmp
