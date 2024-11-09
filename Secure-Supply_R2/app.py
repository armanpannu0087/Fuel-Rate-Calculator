from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import pandas as pd
import dash
from dash import html
from dash import dcc
# import cdata as mod
import pymongo
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
from bs4 import BeautifulSoup
import requests
import time
import os
import fitz
from PIL import Image
import pytesseract
from pymongo import MongoClient
from datetime import datetime
import csv
import boto3
import datetime
from bson import json_util




app = Flask(__name__)
dash_app = dash.Dash(__name__, server=app, url_base_pathname="/app/")
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["InvoiceDB"]
products = db["products"]
suppliers = db["suppliers"]
invoices = db["invoices"]
customers = db["customers"]
suppliers_data = list(suppliers.find({}))
supplier_names = [item['name'] for item in suppliers_data]
invoice_data = list(invoices.find({}))
data = list(products.find({}))
invoice_id = [item['invoice_number'] for item in invoice_data]
items = [item['item_code'] for item in data]
unique_items = set(items)
price = [item['unit_price'] for item in data]
ALLOWED_EXTENSIONS = {'pdf', 'jpeg', 'jpg'} 
fig = go.Figure()
fig.add_trace(go.Bar(x=items, y=price))
pytesseract.pytesseract.tesseract_cmd = 'C:\Program Files\Tesseract-OCR\\tesseract.exe'
app.config['UPLOAD_FOLDER'] = 'uploads'

dash_app.layout = html.Div([
    # html.Label("Select a supplier to display:"),
    # dcc.Dropdown(
    #     id="supplier-dropdown",
    #     options=[{'label': item, 'value': item} for item in supplier_names],
    #     multi=True,
    #     value=items  # Pre-select all items initially
    # ),
    # html.Label("Select invoices to display:"),
    # dcc.Dropdown(
    #     id="invoice-dropdown",
    #     options=[{'label': item, 'value': item} for item in invoice_id],
    #     multi=True,
    #     value=items  # Pre-select all items initially
    # ),
    # html.Label("Select items to display:"),
    # dcc.Dropdown(
    #     id="item-dropdown",
    #     options=[{'label': item, 'value': item} for item in unique_items],
    #     multi=True
    # ),
    # dcc.Graph(figure=fig, id='item-price-graph', style={'width': '800px'})
])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_pdf_to_img(path):
    pdf_document = fitz.open(path)
    images = []
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images

def convert_image_to_text(image):
    text = pytesseract.image_to_string(image)
    final = ""
    total_expense = 0
    current_index = 0
    for line in text.splitlines():
        final += line + '\n'
    data = text.splitlines()
    for line in data:
        if 'Amount' in line:
            start_index = current_index
        if ('ltem Code' in line) or ('Item Code' in line):
            item_start = current_index + 1
        if 'Ordered | Shipped' in line:
            item_end = current_index - 1
        if 'Unit Price' in line:
            price_start = current_index + 1
        current_index += 1

    item_codes = data[item_start:item_end]
    price_values = data[price_start:(start_index - 1)]

    for item in item_codes:
        if item == '':
            item_codes.remove(item)
    for item in price_values:
        if item == '':
            price_values.remove(item)

    individual_expenses = dict(zip(item_codes, price_values))
    print(individual_expenses)

    for item in data[start_index:]:
        try:
            total_expense += float(item)
        except ValueError:
            pass
    return final, total_expense, individual_expenses

@dash_app.callback(
    dash.dependencies.Output('item-price-graph', 'figure'),
    [dash.dependencies.Input('supplier-dropdown', 'value'),
     dash.dependencies.Input('invoice-dropdown', 'value'),
     dash.dependencies.Input('item-dropdown', 'value')]
)

def update_graph(selected_suppliers, selected_invoices, selected_items):

    if not selected_suppliers:
        fig = go.Figure()
        fig.update_layout(title='Price for Each Product', xaxis=dict(title='Item'), yaxis=dict(title='Price'))
        return fig
    
    filtered_supplier = [each for each in suppliers_data if each['name'] in selected_suppliers]
    empty = []
    for each in filtered_supplier:
        for invoice in invoice_data:
            if invoice['supplierName'] == each['name']:
                empty.append(invoice)

    filtered_invoice = [each for each in empty if each['invoice_number'] in selected_invoices]
    print(filtered_invoice)
    item_per_invoice = [item for item in data for invoice in filtered_invoice if 'invoice_number' in invoice and item.get('invoice_number') == invoice['invoice_number']]
    if not selected_items:
        # If no items selected, consider all items in the invoices
        items = [item['item_code'] for item in item_per_invoice]
    else:
        # Filter data based on selected items
        filtered_data_by_items = [item for item in item_per_invoice if item['item_code'] in selected_items]
        items = [item['item_code'] for item in filtered_data_by_items]
        prices = [item['unit_price'] for item in filtered_data_by_items]
    
    color_palette = ['rgba(31, 119, 180, 0.8)', 'rgba(255, 127, 14, 0.8)', 'rgba(44, 160, 44, 0.8)',
                     'rgba(214, 39, 40, 0.8)', 'rgba(148, 103, 189, 0.8)', 'rgba(140, 86, 75, 0.8)',
                     'rgba(227, 119, 194, 0.8)', 'rgba(127, 127, 127, 0.8)', 'rgba(188, 189, 34, 0.8)',
                     'rgba(23, 190, 207, 0.8)']
    
    color_mapping = {item: color for item, color in zip(items, color_palette)}

    colors = [[color_mapping[item] for item in items] for _ in range(len(prices))]

    fig = go.Figure()
    for i in range(len(prices)):
        fig.add_trace(go.Bar(x=[items[i]], y=[prices[i]], marker_color=colors[i], name=items[i], legendgroup=items[i]))

    fig.update_layout(title='Price for Selected Products', xaxis=dict(title='Item'), yaxis=dict(title='Price'), barmode='group')
    return fig

@app.route('/')
def index():
    dash_app_content = dash_app.index()    
    return render_template('index.html', dash_app_content=dash_app_content)


@app.route('/dashboard/it')
def dashboard_it():
    return render_template('dashboard_it.html')


@app.route('/suppliers')
def suppliers():
    return render_template('suppliers.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    username = None
    password = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

    if username == 'user' and password == 'password':
        return redirect(url_for('index'))
    
    if username == 'ituser' and password == 'password':
        return redirect(url_for('dashboard_it'))
    
    if username == 'admin' and password == 'password':
        return redirect(url_for('dashboard_admin'))
    
    return render_template('login.html')

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if 'file' not in request.files:
#         return 'No file part'

#     file = request.files['file']

#     if file.filename == '':
#         return 'No selected file'

#     if file and allowed_file(file.filename):
#         filename = secure_filename(file.filename)
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         file.save(file_path)
#         parsed_text, total_expense, individual_expenses = convert_image_to_text(file_path)

#         if total_expense is not None:
#             response_data = {
#                 'parsed_text': parsed_text,
#                 'total_expense': total_expense,
#                 'individual_expenses': individual_expenses
#             }
#             return jsonify(response_data)
#         else:
#             return jsonify(parsed_text=parsed_text)
#     else:
#         return 'Invalid file format'

@app.route('/templates')
def template():
        return render_template('templates.html')

@app.route("/salesdata")
def salesdata():
    return render_template('visualize.html')

@app.route("/fetch_invoice_number")
def fetch_invoice_number():
    data = list(invoices.find({}))
    data_dict = [{"invoice_number": "INV12145", "supplierName": "Bruce & Clark"}]
    return jsonify(data_dict)


@app.route('/fetch_database_data')
def fetch_database_data():
    # Fetch the data from your database (modify this part as needed)
    data = list(products.find({}))
    
    # Convert the data to a list of dictionaries
    data_dict = [{'item_code': item['item_code'], 'unit_price': item['unit_price']} for item in data]

    # Return the data as JSON
    return jsonify(data_dict)

@app.route('/update', methods=['POST'])
def update_products():
    try:
        upload_data = request.get_json()
        for item in upload_data:
            item_code = item.get('item_code')
            unit_price = float(item.get('price'))
            invoice_number = item.get('invoice_number')
            
            existing_product = products.find_one({'item_code': item_code})
            if existing_product:
                products.update_one({'item_code': item_code}, {'$set': {'unit_price': unit_price}}, {'$set': {'invoice_number': invoice_number}})
            else:
                product = {
                    'item_code': item_code,
                    'unit_price': unit_price,
                    'invoice_number': invoice_number
                }
                products.insert_one(product)

        return 'Products updated successfully'
    except Exception as e:
        return str(e), 400



# AWS credentials and S3 bucket name
AWS_ACCESS_KEY_ID = "<you key id>"
AWS_SECRET_ACCESS_KEY = '<your access key >'
S3_BUCKET_NAME = 'issp-bucket-textract'
LAMBDA_FUNCTION_NAME = 'textract_the_pdf'
AWS_REGION = 'us-west-2'

# Initialize Boto3 S3 client
s3 = boto3.client('s3',
                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                  region_name=AWS_REGION)

# File Upload For Textract
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']

    if file.filename == '':
        return 'No selected file'

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Upload the file to S3
        try:
            s3.upload_file(file_path, S3_BUCKET_NAME, filename)
        except Exception as e:
            return f'Error uploading file to S3: {e}'

        # Trigger Lambda function
        lambda_client = boto3.client('lambda',
                                     aws_access_key_id=AWS_ACCESS_KEY_ID,
                                     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                     region_name=AWS_REGION)

        try:
            lambda_client.invoke(FunctionName=LAMBDA_FUNCTION_NAME,
                                 InvocationType='Event',  # Asynchronous invocation
                                 Payload='{}')  # Optional payload
        except Exception as e:
            return f'Error triggering Lambda function: {e}'

        return 'File uploaded successfully and Lambda triggered'
    else:
        return 'Invalid file format'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload')
def upload():
    image = "uploads/upload.JPG"
    return render_template('upload.html', file_path=image)


# Download the csv file

@app.route('/download_unit_price')
def download_unit_price():
    try:
        # Download unit_price.csv from S3 bucket
        s3.download_file(S3_BUCKET_NAME, 'unit_price.csv', 'unit_price.csv')
        
        if os.path.exists("unit_price.csv"):
            client = MongoClient('localhost', 27017)
            db = client['InvoiceDB']
            client_invoice_collection = db['client_invoice']

            with open("unit_price.csv", "r") as csv_file:
                csv_reader = csv.reader(csv_file)

                data = list(csv_reader)
                num_rows = len(data)

                # Ensure there are at least 3 rows for each set of data
                if num_rows % 3 != 0:
                    return "Invalid CSV file format. Each set of data should have 3 rows."

                # Read CSV row by row
                for i in range(0, num_rows, 3):
                    try:
                        date_of_invoice = data[i][1]
                        delivered_to = data[i+1][1]
                        unit_price = data[i+2][1]

                        # Check if the same data already exists in the database
                        existing_data = client_invoice_collection.find_one({
                            'Delivered to': delivered_to.strip(),
                            'Date of Invoice': date_of_invoice.strip(),
                            'Unit Price': unit_price.strip()
                        })

                        # If same data exists, return "same data"
                        if existing_data:
                            return "Same data"

                        # Insert data into MongoDB
                        client_invoice_collection.insert_one({
                            'Delivered to': delivered_to.strip(),
                            'Date of Invoice': date_of_invoice.strip(),
                            'Unit Price': unit_price.strip()
                        })
                    except IndexError:
                        return "IndexError: list index out of range. Check CSV file structure."

            # Delete the file after saving data into the database
            os.remove("unit_price.csv")

            return "Data from unit_price.csv saved into database and file deleted."
        else:
            return "No data to save. File unit_price.csv not found."

        # return send_file('./unit_price.csv', as_attachment=True)
    except Exception as e:
        return f'Error downloading unit_price.csv from S3: {e}'


# testing
@app.route('/view_suppliers_invoices')
def temp_view():
   
    collections = db.list_collection_names()
    
    # Retrieve the documents from each collection
    collection_data = {}
    for collection_name in collections:
        # Filter out 'petrocan_data' collection
        if collection_name != 'petrocan_data':
            collection_data[collection_name] = list(db[collection_name].find())
    
    return render_template('view_suppliers_invoices.html', collection_data=collection_data)




@app.route('/petrocan_data', methods=['GET', 'POST'])
def scrape_petrocan_data():
    # URL of the Petro-Canada page to scrape
    url = 'https://www.petro-canada.ca/en/business/rack-prices'

    # Send a GET request to the webpage
    response = requests.get(url)

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the effective date element
    effective_date_element = soup.find(class_='rack-pricing__effective-date')
  
    effective_date_text = effective_date_element.get_text().strip()
    effective_date = datetime.datetime.strptime(effective_date_text.split(': ')[1], '%b %d, %Y %I:%M %p').strftime('%m/%d/%Y')


    client = MongoClient('localhost', 27017)
    db = client['InvoiceDB']
    petrocan_collection = db['petrocan_data']

    table_rows = soup.find_all('tr')

    for row_index, row in enumerate(table_rows):
        cells = row.find_all(['td', 'th'])  # Find both td and th elements

        if row_index == 0 or cells[0].get_text().strip() == "Location":
            continue

        location = cells[0].get_text().strip()  # Extract location from the first cell of the row

        reg_87_price = cells[1].get_text().strip() if len(cells) > 1 else ''
        mid_89_price = cells[2].get_text().strip() if len(cells) > 2 else ''
        sup_91_price = cells[3].get_text().strip() if len(cells) > 3 else ''
        reg_e10_price = cells[4].get_text().strip() if len(cells) > 4 else ''
        uls_diesel_price = cells[6].get_text().strip() if len(cells) > 6 else ''

        # Construct the document to be inserted
        entry = {
            'Location': location,
            'REG 87': reg_87_price,
            'MID 89': mid_89_price,
            'SUP 91': sup_91_price,
            'REG E-10': reg_e10_price,
            'ULS Diesel': uls_diesel_price,
            'Effective Date': effective_date
        }

        # Check if the entry already exists in the database
        existing_entry = petrocan_collection.find_one({'Location': location, 'Effective Date': effective_date})

        if existing_entry:
            petrocan_collection.update_one({'Location': location, 'Effective Date': effective_date}, {'$set': entry})
        else:
            petrocan_collection.insert_one(entry)

    # Fetch all unique effective dates from the database
    unique_dates = petrocan_collection.distinct('Effective Date')

    if request.method == 'POST':
        selected_date = request.form['date']
        documents = list(petrocan_collection.find({'Effective Date': selected_date}))
    else:
        # By default, show data for the latest effective date
        selected_date = effective_date
        documents = list(petrocan_collection.find({'Effective Date': effective_date}))

    collection_data = {'petrocan_data': documents}

    return render_template('petrocan_data.html', collection_data=collection_data, unique_dates=unique_dates, selected_date=selected_date)

        

@app.route('/shell_data', methods=['GET', 'POST'])
def scrape_shell_data():
    csv_url = "https://shell-ca-apps.client.hostid.net/prices/rack_prices.csv"
    response = requests.get(csv_url)
    
    client = MongoClient('localhost', 27017)
    db = client['InvoiceDB']
    shell_collection = db['shell_data']

    if response.status_code == 200:
        # Read CSV data from response content
        csv_data = response.content.decode('utf-8')
        
        # Use StringIO to treat the string as a file-like object
        csv_file = csv.reader(csv_data.splitlines())
        
        # Skip header row
        next(csv_file)
        
        # Insert data into MongoDB collection if Location, Product, and Effective Date combination is not already present
        for row in csv_file:
            location, product, price, change, effective_date  = row
        

            # Check if a document with the same Location, Product, and Effective Date combination already exists in the database
            existing_doc = shell_collection.find_one({'Location': location, 'Product': product, 'Effective Date': effective_date})
            
            if existing_doc is None:
                # Insert new document
                shell_collection.insert_one({
                    'Location': location,
                    'Product': product,
                    'Price (cpl)': float(price),
                    'Change': float(change),
                    'Effective Date': effective_date
                })
        
        # Retrieve unique effective dates from MongoDB collection
        unique_dates = shell_collection.distinct('Effective Date')
        
        data_dict = {}  # Initialize data_dict
        
        if request.method == 'POST':
            selected_date = request.form['selected_date']

            # Retrieve data for the selected effective date
            documents = shell_collection.find({'Effective Date': selected_date})
            
            # Loop through each document and organize data
            for doc in documents:
                location = doc['Location']
                product = doc['Product']
                price = doc['Price (cpl)']
                effective_date = doc['Effective Date']
                
                # Initialize a dictionary for the location if it doesn't exist
                if location not in data_dict:
                    data_dict[location] = {'Effective Date': effective_date}
                
                # Store price for each product under the location
                data_dict[location][product] = price
            
            return render_template('shell_data.html', data_dict=data_dict, unique_dates=unique_dates, selected_date=selected_date, collection_name=shell_collection.name)
        
        return render_template('shell_data.html', data_dict=data_dict, unique_dates=unique_dates, collection_name=shell_collection.name)

    else:
        return "Failed to fetch data from the URL."




@app.route('/getprice')
def getprice():
    return render_template('getprice.html')



# try the comparing part



db = client["InvoiceDB"]
client_info = db["client_info"]
client_invoice = db["client_invoice"]
petrocan_data = db["petrocan_data"]
shell_data = db["shell_data"]




@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if request.method == 'POST':
        selected_client = request.form.get('client_name')
        invoices = client_invoice.find({"Delivered to": selected_client})
        invoice_dates = [invoice["Date of Invoice"] for invoice in invoices]
        
        # Fetch default fuel type
        default_fuel_type = client_info.find_one({"client_name_address": selected_client})['default_fuel_type']
        
        return render_template('compare.html', client_name=selected_client, invoice_date=invoice_dates[0], company=request.form.get('company'), location=request.form.get('location'), default_fuel_type=default_fuel_type)
    return render_template('compare.html', client_names=get_client_names(), invoice_dates=[], companies=["Petrocan", "Shell"])


def get_client_names():
    return [client["client_name_address"] for client in client_info.find()]

@app.route('/get_invoice_dates', methods=['GET'])
def get_invoice_dates():
    selected_client = request.args.get('client_name')
    invoices = client_invoice.find({"Delivered to": selected_client})
    invoice_dates = [invoice["Date of Invoice"] for invoice in invoices]
    return jsonify(invoice_dates)

@app.route('/get_locations', methods=['GET'])
def get_locations():
    company = request.args.get('company')
    if company == 'Petrocan':
        locations = set(record['Location'] for record in petrocan_data.find())
    elif company == 'Shell':
        locations = set(record['Location'] for record in shell_data.find())  
    return jsonify(list(locations))



@app.route('/fetch_data', methods=['POST'])
def fetch_data():
    selected_values = request.json
    selected_client = selected_values['client_name']
    invoice_date = selected_values['invoice_date']
    company = selected_values['company']
    query_date = selected_values['query_date'] # Include the selected query date

    # Fetch default fuel type
    default_fuel_type = client_info.find_one({"client_name_address": selected_client})['default_fuel_type']

    # Return the selected data as JSON
    return jsonify({
        'client_name': selected_client,
        'invoice_date': invoice_date,
        'default_fuel_type': default_fuel_type,
        'company': company,
        'query_date': query_date # Include the selected query date
    })


@app.route('/fetch_unit_price', methods=['POST'])
def fetch_unit_price():
    selected_values = request.json
    selected_client = selected_values['client_name']
    invoice_date = selected_values['invoice_date']

    # Query the database to get the unit price
    unit_price = client_invoice.find_one({"Delivered to": selected_client, "Date of Invoice": invoice_date})['Unit Price']
    unit_price = float(unit_price) * 100

    return jsonify(unit_price)



@app.route('/fetch_default_price', methods=['POST'])
def fetch_default_price():
    selected_client = request.json['client_name']
    default_price = client_info.find_one({"client_name_address": selected_client})['default_fuel_type']
    return jsonify(default_price)

@app.route('/get_record_dates', methods=['GET'])
def get_record_dates():
    company = request.args.get('company')
    location = request.args.get('location')
    
    if company == 'Petrocan':
        records = petrocan_data.find({"Location": location})
    elif company == 'Shell':
        records = shell_data.find({"Location": location})
        
    record_dates = {record['Effective Date'] for record in records}  # Using set to remove duplicates
    return jsonify(list(record_dates))





@app.route('/fetch_query_results', methods=['GET'])
def fetch_query_results():
    company = request.args.get('company')
    location = request.args.get('location')
    record_date = request.args.get('record_date')  # Get the record_date from the request
    
    if company == 'Petrocan':
        records = list(petrocan_data.find({"Location": location, "Effective Date": record_date}, {"_id": 0, "Change": 0}))
    elif company == 'Shell':
        # Only include products 'E10', 'MID', 'PRE', 'STOVE', 'ULS1', 'ULSD'
        records = list(shell_data.find({"Location": location, "Effective Date": record_date, "Product": {"$in": ['E10', 'MID', 'PRE', 'STOVE', 'ULS1', 'ULSD']}}, {"_id": 0, "Change": 0}))

    # Convert ObjectId to string for serialization
    for record in records:
        if '_id' in record:
            record['_id'] = str(record['_id'])

    return json_util.dumps(records)


# add client


@app.route('/create_invoice', methods=['GET'])
def create_invoice():
    return render_template('create_invoice.html')

@app.route('/add_client_invoice', methods=['POST'])
def add_client_invoice():
    data = request.json  # Retrieve JSON data from request
    delivered_to = data['deliveredTo']
    date_of_invoice = data['dateOfInvoice']
    unit_price = data['unitPrice']

    existing_client = client_info.find_one({'client_name_address': delivered_to})
    if not existing_client:
        client_info.insert_one({'client_name_address': delivered_to, 'default_fuel_type': 'Diesel'})

    client_invoice.insert_one({'Delivered to': delivered_to, 'Date of Invoice': date_of_invoice, 'Unit Price': unit_price})

    return '>> Client invoice added successfully ! '


# delete client

@app.route('/manage_client', methods=['GET', 'POST'])
def manage_client():
    if request.method == 'POST':
        selected_client = request.json['client_name']
        client_info.delete_one({'client_name_address': selected_client})
        client_invoice.delete_many({'Delivered to': selected_client})

        return 'Client information deleted successfully!'
    else:
        client_names = get_client_names()
        return render_template('manage_client.html', client_names=client_names)
    


if __name__ == '__main__':
    app.run(debug=True)
    

