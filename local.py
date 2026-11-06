import os
import logging
import time
from supabase import create_client, Client
import gc

import tempfile
import base64
import os
# Set your Supabase credentials here
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://zmusspsqfcmjpqnwkpmx.supabase.co')
SUPABASE_API_KEY = os.environ.get('SUPABASE_API_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InptdXNzcHNxZmNtanBxbndrcG14Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTUwNDcwNiwiZXhwIjoyMDU1MDgwNzA2fQ.Fl9y2FJhD09xBadglE9hzv5tFoGCxAU9_hRXZnePDg0')

logger = logging.getLogger("inspection.db")

# Create a Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)


def _with_retry(fn, what, attempts=3):
    """Run fn(), retrying transient failures with exponential backoff."""
    last = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            logger.warning("%s failed (attempt %d/%d): %s", what, i, attempts, e)
            if i < attempts:
                time.sleep(0.5 * 2 ** (i - 1))
    raise last


def insert(table_name, data):
    """Insert a record. Returns True on success, False on failure (logged)."""
    try:
        _with_retry(lambda: supabase.table(table_name).insert(data).execute(),
                    f"insert into {table_name}")
        return True
    except Exception:
        logger.exception("insert into %s failed", table_name)
        return False


def update(table_name, data, conditions):
    """Update matching records. Returns True on success, False on failure (logged)."""
    try:
        _with_retry(lambda: supabase.table(table_name).update(data).match(conditions).execute(),
                    f"update {table_name}")
        return True
    except Exception:
        logger.exception("update of %s failed", table_name)
        return False


_LIGHT_COLUMNS = {
    "Customer": "customer_id, name, site",
    "Inspection_Header": "inspection_id, description, summary, customer_id, date, title",
    "Inspection_Details": "detail_id, inspection_id, area, item, action_required, probability, consequence, time_ranking, unit, observations, recommendations, picture_caption",
}


def fetch(table_name, conditions=None, exclude_image_url=False, raise_on_error=False):
    """
    Fetch records, optionally filtered by conditions (retries transient errors).
    If exclude_image_url is True, the image_url column is excluded.
    On failure returns [] (logged) unless raise_on_error=True, in which case the
    error propagates so callers don't mistake an outage for "no data".
    """
    def _run():
        if exclude_image_url:
            query = supabase.table(table_name).select(_LIGHT_COLUMNS[table_name])
        else:
            query = supabase.table(table_name).select("*")
        if conditions:
            query = query.match(conditions)
        return query.execute().data

    try:
        return _with_retry(_run, f"fetch {table_name}")
    except Exception:
        logger.exception("fetch from %s failed", table_name)
        if raise_on_error:
            raise
        return []


def storage_put(path, data, content_type, bucket="report"):
    """Upload bytes (overwriting). Raises on failure."""
    _with_retry(lambda: supabase.storage.from_(bucket).upload(
        path, data, {"content-type": content_type, "upsert": "true"}),
        f"upload {path}")
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


def storage_get(path, bucket="report"):
    """Download bytes. Raises on failure."""
    return _with_retry(lambda: supabase.storage.from_(bucket).download(path),
                       f"download {path}")


def db_healthy():
    try:
        supabase.table("Customer").select("customer_id").limit(1).execute()
        return True
    except Exception as e:
        logger.error("DB health check failed: %s", e)
        return False


def upload_pdf_to_supabase(data: bytes, file_path: str, content_type: str = "application/pdf") -> str:
    """
    Upload bytes to the 'report' bucket and return the public URL,
    or an error string (not starting with http) if the upload fails.
    """
    try:
        url = storage_put(file_path, data, content_type)
        logger.info("Uploaded %s (%d bytes)", file_path, len(data))
        return url
    except Exception as e:
        logger.exception("Error uploading %s", file_path)
        return f"Error uploading file: {e}"


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
