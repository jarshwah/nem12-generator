from typing import IO

import click

from nem12_tools.generators.nem12 import generate_nem12
from nem12_tools.parsers.nmid import from_nmidiscovery


@click.command()
@click.argument("nmi_discovery_file", type=click.File("r"))
@click.argument("output_file", type=click.File("wb"))
def generate(nmi_discovery_file: IO[str], output_file: IO[str]) -> None:
    meter_config = from_nmidiscovery(nmi_discovery_file.read())
    meter_data_transaction = generate_nem12(meter_config)
    meter_data_transaction.tree.write(
        output_file, pretty_print=True, xml_declaration=True, encoding="utf-8"
    )
    click.echo("NEM12 file generated successfully")
