# Svitlo App Backend 

The backend is used mostly for push notifications

It provides an endpoint for registering devices with specified queue number 
Constantly sends requests to oblenergo API to monitor, which is externally triggered

It scans API with 12 predefined (for now at least) account numbers for the queues
Saves the result and determines if any valid changes have happened

If any changes detected - sends push messages to all registered devices for the queues that had changes

Three env parameters are used:
* GOOGLE_SHEETS_SERVICE_ACCOUNT - json key data for Google Sheets API service account
* GOOGLE_SHEETS_SPREADSHEET_ID - Google Spreadsheet ID - where the data is saved
* FIREBASE_SERVICE_ACCOUNT - json key data for Firebase Cloud Messaging API service account