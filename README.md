# CloudAtCost-Wallet
Python code to export CloudAtCost Wallet Transactions to a .CSV file

This project allows you to log into your CloadAtCost Wallet and create a .CSV of the transactions.  Interactive mode where you enter the username, password, and 2FA code (if needed) manually works. Please install needed modules first (see reqirements.txt).  There is also an automated login using a config file.  The latter is not documented yet, but an example config file is provided.

Time Zone Support:
You can now have tranactions in your local time zone instead of "America/Toronto" time zone.  See TimeZones.EXAMPLES for proper time zone string formats.  Then add, for example,  'timezone,"America/Mountain"' to your config file(s) for America Mountain Time.  Daylight Savings Time is accounted for on both time zones, if needed.

Multiple Account Support:
1) Multiple account support is now available.
2) Rename cac-config.csv to config1.csv
3) Add second account as config2.csv
4) Up to 9 accounts are supported.

Known Issues:
1) Pending Autorization/Confirmation transactions are ignored until complete.
2) There is no way to distingush between purchasing a miner with BTC and an external BTC withdrawal.
3) Not every possible error is handled gracefully.

Google Sheet option pushes the transactions into a google sheet configured in the config file.  Steps to configure include:
1) Create a Google Sheet - add the name of the sheet in the config file
2) Create a worksheet within the Google Sheet - add the name of the worksheet to the config file (default is Sheet1)
3) Create a google Service Account (https://robocorp.com/docs/development-guide/google-sheets/interacting-with-google-sheets)
4) Download the private key JSON file and save in the code folder as "google_creds.json"
4) Within the Google Sheet that was created in Step 1, "Share" the google sheet with the email address of the service account created in step 3

Note on Privacy:
Login credentials are only sent to https://wallet.cloudatcost.com/... and no data is sent to or collected by anyone else.

Note on swivel.run support:
1) CloudAtClost.com and Swivel.run use the same software.
2) Renaming cac.py to swivel.py allows you to export from swivel.
3) The config file, if used, must be named swi-config.csv.
