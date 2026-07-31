"""DataFrame and CSV to FASTA conversion with input validation."""

from __future__ import annotations

import warnings
from typing import Any, Iterable, Optional, Union

import pandas as pd

__all__ = ["ValidationError", "csv_to_fasta", "to_fasta"]


class ValidationError(ValueError):
    """Raised when input data cannot be written as unambiguous FASTA."""


# Standard residues plus the IUPAC ambiguity codes, the stop character, and the
# alignment gap. Deliberately permissive: real curated data contains X at
# unresolved positions, and a validator that fights real data gets turned off.
_ALPHABETS = {
    "protein": frozenset("ACDEFGHIKLMNPQRSTVWYBJOUXZ*-"),
    "dna": frozenset("ACGTNRYSWKMBDHV*-"),
    "rna": frozenset("ACGUNRYSWKMBDHV*-"),
}

_ON_DUPLICATE = ("raise", "warn", "first")


def _offenders(mask: "pd.Series[bool]", limit: int = 5) -> str:
    """Render the index labels of failing rows for an error message."""
    labels = mask[mask].index.tolist()
    shown = ", ".join(repr(label) for label in labels[:limit])
    if len(labels) > limit:
        shown += f", ... ({len(labels)} rows total)"
    return shown


def _require_column(df: pd.DataFrame, name: str, role: str) -> None:
    if name not in df.columns:
        raise ValidationError(
            f"{role} column {name!r} is not in the DataFrame. "
            f"Available columns: {list(df.columns)}"
        )


def _check_no_newlines(values: "pd.Series[str]", role: str) -> None:
    bad = values.str.contains(r"[\r\n]", regex=True)
    if bad.any():
        raise ValidationError(
            f"{role} contains line breaks, which would corrupt the record "
            f"structure, at rows: {_offenders(bad)}"
        )


def _wrap_sequence(sequence: str, width: Optional[int]) -> str:
    if width is None:
        return sequence
    return "\n".join(sequence[i : i + width] for i in range(0, len(sequence), width))


def to_fasta(
    df: pd.DataFrame,
    path_or_buf: Any,
    *,
    id: str,
    seq: str,
    description: Optional[str] = None,
    wrap: Optional[int] = None,
    on_duplicate: str = "raise",
    alphabet: Union[str, Iterable[str], None] = None,
) -> int:
    """Write a DataFrame to a FASTA file and return the number of records written.

    Parameters
    ----------
    df:
        Source frame. One record is written per row.
    path_or_buf:
        Destination path, or any object with a ``write`` method. Paths are
        opened with ``newline="\\n"`` so output is LF terminated on every
        platform.
    id:
        Column holding the record identifier. Identifiers must be unique, and
        must not contain whitespace, because parsers take the header only up to
        the first space.
    seq:
        Column holding the sequence.
    description:
        Optional column appended to the header after a space. Missing values
        are written as no description at all, which is still valid FASTA.
    wrap:
        Wrap sequences at this many characters. ``None`` (the default) writes
        each sequence on a single line, which keeps MMseqs2's
        ``--createdb-mode 1`` available.
    on_duplicate:
        ``"raise"`` (default), ``"warn"``, or ``"first"`` to keep the first
        occurrence of each identifier.
    alphabet:
        ``"protein"``, ``"dna"``, ``"rna"``, or an iterable of permitted
        characters. ``None`` (the default) skips residue checking.

    Raises
    ------
    ValidationError
        If the data cannot be written as unambiguous FASTA.
    """
    _require_column(df, id, "Identifier")
    _require_column(df, seq, "Sequence")
    if description is not None:
        _require_column(df, description, "Description")

    if on_duplicate not in _ON_DUPLICATE:
        raise ValueError(
            f"on_duplicate must be one of {_ON_DUPLICATE}, got {on_duplicate!r}"
        )
    if wrap is not None and (not isinstance(wrap, int) or isinstance(wrap, bool) or wrap < 1):
        raise ValueError(f"wrap must be a positive integer or None, got {wrap!r}")

    permitted: Optional[frozenset] = None
    if alphabet is not None:
        if isinstance(alphabet, str) and alphabet in _ALPHABETS:
            permitted = _ALPHABETS[alphabet]
        else:
            permitted = frozenset(alphabet)
            if not permitted:
                raise ValueError("alphabet must not be empty")

    ids = df[id]
    seqs = df[seq]

    # Null checks come first so the str conversion below cannot turn a missing
    # value into the literal text "nan" and write it as a header.
    for values, role in ((ids, "Identifier"), (seqs, "Sequence")):
        missing = values.isna()
        if missing.any():
            raise ValidationError(
                f"{role} column has missing values at rows: {_offenders(missing)}"
            )

    # A numeric sequence column is always a mistake, and str() would silently
    # turn it into something like "1.0" and write it out as residues.
    if len(seqs) and not pd.api.types.is_object_dtype(seqs) and not pd.api.types.is_string_dtype(seqs):
        raise ValidationError(
            f"Sequence column {seq!r} has dtype {seqs.dtype}, expected text. "
            "Read it with dtype=str if this came from a CSV."
        )

    ids = ids.astype(str)
    seqs = seqs.astype(str)

    for values, role in ((ids, "Identifier"), (seqs, "Sequence")):
        empty = values.str.len() == 0
        if empty.any():
            raise ValidationError(
                f"{role} column has empty values at rows: {_offenders(empty)}"
            )
        _check_no_newlines(values, role)

    spaced = ids.str.contains(r"\s", regex=True)
    if spaced.any():
        raise ValidationError(
            "Identifiers contain whitespace, which parsers treat as the end of "
            f"the identifier, at rows: {_offenders(spaced)}. Pass those columns "
            "via description= instead."
        )

    marked = ids.str.contains(">", regex=False)
    if marked.any():
        raise ValidationError(
            f"Identifiers contain '>' at rows: {_offenders(marked)}"
        )

    whitespace_in_seq = seqs.str.contains(r"\s", regex=True)
    if whitespace_in_seq.any():
        raise ValidationError(
            f"Sequences contain whitespace at rows: {_offenders(whitespace_in_seq)}"
        )

    if permitted is not None:
        invalid = seqs.map(lambda s: not set(s.upper()) <= permitted)
        if invalid.any():
            first = seqs[invalid].iloc[0]
            unexpected = sorted(set(first.upper()) - permitted)
            raise ValidationError(
                f"Sequences contain characters outside the {alphabet!r} alphabet "
                f"at rows: {_offenders(invalid)}. First offending row uses: "
                f"{''.join(unexpected)}"
            )

    keep = pd.Series(True, index=df.index, dtype=bool)
    duplicated = ids.duplicated(keep=False)
    if duplicated.any():
        n_dupes = int(ids.duplicated().sum())
        message = (
            f"Identifier column {id!r} has {n_dupes} duplicate value(s) at rows: "
            f"{_offenders(duplicated)}. Duplicate headers are silently accepted "
            "by most FASTA consumers and produce wrong results rather than errors."
        )
        if on_duplicate == "raise":
            raise ValidationError(message)
        if on_duplicate == "warn":
            warnings.warn(message, stacklevel=2)
        else:  # "first"
            keep = ~ids.duplicated(keep="first")

    ids = ids[keep]
    seqs = seqs[keep]

    if description is not None:
        descriptions = df.loc[keep, description].fillna("").astype(str)
        _check_no_newlines(descriptions, "Description")
        headers = [
            f"{i} {d}" if d else i for i, d in zip(ids, descriptions)
        ]
    else:
        headers = list(ids)

    should_close = False
    if hasattr(path_or_buf, "write"):
        handle = path_or_buf
    else:
        # newline="\n" defeats the platform translation that would otherwise
        # emit CRLF on Windows.
        handle = open(path_or_buf, "w", encoding="utf-8", newline="\n")
        should_close = True

    try:
        for header, sequence in zip(headers, seqs):
            handle.write(f">{header}\n{_wrap_sequence(sequence, wrap)}\n")
    finally:
        if should_close:
            handle.close()

    return len(headers)


def csv_to_fasta(
    csv_path: Any,
    fasta_path: Any,
    *,
    id: str,
    seq: str,
    description: Optional[str] = None,
    read_csv_kwargs: Optional[dict] = None,
    **kwargs: Any,
) -> int:
    """Read a CSV and write it as FASTA, returning the number of records written.

    The identifier, sequence, and description columns are read as text by
    default, so an all-digit identifier is not silently parsed as a number and
    rendered as something like ``1.0``. Pass ``read_csv_kwargs`` to override
    that or to supply any other :func:`pandas.read_csv` argument.
    """
    text_columns = {id: str, seq: str}
    if description is not None:
        text_columns[description] = str

    options: dict = {"dtype": text_columns}
    options.update(read_csv_kwargs or {})

    df = pd.read_csv(csv_path, **options)
    return to_fasta(
        df, fasta_path, id=id, seq=seq, description=description, **kwargs
    )
