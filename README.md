# tofasta

Convert pandas DataFrames and CSV files to FASTA, with validation that refuses
to write malformed output.

FASTA has no formal specification, so every consumer is permissive. Feed BLAST
or MMseqs2 a file with duplicate headers, an empty sequence, or an identifier
containing a space, and you will not get an error. You will get results that are
quietly wrong. `tofasta` checks for those cases up front and raises instead of
writing.

## Install

```bash
pip install tofasta
```

## Use

```python
import pandas as pd
from tofasta import to_fasta

df = pd.DataFrame({
    "accession": ["96602692", "77cd04d8"],
    "sequence": ["MKVLAAGIVL", "GSGEGPREPG"],
})

to_fasta(df, "out.fasta", id="accession", seq="sequence")
```

```
>96602692
MKVLAAGIVL
>77cd04d8
GSGEGPREPG
```

Straight from a CSV:

```python
from tofasta import csv_to_fasta

csv_to_fasta("in.csv", "out.fasta", id="accession", seq="sequence")
```

Or from the shell:

```bash
tofasta in.csv out.fasta --id accession --seq sequence
```

Both return the number of records written, so you can assert on it.

## What it checks

| Problem | Why it matters |
| --- | --- |
| Duplicate identifiers | Accepted silently by BLAST and MMseqs2, producing wrong results rather than errors |
| Missing or empty identifier | Becomes a headerless or garbage record |
| Missing or empty sequence | Produces a header with no residues |
| Whitespace in an identifier | Parsers stop at the first space, so the identifier is silently truncated |
| `>` in an identifier | Starts a new record mid-header |
| Line breaks in any field | Corrupts the record structure |
| Whitespace inside a sequence | Usually a stray column or a copy-paste artifact |
| Numeric sequence column | A float column would otherwise be written out as `1.0` |

Residue validation is opt in, via `alphabet="protein"`, `"dna"`, `"rna"`, or any
iterable of permitted characters. It is off by default because real curated data
legitimately contains `X` at unresolved positions, and a validator that fights
real data gets switched off entirely.

Output is always LF terminated, on every platform.

## Options

```python
to_fasta(
    df,
    path_or_buf,        # path, or anything with a .write method
    *,
    id,                 # identifier column
    seq,                # sequence column
    description=None,   # optional column appended to the header after a space
    wrap=None,          # wrap sequences at N characters
    on_duplicate="raise",   # or "warn", or "first"
    alphabet=None,      # "protein", "dna", "rna", or an iterable of characters
)
```

### On wrapping

Sequences are written on a single line by default. Wrapping at 60 or 80
characters is a widespread convention rather than a rule, and NCBI states only
that lines should be "shorter than 80 characters". No parser written in the last
thirty years cares, because they all concatenate lines until the next `>`.

Single-line output also keeps MMseqs2's `--createdb-mode 1` available, which
soft-links the input instead of copying it and requires single-line records.

Pass `wrap=60` if you want the conventional look.

## Documentation

Full API reference documentation is available at [readthedocs](https://tofasta.readthedocs.io).

## Scope

This library writes FASTA. It does not read it. Reading looks symmetric but is
not: you would own indexing, compression, malformed-record recovery, and memory
behaviour on multi-gigabyte files. Use
[pyfastx](https://github.com/lmdu/pyfastx) or
[Biopython](https://biopython.org/) for that.

If you need sequence objects, alignment, translation, or other file formats,
you want Biopython. `tofasta` exists for the narrow case where you already have
a DataFrame and want a correct FASTA file out of it without building
intermediate record objects.

## Prior art

[Biopython](https://biopython.org/) writes FASTA reliably via
`SeqIO.write`. It requires you to build `SeqRecord` objects, silently appends
`<unknown description>` if you forget `description=""`, hard-wraps at 60 with no
way to disable it, and has no DataFrame awareness. `tofasta` is a smaller,
narrower tool for that specific gap.

Several of the checks here are regression tests against real defects in CDC's
[CSV2FASTA](https://github.com/CDCgov/CSV2FASTA) browser tool, which emits CRLF
unconditionally and writes a phantom `>undefined` record with an empty sequence
whenever the identifier is not the first column of the input.

## Development

```bash
uv sync
uv run pytest
```

To build the documentation, use the same flags Read the Docs does. The `-W` and
`-j auto` both matter: warnings are errors there, and parallel builds surface
extension incompatibilities that a serial build hides.

```bash
uv sync --extra docs
uv run python -m sphinx -T -W --keep-going -j auto -b html docs docs/_build/html
```

## Licence

MIT
