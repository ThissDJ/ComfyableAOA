import schedule
import requests
import time

def job():
    # Make an HTTP GET request to the specified URL
    url = 'http://localhost:8000/salesMonitor/generate_transaction_report'
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        print("Task executed successfully")
    else:
        print(f"Failed to execute task. Status code: {response.status_code}")

# Schedule the job to run every 5 minutes
schedule.every(5).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
