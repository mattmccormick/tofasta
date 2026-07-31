"""Command line entry point, so the library is usable without writing Python."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from tofasta._core import ValidationError, csv_to_fasta


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tofasta",
        description="Convert a CSV file to FASTA, refusing to write malformed output.",
    )
    parser.add_argument("csv", help="input CSV path")
    parser.add_argument("fasta", help="output FASTA path")
    parser.add_argument("--id", required=True, help="column holding record identifiers")
    parser.add_argument("--seq", required=True, help="column holding sequences")
    parser.add_argument("--description", help="optional column appended to the header")
    parser.add_argument(
        "--wrap",
        type=int,
        metavar="N",
        help="wrap sequences at N characters (default: one line per sequence)",
    )
    parser.add_argument(
        "--alphabet",
        choices=["protein", "dna", "rna"],
        help="validate residues against this alphabet (default: no check)",
    )
    parser.add_argument(
        "--on-duplicate",
        choices=["raise", "warn", "first"],
        default="raise",
        dest="on_duplicate",
        help="how to handle duplicate identifiers (default: raise)",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="suppress the summary line")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        written = csv_to_fasta(
            args.csv,
            args.fasta,
            id=args.id,
            seq=args.seq,
            description=args.description,
            wrap=args.wrap,
            alphabet=args.alphabet,
            on_duplicate=args.on_duplicate,
        )
    except ValidationError as exc:
        print(f"tofasta: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"tofasta: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"{written} records written to {args.fasta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
