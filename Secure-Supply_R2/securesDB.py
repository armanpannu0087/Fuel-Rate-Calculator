from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('localhost', 27017)

# Create (or use) the database
db = client['InvoiceDB']

# Suppliers collection
db.suppliers.insert_one({
    "name": "Bruce & Clark"
})

#Invoices collection
db.invoices.insert_one({
    "invoice_number": "INV12145",
    "supplierName": "Bruce & Clark"
})


# Add a collection called client_info
client_info_collection = db['client_info']

# Insert a document into the client_info collection
client_info_collection.insert_one({
    "client_name_address": "JOYCE JOE 5902 SECHELT INLET ROAD SECHELT, BC V7Z0G1",
    "default_fuel_type": "Diesel"
})

