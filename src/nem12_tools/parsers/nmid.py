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
    from_participant: str
    to_participant: str

    meters: list[Meter]


def from_nmidiscovery(xml_doc: str) -> MeterPoint:
    """
    Parse NMI Discovery XML document and return a list of MeterPoint objects.
    """

    root = etree.fromstring(xml_doc)

    return MeterPoint(
        nmi=root.findtext(".//NMI"),
        from_participant=_get_from_participant(root),
        to_participant=_get_to_participant(root),
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


def _get_from_participant(root: etree.Element) -> str:
    """
    Get the 'From' participant from the XML root element.
    """
    from_participant = ""
    for participants in root.findall(".//RoleAssignment"):
        if participants.findtext(".//Role") == "MDP":
            from_participant = participants.findtext(".//Party")
            break
    return from_participant


def _get_to_participant(root: etree.Element) -> str:
    """
    Get the 'To' participant from the XML root element.
    """
    to_participant = ""
    for participants in root.findall(".//RoleAssignment"):
        if participants.findtext(".//Role") == "RP":
            to_participant = participants.findtext(".//Party")
            break
    return to_participant
