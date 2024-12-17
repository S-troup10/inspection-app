from supabase import Client, create_client
import local_database as Local

SUPABASE_URL = "https://djlpjrhedxzkwudzkcik.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqbHBqcmhlZHh6a3d1ZHprY2lrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzIzMzY4NzksImV4cCI6MjA0NzkxMjg3OX0.wmGcSM-OMFc0fHH0clkImlnJ1Rahg2MHRQSnJZssMW0"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Signing in (Ensure that the credentials are valid)
supabase.auth.sign_in_with_password({
    "email": "simontroup27@gmail.com",
    "password": "rexjoeycat21"
})

print('supabase : ' + str(supabase))

def sync(table_name, primary_key='id'):
    """
    Synchronizes the given table between the local and cloud databases.

    Args:
        table_name (str): Name of the table to sync.
        primary_key (str): The primary key column name. Defaults to 'id'.
    """
    try:
        # Fetch all cloud and local records
        cloud_records = supabase.table(table_name).select('*').execute().data
        local_records = Local.fetch(table_name)
    except Exception as e:
        print(f"Error fetching data from table {table_name}: {e}")
        return

    # Create mappings for faster lookups
    cloud_records_map = {record[primary_key]: record for record in cloud_records}
    local_records_map = {record[primary_key]: record for record in local_records}

    # Sync from local to cloud
    for local_record in local_records:
        local_record_id = local_record[primary_key]
        local_last_modified = local_record.get('last_modified') or 0  # Use 0 if None
        cloud_record = cloud_records_map.get(local_record_id)

        if cloud_record:
            cloud_last_modified = cloud_record.get('last_modified') or 0  # Use 0 if None
            if local_last_modified > cloud_last_modified:
                try:
                    supabase.table(table_name).update(local_record).eq(primary_key, local_record_id).execute()
                    print(f"Updated cloud {table_name} record with {primary_key}={local_record_id}")
                except Exception as e:
                    print(f"Error updating cloud {table_name} record: {e}")
            elif cloud_last_modified > local_last_modified:
                try:
                    Local.update(table_name, cloud_record, {primary_key:local_record_id})
                    print(f"Updated local {table_name} record with {primary_key}={local_record_id}")
                except Exception as e:
                    print(f"Error updating local {table_name} record: {e}")
        else:
            try:
                # Handle image upload if the record contains an image
                if local_record.get('image_url'):
                    image_path = local_record['image_url']
                    try:
                        with open(image_path, 'rb') as file:
                            file_content = file.read()
                            filename = image_path.split('/')[-1]
                            storage_path = f"uploads/{filename}"
                            upload_response = supabase.storage.from_('photos').upload(storage_path, file_content, {"upsert": True})
                            print(f"Uploaded image successfully: {upload_response}")
                            local_record['image_url'] = f"{SUPABASE_URL}/storage/v1/object/public/photos/{storage_path}"
                    except FileNotFoundError:
                        print(f"Error: File {image_path} not found.")
                    except Exception as e:
                        print(f"Error uploading image {image_path}: {e}")
                local_record.pop(primary_key)
                supabase.table(table_name).insert(local_record).execute()
                print(f"Inserted cloud {table_name} record with {primary_key}={local_record_id}")
            except Exception as e:
                print(f"Error inserting cloud {table_name} record: {e}")

    # Sync from cloud to local
    for cloud_record in cloud_records:
        cloud_record_id = cloud_record[primary_key]
        cloud_last_modified = cloud_record.get('last_modified') or 0  # Use 0 if None
        local_record = local_records_map.get(cloud_record_id)

        if not local_record:
            try:
                # Handle image download if the cloud record contains an image
                if cloud_record.get('image_url'):
                    image_url = cloud_record['image_url']
                    filename = image_url.split('/')[-1]  # Extract the filename from URL
                    
                    # Attempt to download the file from Supabase storage
                    file_response = supabase.storage.from_('photos').download(f"uploads/{filename}")
                    
                    # Define the local file path where you want to save the file
                    local_filepath = f'./static/cache/{table_name}_{cloud_record_id}_{filename}'
                    
                    # Ensure the file_response contains content
                    if file_response and hasattr(file_response, 'content'):
                        # Write the file to the local cache
                        with open(local_filepath, 'wb') as f:
                            f.write(file_response.content)
                        print(f"Image downloaded and saved to {local_filepath}")
                        
                        # Update the record with the relative path
                        cloud_record['image_url'] = local_filepath
                    else:
                        raise Exception(f"Failed to download image: {image_url}")
                
                # Insert the record into the local database
                cloud_record.pop(primary_key)
                Local.insert(table_name, **cloud_record)
                print(f"Inserted local {table_name} record with {primary_key}={cloud_record_id}")
            except Exception as e:
                print(f"Error downloading or inserting local record: {e}")

        elif cloud_last_modified > (local_record.get('last_modified') or 0):
            try:
                Local.update(table_name, cloud_record, {primary_key:cloud_record_id})
                print(f"Updated local {table_name} record with {primary_key}={cloud_record_id}")
            except Exception as e:
                print(f"Error updating local {table_name} record: {e}")

# Call the sync function for each table
sync('Customer', 'customer_id')
print('done')
