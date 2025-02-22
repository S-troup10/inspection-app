import os
from supabase import create_client, Client
import gc

import tempfile
import base64
import os
# Set your Supabase credentials here
SUPABASE_URL = 'https://zmusspsqfcmjpqnwkpmx.supabase.co'
SUPABASE_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InptdXNzcHNxZmNtanBxbndrcG14Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTUwNDcwNiwiZXhwIjoyMDU1MDgwNzA2fQ.Fl9y2FJhD09xBadglE9hzv5tFoGCxAU9_hRXZnePDg0'

# Create a Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)


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

def fetch(table_name, conditions=None, exclude_image_url=False):
    """
    Fetches records from the specified table, optionally filtered by conditions.
    If exclude_image_url is True, the image_url column will be excluded.
    """
    try:
        # Construct the select query
        
        if exclude_image_url:
            
            columns_to_select = {
            "Customer": "customer_id, name, site",
            "Inspection_Header": "inspection_id, description, summary, customer_id, date, title",
            "Inspection_Details": "detail_id, inspection_id, area, item, action_required, probability, consequence, time_ranking, unit, observations, recommendations, picture_caption",
        }
            query = supabase.table(table_name).select(columns_to_select[table_name])
            
        else:
            query = supabase.table(table_name).select("*")
        
        # Apply conditions if provided
        if conditions:
            query = query.match(conditions)
        
        response = query.execute()
        
        # Return only the data part of the response
        return response.data

    except Exception as e:
        print(f"An error occurred: {e}")
        return []






def upload_pdf_to_supabase(pdf_bytes: bytes, file_path: str) -> str:
    """
    Upload the given PDF to Supabase storage and return the public URL.

    Args:
        pdf_bytes (bytes): The PDF content in bytes.
        file_path (str): The path where the PDF should be stored in Supabase storage.

    Returns:
        str: The public URL of the uploaded PDF, or an error message if upload fails.
    """
    try:
        # Create a temporary file with a .pdf extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_bytes)
            temp_path = tmp_file.name  # Store path before closing

        # Upload the file to Supabase Storage
        with open(temp_path, 'rb') as file:
            response = supabase.storage.from_("report").upload(file_path, file, {"content-type": "application/pdf"})
            print(response)
        # Remove the temporary file after upload
        os.remove(temp_path)

        # Check response using correct attributes
        if hasattr(response, 'error') and response.error:
            print(f"Failed to upload PDF to Supabase: {response.error}")
            return f"Failed to upload PDF: {response.error}"

        # Get the public URL of the uploaded PDF
        pdf_url = supabase.storage.from_("report").get_public_url(file_path)
        print(f"PDF uploaded successfully to Supabase. URL: {pdf_url}")
        return pdf_url

    except Exception as e:
        print(f"Error uploading PDF to Supabase: {e}")
        return f"Error uploading PDF: {str(e)}"







BUCKET_NAME = "images"

def save_image_to_supabase(image_base64: str, file_name: str):
    """
    Converts a base64 image string to an image file and uploads it to Supabase Storage.

    Args:
        image_base64 (str): Base64 encoded image.
        file_name (str): The desired filename for storage.

    Returns:
        str: Public URL of the uploaded image.
    """
    try:
        if image_base64.startswith('data:image'):
            image_base64 = image_base64.split(',')[1]
        image_data = base64.b64decode(image_base64)

        # Create a temporary file to save the image
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            tmp_file.write(image_data)
            tmp_file_path = tmp_file.name  # Temporary file path

        # Upload the image to Supabase Storage
        with open(tmp_file_path, 'rb') as file:
            file_path = f"{file_name}.jpg"  # Define the file name and extension
            supabase.storage.from_(BUCKET_NAME).upload(file_path, file, file_options={"content-type": "image/jpeg"})

        # Generate the public URL
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_path}"

        return public_url

    except Exception as e:
        print(f"Error uploading image: {e}")
        return None

def do_this():
        for row in fetch('Inspection_Header'):
            image_url = row.get('image_url')
            picture_caption = row.get('title')
            
            # Assuming image_url is base64 encoded, and we're replacing it with the public URL
            new_image_url = save_image_to_supabase(image_url, picture_caption)
            print(new_image_url)
            if new_image_url:
                # Replace the image_url field in your database with the new public URL
                res = supabase.table('Inspection_Header').update({"image_url": new_image_url}).eq("inspection_id", row.get("inspection_id")).execute()
                print(res)
