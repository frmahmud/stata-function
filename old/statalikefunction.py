
import pandas as pd
import numpy as np

# ============================================================
# Funtion codebook: Fully automatic Stata-style codebook
# ============================================================

def codebook(df, var_name):
    
    if var_name not in df.columns:
        print(f"Error: '{var_name}' not found in DataFrame.")
        return
    
    ser = df[var_name]
    varlabels = df.attrs.get("variable_labels", {})
    vallabels = df.attrs.get("value_labels", {})
    var_label = varlabels.get(var_name, var_name)
    
    # --- Logic to get Numeric Code from Metadata ---
    forward_map = vallabels.get(var_name, {})
    reverse_map = {v: k for k, v in forward_map.items()}
    was_stata_numeric_coded = var_name in vallabels # Check if variable originally had labels
    
    # Header
    print("-" * 95)
    print(f"{var_name:<70} {var_label}")
    print("-" * 95)
    
    # --- Corrected Type Detection Block ---
    if pd.api.types.is_numeric_dtype(ser):
        # This branch is for variables that were NOT converted (e.g., pure numeric)
        dtype_name = "Numeric (double)"
        
    elif pd.api.types.is_string_dtype(ser) or pd.api.types.is_categorical_dtype(ser):
        if was_stata_numeric_coded:
            # Displays the original type for consistency with Stata
            dtype_name = "Numeric (double)" 
        else:
            # This is a string/object column that was never numeric
            max_len = int(ser.astype(str).str.len().max())
            dtype_name = f"string (str{max_len})"
    else:
        dtype_name = "unknown"
    
    print(f"{'type:':>18}  {dtype_name}")
    # --- End of Corrected Type Detection Block ---
    
    print(f"{'unique values:':>18}  {ser.nunique(dropna=True)}")
    missing = ser.isna().sum()
    total = len(ser)
    print(f"{'missing:':>18}  {missing}/{total}")
    
    if pd.api.types.is_numeric_dtype(ser):
        print(f"{'range:':>18}  [{ser.min()}, {ser.max()}]")
    
    print()
    print(f"{'tabulation:':>18}  {'Freq.':<10} {'Numeric':<10} Label") 
    
    # 1. Get counts of the TEXT labels
    text_counts = ser.value_counts(dropna=False)
    
    # 2. Prepare the data for sorting
    tab_df = pd.DataFrame({
        'Label': text_counts.index,
        'Freq': text_counts.values
    })
    
    # 3. Add the Numeric Code column using the reverse map
    tab_df['Numeric_Code'] = tab_df['Label'].apply(lambda x: reverse_map.get(x) if pd.notna(x) else np.nan)
    
    # 4. Separate and sort: Data rows (by Numeric Code) and Missing rows
    data_rows = tab_df[tab_df['Label'].notna()].copy()
    missing_row = tab_df[tab_df['Label'].isna()].copy()
    
    if not data_rows.empty:
        # Create a Sort_Key column and convert to numeric for accurate sorting
        data_rows.loc[:, 'Sort_Key'] = pd.to_numeric(data_rows['Numeric_Code'], errors='coerce') 
        data_rows = data_rows.sort_values(by='Sort_Key', ascending=True)
    
    # 5. Recombine (data first, then missing) and print
    final_tab = pd.concat([data_rows, missing_row])

    for _, row in final_tab.iterrows():
        val = row['Label']
        freq = row['Freq']
        numeric_val = row['Numeric_Code']
        
        if pd.isna(val):
            numeric_print = "."
            label_print = "Missing"
        else:
            label_print = val 
            numeric_print = numeric_val if not pd.isna(numeric_val) else "N/A"
            if isinstance(numeric_val, (int, float)) and numeric_val == round(numeric_val):
                 numeric_print = int(numeric_val)
            
        print(f"{'':>26}  {freq:<10} {str(numeric_print):<10} {label_print}") 
    
    print()

# ============================================================
# Function tab: Fully automatic Stata-style tabulate
# ============================================================
def tab(df, var_name):
    """
    Fully automatic Stata-style tabulate with Freq, Percent, Cum%.
    Works on the converted text data.
    """
    if var_name not in df.columns:
        raise ValueError(f"Variable '{var_name}' not found in DataFrame.")
    
    ser = df[var_name]
    total = len(ser)
    
    # Frequency counts including NaN (index will be the text labels)
    freq_series = ser.value_counts(dropna=False).sort_index()
    
    # Prepare table
    table = pd.DataFrame({
        'Label': freq_series.index,
        'Freq': freq_series.values
    })
    
    # Handle Missing
    table['Label'] = table['Label'].apply(
        lambda x: "Missing" if pd.isna(x) else str(x)
    )
    
    # Calculate percent and cumulative percent
    table['Percent'] = (table['Freq'] / total * 100).round(2)
    table['CumPercent'] = table['Percent'].cumsum().round(2)
    
    # Optional: move Missing to the bottom
    table = pd.concat([
        table[table['Label'] != 'Missing'],
        table[table['Label'] == 'Missing']
    ])
    
    # Reset index and return
    table = table.reset_index(drop=True)
    return table[['Label', 'Freq', 'Percent', 'CumPercent']]

# ============================================================
# Function replace: Recoding Helper (replace)
# Stata Code -> Text Label for assignment (replace command equivalent)
# ============================================================
def replace(df, condition_series, var_name, stata_code):
    """
    Performs Stata-like assignment: replaces the text label in var_name 
    for rows meeting the condition_series with the text corresponding to stata_code.
    """
    # 1. Look up the corresponding text label
    forward_map = df.attrs.get('value_labels', {}).get(var_name, {})
    new_text_label = forward_map.get(stata_code)
    
    # --- CHANGE: Get the count of rows BEFORE assignment ---
    rows_to_update = condition_series.sum()
    
    if new_text_label is not None:
        if rows_to_update > 0:
            # 2. Use .loc to assign the new text label based on the compound condition
            df.loc[condition_series, var_name] = new_text_label
            
            # --- CHANGE: Print confirmation with specific details ---
            print(f"✅ Success: Recoded '{var_name}' to '{new_text_label}' (Code {stata_code}) in {rows_to_update} row(s).")
        else:
            # Report if the condition matched zero rows
            print(f"⚠️ Warning: Recode skipped. Condition matched 0 rows for variable '{var_name}'.")
    else:
        # Report the error if the Stata code is invalid
        print(f"❌ Error: Stata code {stata_code} not found in the value labels for '{var_name}'.")

    return df

# ============================================================
# Function val_check: Value Checking Helper (val_check)
# Text Label -> Stata Code for inspection
# ============================================================
def val_check(df, condition_series, var_name):
    """
    Returns the original Stata numeric code for the *first* cell 
    that meets the condition, by looking up the text label in the metadata.
    """
    try:
        # 1. Get the text value from the DataFrame using the condition
        text_value = df.loc[condition_series, var_name].iloc[0]
    except IndexError:
        print(f"⚠️ Error: No records found matching the condition for variable '{var_name}'.")
        return None

    # 2. Get the forward map (Code -> Text)
    forward_map = df.attrs.get('value_labels', {}).get(var_name, {})

    # 3. Create the reverse map (Text -> Code)
    reverse_map = {v: k for k, v in forward_map.items()}

    # 4. Return the Stata code
    return reverse_map.get(text_value)
