# Release History

---

## 0.1.0

- Initial release
- `to_fasta()` writes a pandas DataFrame to FASTA from an identifier column and a sequence column
- `csv_to_fasta()` does the same directly from a CSV, reading the identifier, sequence, and description columns as text so an all-digit identifier is not parsed as a number
- `tofasta` command line entry point for converting a CSV without writing Python
- Validation refuses to write rather than emitting malformed FASTA, covering duplicate identifiers, missing or empty identifiers and sequences, whitespace or `>` in identifiers, line breaks in any field, whitespace inside sequences, and non-text sequence columns
- Optional residue validation via `alphabet="protein"`, `"dna"`, `"rna"`, or any iterable of permitted characters
- Output is LF terminated on every platform
- Sequences are written unwrapped by default, with `wrap=N` available
