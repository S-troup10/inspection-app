
from supabase import create_client, Client
import os




try:
    SUPABASE_URL = "https://djlpjrhedxzkwudzkcik.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqbHBqcmhlZHh6a3d1ZHprY2lrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzIzMzY4NzksImV4cCI6MjA0NzkxMjg3OX0.wmGcSM-OMFc0fHH0clkImlnJ1Rahg2MHRQSnJZssMW0"
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase.auth.sign_in_with_password({
        "email": "simontroup27@gmail.com",
        "password": "rexjoeycat21"})
    print("Supabase client initialized successfully.")
except Exception as e:
    print(f"Error initializing Supabase client: {e}")


    
def fetch_table_data():
    try:
        customer_table = fetch('Customer', '*')
        inspection_header_table = fetch('Inspection_Header', '*')
        inspection_detail_table = fetch('Inspection_Detail', '*')
    except Exception as e:
        print(f"Error fetching data from: {e}")
        return [customer_table, inspection_header_table, inspection_detail_table]
   
   
   
    
def insert_data(table_name, data):
    """
    Inserts data into a specified Supabase table. If a file is provided, uploads it to Supabase Storage
    and adds its public URL to the data.

    Args:
        table_name (str): Name of the Supabase table to insert into.
        data (dict): Data to be inserted into the table.
        

    Returns:
        dict: Response from the Supabase insert operation or error message.
    """
    print('running supabase inert')
    response = None  # Initialize response

    try:
        if data.get('image_url') is not None:
            local_path = data.get('image_url')
            supabase_path = Upload_photo(local_path)
        
            #sawp local and cloud paths
            data['image_url'] = supabase_path
    
       
       
    
        response = supabase.table(table_name).insert(data).execute()
        print(response)
        return {"success": True, "data": response}
    except Exception as e:
        print(f"Error inserting data: {e}")
        return {"success": False, "error": str(e)}





def fetch(table_name, select, id=None, column=None):
    try:
        if id is None:    
        # Fetch customer data from the database
            response = supabase.table(table_name).select(select).execute()
            customers = response.data if response.data else []  # Handle empty result
            return customers
        else:
            response = supabase.table(table_name).select("*").eq(column, id).execute()
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []


def download(url: str):
    """
    Downloads a file from Supabase Storage.

    Args:
        url (str): The URL pointing to the file in Supabase Storage.
    
    Returns:
        str: The local file path where the downloaded file is saved.
    """
    try:
        # Base marker to identify the path of the object in Supabase storage
        base_marker = "storage/v1/object/public/photos/"

        
        # Extract the file path from the URL
        filename_with_path = url.split(base_marker, 1)[-1].split("?", 1)[0]
    # Get only the filename, which is the last part after the last '/'
        filename = filename_with_path.split('/')[-1]
        
        # Download the file from Supabase storage
        res = supabase.storage.from_('photos').download(filename_with_path)
        
        # Check if the download was successful (i.e., bytes content is returned)
        if isinstance(res, bytes):
            
            local_file_path = os.path.join("static/cache/", filename)
            
            # Create the necessary directories if they don't exist
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            # Save the downloaded file locally
            with open(local_file_path, 'wb') as f:
                f.write(res)
            
            print(f"File downloaded successfully: {local_file_path}")
            return local_file_path
        else:
            print("Failed to download the file: Response is not byte data.")
            return None
    
    except Exception as e:
        print(f"Error downloading the file: {e}")
        return None



def get_record(table, unique_identifier, id):
    response = supabase.table(table).select('*').eq(unique_identifier, id).execute()
    if response.data:
        return response.data[0]  # Return the first record if found
    return None  # Return None if no matching record

def update_record(table_name, update_data, unique_identifier, id):
    if update_data.get('image_url'):
        update_data['image_url'] = Upload_photo(update_data.get('image_url'))
    return supabase.table(table_name).update(update_data).eq(unique_identifier, id).execute()

def Upload_photo(local_path):
    try:
        
        file_name = os.path.basename(local_path)
        file_storage_path = f"/{file_name}"

            # Check if the file already exists in the folder
        existing_files = supabase.storage.from_('photos').list('/')
        print(existing_files)
        if any(file['name'] == file_name for file in existing_files):
                # File already exists, get its public URL
            file_url = supabase.storage.from_('photos').get_public_url(file_storage_path)
            return file_url

            # Upload the file to Supabase
        with open(local_path, 'rb') as f:
            supabase.storage.from_('photos').upload(file_storage_path, f)

            # Get public URL for the file
        file_url = supabase.storage.from_('photos').get_public_url(file_storage_path)
        return file_url
    except Exception as e:
        return {"error file not uploaded": str(e)}
