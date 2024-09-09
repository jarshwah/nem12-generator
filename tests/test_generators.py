import csv
import datetime
from io import BytesIO
from unittest import mock

from lxml import etree

from nem12_tools.generators import nem12
from nem12_tools.parsers.nmid import Meter, MeterPoint, Register


def test_nem12():
    m = MeterPoint(
        nmi="4102335210",
        role_mdp="ACTIVMDP",
        role_frmp="ENERGEX",
        meters=[
            Meter(
                serial_number="701226207",
                registers=[Register(register_id="E1", uom="KWH", suffix="E1")],
            )
        ],
    )
    notification = nem12.generate_nem12(m)
    xml_file = BytesIO()
    notification.tree.write(
        xml_file, pretty_print=True, xml_declaration=True, encoding="utf-8"
    )

    root = etree.fromstring(xml_file.getvalue())
    assert root.findtext("./Header/From") == "ACTIVMDP"
    assert root.findtext("./Header/To") == "ENERGEX"
    assert root.findtext("./Header/TransactionGroup") == "MTRD"
    assert root.findtext("./Header/Priority") == "Medium"
    assert root.findtext("./Header/Market") == "NEM"

    csv_data = root.findtext(".//CSVIntervalData")
    assert csv_data is not None
    reader = csv.reader(csv_data.splitlines())
    section_100 = next(reader)
    assert section_100 == ["100", "NEM12", mock.ANY, "ACTIVMDP", "ENERGEX"]
    section_200 = next(reader)
    assert section_200 == [
        "200",
        "4102335210",
        "E1",
        "E1",
        "E1",
        "",
        "701226207",
        "KWH",
        "5",
        "",
    ]
    section_300 = next(reader)
    assert section_300[0] == "300"
    assert len(section_300) == 295
    assert section_300[-5:] == ["A", "", "", mock.ANY, mock.ANY]
    section_900 = next(reader)
    assert section_900 == ["900"]


def test_multiple_dates():
    m = MeterPoint(
        nmi="4102335210",
        role_mdp="ACTIVMDP",
        role_frmp="ENERGEX",
        meters=[
            Meter(
                serial_number="701226207",
                registers=[Register(register_id="E1", uom="KWH", suffix="E1")],
            )
        ],
    )
    notification = nem12.generate_nem12(
        m, start=datetime.date(2024, 1, 1), end=datetime.date(2024, 1, 2)
    )
    xml_file = BytesIO()
    notification.tree.write(
        xml_file, pretty_print=True, xml_declaration=True, encoding="utf-8"
    )

    root = etree.fromstring(xml_file.getvalue())
    csv_data = root.findtext(".//CSVIntervalData")
    assert csv_data is not None
    reader = csv.reader(csv_data.splitlines())
    assert next(reader)[0] == "100"
    assert next(reader)[0] == "200"
    # each read date is nested under the 200 section rather than alternating
    assert next(reader)[0] == "300"
    assert next(reader)[0] == "300"
    assert next(reader)[0] == "900"

def test_interval_15():
    m = MeterPoint(
        nmi="4102335210",
        role_mdp="ACTIVMDP",
        role_frmp="ENERGEX",
        meters=[
            Meter(
                serial_number="701226207",
                registers=[Register(register_id="E1", uom="KWH", suffix="E1")],
            )
        ],
    )
    notification = nem12.generate_nem12(m, interval=nem12.IntervalLength.FIFTEEN_MINUTES)
    xml_file = BytesIO()
    notification.tree.write(
        xml_file, pretty_print=True, xml_declaration=True, encoding="utf-8"
    )

    root = etree.fromstring(xml_file.getvalue())
    csv_data = root.findtext(".//CSVIntervalData")
    assert csv_data is not None
    reader = csv.reader(csv_data.splitlines())
    assert next(reader)[0] == "100"
    assert next(reader)[0] == "200"
    row_300 = next(reader)
    assert row_300[0] == "300"
    assert len(row_300) == 103
