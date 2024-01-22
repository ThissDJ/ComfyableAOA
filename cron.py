import requests
import time
from datetime import datetime

# API endpoint URL
API_ENDPOINT = "http://209.97.151.168/salesMonitor/generate_transaction_report"

# Log file path
LOG_FILE = "/home/nginxcaoa/comfyableAOA/media/logs/cron_api_response.log"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

def make_api_request():
    try:
        # Make GET request with headers
        response = requests.get(API_ENDPOINT, headers=HEADERS)
        print(response.text)

        # Log the response to the file with a formatted timestamp
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(
                "API Response at {}: \n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            log_file.write("{}\n".format(response.text))
            print("API request successful. Response logged to", LOG_FILE)

    except requests.exceptions.RequestException as err:
        # Log the error to the file with a formatted timestamp
        with open(LOG_FILE, 'a') as log_file:
            log_file.write("Error making API request at {}. Check the endpoint or connectivity.\n".format(
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            log_file.write("Error details: {}\n".format(err))
            print("API request failed. Error logged to", LOG_FILE)

if __name__ == "__main__":
    # Run the script every 5 minutes
    while True:
        make_api_request()
        time.sleep(300)  # Sleep for 300 seconds (5 minutes)

