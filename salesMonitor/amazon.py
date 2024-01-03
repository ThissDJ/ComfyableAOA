import os
import csv
import csv
from django.http import JsonResponse
# from asgiref.sync import sync_to_async
from django.views.decorators.csrf import csrf_exempt  # Import this decorator
from datetime import datetime
from django.utils import timezone
import requests
from io import StringIO
import json
from salesMonitor.models import DownloadedReport
from sp_api.api import ReportsV2
from sp_api.api import Orders
from sp_api.api import Reports
from sp_api.base import Marketplaces,SellingApiException
import gzip
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64

# Initialize global variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
accessToken = ''
cronRunning = False
token_time_out = 1800000  # milliseconds
auth_time = 0
credentials=dict(
        refresh_token='Atzr|IwEBIK9iYLvNijeYQ9gmWmQ87344f37e7SYk37WG1Qc6gkN3TvDl-NYwO3IoH9IogzgY9MePsuj6jgEXvQYxFGCfMHxx_6dJgYMhKrNm8uzwLAUM8G08VI60XHfWfGFZAiL5Mu2OoR-yCIBjvXghZeg9ipelBl30RonQHzwbgObdVMD8LWJ58yTXLux9DokYwLQIDICO2BFgG2FeUCkwxHf_TrWurZ4F_CiZfRZbAlUmINMGy7pZQMlf7GRGT5ALEwgL_CpePdeu3MUB9-Dtp0gOol6wPqPuw-g_ZSycHmfW3sZlLfoWBfDp-GgbMn0qzZOYFuE',
        lwa_app_id='amzn1.application-oa2-client.42c11463644c44ce8b2461c532817303',
        lwa_client_secret='00fac4478e450c9579ebe9362ad30e70abc9c5ceb00eec994f95378a3e9903e2'
    )

@csrf_exempt
def amazon_authorization(request):
    global accessToken, auth_time

    current_store = {
            "grant_type": 'refresh_token',
            "client_id": "amzn1.application-oa2-client.42c11463644c44ce8b2461c532817303",
            "client_secret": "00fac4478e450c9579ebe9362ad30e70abc9c5ceb00eec994f95378a3e9903e2",
            "refresh_token": "Atzr|IwEBIK9iYLvNijeYQ9gmWmQ87344f37e7SYk37WG1Qc6gkN3TvDl-NYwO3IoH9IogzgY9MePsuj6jgEXvQYxFGCfMHxx_6dJgYMhKrNm8uzwLAUM8G08VI60XHfWfGFZAiL5Mu2OoR-yCIBjvXghZeg9ipelBl30RonQHzwbgObdVMD8LWJ58yTXLux9DokYwLQIDICO2BFgG2FeUCkwxHf_TrWurZ4F_CiZfRZbAlUmINMGy7pZQMlf7GRGT5ALEwgL_CpePdeu3MUB9-Dtp0gOol6wPqPuw-g_ZSycHmfW3sZlLfoWBfDp-GgbMn0qzZOYFuE",
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

# def generate_transaction_report(request):
#     global accessToken, auth_time

#     amazon_authorization(request)

#     headers = {'x-amz-access-token': accessToken}

#     # Replace 'https://api.example.com/endpoint' with the actual API endpoint URL
#     api_url = 'https://sellingpartnerapi-eu.amazon.com/reports/2020-09-04/reports?reportTypes=GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2&marketplaceIds=A21TJRUUN4KGV'

#     try:
#         document_data= get_report_document('amzn1.spdoc.1.4.eu.13e1d40e-46a1-4fdb-ab86-17453cc9a565.T2A4TH4A8KDW6L.1118')
#         if document_data['status'] == 200:
#             print(document_data['data']['url'])
#             download_report_response = download_report(document_data['data']['url'], document_data['data']["encryptionDetails"])
#             # return JsonResponse(download_report_response, status=200,safe=False)
#             return JsonResponse(download_report_response, status=download_report_response['status'])
#         else: 
#             return JsonResponse({})
#         # # Make a POST request to the API
#         # response = requests.get(api_url,headers=headers)
#         # # Check if the request was successful (status code 200)
#         # if response.status_code == 200:
#         #     # Parse the JSON response
#         #     report_response = response.json()
           
#         #     if len(report_response['payload']) <0:
#         #         return {'error': "Report not found"}
#         #     else:
#         #         report_response= get_report_document(report_response['payload'][0]['reportDocumentId'])
#         #         # return JsonResponse(report_response['payload'], status=200,safe=False)
#         #         return JsonResponse(report_response, status=report_response['status'],safe=False)

#         # else:
#         #     # If the request was not successful, return an error response
#         #     return JsonResponse(response.json(), status=response.status_code)

#     except requests.RequestException as e:
#         # Handle request exceptions, such as network errors
#         return JsonResponse({'error': f'Request failed: {str(e)}'}, status=500)

def generate_transaction_report(request):
    global accessToken, auth_time

    amazon_authorization(request)

    headers = {'x-amz-access-token': accessToken}

    # Replace 'https://api.example.com/endpoint' with the actual API endpoint URL
    api_url = 'https://sellingpartnerapi-eu.amazon.com/reports/2020-09-04/reports?reportTypes=GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2&marketplaceIds=A21TJRUUN4KGV'

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
                document_data= get_report_document(report_response['payload'][0]['reportDocumentId'])
                if document_data['status'] == 200:
                    download_report_response = download_report(document_data['data']['url'], document_data['data']["encryptionDetails"])
                    
                    # Check if download_report_response is not None before accessing its attributes
                    if download_report_response is not None:
                        return JsonResponse(download_report_response, status=download_report_response.get('status', 200))
                    else:
                        return JsonResponse({}, status=500)  # Return an appropriate error response
                else:
                     # If the request was not successful, return an error response
                    return JsonResponse(response.json(), status=response.status_code)

        else:
            return JsonResponse({}, status=500)  # Return an appropriate error response
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return JsonResponse({}, status=500)  # Return an appropriate error response

def get_report_document(reportDocumentId):
    global accessToken

    headers = {
       "contentType":"text/tab-separated-values; charset=UTF-8",
        'x-amz-access-token': accessToken,

    }

    api_url = 'https://sellingpartnerapi-eu.amazon.com/reports/2020-09-04/documents/' + reportDocumentId

    try:
        # Make a GET request to the API
        response = requests.get(api_url, headers=headers)
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            report_response = response.json()
            return {"data":report_response['payload'], 'status':200}
        else:
            # If the request was not successful, return an error response
            return {"data":response.json(), "status":response.status_code}

    except requests.RequestException as e:
        # Handle request exceptions, such as network errors
        return {'error': f'Request failed: {str(e)}', 'status':500}
    
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

    return {'message': f'CSV file ({filename}) generated successfully', 'status': 200}

def download_report(report_url,encryptionDetails):
    try:
        fileContent = get_report_document_content(encryptionDetails['key'],encryptionDetails["initializationVector"],report_url)
        return fileContent

    except Exception as e:
        print('Error downloading report:', str(e))
        return {'error': f'Request failed: {str(e)}', 'status':500}
    
def generate_rpt_using_sdk(request):
    try:

        report_types = ["GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2"]
        report_response =Reports(credentials=credentials,marketplace=Marketplaces.IN).get_reports(reportTypes=report_types)
        report_response=report_response.payload['reports']
        # return JsonResponse(report_response, status=200,safe=False)

        report_document_id=report_response[0]['reportDocumentId']
        document_response =Reports(credentials=credentials,marketplace=Marketplaces.IN).get_report_document(report_document_id, download=True, file='GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2.csv')
        return JsonResponse(document_response.payload, status=200,safe=False)

    except SellingApiException as ex:
        # Handle request exceptions, such as network errors
        return JsonResponse({'error': f'Request failed: {str(ex)}'}, status=500)
    
def read_csv_and_process_report(request):
    try:
        csv_file_path = os.path.join(BASE_DIR,'transaction_report_20240101133722.csv')
        processed_data_list = []

        with open(csv_file_path, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
        
            #header skip
            next(csv_reader)
            date_format = "%d.%m.%Y %H:%M:%S UTC"
            first_row = next(csv_file).rstrip('\n').split('\t')

            if first_row:
                settlement_id, start_date, end_date, deposit_date, total_amount, currency = first_row[:6]
               
                settlement_start_date = timezone.make_aware(datetime.strptime(start_date, date_format))
                settlement_end_date = timezone.make_aware(datetime.strptime(end_date, date_format))
                deposite_date = timezone.make_aware(datetime.strptime(deposit_date, date_format))
                # processed_data = {
                #     "settlement_id": settlement_id,
                #     "settlement_start_date": datetime.strptime(start_date, date_format),
                #     "settlement_end_date": datetime.strptime(end_date, date_format),
                #     "deposite_date": datetime.strptime(deposit_date, date_format),
                #     "total_amount": total_amount,
                #     "total_amount": currency
                # }
                # summaryData = DownloadedReport(settlement_id = settlement_id ,\
                #                                            settlement_start_date=settlement_start_date,\
                #                                             settlement_end_date=settlement_end_date,\
                #                                             deposit_date=deposite_date,\
                #                                           total_amount = total_amount ,\
                #                                           currency = currency)
                # print(summaryData)
                # summaryData.save()
            for row in csv_reader:
                newRow = row[0].rstrip('\n').split('\t')
                temp_obj = {
                    "settlement-id": newRow[0],
                    "settlement-start-date": newRow[1],
                    "settlement-end-date": newRow[2],
                    "deposit-date": newRow[3],
                    "total-amount": newRow[4],
                    "currency": newRow[5],
                    "transaction-type": newRow[6],
                    "order-id": newRow[7],
                    "merchant-order-id": newRow[8],
                    "adjustment-id": newRow[9],
                    "shipment-id": newRow[10],
                    "marketplace-name": newRow[11],
                    "amount-type": newRow[12],
                    "amount-description": newRow[13],
                    "amount": newRow[14],
                    "fulfillment-id": newRow[15],
                    "posted-date": newRow[16],
                    "posted-date-time": newRow[17],
                    "order-item-code": newRow[18],
                    "merchant-order-item-id": newRow[19],
                    "merchant-adjustment-item-id": newRow[20],
                    "sku": newRow[21],
                    "quantity-purchased": newRow[22],
                    "promotion-id": newRow[23]
                }
                processed_data_list.append(temp_obj)
        

            grouped_data = {}
            for item in processed_data_list:
                order_id = item["order-id"]
                if order_id not in grouped_data:
                    grouped_data[order_id] = {"order_items": []}
                grouped_data[order_id]["order_items"].append({
                    "order_number": item['order-id'],
                    "order_item_id": item['order-item-code'],
                    "sku": item['sku'],
                    "amount-description": item['amount-description'],
                    "amount": item['amount'],
                })

            # for order_number, order_data in data.items():
            #     order = Order.objects.create(order_number=order_number)

            #     for item_data in order_data["order_items"]:
            #         OrderItem.objects.create(
            #             order=order,
            #             order_item_id=item_data["order_item_id"],
            #             sku=item_data["sku"],
            #             price=Decimal(item_data["price"]),
            #             tax_amount=Decimal(item_data["tax_amount"]),
            #             igst_amount=Decimal(item_data["igst_amount"]),
            #             tds_amount=Decimal(item_data["tds_amount"]),
            #             commission=Decimal(item_data["commission"]),
            #             commission_igst=Decimal(item_data["commission_igst"]),
            #             fix_closing_fee=Decimal(item_data["fix_closing_fee"]),
            #             fix_closing_fee_igst=Decimal(item_data["fix_closing_fee_igst"]),
            #         )



        return JsonResponse({"row_data":grouped_data}, status=200)
        

    except SellingApiException as ex:
        # Handle request exceptions, such as network errors
        return JsonResponse({'error': f'Request failed: {str(ex)}'}, status=500)
