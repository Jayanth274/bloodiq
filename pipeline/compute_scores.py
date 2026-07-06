"""
BloodIQ Criticality Scoring and 72-Hour Forecasting Pipeline.
Supports both Pandas and cuDF for GPU acceleration and includes benchmarking.
"""

import os
import time
from datetime import datetime, timezone
import numpy as np
import pandas as pd

# Attempt to import cuDF/RAPIDS for GPU acceleration
try:
    import cudf
    import cupy as cp
    CUDF_AVAILABLE = True
except ImportError:
    CUDF_AVAILABLE = False


def compute_criticality_score(units_available, avg_daily_usage, 
                               days_to_next_camp, capacity):
    """
    Computes the criticality score and severity for a blood bank's blood type.

    Parameters:
    units_available (float): Number of units currently available.
    avg_daily_usage (float): Average daily usage rate of units.
    days_to_next_camp (int): Days remaining until the next blood drive/camp.
    capacity (int): Storage capacity of the blood bank.

    Returns:
    dict: A dictionary containing 'score' (int), 'severity' (str), and 'days_of_supply' (float).
    """
    days_of_supply = units_available / max(avg_daily_usage, 0.1)
    
    # More balanced thresholds adjusted for data limits (max days of supply is ~4.5)
    if days_of_supply >= 2.85:
        base_score = 10   # 2.85+ days supply = safe
    elif days_of_supply >= 0.9:
        base_score = 50   # 0.9 to 2.85 days = low/watch
    else:
        base_score = 80   # under 0.9 days = critical
    
    camp_penalty = min(10, days_to_next_camp * 1.5)
    score = min(100, int(base_score + camp_penalty))
    severity = 'CRITICAL' if score >= 75 else 'LOW' if score >= 40 else 'SAFE'
    return {
        'score': score, 
        'severity': severity, 
        'days_of_supply': round(days_of_supply, 1)
    }


def process_forecasts_pandas(inventory_path):
    """
    Processes blood inventory timeseries and computes scores using Pandas.

    Parameters:
    inventory_path (str): Path to the inventory timeseries CSV.

    Returns:
    pd.DataFrame: Computed forecasts and severity states.
    """
    df = pd.read_csv(inventory_path)
    
    # 1. Compute avg_daily_usage and avg_daily_donation per bank and blood type
    usage_df = df.groupby(['bank_id', 'blood_type'])['units_used'].mean().reset_index()
    usage_df.rename(columns={'units_used': 'avg_daily_usage'}, inplace=True)
    
    donation_df = df.groupby(['bank_id', 'blood_type'])['units_donated'].mean().reset_index()
    donation_df.rename(columns={'units_donated': 'avg_daily_donation'}, inplace=True)
    
    # 2. Get the most recent date row per bank+blood_type
    df_sorted = df.sort_values('date')
    latest_df = df_sorted.drop_duplicates(subset=['bank_id', 'blood_type'], keep='last').copy()
    
    # Merge latest state with average daily usage and donations
    merged = pd.merge(latest_df, usage_df, on=['bank_id', 'blood_type'])
    merged = pd.merge(merged, donation_df, on=['bank_id', 'blood_type'])
    
    # Compute days_to_next_camp deterministically using hash of str(bank_id)
    merged['days_to_next_camp'] = merged['bank_id'].apply(lambda x: (abs(hash(str(x))) % 7) + 1)
    
    current_scores = []
    projected_scores = []
    severities = []
    forecast_severities = []
    days_of_supplies = []
    
    for _, row in merged.iterrows():
        units_avail = row['units_available']
        avg_usage = row['avg_daily_usage']
        avg_donation = row['avg_daily_donation']
        days_camp = row['days_to_next_camp']
        cap = row['capacity']
        
        # Current criticality score
        curr = compute_criticality_score(units_avail, avg_usage, days_camp, cap)
        current_scores.append(curr['score'])
        severities.append(curr['severity'])
        days_of_supplies.append(curr['days_of_supply'])
        
        # Projected 72h criticality score (depletion with donation offset, bounded by 0 and capacity)
        net_change = avg_donation - avg_usage
        proj_units = max(0, min(cap, units_avail + (net_change * 3)))
        
        proj = compute_criticality_score(proj_units, avg_usage, days_camp, cap)
        proj_score = proj['score']
        projected_scores.append(proj_score)
        
        # Forecast severity with FORECAST_ prefix
        if proj_score >= 75:
            f_sev = 'FORECAST_CRITICAL'
        elif proj_score >= 40:
            f_sev = 'FORECAST_LOW'
        else:
            f_sev = 'FORECAST_SAFE'
        forecast_severities.append(f_sev)
        
    merged['current_score'] = current_scores
    merged['projected_score_72h'] = projected_scores
    merged['severity'] = severities
    merged['forecast_severity'] = forecast_severities
    merged['days_of_supply'] = days_of_supplies
    
    return merged


def process_forecasts_cudf(inventory_path):
    """
    Processes blood inventory timeseries and computes scores using cuDF.

    Parameters:
    inventory_path (str): Path to the inventory timeseries CSV.

    Returns:
    cudf.DataFrame: Computed forecasts and severity states.
    """
    df = cudf.read_csv(inventory_path)
    
    # 1. Compute avg_daily_usage and avg_daily_donation per bank and blood type
    usage_df = df.groupby(['bank_id', 'blood_type'])['units_used'].mean().reset_index()
    usage_df.rename(columns={'units_used': 'avg_daily_usage'}, inplace=True)
    
    donation_df = df.groupby(['bank_id', 'blood_type'])['units_donated'].mean().reset_index()
    donation_df.rename(columns={'units_donated': 'avg_daily_donation'}, inplace=True)
    
    # 2. Get the most recent date row per bank+blood_type
    df_sorted = df.sort_values('date')
    latest_df = df_sorted.drop_duplicates(subset=['bank_id', 'blood_type'], keep='last')
    
    # Merge latest state with average daily usage and donations
    merged = latest_df.merge(usage_df, on=['bank_id', 'blood_type'])
    merged = merged.merge(donation_df, on=['bank_id', 'blood_type'])
    
    # Compute days_to_next_camp deterministically using hash of str(bank_id) on host
    bank_ids_pd = merged['bank_id'].to_pandas()
    days_to_next_camp_pd = bank_ids_pd.apply(lambda x: (abs(hash(str(x))) % 7) + 1)
    merged['days_to_next_camp'] = cudf.Series.from_pandas(days_to_next_camp_pd)
    
    # GPU-accelerated Element-wise Calculations
    avg_usage_clipped = merged['avg_daily_usage'].clip(lower=0.1)
    days_of_supply = merged['units_available'] / avg_usage_clipped
    merged['days_of_supply'] = days_of_supply.round(1)
    
    # Conditional base_score assignment matching new thresholds
    base_score = cudf.Series(cp.where(days_of_supply.values >= 2.85, 10,
                             cp.where(days_of_supply.values >= 0.9, 50, 80)))
    
    camp_penalty = (merged['days_to_next_camp'] * 1.5).clip(upper=10)
    score = (base_score + camp_penalty).astype(int).clip(upper=100)
    merged['current_score'] = score
    
    # Current Severity
    cond_critical = merged['current_score'] >= 75
    cond_low = merged['current_score'] >= 40
    severity = cudf.Series(cp.where(cond_critical.values, 'CRITICAL', 
                                    cp.where(cond_low.values, 'LOW', 'SAFE')))
    merged['severity'] = severity
    
    # Projected Score (72 hours forecast with donation offset, bounded by 0 and capacity)
    net_change = merged['avg_daily_donation'] - merged['avg_daily_usage']
    proj_units = (merged['units_available'] + (net_change * 3)).clip(lower=0, upper=merged['capacity'])
    proj_days_of_supply = proj_units / avg_usage_clipped
    
    proj_base_score = cudf.Series(cp.where(proj_days_of_supply.values >= 2.85, 10,
                                  cp.where(proj_days_of_supply.values >= 0.9, 50, 80)))
    proj_score = (proj_base_score + camp_penalty).astype(int).clip(upper=100)
    merged['projected_score_72h'] = proj_score
    
    # Forecast Severity
    proj_cond_critical = merged['projected_score_72h'] >= 75
    proj_cond_low = merged['projected_score_72h'] >= 40
    forecast_severity = cudf.Series(cp.where(proj_cond_critical.values, 'FORECAST_CRITICAL',
                                             cp.where(proj_cond_low.values, 'FORECAST_LOW', 'FORECAST_SAFE')))
    merged['forecast_severity'] = forecast_severity
    
    return merged


def rank_donors_pandas(forecasts_df, donors_path):
    """
    Ranks eligible donors for blood types with critical/forecast-critical banks using Pandas.
    Matches each donor to the closest critical bank of that blood type.

    Parameters:
    forecasts_df (pd.DataFrame): Computed forecasts.
    donors_path (str): Path to clean donors CSV.

    Returns:
    pd.DataFrame: Ranked donors for critical areas.
    """
    donors_df = pd.read_csv(donors_path)
    
    # Identify critical / forecast-critical entries
    crit_banks = forecasts_df[
        (forecasts_df['severity'] == 'CRITICAL') | 
        (forecasts_df['forecast_severity'] == 'FORECAST_CRITICAL')
    ]
    
    critical_blood_types = crit_banks['blood_type'].unique()
    mobilized_records = []
    
    for bt in critical_blood_types:
        bt_banks = crit_banks[crit_banks['blood_type'] == bt]
        bt_donors = donors_df[donors_df['blood_type'] == bt].copy()
        
        if len(bt_banks) == 0 or len(bt_donors) == 0:
            continue
            
        bank_lats = bt_banks['latitude'].values
        bank_lons = bt_banks['longitude'].values
        bank_cities = bt_banks['city'].values
        
        donor_lats = bt_donors['latitude'].values
        donor_lons = bt_donors['longitude'].values
        
        closest_bank_cities = []
        
        # Geographical distance matching (closest critical bank)
        for d_lat, d_lon in zip(donor_lats, donor_lons):
            dists = (bank_lats - d_lat)**2 + (bank_lons - d_lon)**2
            min_idx = dists.argmin()
            closest_bank_cities.append(bank_cities[min_idx])
            
        bt_donors['matched_bank_city'] = closest_bank_cities
        
        # Rank by last donation days ago DESC
        bt_donors_sorted = bt_donors.sort_values(by='last_donation_days_ago', ascending=False)
        bt_donors_sorted['priority_rank'] = range(1, len(bt_donors_sorted) + 1)
        
        mobilized_records.append(bt_donors_sorted)
        
    if len(mobilized_records) == 0:
        return pd.DataFrame(columns=[
            'donor_id', 'blood_type', 'city', 'last_donation_days_ago', 
            'contact', 'matched_bank_city', 'priority_rank'
        ])
        
    result_df = pd.concat(mobilized_records)
    keep_cols = [
        'donor_id', 'blood_type', 'city', 'last_donation_days_ago', 
        'contact', 'matched_bank_city', 'priority_rank'
    ]
    return result_df[keep_cols]


def rank_donors_cudf(forecasts_df, donors_path):
    """
    Ranks eligible donors for blood types with critical/forecast-critical banks using cuDF.
    Matches each donor to the closest critical bank of that blood type.

    Parameters:
    forecasts_df (cudf.DataFrame): Computed forecasts.
    donors_path (str): Path to clean donors CSV.

    Returns:
    cudf.DataFrame: Ranked donors for critical areas.
    """
    donors_df = cudf.read_csv(donors_path)
    
    crit_banks = forecasts_df[
        (forecasts_df['severity'] == 'CRITICAL') | 
        (forecasts_df['forecast_severity'] == 'FORECAST_CRITICAL')
    ]
    
    critical_blood_types = crit_banks['blood_type'].unique().to_arrow().to_pylist()
    mobilized_records = []
    
    for bt in critical_blood_types:
        bt_banks = crit_banks[crit_banks['blood_type'] == bt]
        bt_donors = donors_df[donors_df['blood_type'] == bt].copy()
        
        if len(bt_banks) == 0 or len(bt_donors) == 0:
            continue
            
        bank_lats = cp.array(bt_banks['latitude'].values)
        bank_lons = cp.array(bt_banks['longitude'].values)
        bank_cities = bt_banks['city'].values
        
        donor_lats = cp.array(bt_donors['latitude'].values)
        donor_lons = cp.array(bt_donors['longitude'].values)
        
        # Parallel distance calculation using CuPy
        diff_lat = donor_lats[:, cp.newaxis] - bank_lats[cp.newaxis, :]
        diff_lon = donor_lons[:, cp.newaxis] - bank_lons[cp.newaxis, :]
        dists = diff_lat**2 + diff_lon**2
        
        min_indices = dists.argmin(axis=1)
        
        bt_donors['matched_bank_city'] = bank_cities.iloc[min_indices].values
        
        bt_donors_sorted = bt_donors.sort_values(by='last_donation_days_ago', ascending=False)
        bt_donors_sorted['priority_rank'] = cp.arange(1, len(bt_donors_sorted) + 1)
        
        mobilized_records.append(bt_donors_sorted)
        
    if len(mobilized_records) == 0:
        return cudf.DataFrame(columns=[
            'donor_id', 'blood_type', 'city', 'last_donation_days_ago', 
            'contact', 'matched_bank_city', 'priority_rank'
        ])
        
    result_df = cudf.concat(mobilized_records)
    keep_cols = [
        'donor_id', 'blood_type', 'city', 'last_donation_days_ago', 
        'contact', 'matched_bank_city', 'priority_rank'
    ]
    return result_df[keep_cols]


def main():
    inventory_path = "data/inventory_timeseries.csv"
    donors_path = "data/clean_donors.csv"
    forecasts_out_path = "data/bloodiq_forecasts.csv"
    donors_out_path = "data/mobilized_donors.csv"
    
    print("--- Running Pandas Scoring & Forecast Implementation ---")
    start_pd = time.time()
    
    # 1. Compute forecasts and scores
    forecasts_pd = process_forecasts_pandas(inventory_path)
    
    # Add computed_at timestamp in ISO format (using UTC timezone-aware replacement to avoid warnings)
    computed_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec='seconds')
    forecasts_pd['computed_at'] = computed_at
    
    # Save forecasts results
    cols_to_save = [
        'bank_id', 'bank_name', 'city', 'blood_type', 'current_score',
        'projected_score_72h', 'severity', 'forecast_severity', 'days_of_supply', 'computed_at'
    ]
    forecasts_pd[cols_to_save].to_csv(forecasts_out_path, index=False)
    
    # 2. Rank and match donors
    donors_pd = rank_donors_pandas(forecasts_pd, donors_path)
    donors_pd.to_csv(donors_out_path, index=False)
    
    end_pd = time.time()
    duration_pd = end_pd - start_pd
    print(f"Pandas execution time: {duration_pd:.4f} seconds")
    
    # Print metrics from Pandas run
    total_banks_scored = len(forecasts_pd)
    critical_count = len(forecasts_pd[forecasts_pd['severity'] == 'CRITICAL'])
    forecast_critical_count = len(forecasts_pd[forecasts_pd['forecast_severity'] == 'FORECAST_CRITICAL'])
    
    print("\n--- Summary Metrics ---")
    print(f"Total Banks Scored: {total_banks_scored}")
    print(f"Critical Count: {critical_count}")
    print(f"Forecast Critical Count: {forecast_critical_count}")
    
    print("\n--- Top 3 Mobilized Donors per Blood Type ---")
    if not donors_pd.empty:
        for bt, group in donors_pd.groupby('blood_type'):
            print(f"\nBlood Type: {bt}")
            top_3 = group.sort_values('priority_rank').head(3)
            for _, r in top_3.iterrows():
                print(f"  Rank {r['priority_rank']}: Donor {r['donor_id']} (Last: {r['last_donation_days_ago']} days ago) "
                      f"-> Matched Bank City: {r['matched_bank_city']} (Contact: {r['contact']})")
    else:
        print("No critical or forecast-critical areas identified to mobilize donors.")
        
    print("\n--- Running cuDF Scoring & Forecast Implementation ---")
    if CUDF_AVAILABLE:
        start_cudf = time.time()
        
        # 1. Compute forecasts on GPU
        forecasts_df = process_forecasts_cudf(inventory_path)
        forecasts_df['computed_at'] = computed_at
        
        # 2. Rank donors on GPU
        donors_df = rank_donors_cudf(forecasts_df, donors_path)
        
        # Trigger actual execution
        _ = len(forecasts_df)
        _ = len(donors_df)
        
        end_cudf = time.time()
        duration_cudf = end_cudf - start_cudf
        print(f"cuDF execution time: {duration_cudf:.4f} seconds")
        
        speedup = duration_pd / duration_cudf
        print(f"Speedup ratio (Pandas / cuDF): {speedup:.2f}x")
    else:
        print("cuDF/GPU not available. Skipping cuDF timing & speedup ratio.")


if __name__ == "__main__":
    main()
