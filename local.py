import os
from supabase import create_client, Client

# Set your Supabase credentials here
SUPABASE_URL = 'https://zmusspsqfcmjpqnwkpmx.supabase.co'
SUPABASE_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InptdXNzcHNxZmNtanBxbndrcG14Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk1MDQ3MDYsImV4cCI6MjA1NTA4MDcwNn0.UmhLQEUxj424-2TbVOYrt_c5y5WFC5RWNmRaiMaj0nA'

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
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def update(table_name, data, conditions):
    """
    Updates records in the specified table based on conditions.
    """
    try:
        response = supabase.table(table_name).update(data).match(conditions).execute()
        
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




