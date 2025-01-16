from flask import Flask, render_template, request, redirect, flash, url_for, send_file, send_from_directory, jsonify
import os
import weasyprint
import local_database as local

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
    customers = local.fetch("Customer")
    
    return render_template('customer.html', customers=customers)

@app.route('/customer-Edit/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
   
        # Fetch customer data by ID
        response = local.fetch('Customer', {'customer_id': customer_id})
        
        customer_data = response if response else None
        
        customer_data = customer_data[0]

        if not customer_data:
            flash('customer not found')
            return redirect('/customer')

        if request.method == 'POST':
            # Handle form submission to update customer data
            name = request.form.get('name')
            site = request.form.get('site')
            
            update_data = {'customer_id': customer_id, 'name': name, 'site': site}

            picture = request.files.get('picture')

            if picture and picture.filename:
                print('user uploaded a file')
                update_data['image_url'] = picture
                
            
            
            local.update('Customer', update_data, {'customer_id': customer_id})
            print(update_data)
            
        
            flash('customesr edited sucsessfully', 'sucsess')
            return redirect('/customer')  # Redirect back to customer view page
        # Render the edit page with preloaded data
        
        return render_template('customerEdit.html', customer=customer_data)

@app.route("/upload-Customer", methods=["POST"])
def add_customer():
    try:
        
        is_picture = 'logo' in request.files and request.files['logo'].filename != ''
        logo = request.files['logo'] if is_picture else None
        name = request.form.get('name')
        site = request.form.get('site')

        if not name or not site:
            flash("Name and site are required fields.", "danger")
            return redirect(url_for('add_Customer_Page'))

        data = {'name': name, 'site': site}
        
        response = local.insert('Customer', data, logo)

        if response:
            flash("Customer added successfully!", "success")
        else:
            flash("Failed to add customer. Please try again later.", "danger")

        return redirect(url_for('view_customers'))

    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('add_Customer_Page'))







@app.route('/inspection-Details/<int:inspection_id>', methods=['GET'])
def inspection_details(inspection_id):
    # Fetch inspections filtered by the inspection_id
    inspections = local.fetch('Inspection_Details', {'inspection_id': inspection_id})
    
    # Ensure inspections is a list even if a single item is returned
    if inspections is None:
        inspections = []
    return render_template('inspectionDetails.html', inspections=inspections, inspection_id=inspection_id)

@app.route('/inspectionDetails-Add/<int:inspection_id>')
def inspection_detail_add(inspection_id):
    return render_template('/inspectionDetailAdd.html', inspection_id=inspection_id)

@app.route("/upload-InspectionDetail/<int:inspection_id>", methods=["POST"])
def upload_inspection_detail(inspection_id):
    try:
        try:
            pic = request.files['picture']
        except: 
            pic = None
        print(f'pic : {pic}')
        # Retrieve form data
        inspection_data = {
            'inspection_id': inspection_id,
            'area': request.form.get('area'),
            'item': request.form.get('item'),
            'action_Required': request.form.get('action_required'),
            'probability': request.form.get('probability'),
            'consequence': request.form.get('consequence'),
            'time_Ranking': request.form.get('time_ranking'),
            'unit': request.form.get('unit'),
            'observations': request.form.get('observations'),
            'recommendations': request.form.get('recommendations'),
            'picture_Caption': request.form.get('picture_caption'),
            'display_On_Report': request.form.get('display_on_Report')
        }

        # Insert data into the database
        
        response = local.insert(
            table_name='Inspection_Details',
            data=inspection_data,
            file=pic,
        )

        # Validate response
        print(f"Insert data response: {response}")
        if response:
            flash("Inspection details uploaded successfully!", "success")
            return redirect(f'/inspection-Details/{inspection_id}')
        else:
            
            
            flash(f"Failed to save inspection details")
            return redirect(f'/inspection-Details/{inspection_id}')

    except Exception as e:
        print(f"Error: {e}")
        flash(f"An error occurred: {e}", "error")
        return redirect(f'/inspection-Details/{inspection_id}')



@app.route('/inspectionDetail-Edit/<int:detail_id>', methods=['GET', 'POST'])
def edit_inspection_detail(detail_id):
    # Fetch inspection data by ID
    response = local.fetch('Inspection_Details', {'detail_id': detail_id})  # Assuming response is a dict
    
    inspection_id = response[0].get('inspection_id')
    
    # Check if the response contains the required data
    if not response:
        flash('no inspection found')

    inspection_data = response[0]  # Access the first record in the 'data' list

    if request.method == 'POST':
        # Handle form submission to update inspection data
        
        area = request.form.get('area')
        item = request.form.get('item')
        action_required = request.form.get('action_required')
        probability = request.form.get('probability')
        consequence = request.form.get('consequence')
        time_ranking = request.form.get('time_Ranking')
        unit = request.form.get('unit')
        observations = request.form.get('observations')
        recommendations = request.form.get('recommendations')
        picture_caption = request.form.get('picture_Caption')
        display_on_report = request.form.get('display_On_Report')

        # Prepare data for update
        update_data = {
            'area': area,
            'inspection_id' : inspection_id,
            'item': item,
            'action_Required': action_required,
            'probability': probability,
            'consequence': consequence,
            'time_Ranking': time_ranking,
            'unit': unit,
            'observations': observations,
            'recommendations': recommendations,
            'picture_Caption': picture_caption,
            
            'display_On_Report': display_on_report,
        }
        picture = request.files.get('picture')

        if picture and picture.filename:
            update_data['image_url'] = picture

        # Update the inspection record
        local.update('Inspection_Details', update_data, {'detail_id':detail_id})
        flash('data inserted sucsessfuly')
        return redirect(f'/inspection-Details/{inspection_id}')  # Redirect to the customer view page

    # Render the edit page with preloaded data
    return render_template('inspectionDetailEdit.html', inspection=inspection_data)













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


@app.route('/inspection-Edit/<int:inspection_id>', methods=['GET', 'POST'])
def edit_inspection(inspection_id):
    # Fetch inspection data
    response = local.fetch('Inspection_Header', {'inspection_id': inspection_id})
    if not response:
        flash('Inspection not found', 'error')
        return redirect('/inspections')

    inspection_data = response[0]
    print(inspection_data)
    # Fetch customers for the dropdown
    customers = local.fetch('Customer')

    if request.method == 'POST':
        
        description = request.form.get('description')
        summary = request.form.get('summary')
        customer_id = request.form.get('customer')
        date = request.form.get('date')
        title = request.form.get('title')

        update_data = {
            'description': description,
            'summary': summary,
            'customer_id': customer_id,
            'date': date,
            'title' : title
        }
        picture = request.files.get('picture')

        if picture and picture.filename:
            print('user uploaded a file')
            update_data['image_url'] = picture

        local.update('Inspection_Header', update_data, {'inspection_id': inspection_id})
        flash('Inspection updated successfully!', 'success')
        return redirect('/inspections')

    return render_template('inspectionsEdit.html', inspection=inspection_data, customers=customers)



@app.route('/select-Inspections', methods=['GET', 'POST'])
def select_inspections():
    customers = local.fetch('Customer')
    inspection_headers = None
    selected_customer_id = None
    
    customers_with_inspections = []
    
    for customer in customers:
        #check if it has an inspection associated with it
        inpection_count = local.fetch('Inspection_Header', {'customer_id': customer.get('customer_id')})
       
        if len(inpection_count) > 0 :
            customers_with_inspections.append(customer)
            
    

    if request.method == 'POST':
        selected_customer_id = request.form.get('customer')
        
        if selected_customer_id:
            
            inspection_headers = local.fetch('Inspection_Header', {'customer_id': selected_customer_id})
            
            
            
            
            filtered_inspections = []
            for inspection in inspection_headers:
                count = len(local.fetch('Inspection_Details', {'inspection_id': inspection.get('inspection_id')}))
                
                if count > 0:  
                    inspection['details_count'] = count
                    filtered_inspections.append(inspection)
            
            # Update inspection headers with filtered list
            inspection_headers = filtered_inspections
                
        
    return render_template(
        '/selectPrint.html',
        customers=customers_with_inspections,
        inspection_data=inspection_headers,
        selected_customer_id=selected_customer_id,
       # Pass the flag to the template
    )






@app.route('/revisions')
def revisions():
    revisions = local.fetch('Revisions')
    return render_template('revisions.html', revisions=revisions)

@app.route('/revisions-Add')
def add_revisions():
    inspections = local.fetch('Inspection_Header')
    return render_template('revisionsAdd.html', inspections=inspections)







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
            print('Revisions Data:', revisions_data)

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
            flash(f"Inspection header not found for ID: {inspection_id}")
            return redirect('/select-Inspections')
        inspection_header = inspection_header[0]

        # Fetch customer data
        customer_data = local.fetch('Customer', {'customer_id': inspection_header.get('customer_id')})
        if not customer_data:
            flash(f"Customer not found for ID: {inspection_header.get('customer_id')}")
            return "Customer not found", 404
        customer = customer_data[0]

        # Fetch and sort inspection details
        inspection_details = local.fetch('Inspection_Details', {'inspection_id': inspection_id})
        #inspection_details.sort(key=lambda x: x.get('time_ranking', 0))

        # Update image URLs
        logo = 'hv.png'
        logo = url_for('static', filename=f'images/{logo.replace("./static/images/", "")}', _external=True)
        css = url_for('static', filename=f'css/reportStyle.css', _external=True)

        for row in inspection_details:
            if row.get("image_url"):
                row["image_url"] = url_for('static', filename=f'cache/{row["image_url"].replace("./static/cache/", "")}', _external=True)
        
        if customer.get("image_url"):
            customer["image_url"] = url_for('static', filename=f'cache/{customer["image_url"].replace("./static/cache/", "")}', _external=True)

        if inspection_header.get("image_url"):
            inspection_header["image_url"] = url_for('static', filename=f'cache/{inspection_header["image_url"].replace("./static/cache/", "")}', _external=True)

        # Prepare report data
        report_data = {
            "customer": customer,
            "inspection_header": inspection_header,
            "rows": inspection_details,
            "total_pages": 2 + len(inspection_details),
            "logo": logo,
            "css": css,
            "revisions": revisions  # Use the fetched revisions here
        }

        # Generate and return the PDF
        html_content = render_template('report.html', **report_data)
        pdf = weasyprint.HTML(string=html_content).write_pdf()
        #pdf_stream = io.BytesIO(pdf)
        # Display the PDF inline in the browser
        pdf_filename = f'inspection_report_{inspection_id}.pdf'
        pdf_filepath = os.path.join('./static/pdf/', pdf_filename)
        os.makedirs(os.path.dirname(pdf_filepath), exist_ok=True)
        with open(pdf_filepath, 'wb') as pdf_file:
            pdf_file.write(pdf)

        # Flash a message with the download link
        pdf_url = url_for('static', filename=f'pdf/{pdf_filename}', _external=True)
        flash(f"Report generated successfully. <a href='{pdf_url}' target='_blank'>Download the PDF</a>", 'success')
        return redirect('/')

    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect('/')

@app.route('/static/templates/<template_name>')
def serve_template(template_name):
    print('this was used')
    try:
        # Render the template when requested
        return render_template(template_name)
    except:
        return "Template not found", 404


if __name__ == '__main__':
    app.run(debug=True)
