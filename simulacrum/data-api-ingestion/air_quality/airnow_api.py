import os
import json
import requests
from datetime import datetime, timezone
from google.cloud import storage

def upload_to_gcs(local_file, bucket_name, destination_blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file)

def main():
    api_key = os.getenv("AIRNOW_API_KEY")
    bucket_name = os.environ["BUCKET_NAME"]

    url = "https://www.airnowapi.org/aq/observation/zipCode/current/"
    params = {
        "format": "application/json",
        "zipCode": "14850",
        "distance": "25",
        "API_KEY": api_key
    }

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"airnow_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    destination = f"air_quality/airnow/{filename}"
    upload_to_gcs(filename, bucket_name, destination)

    print(f"Uploaded {filename} to gs://{bucket_name}/{destination}")

if __name__ == "__main__":
    main()