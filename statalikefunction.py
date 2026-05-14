import pandas as pd
import numpy as np

# ============================================================
# Function read_dta: Load .dta and populate df.attrs properly
# ============================================================
def read_dta(filepath):
    """
    Loads a Stata .dta file and populates df.attrs with:
      - variable_labels : {col: label}
      - value_labels    : {col: {code: label}}
    Use this instead of pd.read_stata() so codebook/tab work correctly.
    """
    with pd.io.stata.StataReader(filepath) as reader:
        var_labels = reader.variable_labels()   # {varname: label}
        val_labels = reader.value_labels()      # {labelname: {code: label}}
        lbllist    = reader._lbllist            # [labelname per column]
        varlist    = reader._varlist            # [column names]

    df = pd.read_stata(filepath)

    # Map value labels per variable (varname -> {code: label})
    col_val_labels = {}
    for col, lblname in zip(varlist, lbllist):
        if lblname and lblname in val_labels:
            col_val_labels[col] = val_labels[lblname]

    df.attrs["variable_labels"] = var_labels
    df.attrs["value_labels"]    = col_val_labels

    return df

# ============================================================
# Function codebook: Fully automatic Stata-style codebook
# ============================================================

def codebook(df, var_name):

    if var_name not in df.columns:
        print(f"Error: '{var_name}' not found in DataFrame.")
        return

    ser = df[var_name]
    varlabels = df.attrs.get("variable_labels", {})
    vallabels = df.attrs.get("value_labels", {})
    var_label = varlabels.get(var_name, "")

    # --- Logic to get Numeric Code from Metadata ---
    forward_map = vallabels.get(var_name, {})
    reverse_map = {v: k for k, v in forward_map.items()}
    was_stata_numeric_coded = var_name in vallabels

    # Header — right-align var_label to column 95
    print("-" * 95)
    print(f"{var_name:<70} {var_label}")
    print("-" * 95)

    n_unique  = ser.nunique(dropna=True)
    missing   = ser.isna().sum()
    total     = len(ser)

    # -------------------------------------------------------
    # TYPE DETECTION
    # -------------------------------------------------------
    # pandas read_stata converts value-labelled numeric vars to Categorical
    if pd.api.types.is_categorical_dtype(ser):
        dtype_name = "Numeric (double)"
        is_numeric = True
        is_string  = False
        # Reconstruct reverse_map from Categorical codes if attrs not present
        if not forward_map:
            # Build from the category order (0-based integer codes → label)
            cats = ser.cat.categories.tolist()
            forward_map = {i: c for i, c in enumerate(cats)}
            reverse_map = {v: k for k, v in forward_map.items()}
        was_stata_numeric_coded = True

    elif pd.api.types.is_numeric_dtype(ser):
        dtype_name = "Numeric (float)" if pd.api.types.is_float_dtype(ser) else "Numeric (int)"
        is_numeric = True
        is_string  = False

    elif pd.api.types.is_string_dtype(ser):
        if was_stata_numeric_coded:
            dtype_name = "Numeric (double)"
            is_numeric = True
            is_string  = False
        else:
            max_len   = int(ser.dropna().astype(str).str.len().max()) if not ser.dropna().empty else 0
            dtype_name = f"string (str{max_len})"
            is_numeric = False
            is_string  = True
    else:
        dtype_name = "unknown"
        is_numeric = False
        is_string  = False

    print(f"{'Type:':>18}  {dtype_name}")
    print(f"{'Unique values:':>18}  {n_unique:<30} Missing {'\"\"' if is_string else '.'}:  {missing}/{total}")

    # -------------------------------------------------------
    # STRING BRANCH
    # -------------------------------------------------------
    if is_string:
        # Show up to 4 examples FIRST (Stata order)
        examples = ser.dropna().unique()
        print()
        if len(examples) > 0:
            print(f"{'Examples:':>18}  \"{examples[0]}\"")
            for ex in examples[1:4]:
                print(f"{'':>18}  \"{ex}\"")

        # Warning at the BOTTOM (Stata order)
        has_embedded = ser.dropna().apply(lambda x: '  ' in str(x) or (str(x) != str(x).strip())).any()
        if has_embedded:
            print()
            print(f"{'Warning:':>18}  Variable has embedded blanks.")

        # Only tabulate if low-cardinality (<=20 unique values)
        if n_unique <= 20:
            print()
            print(f"{'Tabulation:':>18}  {'Freq.':<10} {'Numeric':<10} Label")
            text_counts = ser.value_counts(dropna=False).sort_index()
            for label, freq in text_counts.items():
                if pd.isna(label):
                    print(f"{'':>26}  {freq:<10} {'.':<10} Missing")
                else:
                    num_code = reverse_map.get(label, "N/A")
                    if isinstance(num_code, float) and num_code == round(num_code):
                        num_code = int(num_code)
                    print(f"{'':>26}  {freq:<10} {str(num_code):<10} {label}")

    # -------------------------------------------------------
    # NUMERIC BRANCH
    # -------------------------------------------------------
    else:
        if pd.api.types.is_categorical_dtype(ser):
            numeric_ser = pd.to_numeric(ser.cat.codes.replace(-1, pd.NA), errors='coerce')
        elif not pd.api.types.is_numeric_dtype(ser):
            numeric_ser = pd.to_numeric(ser, errors='coerce')
        else:
            numeric_ser = ser

        # Range
        print(f"{'Range:':>18}  [{numeric_ser.min()}, {numeric_ser.max()}]{'':>15} Units:  1")

        # Mean & Std dev — only for continuous (skip for low-cardinality value-labelled)
        show_stats = not was_stata_numeric_coded and n_unique > 10
        if show_stats:
            print()
            print(f"{'Mean:':>18}  {numeric_ser.mean():.4f}")
            print(f"{'Std. dev.:':>18}  {numeric_ser.std():.4f}")
            print()
            pcts = numeric_ser.quantile([0.10, 0.25, 0.50, 0.75, 0.90])
            print(f"{'Percentiles:':>18}  {'10%':<10} {'25%':<10} {'50%':<10} {'75%':<10} {'90%':<10}")
            print(f"{'':>18}  {pcts[0.10]:<10.4g} {pcts[0.25]:<10.4g} {pcts[0.50]:<10.4g} {pcts[0.75]:<10.4g} {pcts[0.90]:<10.4g}")

        if was_stata_numeric_coded and n_unique <= 20:
            print()
            # Fixed column widths matching header and data rows
            print(f"{'Tabulation:':>18}  {'Freq.':>10}  {'Numeric':>10}  Label")

            # For Categorical, convert to string first for counting
            ser_str = ser.astype(str) if pd.api.types.is_categorical_dtype(ser) else ser
            text_counts = ser_str.value_counts(dropna=False)
            tab_df = pd.DataFrame({'Label': text_counts.index, 'Freq': text_counts.values})
            tab_df['Numeric_Code'] = tab_df['Label'].apply(lambda x: reverse_map.get(x) if pd.notna(x) else np.nan)

            data_rows   = tab_df[tab_df['Label'].notna()].copy()
            missing_row = tab_df[tab_df['Label'].isna()].copy()

            if not data_rows.empty:
                data_rows['Sort_Key'] = pd.to_numeric(data_rows['Numeric_Code'], errors='coerce')
                data_rows = data_rows.sort_values('Sort_Key')

            final_tab = pd.concat([data_rows, missing_row])

            for _, row in final_tab.iterrows():
                val         = row['Label']
                freq        = row['Freq']
                numeric_val = row['Numeric_Code']

                if pd.isna(val):
                    print(f"{'':>18}  {freq:>10}  {'.':>10}  Missing")
                else:
                    num_print = int(numeric_val) if not pd.isna(numeric_val) and float(numeric_val) == round(float(numeric_val)) else (numeric_val if not pd.isna(numeric_val) else "N/A")
                    print(f"{'':>18}  {freq:>10}  {str(num_print):>10}  {val}")

    print()


# ============================================================
# Function tab: Fully automatic Stata-style tabulate
# ============================================================
def tab(df, var_name):
    """
    Prints a Stata-style tabulation with Freq., Percent, and Cum.
    """
    if var_name not in df.columns:
        raise ValueError(f"Variable '{var_name}' not found in DataFrame.")

    ser       = df[var_name]
    total     = len(ser)
    varlabels = df.attrs.get("variable_labels", {})
    var_label = varlabels.get(var_name, var_name)

    # For Categorical, convert to string labels for counting
    if pd.api.types.is_categorical_dtype(ser):
        ser_str = ser.astype(str)
    else:
        ser_str = ser

    # Frequency counts excluding NaN for percent/cum (Stata excludes missing)
    freq_series = ser_str.value_counts(dropna=True).sort_index()

    table = pd.DataFrame({
        'Label':   freq_series.index.astype(str),
        'Freq':    freq_series.values
    })

    # Move missing to bottom if present
    missing_count = ser_str.isna().sum()

    table['Percent']    = (table['Freq'] / total * 100).round(2)
    table['Cum']        = table['Percent'].cumsum().round(2)

    # --- Print ---
    col_w   = max(table['Label'].str.len().max(), len(var_label), 8)
    sep     = f"  {'-' * col_w}  {'-'*10}  {'-'*10}  {'-'*10}"

    print()
    print(f"  {var_label:>{col_w}}  {'Freq.':>10}  {'Percent':>10}  {'Cum.':>10}")
    print(sep)

    for _, row in table.iterrows():
        print(f"  {row['Label']:>{col_w}}  {row['Freq']:>10}  {row['Percent']:>10.2f}  {row['Cum']:>10.2f}")

    if missing_count > 0:
        print(f"  {'Missing':>{col_w}}  {missing_count:>10}")

    print(sep)
    print(f"  {'Total':>{col_w}}  {total:>10}  {'100.00':>10}")
    print()


# ============================================================
# Function replace: Recoding Helper (replace)
# ============================================================
def replace(df, condition_series, var_name, stata_code):
    forward_map    = df.attrs.get('value_labels', {}).get(var_name, {})
    new_text_label = forward_map.get(stata_code)
    rows_to_update = condition_series.sum()

    if new_text_label is not None:
        if rows_to_update > 0:
            df.loc[condition_series, var_name] = new_text_label
            print(f"✅ Success: Recoded '{var_name}' to '{new_text_label}' (Code {stata_code}) in {rows_to_update} row(s).")
        else:
            print(f"⚠️  Warning: Recode skipped. Condition matched 0 rows for variable '{var_name}'.")
    else:
        print(f"❌ Error: Stata code {stata_code} not found in the value labels for '{var_name}'.")

    return df


# ============================================================
# Function val_check: Value Checking Helper
# ============================================================
def val_check(df, condition_series, var_name):
    try:
        text_value = df.loc[condition_series, var_name].iloc[0]
    except IndexError:
        print(f"⚠️  Error: No records found matching the condition for variable '{var_name}'.")
        return None

    forward_map = df.attrs.get('value_labels', {}).get(var_name, {})
    reverse_map = {v: k for k, v in forward_map.items()}
    return reverse_map.get(text_value)
