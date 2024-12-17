import sqlite3
import os
from PIL import Image
db_name = 'local_data.db'



def process_file(file):

    try:
        

        # Create local directory if it doesn't exist
        local_folder = './static/cache/'
        os.makedirs(local_folder, exist_ok=True)

        # Save the resized image locally
        local_file_path = os.path.join(local_folder, file.filename)
        print(file.save(local_file_path))
        
        return local_file_path

    except Exception as e:
        print(f"Error in process_file: {e}")
        return None





def initialize_database(db_name=db_name):
    """
    Initializes a SQLite database with tables: Inspection_Header, Inspection_Details, and Customer.
    Adds a last_modified column to each table for tracking updates.
    If the tables already exist, it does nothing.
    """
    try:
        # Connect to SQLite database (or create it if it doesn't exist)
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Create the Inspection_Header table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Customer (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                site TEXT,
                image_url TEXT DEFAULT NULL,
                last_modified TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Inspection_Header (
                inspection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                summary TEXT,
                customer_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                image_url TEXT DEFAULT NULL,
                title TEXT,
                last_modified TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
            )
        ''')

        
        
        # Create the Inspection_Details table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Inspection_Details (
                detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id INTEGER NOT NULL,
                area TEXT,
                item TEXT,
                action_required TEXT,
                probability INTEGER,
                consequence INTEGER,
                time_ranking INTEGER,
                unit TEXT,
                observations TEXT,
                recommendations TEXT,
                picture_caption TEXT,
                display_on_report BOOLEAN,
                image_url TEXT DEFAULT NULL,
                last_modified TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inspection_id) REFERENCES Inspection_Header(inspection_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id INTEGER NOT NULL,
                date DATE NOT NULL,
                status TEXT,
                detail TEXT,
                issued_by TEXT,             
                FOREIGN KEY (inspection_id) REFERENCES Inspection_Header(inspection_id)
            )
        ''')



        # Commit the changes and close the connection
        conn.commit()
        print("Database initialized successfully.")
    
    except sqlite3.Error as e:
        print(f"An error occurred while initializing the database: {e}")
    
    finally:
        if conn:
            conn.close()




def get_column_names(table_name, db_name=db_name):
    """
    Fetches the column names for a given table in the SQLite database.

    Args:
        db_path (str): Path to the SQLite database.
        table_name (str): Name of the table.

    Returns:
        list: A list of column names.
    """
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Execute PRAGMA statement to retrieve table info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()

        # Extract column names from the result
        column_names = [column[1] for column in columns_info]

        return column_names
    except sqlite3.Error as e:
        print(f"Error fetching column names for table '{table_name}': {e}")
        return []
    finally:
        if conn:
            conn.close()



def replace_local_table(table_name, online_data):
    """
    Replace a local table with data from an online source.
    """
    # Connect to the local database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Drop the local table if it exists
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    # Create the table structure dynamically from online data
    # Assuming `online_data` is a list of dictionaries
    if online_data:
        # Extract column names from the first entry
        columns = online_data[0].keys()
        columns_def = ", ".join([f"{col} TEXT" for col in columns])  # Assuming all fields are TEXT for simplicity
        
        # Create the new table
        cursor.execute(f"CREATE TABLE {table_name} ({columns_def})")
        
        # Insert the data
        for row in online_data:
            placeholders = ", ".join("?" for _ in row)
            values = tuple(row.values())
            cursor.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", values)
    
    # Commit and close the connection
    conn.commit()
    conn.close()




def fetch_all_data():
     # Step 1: Connect to the local SQLite database
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row  # Enable dictionary-like cursor
        cursor = conn.cursor()
        
        # Step 2: Fetch local data
        local_data = {}
        for table_name in ["Customer", "Inspection_Header", "Inspection_Details"]:
            cursor.execute(f"SELECT * FROM {table_name}")
            local_data[table_name] = cursor.fetchall()
        
        close(conn)
        return local_data






def execute_sql(query, parameters=None):
    conn = None
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        if parameters:
            cursor.execute(query, parameters)
        else:
            cursor.execute(query)

        if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("PRAGMA"):
            rows = cursor.fetchall()
            return rows if rows else []  # Always return a list
        else:
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        # Return an empty list for SELECT queries or PRAGMA
        if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("PRAGMA"):
            return []
        return False  # Return False for non-SELECT queries
    finally:
        if conn:
            conn.close()





def insert(table_name, data, file=None):
    """
    Inserts a record into the specified table with automatic handling for `customer_id` and `last_modified`.

    Args:
        table_name (str): The name of the table.
        data (dict): A dictionary where keys are column names and values are the data to insert.
        file (str, optional): The file path for the image to be processed (default is None).
        resize (tuple, optional): The dimensions for resizing the image (default is (800, 800)).

    Returns:
        bool: True if the insert was successful, otherwise False.
    """
    if file:
        local_path = process_file(file)
        data['image_url'] = local_path

    # Build the query dynamically
    columns = ', '.join(data.keys())
    placeholders = ', '.join('?' for _ in data.values())
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    # Debugging output
    print(f"Query: {query}")
    print(f"Values: {tuple(data.values())}")

    return execute_sql(query, tuple(data.values()))

    
    
    

    
    
    
    
    
def update(table_name, data, conditions):
    """
    Updates records in the specified table based on conditions.

    Args:
        table_name (str): The name of the table.
        data (dict): A dictionary where keys are column names and values are the new data.
        conditions (dict): A dictionary where keys are column names and values are the conditions for the update.

    Returns:
        None
    """
    # Safely quote table and column names to avoid conflicts with reserved keywords
    table_name = f'"{table_name}"'
    set_clause = ', '.join(f'"{key}" = ?' for key in data.keys())
    condition_clause = ' AND '.join(f'"{key}" = ?' for key in conditions.keys())

    # Prepare the full SQL query
    query = f"UPDATE {table_name} SET {set_clause} WHERE {condition_clause}"

    # Combine values from data and conditions to pass as parameters for the query
    parameters = tuple(data.values()) + tuple(conditions.values())

    # Execute the query using the execute_sql function
    try:
        execute_sql(query, parameters)
        print(f"Updated records in {table_name} where {condition_clause}")
    except Exception as e:
        print(f"Error updating records in {table_name}: {e}")







def fetch(table_name, conditions=None):
    """
    Fetches records from the specified table, optionally filtered by conditions.

    Args:
        table_name (str): The name of the table.
        conditions (dict, optional): A dictionary where keys are column names and values are the conditions.

    Returns:
        list of dicts: A list of dictionaries where keys are column names and values are the data in that row.
    """
    # Start by fetching the rows from the database
    if conditions:
        condition_clause = ' AND '.join(f"{key} = ?" for key in conditions.keys())
        query = f"SELECT * FROM {table_name} WHERE {condition_clause}"
        rows = execute_sql(query, tuple(conditions.values()))
    else:
        query = f"SELECT * FROM {table_name}"
        rows = execute_sql(query)
    
    # If no rows are returned, return an empty list
    if not rows:
        return []
    
    # Fetch column names from the table's schema
    column_names = [description[1] for description in execute_sql(f"PRAGMA table_info({table_name})")]

    # Convert each row into a dictionary
    result = []
    for row in rows:
        row_dict = {column_names[i]: row[i] for i in range(len(row))}
        result.append(row_dict)

    return result













def close(conn):
    conn.close()
    print('connection to local database closed')
    
    
    
    
    
    
    
    
    
initialize_database(db_name) 
    
    
    
def resize_image(image_file, size=(800, 800)):
    """
    Resizes an image to the specified dimensions while maintaining aspect ratio.

    Args:
        image_file (FileStorage): The image file object.
        size (tuple): Desired size as (width, height).
    """
    try:
        img = Image.open(image_file)
        img_resized = img.resize(size)
        return img_resized

    except Exception as e:
        print(f"Error resizing image: {e}")
        return None