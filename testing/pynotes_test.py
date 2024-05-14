"""Pynotes tests"""

import difflib
import pytest

import pynotes

evaluation = pynotes.Evaluation("testing/data.ods", -1)

names = evaluation.df["NOM"].to_list()
totals = [4.5, 3.5, 1, 1.8625]


@pytest.fixture
def expected_out():
    """Read expected output from file"""
    with open("testing/output/data_reports.txt", "r", encoding="utf8") as data:
        return data.read()


def test_totals():
    """Test correct computation of TOTAL column"""
    for nom, total in zip(names, totals):
        assert evaluation.df.set_index("NOM").at[nom, "TOTAL"] == total


def test_individual_reports(expected_out, capfd):
    """Test correct individual reports"""
    evaluation.print("individual")
    captured = capfd.readouterr()
    diff = difflib.SequenceMatcher(None, captured.out, expected_out)
    assert diff.ratio() == 1


def test_done_percent(capfd):
    """Test correct done percentage"""
    evaluation.done_percent()
    captured = capfd.readouterr()
    diff = difflib.SequenceMatcher(None, captured.out, "100.00% done\n")
    assert diff.ratio() == 1


def test_data_validation():
    # import pandera as pa
    from validation import schema
    # After loading, enforce schema
    # try:
    schema.validate(evaluation.df)
    # except pa.errors.SchemaError as exc:
    #     print(exc)
