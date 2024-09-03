import os

from nem12_tools.parsers import nmid


def test_nmidiscovery_parsed():
    here = os.path.dirname(os.path.realpath(__file__))
    xml = open(f"{here}/../examples/nmi-discovery.xml").read()
    parsed = nmid.from_nmidiscovery(xml)
    assert parsed.nmi == "4102335210"
    assert parsed.role_mdp == "ACTIVMDP"
    assert parsed.role_frmp == "ENERGEX"
    assert len(parsed.meters) == 1
    meter = parsed.meters[0]
    assert meter.serial_number == "701226207"
    assert len(meter.registers) == 1
    register = meter.registers[0]
    assert register.register_id == "E1"
    assert register.uom == "KWH"
    assert register.suffix == "E1"
