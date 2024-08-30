import click

from nem12_tools.generators.nem12 import generate_nem12


@click.command()
@click.argument("input")
@click.argument("output")
def generate(input, output):
    generate_nem12(input, output)
