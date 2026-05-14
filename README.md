# stata-function

Stata-style data analysis functions for Python — built with `pandas` and `numpy` only.

## Background

This project was created to allow teams that use Stata for data analysis to transition to Python **without a Stata licence** and without any Stata-specific Python packages (e.g. no `pyreadstat`). It replicates the most commonly used Stata commands as Python functions that work directly on `.dta` files.

---

## Folder Structure

```
stata-function/
├── auto.dta                 # Example dataset (Stata's built-in auto dataset)
├── automation.ipynb         # Example notebook demonstrating all functions
├── statalikefunction.py     # All custom functions live here
└── README.md
```

---

## Requirements

- Python 3.8+
- `pandas`
- `numpy`

No other packages required.

---

## Getting Started

Instead of `pd.read_stata()`, always use `read_dta()` from this library. This ensures variable labels and value labels are correctly loaded into the DataFrame for use by `codebook`, `tab`, and other functions.

```python
import pandas as pd
import numpy as np
from statalikefunction import read_dta, codebook, tab

df = read_dta("auto.dta")
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} columns")
```

---

## Function Reference

### `read_dta(filepath)`

Loads a `.dta` file and correctly populates variable labels and value labels into `df.attrs`. Must be used instead of `pd.read_stata()`.

```python
df = read_dta("auto.dta")
```

---

### `codebook(df, var_name)`

Replicates Stata's `codebook` command. Displays variable label, type, unique values, missing count, and — depending on variable type:

- **String variables** — examples and embedded blank warning
- **Continuous numeric** — range, mean, std deviation, percentiles (10/25/50/75/90)
- **Value-labelled numeric** — range and tabulation with numeric codes and labels

```python
# String variable
codebook(df, 'make')

# Continuous numeric
codebook(df, 'price')
codebook(df, 'mpg')
codebook(df, 'trunk')

# Value-labelled numeric
codebook(df, 'foreign')
codebook(df, 'rep78')
```

**Example output — continuous numeric (`mpg`):**
```
-----------------------------------------------------------------------------------------------
mpg
-----------------------------------------------------------------------------------------------
          Type:  Numeric (int)
Unique values:  21                             Missing .:  0/74
         Range:  [12, 41]               Units:  1

          Mean:  21.2973
     Std. dev.:  5.7855

  Percentiles:  10%        25%        50%        75%        90%
                14         18         20         25         29
```

**Example output — value-labelled (`foreign`):**
```
-----------------------------------------------------------------------------------------------
foreign                                                                Car origin
-----------------------------------------------------------------------------------------------
          Type:  Numeric (double)
Unique values:  2                              Missing .:  0/74
         Range:  [0, 1]               Units:  1

   Tabulation:       Freq.     Numeric  Label
                        52           0  Domestic
                        22           1  Foreign
```

---

### `tab(df, var_name)`

Replicates Stata's `tab` command. Prints frequency, percent, and cumulative percent with a total row. Missing values are shown separately at the bottom.

```python
tab(df, 'mpg')
tab(df, 'foreign')
tab(df, 'rep78')  # has missing values
```

**Example output (`mpg`):**
```
  Mileage (mpg)       Freq.     Percent        Cum.
  -------------  ----------  ----------  ----------
             12           2        2.70        2.70
             14           6        8.11       10.81
            ...
             41           1        1.35      100.00
  -------------  ----------  ----------  ----------
          Total          74      100.00
```

---

## Notes

- Always use `read_dta()` to load `.dta` files — `pd.read_stata()` does not populate variable and value label metadata correctly.
- `codebook` automatically detects variable type and adjusts its output accordingly — no manual configuration needed.
- `tab` excludes missing values from percent and cumulative percent calculations, consistent with Stata's default behaviour.

---

## Coming Soon

The following functions are implemented in `statalikefunction.py` and will be documented in a future update:

- `replace` — recodes a value-labelled variable for rows matching a condition (equivalent to Stata's `replace`)
- `val_check` — returns the Stata numeric code for the first row matching a condition
