from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Path to your service account file
credentials_path = r"C:\Users\ASUS\Downloads\dotted-ranger-452122-e4-8ba8546f0499.json"

# Load the credentials
credentials = service_account.Credentials.from_service_account_file(credentials_path)

# Test the credentials by making a request to Google Cloud Storage (you can use any other service you are using)
from google.cloud import storage

client = storage.Client(credentials=credentials)
print(client.list_buckets())  # This should list your project buckets if the credentials are valid
