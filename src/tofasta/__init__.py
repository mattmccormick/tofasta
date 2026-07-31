"""Convert pandas DataFrames and CSV files to FASTA.

The guiding principle is that refusing to write is always better than writing
something subtly wrong, because FASTA consumers accept malformed input happily
and give you wrong answers rather than errors.
"""

from tofasta._core import ValidationError, csv_to_fasta, to_fasta

__all__ = ["ValidationError", "csv_to_fasta", "to_fasta"]
__version__ = "0.1.0"
