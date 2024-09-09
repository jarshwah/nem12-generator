from xml.etree import ElementTree as ET

from lxml import etree


class MeterDataNotification:
    parser: etree.XMLParser
    root: etree._Element
    tree: etree._ElementTree

    def __init__(self):
        self.parser = etree.XMLParser(
            remove_blank_text=True
        )  # This will remove all ignorable whitespace and let the subsequent pretty-printing "start from scratch".
        self.root = etree.fromstring(self.xml_root(), self.parser)
        self.tree = etree.ElementTree(self.root)

    def xml_root(self):
        NS1 = "urn:aseXML:r43"
        NS2 = "http://www.w3.org/2001/XMLSchema-instance"
        ET.register_namespace("ase", NS1)
        ET.register_namespace("xsi", NS2)
        qname1 = ET.QName(NS1, "aseXML")  # Element QName
        qname2 = ET.QName(NS2, "schemaLocation")  # Attribute QName
        root = ET.Element(
            qname1.text,
            {
                qname2.text: "urn:aseXML:r43 http://www.nemmco.com.au/aseXML/schemas/r43/aseXML_r43.xsd"
            },
        )
        return ET.tostring(root)

    def header(
        self,
        from_text,
        to_text,
        message_id,
        message_date,
        transaction_group,
        priority,
        market,
    ):
        """
        <Header>
        <From>TXUN</From>
        <To>LOLOL</To>
        <MessageID>TXUN 3009a20200227120425987</MessageID>
        <MessageDate>2020-02-27T12:00:26+10:00</MessageDate>
        <TransactionGroup>SORD</TransactionGroup>
        <Priority>Low</Priority>
        <Market>VICGAS</Market>
        </Header>
        """
        self.header_parent = etree.SubElement(self.root, "Header")

        self.header_from = etree.SubElement(self.header_parent, "From")
        self.header_from.text = from_text

        self.header_to = etree.SubElement(self.header_parent, "To")
        self.header_to.text = to_text

        self.header_msg_id = etree.SubElement(self.header_parent, "messageID")
        self.header_msg_id.text = message_id

        self.header_msg_date = etree.SubElement(self.header_parent, "MessageDate")
        self.header_msg_date.text = message_date

        self.header_trans_grp = etree.SubElement(self.header_parent, "TransactionGroup")
        self.header_trans_grp.text = transaction_group

        self.header_priority = etree.SubElement(self.header_parent, "Priority")
        self.header_priority.text = priority

        self.header_market = etree.SubElement(self.header_parent, "Market")
        self.header_market.text = market

    def transactions(
        self,
        transaction_id,
        transaction_date,
        transaction_type,
        transaction_schema_version,
        csv_interval_data,
        participant_role,
    ):
        self.transactions_parent = etree.SubElement(self.root, "Transactions")
        self.transaction = etree.SubElement(
            self.transactions_parent,
            "Transaction",
            attrib={
                "transactionID": transaction_id,
                "transactionDate": transaction_date,
            },
        )
        self.transaction_type = etree.SubElement(
            self.transaction,
            transaction_type,
            attrib={"version": transaction_schema_version},
        )

        self.interval_data = etree.SubElement(self.transaction_type, "CSVIntervalData")
        self.interval_data.text = csv_interval_data

        self.trans_participant = etree.SubElement(self.transaction_type, "ParticipantRole")

        self.trans_participant_role = etree.SubElement(self.trans_participant, "Role")
        self.trans_participant_role.text = participant_role

        """
      <Transactions>
        <Transaction transactionID="MTRD_MSG_NEM12_202112271020" transactionDate="2021-12-27T10:20:05.000+10:00">
          <MeterDataNotification version="r25">
            <CSVIntervalData>
            </CSVIntervalData>
              <ParticipantRole>
              </ParticipantRole>
          </MeterDataNotification>
        </Transaction>
      </Transactions>
      """

    def write_xml(self, output_filename: str):
        self.tree.write(
            output_filename,
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8",
        )
