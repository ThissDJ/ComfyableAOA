import os
import json
import requests
import csv
import gzip
import base64
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from salesMonitor.models import DownloadedReport, PaymentTransactionDetail

# from sp_api.api import ReportsV2
# from sp_api.api import Orders
# from sp_api.api import Reports
# from sp_api.base import Marketplaces,SellingApiException

# Initialize global variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
accessToken = ''
cronRunning = False
token_time_out = 1800000  # milliseconds
auth_time = 0
# Load environment variables from .env
load_dotenv()

credentials=dict(
        refresh_token=os.getenv("SELLING_PARTNER_APP_REFRESH_TOKEN"),
        lwa_app_id=os.getenv("SELLING_PARTNER_APP_CLIENT_ID"),
        lwa_client_secret=os.getenv("SELLING_PARTNER_APP_CLIENT_SECRET")
    )

@csrf_exempt
def amazon_authorization():
    global accessToken, auth_time

    current_store = {
            "grant_type": 'refresh_token',
            "client_id": os.getenv("SELLING_PARTNER_APP_CLIENT_ID"),
            "client_secret": os.getenv("SELLING_PARTNER_APP_CLIENT_SECRET"),
            "refresh_token": os.getenv("SELLING_PARTNER_APP_REFRESH_TOKEN"),
        }  # Adjust based on your data

    if auth_time != 0 and (datetime.now().timestamp() * 1000 - auth_time) <= token_time_out:
        # Authentication is still valid
        return JsonResponse({'status': 'Authentication is still valid'})

    # Replace 'https://api.example.com/endpoint' with the actual API endpoint URL
    api_url = 'https://api.amazon.com/auth/o2/token'

    try:
        payload = {
            "grant_type": 'refresh_token',
            "client_id": current_store.get('client_id', ''),
            "client_secret": current_store.get('client_secret', ''),
            "refresh_token": current_store.get('refresh_token', ''),
        }

        # Make a POST request to the API
        response = requests.post(api_url, data=json.dumps(payload))
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            auth_response = response.json()
            accessToken = auth_response.get('access_token', '')
            auth_time = int(datetime.now().timestamp() * 1000)  # Update auth_time
            return JsonResponse({'status': 'Authentication successful', 'access_token': accessToken})
        else:

            # If the request was not successful, return an error response
            return JsonResponse({'error': 'Failed to fetch data from the API'}, status=response.status_code)

    except requests.RequestException as e:
        # Handle request exceptions, such as network errors
        return JsonResponse({'error': f'Request failed: {str(e)}'}, status=500)

def generate_transaction_report(request):
    global accessToken, auth_time

    amazon_authorization()
    # return JsonResponse({"message": "Access token generated"}, status=200) 
    headers = {'x-amz-access-token': accessToken}

    # Replace 'https://api.example.com/endpoint' with the actual API endpoint URL
    api_url = 'https://sellingpartnerapi-fe.amazon.com/reports/2020-09-04/reports?reportTypes=GET_DATE_RANGE_FINANCIAL_TRANSACTION_DATA&marketplaceIds=A39IBJ37TRP1C6'

    try:

         # # Make a POST request to the API
        response = requests.get(api_url,headers=headers)
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            report_response = response.json()
            if len(report_response['payload']) <0:
                return {'error': "Report not found"}
            else:
                current_report_data= report_response['payload'][0]
                # Check if a record with the same report_id already exists
                existing_report = DownloadedReport.objects.filter(report_id=current_report_data['reportId']).first()
                
                if existing_report:
                    print(f"Report with report_id '{current_report_data['reportId']}' already exists in the database.")
                    return JsonResponse({"message":f"Report with report_id '{current_report_data['reportId']}' already exists in the database."}, status=403) 
                
                document_data= get_report_document(report_response['payload'][0]['reportDocumentId'])
                if document_data['status'] == 200:
                    download_report_response = download_report(document_data['data']['url'], document_data['data']["encryptionDetails"])
                    # Check if download_report_response is not None before accessing its attributes
                    if download_report_response is not None:
                        read_csv_and_process_report(current_report_data, download_report_response.get('filename', ''))
                        print("Done",download_report_response)
                        return JsonResponse(download_report_response, status=download_report_response.get('status', 200))
                    else:
                        return JsonResponse({"message":"Error while downloading report"}, status=500)  # Return an appropriate error response
                else:
                     # If the request was not successful, return an error response
                    return JsonResponse(response.json(), status=response.status_code)

        else:
            # If the request was not successful, return an error response
            return {"data":response.json(), "status":response['status_code']}
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return JsonResponse({}, status=500)  # Return an appropriate error response

# Function to get the document content of a report
def get_report_document(reportDocumentId):
    global accessToken

    headers = {
        "contentType": "text/tab-separated-values; charset=UTF-8",
        'x-amz-access-token': accessToken,
    }

    api_url = 'https://sellingpartnerapi-fe.amazon.com/reports/2020-09-04/documents/' + reportDocumentId

    try:
        # Make a GET request to the API
        response = requests.get(api_url, headers=headers)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            report_response = response.json()
            return {"data": report_response['payload'], 'status': 200}
        else:
            # If the request was not successful, return an error response
            return {"data": response.json(), "status": response.status_code}

    except requests.RequestException as e:
        # Handle request exceptions, such as network errors
        return {'error': f'Request failed: {str(e)}', 'status': 500}
       
# Function for AES CBC decryption
def ase_cbc_decryptor(key, iv, encryption):
    cipher = Cipher(algorithms.AES(base64.b64decode(key)), modes.CBC(base64.b64decode(iv)))
    decryptor = cipher.decryptor()
    decrypted_text = decryptor.update(encryption)
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    unpaded_text = unpadder.update(decrypted_text)
    return unpaded_text + unpadder.finalize()

    
def get_report_document_content(key, iv, url, compression_type=None):
    resp = requests.get(url=url)
    resp_content = resp.content

    decrypted_content = ase_cbc_decryptor(key=key, iv=iv, encryption=resp_content)

    if compression_type == 'GZIP':
        decrypted_content = gzip.decompress(decrypted_content)

    # Assuming the decrypted content is in CSV format
    decoded_content = decrypted_content.decode('utf-8')
    
    # Assuming CSV content is comma-separated, adjust accordingly based on your actual data
    csv_reader = csv.reader(decoded_content.splitlines())
    
    # Assuming the first row contains column headers, adjust accordingly
    headers = next(csv_reader)

    # Generate timestamp for the filename
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    # Create a CSV file with a timestamp in the name
    filename = f'transaction_report_{timestamp}.csv'
    csv_file_path= os.path.join(BASE_DIR,filename)
    with open(csv_file_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(headers)

        # Write the remaining rows
        csv_writer.writerows(csv_reader)

    return {'message': f'CSV file ({filename}) generated successfully',"filename":filename, 'status': 200}

# Function to download a report
def download_report(report_url, encryptionDetails):
    try:
        fileContent = get_report_document_content(encryptionDetails['key'], encryptionDetails["initializationVector"], report_url)
        return fileContent

    except Exception as e:
        # Handle errors during report download
        print('Error downloading report:', str(e))
        return {'error': f'Request failed: {str(e)}', 'status': 500}

def read_csv_and_process_report(current_report_data, filename):
    try:

        summaryData = DownloadedReport(report_id=current_report_data['reportId'],
                                       report_start_time=datetime.fromisoformat(current_report_data['dataStartTime']).strftime('%Y-%m-%d'),
                                       report_end_time=datetime.fromisoformat(current_report_data['dataEndTime']).strftime('%Y-%m-%d'))
        summaryData.save()

        csv_file_path = os.path.join(BASE_DIR,filename)

        with open(csv_file_path, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
        
            # Skip header rows
            for _ in range(8):
                next(csv_reader)

            date_format = "%d %b %Y %I:%M:%S %p"

            for i,read_row in enumerate(csv_reader):
                payment_type = read_row[2]
                order_id = read_row[3]
                sku = read_row[4]

                # Try to get an existing record based on order_id, sku, and type
                # existing_record = PaymentTransactionDetail.objects.filter(
                #     order_id=order_id, sku=sku, type=payment_type
                # ).first()
                
                # Continue with processing the CSV rows
                date_string = read_row[0].replace(' GMT+9', '')
                parsed_date = datetime.strptime(date_string, date_format)
                timezone_offset = timezone(timedelta(hours=9))  # GMT+9
                parsed_date = parsed_date.replace(tzinfo=timezone_offset)
                read_row[21] = read_row[21].replace(',', '')
                read_row[22] = read_row[22].replace(',', '')
                
                # if existing_record:
                #     # If the record exists, update its fields
                #     existing_record.date_time = parsed_date
                #     existing_record.settlement_id = read_row[1]
                #     existing_record.description = read_row[5]
                #     existing_record.quantity=0 if read_row[6] == '' else read_row[6],
                #     existing_record.marketplace = read_row[7]
                #     existing_record.fulfillment = read_row[8]
                #     existing_record.order_city = read_row[9]
                #     existing_record.order_state = read_row[10]
                #     existing_record.order_postal = read_row[11]
                #     existing_record.product_sales = Decimal(read_row[12])
                #     existing_record.shipping_credits = Decimal(read_row[13])
                #     existing_record.gift_wrap_credits = Decimal(read_row[14])
                #     existing_record.promotional_rebates = Decimal(read_row[15])
                #     existing_record.sales_tax_collected = Decimal(read_row[16])
                #     existing_record.low_value_goods = Decimal(read_row[17])
                #     existing_record.selling_fees = Decimal(read_row[18])
                #     existing_record.fba_fees = Decimal(read_row[19])
                #     existing_record.other_transaction_fees = Decimal(read_row[20])
                #     existing_record.other = Decimal(read_row[21])
                #     existing_record.total = Decimal(read_row[22])

                #     # Save the changes
                #     existing_record.save()
                # else:
                # If the record doesn't exist, create a new one
                new_record = PaymentTransactionDetail(
                    date_time=parsed_date,
                    settlement_id=read_row[1],
                    type=payment_type,
                    order_id=order_id,
                    sku=sku,
                    description=read_row[5],
                    quantity=0 if read_row[6] == '' else read_row[6],
                    marketplace=read_row[7],
                    fulfillment=read_row[8],
                    order_city=read_row[9],
                    order_state=read_row[10],
                    order_postal=read_row[11],
                    product_sales=Decimal(read_row[12]),
                    shipping_credits=Decimal(read_row[13]),
                    gift_wrap_credits=Decimal(read_row[14]),
                    promotional_rebates=Decimal(read_row[15]),
                    sales_tax_collected=Decimal(read_row[16]),
                    low_value_goods=Decimal(read_row[17]),
                    selling_fees=Decimal(read_row[18]),
                    fba_fees=Decimal(read_row[19]),
                    other_transaction_fees=Decimal(read_row[20]),
                    other=Decimal(read_row[21]),
                    total=Decimal(read_row[22]),
                    downloaded_file_id=summaryData
                )

                # Save the new record
                new_record.save()    

        # return JsonResponse({"row_data":json.dumps(new_array, indent=2)}, status=200)
        return JsonResponse({"row_data":new_record}, status=200)
        

    except Exception as e:
        # Handle request exceptions, such as network errors
        return JsonResponse({'error': f'Request failed: {str(e)}'}, status=500)

def generate_rpt_using_sdk(request):
    try:

        report_types = ["GET_DATE_RANGE_FINANCIAL_TRANSACTION_DATA"]
        report_response =Reports(credentials=credentials,marketplace=Marketplaces.IN).get_reports(reportTypes=report_types)
        report_response=report_response.payload['reports']
        # return JsonResponse(report_response, status=200,safe=False)

        report_document_id=report_response[0]['reportDocumentId']
        document_response =Reports(credentials=credentials,marketplace=Marketplaces.IN).get_report_document(report_document_id, download=True, file='GET_DATE_RANGE_FINANCIAL_TRANSACTION_DATA.csv')
        return JsonResponse(document_response.payload, status=200,safe=False)

    except SellingApiException as ex:
        # Handle request exceptions, such as network errors
        return JsonResponse({'error': f'Request failed: {str(ex)}'}, status=500)
   