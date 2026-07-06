"""
Ingests cleaned data directly into BigQuery for BloodIQ.
Supports BigQuery Sandbox (GCS disabled).
"""

import os
import time
import json
import numpy as np
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Exact parameters requested
PROJECT_ID = "bloodiq-501517"
DATASET_ID = "bloodiq_data"
REGION = "asia-south1"


def get_bigquery_client(project_id: str) -> bigquery.Client:
    """
    Returns a BigQuery Client, authenticated via GOOGLE_CREDENTIALS_JSON env var if available,
    otherwise falling back to Application Default Credentials (ADC).

    Parameters:
    project_id (str): Google Cloud Project ID.

    Returns:
    bigquery.Client: Authenticated BigQuery client.
    """
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        try:
            info = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(info)
            return bigquery.Client(project=project_id, credentials=credentials)
        except Exception as e:
            print(f"Warning: Failed to load GOOGLE_CREDENTIALS_JSON: {e}. Falling back to default.")
    return bigquery.Client(project=project_id)


def create_bigquery_dataset(project_id: str, dataset_id: str, region: str) -> None:
    """
    Creates a BigQuery dataset if it does not already exist.

    Parameters:
    project_id (str): Google Cloud Project ID.
    dataset_id (str): BigQuery Dataset ID.
    region (str): Geographic location for the dataset.
    """
    client = get_bigquery_client(project_id)
    dataset_ref = bigquery.DatasetReference(project_id, dataset_id)
    
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset {project_id}.{dataset_id} already exists.")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = region
        dataset = client.create_dataset(dataset, timeout=30)
        print(f"Created dataset {project_id}.{dataset.dataset_id} in location {region}.")


def get_table_schema(table_name: str) -> list:
    """
    Returns the BigQuery Schema definition for the requested tables.

    Parameters:
    table_name (str): Name of the table.

    Returns:
    list: List of SchemaField objects.
    """
    schemas = {
        "bloodiq_banks": [
            bigquery.SchemaField("bank_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("bank_name", "STRING"),
            bigquery.SchemaField("state", "STRING"),
            bigquery.SchemaField("city", "STRING"),
            bigquery.SchemaField("latitude", "FLOAT64"),
            bigquery.SchemaField("longitude", "FLOAT64"),
            bigquery.SchemaField("contact", "STRING"),
            bigquery.SchemaField("capacity", "INT64"),
        ],
        "bloodiq_donations": [
            bigquery.SchemaField("donation_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("bank_id", "STRING"),
            bigquery.SchemaField("blood_type", "STRING"),
            bigquery.SchemaField("donation_date", "DATE"),
            bigquery.SchemaField("units_donated", "INT64"),
            bigquery.SchemaField("donor_id", "STRING"),
        ],
        "bloodiq_donors": [
            bigquery.SchemaField("donor_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("blood_type", "STRING"),
            bigquery.SchemaField("city", "STRING"),
            bigquery.SchemaField("state", "STRING"),
            bigquery.SchemaField("latitude", "FLOAT64"),
            bigquery.SchemaField("longitude", "FLOAT64"),
            bigquery.SchemaField("last_donation_days_ago", "INT64"),
            bigquery.SchemaField("contact", "STRING"),
        ],
        "bloodiq_inventory": [
            bigquery.SchemaField("bank_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("bank_name", "STRING"),
            bigquery.SchemaField("city", "STRING"),
            bigquery.SchemaField("state", "STRING"),
            bigquery.SchemaField("latitude", "FLOAT64"),
            bigquery.SchemaField("longitude", "FLOAT64"),
            bigquery.SchemaField("blood_type", "STRING"),
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("units_available", "INT64"),
            bigquery.SchemaField("units_donated", "INT64"),
            bigquery.SchemaField("units_used", "INT64"),
            bigquery.SchemaField("capacity", "INT64"),
        ]
    }
    return schemas.get(table_name, [])


def create_bigquery_table(client: bigquery.Client, project_id: str, dataset_id: str, table_name: str) -> None:
    """
    Creates a BigQuery table with the designated schema if it does not already exist.

    Parameters:
    client (bigquery.Client): BigQuery Client object.
    project_id (str): Google Cloud Project ID.
    dataset_id (str): BigQuery Dataset ID.
    table_name (str): Table name.
    """
    table_ref = bigquery.TableReference.from_string(f"{project_id}.{dataset_id}.{table_name}")
    schema = get_table_schema(table_name)
    
    try:
        client.get_table(table_ref)
        print(f"Table {table_name} already exists.")
    except Exception:
        table = bigquery.Table(table_ref, schema=schema)
        table = client.create_table(table)
        print(f"Created table {table_name} in BigQuery.")


def prepare_banks_data(local_path: str) -> pd.DataFrame:
    """
    Prepares cleaned blood banks data to match the BigQuery schema.

    Parameters:
    local_path (str): Path to clean_blood_banks.csv

    Returns:
    pd.DataFrame: Formatted DataFrame.
    """
    df = pd.read_csv(local_path)
    
    # Generate capacities using same seed as synthetic generator
    np.random.seed(42)
    bank_ids = df['sr_no'].values
    capacities = np.random.randint(40, 100, size=len(bank_ids))
    bank_capacity_map = dict(zip(bank_ids, capacities))
    
    # Map required schema columns
    prepared = pd.DataFrame()
    prepared['bank_id'] = df['sr_no'].astype(str)
    prepared['bank_name'] = df['blood_bank_name']
    prepared['state'] = df['state']
    prepared['city'] = df['city']
    prepared['latitude'] = df['latitude'].astype(float)
    prepared['longitude'] = df['longitude'].astype(float)
    prepared['contact'] = df['contact_no'].fillna(df['mobile']).fillna('N/A').astype(str)
    prepared['capacity'] = df['sr_no'].map(bank_capacity_map).astype(int)
    
    return prepared


def prepare_donations_data(local_path: str, clean_banks_path: str) -> pd.DataFrame:
    """
    Prepares cleaned donations data to match the BigQuery schema.

    Parameters:
    local_path (str): Path to clean_donations.csv.
    clean_banks_path (str): Path to clean_blood_banks.csv.

    Returns:
    pd.DataFrame: Formatted DataFrame.
    """
    df = pd.read_csv(local_path)
    banks = pd.read_csv(clean_banks_path)
    
    # Build a deterministic mapping from donation center names to bank IDs
    import random
    random.seed(42)
    valid_bank_ids = banks['sr_no'].astype(str).tolist()
    unique_centers = df['donation_center'].unique()
    
    center_to_bank_id = {}
    for center in unique_centers:
        matches = banks[banks['blood_bank_name'].str.contains(str(center), case=False, na=False)]
        if not matches.empty:
            center_to_bank_id[center] = str(matches.iloc[0]['sr_no'])
        else:
            center_to_bank_id[center] = random.choice(valid_bank_ids)
            
    prepared = pd.DataFrame()
    prepared['donation_id'] = [f"DN_{i:06d}" for i in range(len(df))]
    prepared['bank_id'] = df['donation_center'].map(center_to_bank_id).astype(str)
    prepared['blood_type'] = df['blood_group'].astype(str)
    
    # Parse date to YYYY-MM-DD
    parsed_dates = pd.to_datetime(df['last_donation_date'], format='%d-%m-%Y', errors='coerce')
    fallback_date = pd.Timestamp('2023-06-01')
    parsed_dates = parsed_dates.fillna(fallback_date)
    prepared['donation_date'] = parsed_dates.dt.date
    
    prepared['units_donated'] = 1
    prepared['donor_id'] = df['donor_id'].astype(str)
    
    return prepared


def load_dataframe_to_bq(client: bigquery.Client, df: pd.DataFrame, table_name: str) -> None:
    """
    Loads a Pandas DataFrame into a BigQuery table with WRITE_TRUNCATE.

    Parameters:
    client (bigquery.Client): BigQuery client.
    df (pd.DataFrame): Dataframe to load.
    table_name (str): Destination BigQuery table name.
    """
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        schema=get_table_schema(table_name),
        write_disposition="WRITE_TRUNCATE"
    )
    
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Waits for the job to complete.
    print(f"Loaded {len(df)} rows into table {table_id}.")


def print_table_row_counts(client: bigquery.Client) -> None:
    """
    Queries and prints the row counts for the four ingested BigQuery tables.

    Parameters:
    client (bigquery.Client): BigQuery client.
    """
    tables = ["bloodiq_banks", "bloodiq_donations", "bloodiq_donors", "bloodiq_inventory"]
    print("\n--- BigQuery Table Row Counts ---")
    for table_name in tables:
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
        query = f"SELECT COUNT(*) as cnt FROM `{table_ref}`"
        query_job = client.query(query)
        result = query_job.result()
        row_count = next(result).cnt
        print(f"Table '{table_name}': {row_count} rows loaded.")


def main():
    print("=== Step 1: Creating BigQuery Dataset ===")
    create_bigquery_dataset(PROJECT_ID, DATASET_ID, REGION)
    
    bq_client = get_bigquery_client(PROJECT_ID)
    
    print("\n=== Step 2: Creating BigQuery Tables ===")
    tables_to_create = ["bloodiq_banks", "bloodiq_donations", "bloodiq_donors", "bloodiq_inventory"]
    for table in tables_to_create:
        create_bigquery_table(bq_client, PROJECT_ID, DATASET_ID, table)
        
    print("\n=== Step 3: Loading Small Tables directly into BigQuery ===")
    # 3.1: Load blood banks
    print("Preparing and loading blood banks...")
    banks_df = prepare_banks_data("data/clean_blood_banks.csv")
    load_dataframe_to_bq(bq_client, banks_df, "bloodiq_banks")
    
    # 3.2: Load donations
    print("Preparing and loading donations...")
    donations_df = prepare_donations_data("data/clean_donations.csv", "data/clean_blood_banks.csv")
    load_dataframe_to_bq(bq_client, donations_df, "bloodiq_donations")
    
    # 3.3: Load donors
    print("Preparing and loading donors...")
    donors_df = pd.read_csv("data/clean_donors.csv")
    donors_df['donor_id'] = donors_df['donor_id'].astype(str)
    donors_df['blood_type'] = donors_df['blood_type'].astype(str)
    donors_df['city'] = donors_df['city'].astype(str)
    donors_df['state'] = donors_df['state'].astype(str)
    donors_df['contact'] = donors_df['contact'].astype(str)
    load_dataframe_to_bq(bq_client, donors_df, "bloodiq_donors")
    
    print("\n=== Step 4: Loading Big Table (inventory_timeseries.csv) in Chunks ===")
    chunk_size = 100000
    inv_table_id = f"{PROJECT_ID}.{DATASET_ID}.bloodiq_inventory"
    
    rows_loaded = 0
    chunk_count = 0
    first_chunk = True
    
    # Loop over chunks
    for chunk in pd.read_csv("data/inventory_timeseries.csv", chunksize=chunk_size):
        # Format columns to match BQ schema types
        chunk['date'] = pd.to_datetime(chunk['date']).dt.date
        chunk['bank_id'] = chunk['bank_id'].astype(str)
        chunk['bank_name'] = chunk['bank_name'].astype(str)
        chunk['city'] = chunk['city'].astype(str)
        chunk['state'] = chunk['state'].astype(str)
        chunk['blood_type'] = chunk['blood_type'].astype(str)
        
        # Configure job - truncate on first chunk to clear, append on subsequent chunks
        job_config = bigquery.LoadJobConfig(
            schema=get_table_schema("bloodiq_inventory"),
            write_disposition="WRITE_TRUNCATE" if first_chunk else "WRITE_APPEND"
        )
        
        job = bq_client.load_table_from_dataframe(chunk, inv_table_id, job_config=job_config)
        job.result()  # Wait for completion
        
        rows_loaded += len(chunk)
        chunk_count += 1
        first_chunk = False
        
        if chunk_count % 10 == 0:
            print(f"Loaded {rows_loaded:,} / 7,118,960 rows...")
            
    print(f"Finished loading inventory timeseries. Total rows loaded: {rows_loaded:,}")
    
    print("\n=== Step 5: Printing Table Row Counts ===")
    print_table_row_counts(bq_client)


if __name__ == "__main__":
    main()
