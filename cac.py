#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 25 19:28:42 2021

@author: Jeffrey Paul Machado

@license: see MIT license
"""

from getpass import getpass as getpassword

import re
import csv

from time import time, localtime, strftime, strptime, mktime, sleep

import os

from sys import version_info as vinfo
assert vinfo[0]==3 and vinfo[1]>5, "Python 3.6+ required."


# (Required) external modules
try:
    from twill.commands import reset_browser, log, go, fv, submit, save_html, browser, load_cookies, save_cookies, getinput
    from bs4 import BeautifulSoup
except:
    assert False, "Install requirements.txt Python modules first..."


# (Optional) 2FA Support
try:
    import pyotp
    pyotpDisabledInternal = False
except:
    pyotpDisabledInternal = True


# (Optional) Google Sheets Support
try:
    import gspread
    from gspread.models import Cell
    from google.oauth2 import service_account
    gspredDisabledInternal = False
except:
    gspredDisabledInternal = True

configs = []

def main():
    new_config = False
    for file_number in ["1","2","3","4","5","6","7","8","9"]:
        if os.path.exists("config"+file_number+".csv"):
            new_config = True
            config = { "new_config":True }
            set_defaults(config, file_number)
            load_config(config)
            configs.append(config)
        
    if new_config:
        for config in configs:
            if not config["silentMode"]:
                print("Config file",config["configFile"],"loaded...")
            html = load_transactions(config)
            process_transactions(config, html)
    else:
        config = {}
        set_defaults(config)
        load_config(config)
        configs.append(config)
        html = load_transactions(config)
        process_transactions(config, html)


def set_defaults(config, file_number=""):  
    config["pythonScriptName"] = os.path.basename(__file__).lower()

    config["useragent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36 Edg/90.0.818.46"

    config["file_number"] = file_number

    # CloudAtCost.com URLs or Swivel.run
    if config["pythonScriptName"] == "swivel.py":
        config["baseURL"] = "https://wallet.swivel.run/"
        config["prefix"] = "swi"
    else:
        config["baseURL"] = "https://wallet.cloudatcost.com/"    # Summary Page
        config["prefix"] = "cac"

    config["loginURL"] = config["baseURL"]+"login"
    config["auth_2faURL"] = config["baseURL"]+"auth"
    config["walletURL"] = config["baseURL"]+"wallet"
    config["transactionURL"] = config["baseURL"]+"transaction"

    ltime = localtime(time())
    config["datetime"] = strftime("%Y-%m-%d %H-%M", ltime)

    # Credentials
    config["username"] = ""
    config["password"] = ""
    config["auth_2fa"] = ""
    config["run_mode"] = "Interactive"

    # Config
    config["useCookies"] = False
    config["saveHTML"] = False
    config["saveCSV"] = True
    config["silentMode"] = False
    config["addDateTime"] = True
    
    config["populategooglesheet"] = False
    config["googleSheet"] = "CloudAtCost"   # The name of the Google Sheet to populate
    # The name of the google worksheet tab inside the above Spreadsheet
    config["googleWorksheet"] = "Sheet1"

    # Filenames
    if file_number == "":
        config["configFile"] = config["prefix"]+"-config"+".csv"
        config["cookieFile"] = config["prefix"]+"-cookie"+".bin"
    else:
        config["configFile"] = "config"+file_number+".csv"
        config["cookieFile"] = "cookie"+file_number+".bin"
        
    if config["addDateTime"]:
        config["summaryHtmlFile"] = "Summary "+config["datetime"]+".html"
        config["transactionHtmlFile"] = "Transactions "+config["datetime"]+".html"
        config["csvFile"] = "Transactions "+config["datetime"]+".csv"
    else:
        config["summaryHtmlFile"] = "Summary.html"
        config["transactionHtmlFile"] = "Transactions.html"
        config["csvFile"] = "Transactions.csv"

    config["googleCreds"] = "google_creds.json"


def load_config(config):
    # Delete cookies file if config file was modified
    config["configModified"] = False
    try:
        configTime = os.path.getmtime(config["configFile"])
        cookieTime = os.path.getmtime(config["cookieFile"])
        if configTime > cookieTime:
            os.unlink(config["cookieFile"])
            config["configModified"] = True
    except:
        pass

    # Load configFile, if available
    try:
        with open(config["configFile"], mode='r') as file:
            csvf = csv.reader(file)
            for lines in csvf:
                if lines[1] == "False":
                    config[lines[0]] = False
                elif lines[1] == "True":
                    config[lines[0]] = True
                else:
                    config[lines[0]] = lines[1]
    except FileNotFoundError:
        pass

    if gspredDisabledInternal and config["populategooglesheet"]:
        assert False, "Python 'gspred' and 'google' modules not installed!"

    if config["configModified"] and not config["silentMode"]:
        print("Notice: Config file modified, cookie file removed.")

    if config["run_mode"] == "Interactive":
        config["interactive"] = True
    elif config["run_mode"] == "Automatic":
        config["interactive"] = False
        config["useCookies"] = True
    else:
        assert False, "Bad Run Mode"

    # Setup TOPT with 2FA Secret, if needed
    if not config["interactive"] and config["auth_2fa"] != "":
        if pyotpDisabledInternal:
            assert False, "Python 'pyotp' module not installed!"
        else:
            config["totp"] = pyotp.TOTP(config["auth_2fa"])
    
    if "saveFilePrefix" in config:
        config["summaryHtmlFile"] = config["saveFilePrefix"] + config["summaryHtmlFile"]
        config["transactionHtmlFile"] = config["saveFilePrefix"] + config["transactionHtmlFile"]
        config["csvFile"] = config["saveFilePrefix"] + config["csvFile"]
    elif "new_config" in config and config["file_number"] != "":
        config["summaryHtmlFile"] = config["file_number"] + " " + config["summaryHtmlFile"]
        config["transactionHtmlFile"] = config["file_number"] + " " + config["transactionHtmlFile"]
        config["csvFile"] = config["file_number"] + " " + config["csvFile"]
        


def load_transactions(config):
    # Initialize Twill Browser
    log.disabled = True
    reset_browser()
    browser.agent_string = config["useragent"]

    # See if we can load cached cookies
    if config["useCookies"]:
        try:
            load_cookies(config["cookieFile"])
        except:
            pass

    # Do the login and possibly 2FA, if needed
    retries = -1
    while browser.url != config["baseURL"] or browser.code != 200:
        retries += 1
        # Check for retry failure...
        if retries > 3 and (browser.url != config["baseURL"] or browser.code != 200):
            assert False, "Retry max exceeded!"
        elif not config["silentMode"] and retries > 0:
            print("Retrying...")
            print(browser.url, "==>", browser.code)

        if browser.url == None:
            if not config["silentMode"]:
                print("Accessing", config["baseURL"])
            go(config["baseURL"])

        if browser.code == 200 and browser.url == config["loginURL"]:
            assert browser.forms != [], "Login Form Missing!"
            if config["interactive"]:
                config["username"] = getinput("Username: ")
                config["password"] = getpassword("Password: ")
            fv("login", "email",  config["username"])
            fv("login", "password", config["password"])
            if config["interactive"]:
                #username = ""
                config["password"] = ""
            elif not config["silentMode"]:
                print("Logging In...")
            sleep(1)
            submit("0")
            if browser.code != 200 or browser.url == config["loginURL"]:
                if not config["silentMode"]:
                    print("Login Failed!")
                if not config["interactive"]:
                    if not config["silentMode"]:
                        print("Retrying in 30 seconds...")
                        sleep(30)

        if browser.code == 200 and browser.url == config["auth_2faURL"]:
            assert browser.forms != [], "2FA Form Missing!"
            if config["interactive"]:
                authCode = getinput("2FA Code: ")
            else:
                sleep(1)
                authCode = str(config["totp"].now())
            fv("authCheck", "authCode", authCode)
            if config["interactive"]:
                authCode = ""
            elif not config["silentMode"]:
                print("Generating 2FA Code...")
            submit("0")

            # check if code expired
            if browser.code == 422:
                if not config["silentMode"]:
                    print("422: 2FA Failed!")
                if not config["interactive"]:
                    wait = [1, 30, 31, 31][retries]
                    if not config["silentMode"] and wait > 2:
                        print("Retrying in", wait, "seconds...")
                    sleep(wait)

        if browser.code == 404:
            assert False, "404: Page Not Found!"

        if browser.code == 500:
            assert False, "500: Internal Server Error!"

        # Needs better verification via HTML
        if browser.code == 502:
            assert False, "502: Website down for maintence!"

        if browser.code == 504:
            assert False, "504: Gateway Timeout!"

    if config["saveHTML"]:
        if not config["silentMode"]:
            print("Saving HTML", config["summaryHtmlFile"])
        save_html(config["summaryHtmlFile"])

    #print("Loading Wallet...")
    #go(walletURL)

    if not config["silentMode"]:
        print("Loading Transactions...")

    go(config["transactionURL"])
    assert browser.code == 200, "Failed to Load Transactions"

    if config["saveHTML"]:
        if not config["silentMode"]:
            print("Saving HTML", config["transactionHtmlFile"])
        save_html(config["transactionHtmlFile"])

    if not config["interactive"] or config["useCookies"]:
        if not config["silentMode"]:
            print("Saving Cookies...")
        save_cookies(config["cookieFile"])
    
    return browser.html
        

def process_transactions(config, html):
    # Parse HTML
    if not config["silentMode"]:
        print("Processing Transactions...")
    soup = BeautifulSoup(html, "lxml")

    transactions = []
    totalTransactions = 0
    totalBTCdeposited = 0.0
    totalBTCwithdrawn = 0.0
    totalBTCmined = 0.0
    minersBTCmined = {}

    if config["populategooglesheet"]:
        row = 1  # starting row in the google sheet
        cells = []
        # mark the time in the google sheet
        cells.append(Cell(row=row, col=1, value=config["datetime"]))
        row += 1

    for link in soup.find_all("a")[::-1]:
        res = re.sub('(\t| )+', ' ', link.text)
        res = re.sub('\n+', '\n', res)
        res = re.sub(' 0.', "0.", res)

        res = res.strip()
        res = res.splitlines()
        if len(res) == 3:
            date = res[1].split(" ")
            if len(date) == 5:

                totalTransactions += 1
                transaction_id = totalTransactions

                # Line 1
                miner_id = 0
                line1 = res[0].split(" ")
                transaction_type = line1[0]
                if len(line1) == 3:
                    miner_id = int(line1[2][0:-1])

                # Line 2
                ttime = strptime(res[1], "%b %d, %Y %I:%M %p")
                transaction_time = strftime("%Y-%m-%d %H:%M", ttime)

                # Synthetic ID (Time + Miner)
                transaction_sid = int(mktime(ttime))*10000000+miner_id

                # Line 3
                line3 = res[2].split(" ")
                transaction_amount = line3[0]
                transaction_amount_type = line3[1]

                if transaction_type == "Withdraw":
                    totalBTCwithdrawn += float(transaction_amount)
                elif len(line1) == 3:  # Miner Deposit
                    totalBTCmined += float(transaction_amount)
                    try:
                        minersBTCmined[miner_id] += float(transaction_amount)
                    except:
                        minersBTCmined[miner_id] = float(transaction_amount)
                elif len(line1) == 2:  # BTC deposit
                    totalBTCdeposited += float(transaction_amount)

                transaction = []
                transaction.append(transaction_sid)
                transaction.append(transaction_id)
                transaction.append(transaction_time)
                transaction.append(transaction_type)
                transaction.append(miner_id)
                transaction.append(transaction_amount)
                transaction.append(transaction_amount_type)
                transactions.insert(0, transaction)

    if config["populategooglesheet"] and totalTransactions > 0:
        cells.append(Cell(row=row, col=1, value="Miner ID"))
        cells.append(Cell(row=row, col=2, value="SID"))
        cells.append(Cell(row=row, col=3, value="Transcation"))
        cells.append(Cell(row=row, col=4, value="Amount"))
        cells.append(Cell(row=row, col=5, value="Date"))
        cells.append(Cell(row=row, col=6, value="Type"))
        cells.append(Cell(row=row, col=7, value="Currency"))
        row += 1
        for transaction in transactions:
            cells.append(Cell(row=row, col=1, value=transaction[4]))
            cells.append(Cell(row=row, col=2, value=transaction[0]))
            cells.append(Cell(row=row, col=3, value=transaction[1]))
            cells.append(Cell(row=row, col=4, value=transaction[5]))
            cells.append(Cell(row=row, col=5, value=transaction[2]))
            cells.append(Cell(row=row, col=6, value=transaction[3]))
            cells.append(Cell(row=row, col=7, value=transaction[6]))
            row += 1

    if totalTransactions > 0:
        if config["saveCSV"]:
            if not config["silentMode"]:
                print("Saving '"+config["csvFile"]+"'")

            with open(config["csvFile"], 'w') as f:
                f.write("SID, Transaction, Date, Type, Miner ID, Amount, Currency\n")
                for transaction in transactions:
                    f.write(re.sub("'", '', str(transaction)[1:-1])+"\n")

        if config["populategooglesheet"]:
            if not config["silentMode"]:
                print("Populating Google Sheet")

            # google sheets scope setup
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/spreadsheets',
                     'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']

            try:
                private_file = open(config["googleCreds"], mode='r')
                creds = service_account.Credentials.from_service_account_file(
                    config["googleCreds"], scopes=scope)
            except FileNotFoundError:
                print(
                    "Google service account credentials file not found ("+config["googleCreds"]+")")
                assert False, "Exiting"
            client = gspread.authorize(creds)
            sheet = client.open(config["googleSheet"])  # the spreadhseet name
            # the worksheet name (in the spreadsheet above)
            wksheet = sheet.worksheet(config["googleWorksheet"])
            wksheet.update_cells(cells, value_input_option='USER_ENTERED')

        if not config["silentMode"]:
            print("")
            print("Total Transactions  =", totalTransactions)
            print("")
            print("Total BTC Deposited =", round(totalBTCdeposited, 8))
            print("Total BTC Withdrawn =", round(totalBTCwithdrawn, 8))
            print("")
            print("Total BTC Mined     =", round(totalBTCmined, 8))
            print("")
            for miner in sorted(minersBTCmined.keys()):
                print(f'Miner {miner} = {minersBTCmined[miner]:.8f} BTC')
            print("")
    elif not config["silentMode"]:
        print("No Transactions!")

if __name__ == "__main__":
    main()
