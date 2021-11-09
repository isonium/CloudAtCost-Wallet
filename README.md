# CloudAtCost-Wallet
Python code to export CloudAtCost Wallet Transactions to a .CSV file

This project allows you to log into your CloadAtCost Wallet and create a .CSV of the transactions.  Interactive mode where you enter the username, password, and 2FA code (if needed) manually works. Please install needed modules first (see reqirements.txt).  There is also an automated login using a config file.  The latter is not documented yet, but an example config file is provided. 

Note on Privacy: Login credentials are only sent to https://wallet.cloudatcost.com/... and no data is sent to or collected by anyone else.

Note on swivel.run: CloudAtClost.com and Swivel.run appear to use the same software.  Renaming cac.py to swivel.py might allow you to export from swivel.  So far this is untested.
