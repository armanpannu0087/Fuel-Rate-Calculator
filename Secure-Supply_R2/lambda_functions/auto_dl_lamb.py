import json
import boto3
from collections import defaultdict
from urllib.parse import unquote_plus
import csv

def get_kv_map(bucket, key):
    # process using image bytes
    client = boto3.client('textract')
    response = client.analyze_document(Document={'S3Object': {'Bucket': bucket, "Name": key}}, FeatureTypes=['FORMS'])

    # Get the text blocks
    blocks = response['Blocks']

    # get key and value maps
    key_map = {}
    value_map = {}
    block_map = {}
    for block in blocks:
        block_id = block['Id']
        block_map[block_id] = block
        if block['BlockType'] == "KEY_VALUE_SET":
            if 'KEY' in block['EntityTypes']:
                key_map[block_id] = block
            else:
                value_map[block_id] = block

    return key_map, value_map, block_map


def get_kv_relationship(key_map, value_map, block_map):
    kvs = defaultdict(list)
    for block_id, key_block in key_map.items():
        value_block = find_value_block(key_block, value_map)
        key = get_text(key_block, block_map)
        val = get_text(value_block, block_map)
        kvs[key].append(val)
    return kvs


def find_value_block(key_block, value_map):
    for relationship in key_block['Relationships']:
        if relationship['Type'] == 'VALUE':
            for value_id in relationship['Ids']:
                value_block = value_map[value_id]
    return value_block
    

def get_text(result, blocks_map):
    text = ''
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        text += word['Text'] + ' '
                    if word['BlockType'] == 'SELECTION_ELEMENT':
                        if word['SelectionStatus'] == 'SELECTED':
                            text += 'X'

    return text

def get_unit_price(kvs):
    unit_price = None
    for key, value in kvs.items():
        if "UNIT PRICE" in key:
            unit_price = value[0].split()[0]  # Assuming unit price is a single value
            break
    return unit_price

def write_to_csv(filename, data):
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        for row in data:
            writer.writerow(row)

def upload_to_s3(bucket, key, filename):
    s3 = boto3.client('s3')
    s3.upload_file(filename, bucket, key)

def lambda_handler(event, context):
    file_obj = event["Records"][0]
    bucket = unquote_plus(str(file_obj["s3"]["bucket"]["name"]))
    file_name = unquote_plus(str(file_obj["s3"]["object"]["key"]))
    print(f'Bucket: {bucket}, file: {file_name}')
    key_map, value_map, block_map = get_kv_map(bucket, file_name)

    # Get Key Value relationship
    kvs = get_kv_relationship(key_map, value_map, block_map)

    unit_price = get_unit_price(kvs)
    print("Unit Price:", unit_price)
    
    # Write data to CSV file
    csv_data = [['Unit Price', unit_price]]
    csv_filename = '/tmp/unit_price.csv'  # Store the CSV file in Lambda's temporary directory
    write_to_csv(csv_filename, csv_data)
    
    # Upload CSV file to S3 bucket
    s3_key = 'unit_price.csv'  # Specify the key (path) where you want to upload the CSV file in your bucket
    upload_to_s3(bucket, s3_key, csv_filename)
    
    return {
        'statusCode': 200,
        'body': json.dumps({'Unit Price': unit_price}),
        's3_bucket': bucket,
        's3_key': s3_key
    }
