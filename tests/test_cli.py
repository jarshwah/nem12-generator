import pathlib

from click.testing import CliRunner

from nem12_tools.cli import generate


def test_generate(tmp_path: pathlib.Path):
    nmi_discovery = pathlib.Path(__file__).parent.parent / "examples/nmi-discovery.xml"
    nmi_discovery.resolve()
    runner = CliRunner()
    output_file = tmp_path / "output.xml"
    result = runner.invoke(
        generate,
        [
            str(nmi_discovery),
            str(output_file),
            "--from",
            "2021-01-01",
            "--to",
            "2021-01-02",
            "--frmp",
            "TEST",
            "--interval",
            "5",
        ],
    )

    assert result.exit_code == 0, result.exception
    assert "NEM12 file generated successfully" in result.output
    assert output_file.read_text().startswith("<?xml")
