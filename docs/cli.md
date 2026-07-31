# Command line

Installing the package puts a `tofasta` command on your path. It is a thin
wrapper over {func}`tofasta.csv_to_fasta`, for converting a CSV without writing
any Python.

```bash
tofasta in.csv out.fasta --id accession --seq sequence
```

It exits `0` on success, `2` when the input fails validation, and `1` on other
errors such as an unreadable file. Validation messages go to stderr and name the
offending rows.

## Options

```{eval-rst}
.. argparse::
   :module: tofasta._cli
   :func: build_parser
   :prog: tofasta
```
