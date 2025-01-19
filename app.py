from flask import Flask, render_template, request, redirect, flash, url_for, send_file, send_from_directory, jsonify
import os
import weasyprint
import local_database as local
import gunicorn
import base64
import urllib.parse



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


#html routes
@app.route("/<path:filename>")
def serve_file(filename):
    
    return send_from_directory(os.path.join(app.root_path, 'templates'), filename)





@app.route('/sync/<table_name>', methods=['GET'])
def sync_customer(table_name):
    table = local.fetch(table_name)
    for record in table:
        if record.get("image_url"):
            try:
                with open(record['image_url'], 'rb') as file:
                        # Read the file content
                    file_content = file.read()
                        
                        # Encode the content to Base64
                    encoded_content = base64.b64encode(file_content)
                        
                        # Convert bytes to string
                    record['image_url'] = encoded_content.decode('utf-8')  # Store Base64 as a string

                    
            except Exception as e:
                print(f"Error reading or encoding image for record {record.get('customer_id')}: {e}")
    return jsonify(table)



@app.route('/sync/process', methods=['POST'])
def sync_process():
    try:
        # Parse the incoming JSON data
        data = request.json

        if not data:
            return jsonify({"error": "No data received."}), 400

        for table_name, records in data.items():
            print(f"Processing {len(records)} records for table: {table_name}")

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
    inspection_header = local.fetch("Inspection_Header")

    for dictionary in inspection_header:
        # Fetch customer details based on customer_id from the inspection header
        customer = local.fetch('Customer', {'customer_id': dictionary['customer_id']})

        # Check if customer data exists (i.e., not an empty list)
        if customer:
            # Assuming customer[0] contains the dictionary for the first matching customer
            dictionary.update({'name': customer[0]['name']})
        else:
            dictionary.update({'name': 'Unknown Customer'})

    # Debugging to verify updates
    print(inspection_header)
    return render_template('inspections.html', inspections=inspection_header)

@app.route('/inspection-Add')
def Inspection_add():
    #pass a table of all the customers to display the name of the customers in the form
    customers = local.fetch('Customer')
    
    return render_template('/inspectionsAdd.html', customers=customers)


@app.route('/inspections/edit', methods=['GET', 'POST'])
def edit_inspection():
    
    # Fetch customers for the dropdown
    

    return render_template('inspectionsEdit.html')



@app.route('/select-Inspections', methods=['GET', 'POST'])
def select_inspections():
    # Handle GET request (render the page)
    # Fetch all inspection headers
    inspections = local.fetch('Inspection_Header')

    # Fetch customer details and map customer_id to customer name
    customers = local.fetch('Customer')
    customer_map = {customer['customer_id']: customer['name'] for customer in customers}

    # Add customer name to each inspection
    filtered_inspections = []
    for inspection in inspections:
        details_count = len(local.fetch('Inspection_Details', {'inspection_id': inspection.get('inspection_id')}))
        if details_count > 0:
            inspection['details_count'] = details_count
            filtered_inspections.append(inspection)
        inspection['customer_name'] = customer_map.get(inspection['customer_id'], 'Unknown')

    # Pass inspections to the template
    return render_template('selectPrint.html', inspections=filtered_inspections)





@app.route('/inspection-Print/<int:inspection_id>', methods=['POST'])
def generate_report(inspection_id):
    print("Function generate_report called with method:", request.method)

    try:
        if request.method == 'POST':
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
            

            # Insert revisions data into the local database
            try:
                local.insert('Revisions', revisions_data)
                print("Data inserted successfully.")
            except Exception as e:
                print("Error during insert:", e)

            # Fetch revisions after inserting new revision
            revisions = local.fetch('Revisions', {'inspection_id': inspection_id})

        # Fetch revisions regardless of POST
        revisions = local.fetch('Revisions', {'inspection_id': inspection_id})

        # Fetch inspection header
        inspection_header = local.fetch('Inspection_Header', {'inspection_id': inspection_id})
        if not inspection_header:
            
            return redirect('/select-Inspections')
        inspection_header = inspection_header[0]

        # Fetch customer data
        customer_data = local.fetch('Customer', {'customer_id': inspection_header.get('customer_id')})
        if not customer_data:
            
            return "Customer not found", 404
        customer = customer_data[0]

        # Fetch and sort inspection details
        inspection_details = local.fetch('Inspection_Details', {'inspection_id': inspection_id})
        
        
        logo_filename = 'hv.png'
        base_url = request.host_url  
        logo_path = f"{base_url}static/images/{logo_filename}"


        # Prepare report data
        report_data = {
            "customer": customer,
            "inspection_header": inspection_header,
            "rows": inspection_details,
            "revisions": revisions,  # Use the fetched revisions here
            "logo": logo_path  # Full path to logo
        }

        # Generate and return the PDF
        html_content = render_template('report.html', **report_data)
        pdf = weasyprint.HTML(string=html_content).write_pdf()

        # Save the PDF to the server
        
        return serve_pdf_dynamically(pdf)
        
    except Exception as e:
        
        return redirect('/')

@app.route('/static/templates/<template_name>')
def serve_template(template_name):
    print('this was used')
    try:
        # Render the template when requested
        return render_template(template_name)
    except:
        return "Template not found", 404






from flask import make_response

# Serve the PDF dynamically
def serve_pdf_dynamically(pdf):
    # Create a Flask response object with the PDF content
    response = make_response(pdf)
    
    # Set headers for the response to indicate a file download
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=inspection_report.pdf'

    
    return response

if __name__ == '__main__':
    app.run(debug=True)


