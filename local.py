import os
from supabase import create_client, Client

# Set your Supabase credentials here
SUPABASE_URL = 'https://djlpjrhedxzkwudzkcik.supabase.co'
SUPABASE_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqbHBqcmhlZHh6a3d1ZHprY2lrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMjMzNjg3OSwiZXhwIjoyMDQ3OTEyODc5fQ.JX1iDHppSTB2Rijw1s3KHabPfzJPwTefcUvs1yYd8-M'

# Create a Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)
print(supabase)

def insert(table_name, data):
    """
    Inserts a record into the specified table with automatic handling for `customer_id` and `last_modified`.
    """
    try:
        response = supabase.table(table_name).insert(data).execute()
        # Check if insertion is successful
        print(response)
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def update(table_name, data, conditions):
    """
    Updates records in the specified table based on conditions.
    """
    try:
        response = supabase.table(table_name).update(data).match(conditions).execute()
        print(response)
    except Exception as e:
        print(f"An error occurred: {e}")

def fetch(table_name, conditions=None):
    """
    Fetches records from the specified table, optionally filtered by conditions.
    """
    try:
        # Fetch records based on conditions
        if conditions:
            response = supabase.table(table_name).select("*").match(conditions).execute()
        else:
            response = supabase.table(table_name).select("*").execute()

        # Print the entire response object to inspect its structure
        return response.data

        # Check if the request was successful and return the data
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


# Fetch data from the 'Customer' table
customers = fetch('Customer')  # If you want to use an empty condition
print(customers)

