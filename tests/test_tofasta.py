"""Tests for tofasta.

Several of these are regression tests against real defects in CDC's CSV2FASTA
web tool (github.com/CDCgov/CSV2FASTA), which emits CRLF unconditionally and
writes a phantom ">undefined" record with an empty sequence when the identifier
column is not the first column. They are named accordingly.
"""

from __future__ import annotations

import io

import pandas as pd
import pytest

from tofasta import ValidationError, csv_to_fasta, to_fasta
from tofasta._cli import main


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "ID": ["96602692", "77cd04d8", "0d9de872"],
            "Sequence": ["MKVLAA", "GSGEGPREP", "AKLKVAINGF"],
            "Organism": ["Homo sapiens", "Escherichia coli", None],
        }
    )


def read(path):
    return path.read_bytes().decode()


# --- happy path ------------------------------------------------------------


def test_writes_expected_records(df, tmp_path):
    out = tmp_path / "out.fasta"
    written = to_fasta(df, out, id="ID", seq="Sequence")

    assert written == 3
    assert read(out) == (
        ">96602692\nMKVLAA\n"
        ">77cd04d8\nGSGEGPREP\n"
        ">0d9de872\nAKLKVAINGF\n"
    )


def test_sequences_are_unwrapped_by_default(df, tmp_path):
    out = tmp_path / "out.fasta"
    to_fasta(df, out, id="ID", seq="Sequence")

    body = [line for line in read(out).splitlines() if not line.startswith(">")]
    assert body == ["MKVLAA", "GSGEGPREP", "AKLKVAINGF"]


def test_wrap_splits_sequences(tmp_path):
    out = tmp_path / "out.fasta"
    frame = pd.DataFrame({"ID": ["a"], "Sequence": ["A" * 25]})
    to_fasta(frame, out, id="ID", seq="Sequence", wrap=10)

    assert read(out) == ">a\n" + "AAAAAAAAAA\nAAAAAAAAAA\nAAAAA\n"


def test_description_is_appended_after_a_space(df, tmp_path):
    out = tmp_path / "out.fasta"
    to_fasta(df, out, id="ID", seq="Sequence", description="Organism")

    headers = [line for line in read(out).splitlines() if line.startswith(">")]
    assert headers == [
        ">96602692 Homo sapiens",
        ">77cd04d8 Escherichia coli",
        ">0d9de872",  # missing description leaves no trailing space
    ]


def test_accepts_a_file_object(df):
    buffer = io.StringIO()
    written = to_fasta(df, buffer, id="ID", seq="Sequence")

    assert written == 3
    assert buffer.getvalue().startswith(">96602692\n")


# --- CSV2FASTA regressions -------------------------------------------------


def test_output_never_contains_carriage_returns(df, tmp_path):
    """CSV2FASTA hardcodes \\r\\n in its template literal with no escape hatch."""
    out = tmp_path / "out.fasta"
    to_fasta(df, out, id="ID", seq="Sequence")

    assert b"\r" not in out.read_bytes()


def test_trailing_newline_in_csv_does_not_produce_a_phantom_record(tmp_path):
    """CSV2FASTA emits '>undefined' for the terminating newline of a valid CSV."""
    csv = tmp_path / "in.csv"
    csv.write_text("Sequence,ID\nMKVLAA,abc\nGSGEGP,def\n")  # ID deliberately second
    out = tmp_path / "out.fasta"

    written = csv_to_fasta(csv, out, id="ID", seq="Sequence")

    assert written == 2
    assert "undefined" not in read(out)
    assert read(out).count(">") == 2


def test_missing_identifier_raises_rather_than_stringifying(tmp_path):
    """JavaScript coerced a missing id into the text 'undefined'; we refuse."""
    frame = pd.DataFrame({"ID": ["abc", None], "Sequence": ["MKV", "GSG"]})

    with pytest.raises(ValidationError, match="missing values"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence")


def test_empty_sequence_raises(tmp_path):
    frame = pd.DataFrame({"ID": ["abc", "def"], "Sequence": ["MKV", ""]})

    with pytest.raises(ValidationError, match="empty values"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence")


def test_empty_identifier_raises(tmp_path):
    frame = pd.DataFrame({"ID": ["abc", ""], "Sequence": ["MKV", "GSG"]})

    with pytest.raises(ValidationError, match="empty values"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence")


def test_missing_sequence_raises(tmp_path):
    frame = pd.DataFrame({"ID": ["abc", "def"], "Sequence": ["MKV", None]})

    with pytest.raises(ValidationError, match="missing values"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence")


# --- duplicate identifiers -------------------------------------------------


def test_duplicate_identifiers_raise_by_default(tmp_path):
    frame = pd.DataFrame({"ID": ["a", "b", "a"], "Sequence": ["MK", "GS", "AK"]})

    with pytest.raises(ValidationError, match="duplicate"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence")


def test_on_duplicate_first_keeps_the_first_occurrence(tmp_path):
    out = tmp_path / "out.fasta"
    frame = pd.DataFrame({"ID": ["a", "b", "a"], "Sequence": ["MK", "GS", "AK"]})

    written = to_fasta(frame, out, id="ID", seq="Sequence", on_duplicate="first")

    assert written == 2
    assert read(out) == ">a\nMK\n>b\nGS\n"


def test_on_duplicate_warn_writes_everything(tmp_path):
    out = tmp_path / "out.fasta"
    frame = pd.DataFrame({"ID": ["a", "b", "a"], "Sequence": ["MK", "GS", "AK"]})

    with pytest.warns(UserWarning, match="duplicate"):
        written = to_fasta(frame, out, id="ID", seq="Sequence", on_duplicate="warn")

    assert written == 3


def test_invalid_on_duplicate_rejected(df, tmp_path):
    with pytest.raises(ValueError, match="on_duplicate"):
        to_fasta(df, tmp_path / "out.fasta", id="ID", seq="Sequence", on_duplicate="nope")


# --- header and sequence hygiene -------------------------------------------


def test_whitespace_in_identifier_raises(tmp_path):
    frame = pd.DataFrame({"ID": ["has space"], "Sequence": ["MKV"]})

    with pytest.raises(ValidationError, match="whitespace"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence")


def test_angle_bracket_in_identifier_raises(tmp_path):
    frame = pd.DataFrame({"ID": ["a>b"], "Sequence": ["MKV"]})

    with pytest.raises(ValidationError, match="'>'"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence")


def test_newline_in_sequence_raises(tmp_path):
    frame = pd.DataFrame({"ID": ["a"], "Sequence": ["MK\nV"]})

    with pytest.raises(ValidationError, match="line breaks"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence")


def test_whitespace_in_sequence_raises(tmp_path):
    frame = pd.DataFrame({"ID": ["a"], "Sequence": ["MK V"]})

    with pytest.raises(ValidationError, match="whitespace"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence")


def test_numeric_sequence_column_raises(tmp_path):
    frame = pd.DataFrame({"ID": ["a", "b"], "Sequence": [1.0, 2.0]})

    with pytest.raises(ValidationError, match="expected text"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence")


def test_missing_column_names_the_available_ones(df, tmp_path):
    with pytest.raises(ValidationError, match="Available columns"):
        to_fasta(df, tmp_path / "out.fasta", id="nope", seq="Sequence")


# --- alphabet --------------------------------------------------------------


def test_protein_alphabet_allows_x(tmp_path):
    """Curated interaction data legitimately contains X at unresolved positions."""
    out = tmp_path / "out.fasta"
    frame = pd.DataFrame({"ID": ["a"], "Sequence": ["MKXVAA"]})

    assert to_fasta(frame, out, id="ID", seq="Sequence", alphabet="protein") == 1


def test_protein_alphabet_rejects_digits(tmp_path):
    frame = pd.DataFrame({"ID": ["a"], "Sequence": ["MKV123"]})

    with pytest.raises(ValidationError, match="alphabet"):
        to_fasta(frame, tmp_path / "out.fasta", id="ID", seq="Sequence", alphabet="protein")


def test_custom_alphabet_accepted(tmp_path):
    out = tmp_path / "out.fasta"
    frame = pd.DataFrame({"ID": ["a"], "Sequence": ["ACAC"]})

    assert to_fasta(frame, out, id="ID", seq="Sequence", alphabet="AC") == 1

    with pytest.raises(ValidationError):
        to_fasta(frame, out, id="ID", seq="Sequence", alphabet="GT")


def test_lowercase_sequences_pass_alphabet_check(tmp_path):
    out = tmp_path / "out.fasta"
    frame = pd.DataFrame({"ID": ["a"], "Sequence": ["mkvlaa"]})

    assert to_fasta(frame, out, id="ID", seq="Sequence", alphabet="protein") == 1
    assert "mkvlaa" in read(out), "case must be preserved, not normalised"


# --- csv_to_fasta ----------------------------------------------------------


def test_all_digit_identifiers_stay_strings(tmp_path):
    csv = tmp_path / "in.csv"
    csv.write_text("ID,Sequence\n1,MKV\n2,GSG\n")
    out = tmp_path / "out.fasta"

    csv_to_fasta(csv, out, id="ID", seq="Sequence")

    assert ">1\n" in read(out)
    assert "1.0" not in read(out)


def test_read_csv_kwargs_are_forwarded(tmp_path):
    csv = tmp_path / "in.csv"
    csv.write_text("# a comment\nID,Sequence\na,MKV\n")
    out = tmp_path / "out.fasta"

    written = csv_to_fasta(
        csv, out, id="ID", seq="Sequence", read_csv_kwargs={"skiprows": 1}
    )

    assert written == 1


# --- cli -------------------------------------------------------------------


def test_cli_writes_and_reports(tmp_path, capsys):
    csv = tmp_path / "in.csv"
    csv.write_text("ID,Sequence\na,MKV\nb,GSG\n")
    out = tmp_path / "out.fasta"

    code = main([str(csv), str(out), "--id", "ID", "--seq", "Sequence"])

    assert code == 0
    assert "2 records written" in capsys.readouterr().out
    assert read(out) == ">a\nMKV\n>b\nGSG\n"


def test_cli_reports_validation_failure_on_stderr(tmp_path, capsys):
    csv = tmp_path / "in.csv"
    csv.write_text("ID,Sequence\na,MKV\na,GSG\n")
    out = tmp_path / "out.fasta"

    code = main([str(csv), str(out), "--id", "ID", "--seq", "Sequence"])

    assert code == 2
    assert "duplicate" in capsys.readouterr().err
