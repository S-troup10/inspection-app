import local_database as local
import http.client
import json
import os
from datetime import datetime
import time
import supabase_manager as cloud

QUEUE_FILE = "function_queue.json"

def check_internet():
    """
    Checks if there is an active internet connection.
    """
    try:
        conn = http.client.HTTPConnection("www.google.com", timeout=3)
        conn.request("HEAD", "/")
        conn.close()
        return True
    except:
        return False
    
def initialize_function_queue():
    """
    Ensures the function queue file exists and initializes it if it does not.
    """
    if not os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'w') as f:
            json.dump([], f)

def queue_function(func_name, args=None, kwargs=None):
    """
    Queues a function to be executed when an internet connection is available.

    Args:
        func_name (str): The name of the function (as a string).
        args (list): Positional arguments for the function.
        kwargs (dict): Keyword arguments for the function.
    """
    try:
        initialize_function_queue()
        with open(QUEUE_FILE, 'r+') as f:
            queue = json.load(f)
            request = {
                "func_name": func_name,
                "args": args or [],
                "kwargs": kwargs or {},
                "timestamp": str(datetime.now())
            }
            queue.append(request)
            f.seek(0)
            json.dump(queue, f, indent=4)
        print(f"Function '{func_name}' queued successfully.")
    except Exception as e:
        print(f"Error queuing function: {e}")

###############################################################################
def import_supabase():
    import supabase_manager as cloud


if check_internet():
    import supabase_manager as cloud
else:
    queue_function('import_supabase')


def sync_record_online(table_name, record, unique_identifier="id"):
    """
    Syncs a single record to the online database via provided cloud functions.
    
    Args:
        table_name (str): Name of the Supabase table to sync data with.
        record (dict): The record to sync.
        unique_identifier (str): Column used to uniquely identify the record (default is "id").
    """
    try:
        # Step 1: Check if the record exists in the online database
        existing_record = cloud.get_record(table_name, unique_identifier, record[unique_identifier])

        if not existing_record:
            # Step 2: Record doesn't exist online; insert it
            response = cloud.insert_data(table_name, record)
            if response.get("success"):
                pass
            else:
                print(f"Error adding record to {table_name}: {response.get('error')}")
        else:
            # Step 3: Record exists; compare and update if necessary
            online_last_modified = existing_record.get("last_modified", "")
            local_last_modified = record.get("last_modified", "")

            if online_last_modified < local_last_modified:
                response = cloud.update_record(table_name, record, unique_identifier, record[unique_identifier])
                if response.get("data"):
                    pass
                else:
                    print(f"Error updating record in {table_name}: {response.get('error')}")

    except Exception as e:
        print(f"Error syncing record {record.get(unique_identifier)} in {table_name}: {e}")



def insert(table, data, file=None, resize=(800,800)):
    if data.get('image_url') is not None:
        data['image_url'] = local.process_file(file, resize)
    
    status = local.insert(table, data, file)
    print(status)
    if status:
        queue_function('cloud_insert', [table, data])
   
   
        
def update(table, data, primary_key, id,file=None, resize=None):
    if file:
        data['image_url'] = local.process_file(file, resize)
        
    status = local.update(table, data, [primary_key, id])
    if status:
        queue_function('cloud_update', [table, data, primary_key, id])
        
    
    
    

def download_online():
    # Fetch data from the cloud
    customer_data = cloud.fetch('Customer', "*")
    inspection_header_data = cloud.fetch('Inspection_Header', "*")
    inspection_details_data = cloud.fetch('Inspection_Details', "*")

    # Replace local tables (done once after fetching data)
    local.replace_local_table('Customer', customer_data)
    local.replace_local_table('Inspection_Header', inspection_header_data)
    local.replace_local_table('Inspection_Details', inspection_details_data)

    # Iterate over the LOCAL tables defined in table_config
    for table in table_config:
        # Fetch records for the table
        records = cloud.fetch(table, f'image_url, {table_config.get(table)}')
        
        for record in records:
            # Check if the record has an 'image_url' field
            image_url = record.get('image_url')
            
            if image_url is not None:
                
                #####################################################################################################
                #image = cloud.download(image_url)
                ########################################################################################################
                image = None
                if image is not None:
                    # Assuming 'image' returns the local path where the file is saved
                    local_file_path = image
                    print(local_file_path)
                    # Replace the image URL with the local path in the record
                    record['image_url'] = local_file_path
                    
                    # Prepare the conditions for the update
                    conditions = {table_config.get(table): record[table_config.get(table)]}
                    
                    # Prepare the data for the update (include 'image_url')
                    data = {key: value for key, value in record.items() if key != 'image_url'}
                    data['image_url'] = local_file_path
                    
                    # Update the local database with the updated record
                    local.update(table, data, conditions)
                    
                    print(f"Downloaded and updated image for {table} with ID {record[table_config.get(table)]}")
                else:
                    print(f"Failed to download image for record {record[table_config.get(table)]}")
            
                

    print('Local tables synced with Supabase')






def process_function_queue(function_map):
    """
    Processes all functions in the queue if an internet connection is available.

    Args:
        function_map (dict): A dictionary mapping function names to actual function references.
    """
    if check_internet():
        try:
            initialize_function_queue()
            
            with open(QUEUE_FILE, 'r+') as f:
                queue = json.load(f)
                if not queue:
                    print("Function queue is empty. Nothing to process.")
                    return

                successful_requests = []
                for request in queue:
                    func_name = request.get("func_name")
                    args = request.get("args", [])
                    kwargs = request.get("kwargs", {})

                    # Fetch the function from the map
                    func = function_map.get(func_name)
                    if func:
                        try:
                            print(f"Executing function '{func_name}' with args={args}, kwargs={kwargs}")
                            func(*args, **kwargs)
                            successful_requests.append(request)
                        except Exception as e:
                            print(f"Error executing function '{func_name}': {e}")
                    else:
                        print(f"Function '{func_name}' not found in function map.")

                # Remove successful requests from the queue
                queue = [req for req in queue if req not in successful_requests]
                f.seek(0)
                f.truncate()
                json.dump(queue, f, indent=4)
        except Exception as e:
            print(f"Error processing function queue: {e}")
    else:
        print("No internet connection. Function queue processing postponed.")


def commit():
    if check_internet():
        process_function_queue()
    else:
        print('no internet')

function_map = {
    "cloud_update": cloud.update_record,
    "cloud_insert": cloud.insert_data,
    "download_online": download_online,
    "import_supabase": import_supabase,




}
table_config = {
    "Customer": "customer_id",
    "Inspection_Header": "inspection_id",
    "Inspection_Details": "detail_id"
}



local.initialize_database()
#queue_function('cloud_update', ['Customers', data, 'customer_id', 3])
#queue_function('download_online')

process_function_queue(function_map)
