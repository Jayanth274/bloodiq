"""
Synthetic data generator for BloodIQ.
Generates daily blood inventory timeseries for all valid blood banks.
"""

import os
import time
import numpy as np
import pandas as pd

# Try to import cuDF/RAPIDS for GPU acceleration
try:
    import cudf
    import cupy as cp
    CUDF_AVAILABLE = True
except ImportError:
    CUDF_AVAILABLE = False


def load_and_filter_banks_pandas(filepath: str) -> pd.DataFrame:
    """
    Load blood banks CSV and filter by valid Indian geographical coordinates using Pandas.

    Parameters:
    filepath (str): Path to the input CSV file.

    Returns:
    pd.DataFrame: Filtered DataFrame containing valid blood banks.
    """
    df = pd.read_csv(filepath, encoding='latin-1')
    df.columns = df.columns.str.strip()
    # Filter coordinates
    df = df[(df['Latitude'] >= 8.0) & (df['Latitude'] <= 37.0) &
            (df['Longitude'] >= 68.0) & (df['Longitude'] <= 97.0)]
    return df


def load_and_filter_banks_cudf(filepath: str) -> 'cudf.DataFrame':
    """
    Load blood banks CSV and filter by valid Indian geographical coordinates using cuDF.

    Parameters:
    filepath (str): Path to the input CSV file.

    Returns:
    cudf.DataFrame: Filtered DataFrame containing valid blood banks.
    """
    df = cudf.read_csv(filepath, encoding='latin-1')
    df.columns = df.columns.str.strip()
    # Filter coordinates
    df = df[(df['Latitude'] >= 8.0) & (df['Latitude'] <= 37.0) &
            (df['Longitude'] >= 68.0) & (df['Longitude'] <= 97.0)]
    return df


def generate_inventory_pandas(banks_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates synthetic daily inventory timeseries data for the year 2023 using Pandas.

    Parameters:
    banks_df (pd.DataFrame): DataFrame of filtered blood banks.

    Returns:
    pd.DataFrame: Synthetic inventory timeseries DataFrame.
    """
    # Define parameters
    blood_types = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
    dates = pd.date_range(start='2023-01-01', end='2023-12-31')
    
    # Pre-calculate capacity for each bank
    np.random.seed(42)
    bank_ids = banks_df['Sr No'].values
    capacities = np.random.randint(40, 100, size=len(bank_ids))
    bank_capacity_map = dict(zip(bank_ids, capacities))
    
    # Build the Cartesian product: Banks x Dates x Blood Types
    # To do this efficiently, repeat coordinates and bank details
    num_banks = len(banks_df)
    num_dates = len(dates)
    num_types = len(blood_types)
    total_rows = num_banks * num_dates * num_types
    
    # Repeat bank information
    # Repeats each bank's row (num_dates * num_types) times
    banks_repeated = banks_df.loc[banks_df.index.repeat(num_dates * num_types)].copy()
    
    # Repeat dates
    # For each bank, we want all dates, each repeated num_types times
    date_tile = np.tile(np.repeat(dates, num_types), num_banks)
    banks_repeated['date'] = date_tile
    
    # Repeat blood types
    # For each date, we want all blood types
    type_tile = np.tile(blood_types, num_banks * num_dates)
    banks_repeated['blood_type'] = type_tile
    
    # Rename columns to match requested schema
    banks_repeated = banks_repeated.rename(columns={
        'Sr No': 'bank_id',
        'Blood Bank Name': 'bank_name',
        'State': 'state',
        'City': 'city',
        'Latitude': 'latitude',
        'Longitude': 'longitude'
    })
    
    # Retain only required columns plus temporary ones
    keep_cols = ['bank_id', 'bank_name', 'state', 'city', 'latitude', 'longitude', 'date', 'blood_type']
    banks_repeated = banks_repeated[keep_cols]
    
    # Map capacity
    banks_repeated['capacity'] = banks_repeated['bank_id'].map(bank_capacity_map)
    
    # Generate random fields
    # Generate base units_available, units_donated, and units_used
    base_available = np.random.randint(0, 50, size=total_rows)
    banks_repeated['units_donated'] = np.random.randint(0, 15, size=total_rows)
    banks_repeated['units_used'] = np.random.randint(0, 20, size=total_rows)
    
    # Apply weekly pattern to units_available
    # Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
    day_of_week = banks_repeated['date'].dt.dayofweek.values
    multipliers = np.ones(total_rows)
    multipliers[day_of_week == 0] = 0.7  # Monday
    multipliers[day_of_week == 4] = 0.9  # Friday
    multipliers[(day_of_week == 5) | (day_of_week == 6)] = 0.8  # Saturday & Sunday
    
    banks_repeated['units_available'] = (base_available * multipliers).astype(int)
    
    # Final column ordering
    final_cols = [
        'bank_id', 'bank_name', 'state', 'city', 'latitude', 'longitude',
        'blood_type', 'date', 'units_available', 'units_donated', 'units_used', 'capacity'
    ]
    return banks_repeated[final_cols]


def generate_inventory_cudf(banks_df: 'cudf.DataFrame') -> 'cudf.DataFrame':
    """
    Generates synthetic daily inventory timeseries data for the year 2023 using cuDF.

    Parameters:
    banks_df (cudf.DataFrame): DataFrame of filtered blood banks.

    Returns:
    cudf.DataFrame: Synthetic inventory timeseries DataFrame.
    """
    # Define parameters
    blood_types = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
    dates = pd.date_range(start='2023-01-01', end='2023-12-31')
    
    num_banks = len(banks_df)
    num_dates = len(dates)
    num_types = len(blood_types)
    total_rows = num_banks * num_dates * num_types
    
    # Use CuPy for accelerated random generations
    cp.random.seed(42)
    
    # Pre-calculate capacity for each bank
    bank_ids = banks_df['Sr No'].values
    capacities = cp.random.randint(40, 100, size=num_banks)
    capacity_df = cudf.DataFrame({'Sr No': bank_ids, 'capacity': capacities})
    
    # Create Cartesian Product in cuDF
    # For cuDF, we can merge with cross joins or construct indices
    dates_df = cudf.DataFrame({'date': dates})
    types_df = cudf.DataFrame({'blood_type': blood_types})
    
    # Cross join: banks X dates
    banks_df['temp_key'] = 1
    dates_df['temp_key'] = 1
    cross_banks_dates = banks_df.merge(dates_df, on='temp_key')
    
    # Cross join: (banks x dates) X types
    cross_banks_dates['temp_key'] = 1
    types_df['temp_key'] = 1
    final_df = cross_banks_dates.merge(types_df, on='temp_key')
    
    # Drop temp key
    final_df = final_df.drop(columns=['temp_key'])
    
    # Merge with capacities
    final_df = final_df.merge(capacity_df, on='Sr No')
    
    # Rename columns to match requested schema
    final_df = final_df.rename(columns={
        'Sr No': 'bank_id',
        'Blood Bank Name': 'bank_name',
        'State': 'state',
        'City': 'city',
        'Latitude': 'latitude',
        'Longitude': 'longitude'
    })
    
    # Generate random variables using CuPy
    base_available = cp.random.randint(0, 50, size=total_rows)
    final_df['units_donated'] = cp.random.randint(0, 15, size=total_rows)
    final_df['units_used'] = cp.random.randint(0, 20, size=total_rows)
    
    # Day of week multiplier logic in cuDF
    day_of_week = final_df['date'].dt.dayofweek
    
    # Apply weekly pattern
    multipliers = cp.ones(total_rows)
    
    # Convert day_of_week to CuPy array or use cuDF masking
    day_of_week_arr = day_of_week.to_cupy()
    multipliers[day_of_week_arr == 0] = 0.7
    multipliers[day_of_week_arr == 4] = 0.9
    multipliers[(day_of_week_arr == 5) | (day_of_week_arr == 6)] = 0.8
    
    final_df['units_available'] = (base_available * multipliers).astype(cp.int32)
    
    # Final column ordering
    final_cols = [
        'bank_id', 'bank_name', 'state', 'city', 'latitude', 'longitude',
        'blood_type', 'date', 'units_available', 'units_donated', 'units_used', 'capacity'
    ]
    return final_df[final_cols]


def main():
    input_file = "data/blood-banks.csv"
    output_file = "data/inventory_timeseries.csv"
    
    print("--- Running Pandas Implementation ---")
    start_pd = time.time()
    
    # 1. Load and filter banks
    filtered_banks_pd = load_and_filter_banks_pandas(input_file)
    valid_count_pd = len(filtered_banks_pd)
    print(f"Pandas: Count of valid banks after filtering: {valid_count_pd}")
    
    # 2. Generate timeseries
    inventory_pd = generate_inventory_pandas(filtered_banks_pd)
    end_pd = time.time()
    duration_pd = end_pd - start_pd
    print(f"Pandas execution time: {duration_pd:.4f} seconds")
    
    # Save the pandas output as the source of truth
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    inventory_pd.to_csv(output_file, index=False)
    
    # Get statistics
    total_rows = len(inventory_pd)
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    
    print("\n--- Running cuDF Implementation ---")
    if CUDF_AVAILABLE:
        start_cudf = time.time()
        filtered_banks_df = load_and_filter_banks_cudf(input_file)
        valid_count_df = len(filtered_banks_df)
        print(f"cuDF: Count of valid banks after filtering: {valid_count_df}")
        
        inventory_df = generate_inventory_cudf(filtered_banks_df)
        # Trigger computation
        _ = len(inventory_df)
        end_cudf = time.time()
        duration_cudf = end_cudf - start_cudf
        print(f"cuDF execution time: {duration_cudf:.4f} seconds")
        
        speedup = duration_pd / duration_cudf
        print(f"Speedup ratio (Pandas / cuDF): {speedup:.2f}x")
    else:
        duration_cudf = None
        print("cuDF/GPU not available. Skipping cuDF timing & speedup ratio.")
        
    print("\n--- Summary Statistics ---")
    print(f"Total rows generated: {total_rows}")
    print(f"File size of output: {file_size_mb:.2f} MB")
    print(f"Time taken to generate and save (Pandas): {duration_pd:.4f} seconds")


if __name__ == "__main__":
    main()
