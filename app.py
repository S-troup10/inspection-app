from flask import Flask, render_template, request, redirect, send_from_directory, jsonify
from PIL import Image
import weasyprint
import local as local
import gunicorn
import base64
import urllib.parse
import openpyxl
from openpyxl.utils import get_column_letter
from PyPDF2 import PdfReader, PdfWriter
from openpyxl.drawing.image import Image as ExcelImage
import tempfile

import io
import openpyxl


# ipad password 431619


app = Flask(__name__)
app.secret_key = 'ddd'

app.config['UPLOAD_FOLDER'] = './static/cache'
app.config['MAX_CONTENT_LENGTH'] = 100 * 3000 * 3000  # 100 MB limit
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}



#service worker setup
@app.after_request
def add_security_headers(response):
    
    if request.path == '/static/js/service-worker.js':
        response.headers['Service-Worker-Allowed'] = '/'
    return response


@app.route('/sync/<table_name>', methods=['GET'])
def sync_customer(table_name):
    table = local.fetch(table_name)
    
    return jsonify(table)



@app.route('/sync/process', methods=['POST'])
def sync_process():
    try:
        # Parse the incoming JSON data
        data = request.json

        if not data:
            return jsonify({"error": "No data received."}), 400

        for table_name, records in data.items():
            

            # Iterate through the records and upsert them into the local database
            for record in records:
                if 'image_url' in record and record['image_url']:
                    record['image_url'] = urllib.parse.unquote(record['image_url'])
                try:
                    # Check if the record exists based on the primary key
                    primary_key = None

                    # Define primary keys for each table
                    primary_keys = {
                        "Customer": "customer_id",
                        "Inspection_Header": "inspection_id",
                        "Inspection_Details": "detail_id"
                    }

                    if table_name in primary_keys:
                        primary_key = primary_keys[table_name]

                    if primary_key and primary_key in record:
                        existing_record_list = local.fetch(table_name, {primary_key: record[primary_key]})
                        existing_record = existing_record_list

                        if existing_record:
                            
                            # Update the record if it exists
                            local.update(table_name, record, {primary_key: record[primary_key]})
                        else:
                            # Insert the record if it does not exist
                            
                            local.insert(table_name, record)
                    else:
                        
                        # Insert the record if no primary key is provided
                        local.insert(table_name, record)

                except Exception as e:
                    print(f"Error processing record for table {table_name}: {e}")

        return jsonify({"status": "success", "message": "Data synchronized successfully."}), 200

    except Exception as e:
        print(f"Error in sync_process: {e}")
        return jsonify({"error": "An error occurred during synchronization.", "details": str(e)}), 500




















# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/customer-Add')
def add_Customer_Page():
    return render_template('customerAdd.html')

@app.route('/customer')
def view_customers():
    return render_template('customer.html')

@app.route('/customer/edit', methods=['GET', 'POST'])
def edit_customer():
        return render_template('customerEdit.html')





@app.route('/inspection-Details', methods=['GET'])
def inspection_details():
    return render_template('inspectionDetails.html')


@app.route('/inspectionDetails-Add', methods=['GET', 'POST'])
def inspection_detail_add():
    # The frontend ensures inspection_id is passed correctly
    inspection_id = request.args.get('inspection_id')
    return render_template('/inspectionDetailAdd.html', inspection_id=inspection_id)




@app.route('/inspection-Details/edit', methods=['GET', 'POST'])
def edit_inspection_detail():
    
    # Render the edit page with preloaded data
    return render_template('inspectionDetailEdit.html')













@app.route('/inspections')
def inspection_summary():
 

   

    return render_template('inspections.html')

@app.route('/inspection-Add')
def Inspection_add():
    #pass a table of all the customers to display the name of the customers in the form
    customers = local.fetch('Customer', exclude_image_url=True)
    
    return render_template('/inspectionsAdd.html', customers=customers)


@app.route('/inspections/edit', methods=['GET', 'POST'])
def edit_inspection():
    
    # Fetch customers for the dropdown
    

    return render_template('inspectionsEdit.html')



@app.route('/select-Inspections', methods=['GET', 'POST'])
def select_inspections():
    # Handle GET request (render the page)
    # Fetch all inspection headers
    inspections = local.fetch('Inspection_Header', exclude_image_url=True)

    # Fetch customer details and map customer_id to customer name
    customers = local.fetch('Customer', exclude_image_url=True)
    customer_map = {customer['customer_id']: customer['name'] for customer in customers}

    # Add customer name to each inspection
    filtered_inspections = []
    for inspection in inspections:
        details_count = len(local.fetch('Inspection_Details', {'inspection_id': inspection.get('inspection_id')}, exclude_image_url=True))
        if details_count > 0:
            inspection['details_count'] = details_count
            filtered_inspections.append(inspection)
        inspection['customer_name'] = customer_map.get(inspection['customer_id'], 'Unknown')

    # Pass inspections to the template
    return render_template('selectPrint.html', inspections=filtered_inspections)



import Email

import gc
import tempfile

@app.route('/inspection-Print/<int:inspection_id>', methods=['POST'])
def generate_report(inspection_id):
    try:
        # Step 1: Fetch inspection data
        inspection_header = local.fetch('Inspection_Header', {'inspection_id': inspection_id})
        if not inspection_header:
            return redirect('/select-Inspections')
        inspection_header = inspection_header[0]

        customer_data = local.fetch('Customer', {'customer_id': inspection_header.get('customer_id')})
        if not customer_data:
            return "Customer not found", 404
        customer = customer_data[0]
        
        # Free memory after fetching and processing data
        del customer_data
        gc.collect()

        # Step 2: Process inspection details in smaller chunks
        inspection_details_raw = local.fetch('Inspection_Details', {'inspection_id': inspection_id})
        inspection_details = filter_by_time(calculate_risk(inspection_details_raw))
        
        # Free memory after processing
        del inspection_details_raw
        gc.collect()

        # Step 3: Prepare logo (small, quick operation)
        with open(f'static/images/hv.png', 'rb') as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        logo = f"data:image/png;base64,{logo_base64}"
        
        # Free memory after preparing logo
        del logo_base64
        gc.collect()

        # Step 4: Generate HTML for PDF
        report_data = {
            "customer": customer,
            "inspection_header": inspection_header,
            "rows": inspection_details,
            "revisions": local.fetch('Revisions', {'inspection_id': inspection_id}),
            "logo": logo
        }
        
        html_content = render_template('report.html', **report_data)
        del report_data
        gc.collect()

        # Step 5: Generate and Optimize PDF
        raw_pdf = weasyprint.HTML(string=html_content).write_pdf()
        pdf = remove_last_page(raw_pdf)
        
        del raw_pdf, html_content
        gc.collect()

        # Step 6: Generate Excel
        excel = generate_excel(inspection_details)
        del inspection_details
        gc.collect()
        
        # Step 7: Send email and delete large files
        email = request.form.get('email')
        customer_name = customer.get('name')
        Email.send_Email(pdf, excel, email, customer_name)
        
        del pdf, excel, customer
        gc.collect()
        print_memory_usage()
        return render_template('report_ready.html', email=email)

    except Exception as e:
        print(f"Error: {e}")
        return redirect('/')





def calculate_risk(data):
    """
    Calculates a risk rating for each record based on 'probability' and 'consequence'.
    
    Args:
        data (list): List of dictionaries, each containing 'probability' and 'consequence' keys.
    
    Returns:
        list: The original list with an added 'risk_rating' key for each record.
    """
    # Map for converting string values to numerical scores
    probability_map = {
        'Almost Certain': 5,
        'Likely': 4,
        'Possible': 3,
        'Unlikely': 2,
        'Very Rare': 1
    }

    consequence_map = {
        'Critical': 5,
        'Major': 4,
        'Moderate': 3,
        'Minor': 2,
        'Low': 1
    }
    
    # Function to determine risk rating based on the combined score
    def get_risk_rating(score):
        if 8 <= score <= 10:
            return 'Extreme'
        elif 6 <= score <= 7:
            return 'High'
        elif score == 5:
            return 'Medium'
        else:
            return 'Low'
    
    # Iterate over each record and calculate the risk rating
    for record in data:
        # Get the numerical values for probability and consequence
        probability_score = probability_map.get(record.get('probability'), 1)
        consequence_score = consequence_map.get(record.get('consequence'), 1)
        
        # Calculate the combined risk score
        combined_score = probability_score + consequence_score
        print(get_risk_rating(combined_score))
        # Assign the risk rating
        record['risk_rating'] = get_risk_rating(combined_score)
        
    
    return data




def remove_last_page(pdf):
    print_memory_usage()
    reader = PdfReader(io.BytesIO(pdf))
    writer = PdfWriter()
    total_pages = len(reader.pages)

    # Add all pages except the last one to the writer
    for i in range(total_pages - 1):
        writer.add_page(reader.pages[i])

    # Write the new PDF to a bytes object
    output_pdf = io.BytesIO()
    writer.write(output_pdf)
    output_pdf.seek(0)  # Move the pointer to the beginning of the bytes object

    return output_pdf.getvalue()
    

def generate_excel(data):
    print_memory_usage()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inspection Details"

    # Include headers, excluding 'display_on_report' and 'inspection_id'
    headers = [key for key in data[0].keys() if key not in ('display_on_report', 'inspection_id', 'last_modified')] if data else []

    # Write header row
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)

    # Write data rows and embed images in the 'image_url' column
    for row_num, row_data in enumerate(data, 2):
        col_offset = 0  # Tracks the column index for each row
        for key in headers:  # Only iterate through headers to ensure excluded columns are skipped
            value = row_data.get(key)
            if key == 'image_url' and value and value.startswith("data:image"):
                try:
                    base64_str = value.split(',')[1]
                    image_data = base64.b64decode(base64_str)

                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_image:
                        temp_image.write(image_data)
                        temp_image_path = temp_image.name

                        # Handle WebP or MPO conversion to PNG if necessary
                        if 'webp' in value or 'mpo' in value:
                            with Image.open(temp_image_path) as img:
                                temp_png = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                                img = img.convert("RGBA")
                                
                                # Rotate for MPO images
                                if 'mpo' in value:
                                    img = img.rotate(180, expand=True)
                                
                                img.save(temp_png.name, format="PNG")
                                temp_image_path = temp_png.name


                    # Embed the image in the 'image_url' column
                    img = ExcelImage(temp_image_path)
                    img.height = 150  # Adjust the height for better visibility
                    img.width = 175   # Adjust the width for better visibility
                    img_cell = get_column_letter(col_offset + 1) + str(row_num)
                    ws.add_image(img, img_cell)

                    # Adjust the row height to fit the image
                    ws.row_dimensions[row_num].height = 100
                except Exception as e:
                    pass
            else:
                # Write other data columns
                ws.cell(row=row_num, column=col_offset + 1, value=value)
            col_offset += 1

    # Adjust column widths for better readability
    for col_num in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col_num)].width = 25

    # Save to a BytesIO stream
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return output


def filter_by_time(data):
    """
    Sorts a list of dictionaries by the 'time_ranking' key based on a custom ranking order.

    Args:
        data (list): List of dictionaries with a 'time_ranking' key.

    Returns:
        list: The sorted list of dictionaries.
    """
    # Define the custom ranking order
    ranking_order = [
        'Immediate', 
        'Under 1 month', 
        'Under 3 months', 
        'Under 6 months', 
        'Under 12 months', 
        'Under 18 months', 
        'Over 18 months'
    ]

    # Create a lookup dictionary for the ranking order
    ranking_map = {value: index for index, value in enumerate(ranking_order)}

    # Sort the data using the ranking order
    sorted_data = sorted(data, key=lambda x: ranking_map.get(x['time_ranking'], float('inf')))

    return sorted_data

    
import psutil

def print_memory_usage():
    process = psutil.Process()  # Get the current process
    memory_in_mb = process.memory_info().rss / 1024 ** 2  # Resident Set Size in MB
    print(f"Current memory usage: {memory_in_mb:.2f} MB")


if __name__ == '__main__':
    app.run()