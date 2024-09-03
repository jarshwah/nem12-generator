import datetime
from typing import IO

import click

from nem12_tools.generators.nem12 import generate_nem12
from nem12_tools.parsers.nmid import from_nmidiscovery


@click.command()
@click.argument("nmi_discovery_file", type=click.File("r"))
@click.argument("output_file", type=click.File("wb"))
@click.option(
    "--from",
    "from_date",
    type=click.DateTime(),
    help="Date to generate reads from. Default: today",
)
@click.option(
    "--to",
    "to_date",
    type=click.DateTime(),
    help="Date to generate reads to. Default: today",
)
@click.option(
    "--frmp",
    type=str,
    help="The FRMP role to receive the NEM data. Default: the MDP role in the NMI Discovery file.",
)
def generate(
    nmi_discovery_file: IO[str],
    output_file: IO[bytes],
    from_date: datetime.datetime | None,
    to_date: datetime.datetime | None,
    frmp: str | None,
) -> None:
    if not from_date:
        from_date = datetime.datetime.now()
    if not to_date:
        to_date = datetime.datetime.now()
    meter_config = from_nmidiscovery(nmi_discovery_file.read())
    if frmp:
        meter_config.role_frmp = frmp
    meter_data_transaction = generate_nem12(
        meter_config, from_date.date(), to_date.date()
    )
    meter_data_transaction.tree.write(
        output_file, pretty_print=True, xml_declaration=True, encoding="utf-8"
    )
    click.echo("NEM12 file generated successfully")
