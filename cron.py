import schedule
import requests
import time

def job():

    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"Job executed at {current_time}")

    # Make an HTTP GET request to the specified URL
    url = 'http://localhost:8000/salesMonitor/generate_transaction_report'
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        print("Task executed successfully")
    else:
        print(f"Failed to execute task. Status code: {response.status_code}")

# Schedule the job to run every 2 hours
schedule.every(2).hours.do(job)
# schedule.every(1).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(2 * 3600)  # Sleep for the scheduled interval of 2 hours
    # time.sleep(1 * 60)  # Sleep for the scheduled interval of 2 hours
