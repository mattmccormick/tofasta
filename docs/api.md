# API reference

Everything below is generated from the docstrings in `tofasta`, so it stays in
step with the code.

## Writing FASTA

```{eval-rst}
.. autofunction:: tofasta.to_fasta
```

```{eval-rst}
.. autofunction:: tofasta.csv_to_fasta
```

## Errors

```{eval-rst}
.. autoexception:: tofasta.ValidationError
   :show-inheritance:
```

`ValidationError` subclasses `ValueError`, so existing `except ValueError`
handlers keep working, but you can catch it specifically to distinguish "this
data cannot be written as FASTA" from an ordinary bad argument.
