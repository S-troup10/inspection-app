from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, send_file
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
import gc
import io
import openpyxl
from io import BytesIO

# ipad password 431619
def print_memory_usage():
    process = psutil.Process()  # Get the current process
    memory_in_mb = process.memory_info().rss / 1024 ** 2  # Resident Set Size in MB
    print(f"Current memory usage: {memory_in_mb:.2f} MB")

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









from weasyprint import HTML
from PyPDF2 import PdfMerger


from threading import Thread  # For background task

@app.route('/inspection-Print/<int:inspection_id>', methods=['POST'])
def generate_report(inspection_id):
    try:
        if request.method == 'POST':
            # Get form data
            date_issued = request.form.get('date_issued')
            version = request.form.get('version')
            issued_by = request.form.get('issued_by')
            other_version = request.form.get('other_version') if version == 'other' else None

            revisions_data = {
                "inspection_id": inspection_id,
                "date": date_issued,
                "status": other_version if other_version else version,
                "detail": other_version if other_version else version,
                "issued_by": issued_by
            }

            # Insert revisions data into the local database only if necessary
            
            try:
                local.insert('Revisions', revisions_data)
                print("Data inserted successfully.")
            except Exception as e:
                print("Error during insert:", e)

        # Step 1: Fetch all data in one go to minimize database calls
        inspection_header = local.fetch('Inspection_Header', {'inspection_id': inspection_id})
        if not inspection_header:
            return redirect('/select-Inspections')
        inspection_header = inspection_header[0]

        customer_data = local.fetch('Customer', {'customer_id': inspection_header.get('customer_id')})
        if not customer_data:
            return "Customer not found", 404
        customer = customer_data[0]

        
        risk_type = customer.get('risk_type')
        inspection_details_raw = local.fetch('Inspection_Details', {'inspection_id': inspection_id})
        inspection_details = filter_by_time(calculate_risk(inspection_details_raw, risk_type))

        # Step 2: Prepare data for rendering and PDF generation
        logo = 'https://zmusspsqfcmjpqnwkpmx.supabase.co/storage/v1/object/public/images//hv.png'
        report_data = {
            "customer": customer,
            "inspection_header": inspection_header,
            "rows": inspection_details,
            "revisions": local.fetch('Revisions', {'inspection_id': inspection_id}),
            "logo": logo
        }

        total_pages = len(inspection_details) + 2
        pages = [
            render_template('report-title.html', **report_data, num=f'page 1 of {total_pages}'),
            render_template('report-table.html', **report_data, num=f'page 2 of {total_pages}')
        ]

        # Add detailed rows as HTML
        for i, row in enumerate(inspection_details, start=3):
            pages.append(render_template('report-detail.html', row=row, **report_data, num=f'page {i} of {total_pages}'))

        # Step 3: Generate PDF in one pass rather than multiple calls
        pdf_files = []
        for page_html in pages:
            pdf_bytes = HTML(string=page_html).write_pdf(resolution=72)  # Generate PDF from HTML
            pdf_files.append(BytesIO(pdf_bytes))  # Store in memory

        # Step 4: Merge PDFs using PdfMerger
        merged_pdf = PdfMerger()
        for pdf in pdf_files:
            pdf.seek(0)  # Reset buffer before appending
            merged_pdf.append(pdf)

        final_pdf_buffer = BytesIO()
        merged_pdf.write(final_pdf_buffer)
        final_pdf_buffer.seek(0)
        merged_pdf.close()
        print("PDF merged successfully.")

        # Step 5: Generate Excel asynchronously
        excel = generate_excel(inspection_details)

        # Step 6: Send email asynchronously using a background task
        email = request.form.get('email')
        customer_name = customer.get('name')
        final_pdf_bytes = final_pdf_buffer.getvalue()

        # Use threading to send email without blocking the response
        def send_email_task():
            Email.send_Email(final_pdf_bytes, excel, email, customer_name)

        email_thread = Thread(target=send_email_task)
        email_thread.start()

        # Clean up and return response
        del excel, customer
        gc.collect()

        # Return confirmation page after email is sent
        return render_template('report_ready.html', email=email)

    except Exception as e:
        print(f"Error: {e}")
        return redirect('/')







        






def calculate_risk(data, risk_type):
    """
    Calculates a risk rating for each record based on 'probability' and 'consequence'.

    Args:
        data (list): List of dictionaries, each containing 'probability' and 'consequence' keys.

    Returns:
        list: The original list with an added 'risk_rating' key for each record.
    """
    # Updated probability mapping
    probability_map = {
        'a - almost certain': 5,
        'b - likely': 4,
        'c - possible': 3,
        'd - unlikely': 2,
        'e - rare': 1
    }

    # Updated consequence mapping
    consequence_map = {
        '5 - critical': 5,
        '4 - major': 4,
        '3 - moderate': 3,
        '2 - minor': 2,
        '1 - low': 1
    }

    # Function to determine risk rating based on the combined score
    def hv(score):
        if 8 <= score <= 10:
            return 'Extreme'
        elif 6 <= score <= 7:
            return 'High'
        elif score == 5:
            return 'Medium'
        else:
            return 'Low'
            
            
            
            
            

    def nonStrutural(score):
        if score < 7:
            return 'Low Risk'
        if score < 17:
            return 'Medium Risk'
        else:
            return 'High Risk'
        
            
    
    def structural(score):
        if score < 4:
            return 'normal'
        elif score < 11:
            return 'Moderate'
        elif score < 20:
            return 'Abnormal'
        else:
            return 'Critical'
        
        
    # Iterate over each record and calculate the risk rating
    for record in data:
        # Get the numerical values for probability and consequence
        probability_score = probability_map.get(record.get('probability').lower(), 1)
        consequence_score = consequence_map.get(record.get('consequence').lower(), 1)

        # Calculate the combined risk score
        
        
        # Assign the risk rating
        match int(risk_type):
            case 1:
                combined_score = probability_score + consequence_score
                record['risk_rating'] = hv(combined_score)
            case 2:
                combined_score = probability_score * consequence_score
                record['risk_rating'] = nonStrutural(combined_score)
            case 3:
                combined_score = probability_score * consequence_score
                record['risk_rating'] = structural(combined_score)
            
        
                
        
        

    return data

    

def generate_excel(data):
    print_memory_usage()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inspection Details"

    # Include headers, excluding 'display_on_report' and 'inspection_id'
    headers = [key for key in data[0].keys() if key not in ('display_on_report', 'inspection_id', 'last_modified', 'detail_id', 'action_required', )] if data else []

    # Write header row
    for col_num, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header)

    # Write data rows and embed images in the 'image_url' column
    for row_num, row_data in enumerate(data, 2):
        col_offset = 0  # Tracks the column index for each row
        for key in headers:  # Only iterate through headers to ensure excluded columns are skipped
            value = row_data.get(key)

            ws.cell(row=row_num, column=col_offset + 1, value=value)
            col_offset += 1

    # Adjust column widths for better readability
    for col_num in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col_num)].width = 25

    # Save to a BytesIO stream
    output = BytesIO()
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