"""
Data cleaning and synthetic donor generation pipeline for BloodIQ.
Supports both Pandas and cuDF.
"""

import os
import time
import pandas as pd

# Attempt to import cuDF/RAPIDS for GPU acceleration
try:
    import cudf
    import cupy as cp
    CUDF_AVAILABLE = True
except ImportError:
    CUDF_AVAILABLE = False


def to_snake_case_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes DataFrame column names to snake_case using Pandas.

    Parameters:
    df (pd.DataFrame): Input DataFrame.

    Returns:
    pd.DataFrame: DataFrame with standardized column names.
    """
    new_cols = {}
    for col in df.columns:
        clean = col.strip().lower()
        clean = clean.replace(' ', '_').replace('-', '_').replace('#', 'num').replace('(', '').replace(')', '').replace('.', '')
        # Replace multiple underscores
        while '__' in clean:
            clean = clean.replace('__', '_')
        new_cols[col] = clean
    return df.rename(columns=new_cols)


def to_snake_case_cudf(df: 'cudf.DataFrame') -> 'cudf.DataFrame':
    """
    Standardizes DataFrame column names to snake_case using cuDF.

    Parameters:
    df (cudf.DataFrame): Input DataFrame.

    Returns:
    cudf.DataFrame: DataFrame with standardized column names.
    """
    new_cols = {}
    for col in df.columns:
        clean = str(col).strip().lower()
        clean = clean.replace(' ', '_').replace('-', '_').replace('#', 'num').replace('(', '').replace(')', '').replace('.', '')
        while '__' in clean:
            clean = clean.replace('__', '_')
        new_cols[col] = clean
    return df.rename(columns=new_cols)


def clean_blood_banks_pandas(filepath: str) -> pd.DataFrame:
    """
    Cleans raw blood banks data using Pandas:
    - Standardizes column names to snake_case.
    - Filters latitude between 8.0–37.0 and longitude between 68.0–97.0.
    - Drops duplicates on bank name + city combination.
    - Fills missing contact fields with 'N/A'.

    Parameters:
    filepath (str): Path to raw CSV.

    Returns:
    pd.DataFrame: Cleaned DataFrame.
    """
    df = pd.read_csv(filepath, encoding='latin-1')
    df = to_snake_case_pandas(df)
    
    # Filter coordinates
    df = df[(df['latitude'] >= 8.0) & (df['latitude'] <= 37.0) &
            (df['longitude'] >= 68.0) & (df['longitude'] <= 97.0)]
    
    # Drop duplicates on name + city
    df = df.drop_duplicates(subset=['blood_bank_name', 'city'])
    
    # Fill missing contact fields
    contact_fields = ['contact_no', 'mobile', 'helpline', 'email']
    for field in contact_fields:
        if field in df.columns:
            df[field] = df[field].fillna('N/A')
            
    return df


def clean_blood_banks_cudf(filepath: str) -> 'cudf.DataFrame':
    """
    Cleans raw blood banks data using cuDF:
    - Standardizes column names to snake_case.
    - Filters latitude between 8.0–37.0 and longitude between 68.0–97.0.
    - Drops duplicates on bank name + city combination.
    - Fills missing contact fields with 'N/A'.

    Parameters:
    filepath (str): Path to raw CSV.

    Returns:
    cudf.DataFrame: Cleaned DataFrame.
    """
    df = cudf.read_csv(filepath, encoding='latin-1')
    df = to_snake_case_cudf(df)
    
    # Filter coordinates
    df = df[(df['latitude'] >= 8.0) & (df['latitude'] <= 37.0) &
            (df['longitude'] >= 68.0) & (df['longitude'] <= 97.0)]
    
    # Drop duplicates on name + city
    df = df.drop_duplicates(subset=['blood_bank_name', 'city'])
    
    # Fill missing contact fields
    contact_fields = ['contact_no', 'mobile', 'helpline', 'email']
    for field in contact_fields:
        if field in df.columns:
            df[field] = df[field].fillna('N/A')
            
    return df


def clean_donations_pandas(filepath: str) -> pd.DataFrame:
    """
    Cleans donation records using Pandas:
    - Standardizes column names to snake_case.
    - Drops rows where blood group is null.
    - Normalizes blood type values.

    Parameters:
    filepath (str): Path to raw CSV.

    Returns:
    pd.DataFrame: Cleaned DataFrame.
    """
    df = pd.read_csv(filepath, encoding='latin-1')
    df = to_snake_case_pandas(df)
    
    # Drop rows where blood group is null
    df = df.dropna(subset=['blood_group'])
    
    # Normalize blood group values
    df['blood_group'] = df['blood_group'].astype(str).str.strip().str.upper()
    # Handle replacing spaces or potential incorrect strings
    df['blood_group'] = df['blood_group'].str.replace(' ', '')
    
    return df


def clean_donations_cudf(filepath: str) -> 'cudf.DataFrame':
    """
    Cleans donation records using cuDF:
    - Standardizes column names to snake_case.
    - Drops rows where blood group is null.
    - Normalizes blood type values.

    Parameters:
    filepath (str): Path to raw CSV.

    Returns:
    cudf.DataFrame: Cleaned DataFrame.
    """
    df = cudf.read_csv(filepath, encoding='latin-1')
    df = to_snake_case_cudf(df)
    
    # Drop rows where blood group is null
    df = df.dropna(subset=['blood_group'])
    
    # Normalize blood group values
    df['blood_group'] = df['blood_group'].astype(str).str.strip().str.upper()
    df['blood_group'] = df['blood_group'].str.replace(' ', '')
    
    return df


def generate_synthetic_donors_pandas(clean_banks_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates synthetic donors from the clean_blood_banks.csv coordinates using Pandas.

    Parameters:
    clean_banks_df (pd.DataFrame): Cleaned blood banks DataFrame.

    Returns:
    pd.DataFrame: Generated donors DataFrame.
    """
    import random
    random.seed(42)
    
    blood_types = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
    donors = []
    
    banks_df_reset = clean_banks_df.reset_index(drop=True)
    
    for idx, bank in banks_df_reset.iterrows():
        # Generate 5-15 synthetic donors per bank area
        n = random.randint(5, 15)
        for i in range(n):
            last_donation_days = random.randint(30, 180)
            donors.append({
                'donor_id': f"D{idx}_{i:03d}",
                'blood_type': random.choice(blood_types),
                'city': bank.get('city', 'Unknown'),
                'state': bank.get('state', 'Unknown'),
                'latitude': float(bank.get('latitude', 0)) + random.uniform(-0.05, 0.05),
                'longitude': float(bank.get('longitude', 0)) + random.uniform(-0.05, 0.05),
                'last_donation_days_ago': last_donation_days,
                'contact': f"+91{random.randint(7000000000, 9999999999)}"
            })
            
    return pd.DataFrame(donors)


def generate_synthetic_donors_cudf(clean_banks_df: 'cudf.DataFrame') -> 'cudf.DataFrame':
    """
    Generates synthetic donors from the clean_blood_banks.csv coordinates using cuDF and CuPy.

    Parameters:
    clean_banks_df (cudf.DataFrame): Cleaned blood banks DataFrame.

    Returns:
    cudf.DataFrame: Generated donors DataFrame.
    """
    import cupy as cp
    cp.random.seed(42)
    
    blood_types = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
    num_banks = len(clean_banks_df)
    
    # Generate random counts of donors per bank (5 to 15)
    counts = cp.random.randint(5, 16, size=num_banks)
    total_donors = int(counts.sum())
    
    banks_df_reset = clean_banks_df.reset_index(drop=True)
    
    # Repeat indices of banks
    repeated_indices = cp.repeat(cp.arange(num_banks), counts)
    repeated_df = banks_df_reset.iloc[repeated_indices].copy()
    
    repeated_df['last_donation_days_ago'] = cp.random.randint(30, 181, size=total_donors)
    
    # Add offsets
    lat_offsets = cp.random.uniform(-0.05, 0.05, size=total_donors)
    lng_offsets = cp.random.uniform(-0.05, 0.05, size=total_donors)
    
    repeated_df['latitude'] = repeated_df['latitude'] + lat_offsets
    repeated_df['longitude'] = repeated_df['longitude'] + lng_offsets
    
    # Random blood types
    blood_indices = cp.random.randint(0, len(blood_types), size=total_donors)
    blood_types_df = cudf.DataFrame({'blood_idx': range(8), 'blood_type': blood_types})
    repeated_df['blood_idx'] = blood_indices
    repeated_df = repeated_df.merge(blood_types_df, on='blood_idx').drop(columns=['blood_idx'])
    
    # Random +91 contacts
    contacts = cp.random.randint(7000000000, 10000000000, size=total_donors)
    repeated_df['contact'] = '+91' + cudf.Series(contacts).astype(str)
    
    # Generate unique ID: D{bank_idx}_{donor_idx:03d}
    repeated_df['bank_idx'] = repeated_indices
    repeated_df = repeated_df.sort_values(by=['bank_idx']).reset_index(drop=True)
    repeated_df['donor_idx'] = repeated_df.groupby('bank_idx').cumcount()
    repeated_df['donor_id'] = 'D' + repeated_df['bank_idx'].astype(str) + '_' + repeated_df['donor_idx'].astype(str).str.zfill(3)
    
    keep_cols = ['donor_id', 'blood_type', 'city', 'state', 'latitude', 'longitude', 'last_donation_days_ago', 'contact']
    return repeated_df[keep_cols]


def main():
    banks_path = "data/blood-banks.csv"
    donations_path = "data/blood_donation.csv"
    donor_mgmt_path = "data/BLOODBANK-AND-DONOR-MANAGEMENT-SYSTEM (1).csv"
    
    print("--- Running Pandas Implementation ---")
    start_pd = time.time()
    
    # Get counts before
    raw_banks_count = len(pd.read_csv(banks_path, nrows=1, encoding='latin-1'))  # Dummy load to get columns, read full count
    raw_banks_count = len(pd.read_csv(banks_path, encoding='latin-1'))
    raw_donations_count = len(pd.read_csv(donations_path, encoding='latin-1'))
    raw_donors_count = len(pd.read_csv(donor_mgmt_path, encoding='latin-1'))
    
    # 1. Clean blood banks
    clean_banks_pd = clean_blood_banks_pandas(banks_path)
    clean_banks_pd.to_csv("data/clean_blood_banks.csv", index=False)
    
    # 2. Clean donations
    clean_donations_pd = clean_donations_pandas(donations_path)
    clean_donations_pd.to_csv("data/clean_donations.csv", index=False)
    
    # 3. Clean donors (Generate synthetic)
    clean_donors_pd = generate_synthetic_donors_pandas(clean_banks_pd)
    clean_donors_pd.to_csv("data/clean_donors.csv", index=False)
    
    end_pd = time.time()
    duration_pd = end_pd - start_pd
    print(f"Pandas execution time: {duration_pd:.4f} seconds")
    
    print("\n--- Running cuDF Implementation ---")
    if CUDF_AVAILABLE:
        start_cudf = time.time()
        
        # 1. Clean blood banks
        clean_banks_df = clean_blood_banks_cudf(banks_path)
        
        # 2. Clean donations
        clean_donations_df = clean_donations_cudf(donations_path)
        
        # 3. Clean donors (Generate synthetic)
        clean_donors_df = generate_synthetic_donors_cudf(clean_banks_df)
        
        # Trigger execution
        _ = len(clean_banks_df)
        _ = len(clean_donations_df)
        _ = len(clean_donors_df)
        
        end_cudf = time.time()
        duration_cudf = end_cudf - start_cudf
        print(f"cuDF execution time: {duration_cudf:.4f} seconds")
        
        speedup = duration_pd / duration_cudf
        print(f"Speedup ratio (Pandas / cuDF): {speedup:.2f}x")
    else:
        print("cuDF/GPU not available. Skipping cuDF timing & speedup ratio.")
        
    print("\n--- Row Count Summary ---")
    print(f"Blood Banks: Before = {raw_banks_count}, After = {len(clean_banks_pd)}")
    print(f"Donations:   Before = {raw_donations_count}, After = {len(clean_donations_pd)}")
    print(f"Donors:      Before = {raw_donors_count} (Text Document), After = {len(clean_donors_pd)} (Generated Synthetic)")


if __name__ == "__main__":
    main()
