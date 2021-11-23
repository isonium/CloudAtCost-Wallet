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
import sys
assert sys.version_info[0] == 3, "Python 3.x required."


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


def main():
    get_cac_wallet()


def get_cac_wallet():
    pythonScriptName = os.path.basename(__file__).lower()

    useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36 Edg/90.0.818.46"
    
    # CloudAtCost.com URLs or Swivel.run
    if pythonScriptName == "swivel.py":
        baseURL = "https://wallet.swivel.run/"
        prefix = "swi"
    else:
        baseURL = "https://wallet.cloudatcost.com/"    # Summary Page
        prefix = "cac"

    loginURL = baseURL+"login"
    auth_2faURL = baseURL+"auth"
    #walletURL = baseURL+"wallet"
    transactionURL = baseURL+"transaction"

    ltime = localtime(time())
    datetime = strftime("%Y-%m-%d %H-%M", ltime)

    # Credentials
    username = ""
    password = ""
    auth_2fa = ""
    run_mode = "Interactive"

    # Config
    useCookies = False
    saveHTML = False
    saveCSV = True
    silentMode = False
    addDateTime = True
    populateGoogleSheet = False
    googleSheet = "CloudAtCost"   # The name of the Google Sheet to populate
    # The name of the google worksheet tab inside the above Spreadsheet
    googleWorksheet = "Sheet1"

    # Filenames
    configFile = prefix+"-config.csv"
    cookieFile = prefix+"-cookie.txt"

    if addDateTime:
        summaryHtmlFile = "Summary "+datetime+".html"
        transactionHtmlFile = "Transactions "+datetime+".html"
        csvFile = "Transactions "+datetime+".csv"
    else:
        summaryHtmlFile = "Summary.html"
        transactionHtmlFile = "Transactions.html"
        csvFile = "Transactions.csv"

    googleCreds = "google_creds.json"

    # Delete cookies file if config file was modified
    configModified = False
    try:
        configTime = os.path.getmtime(configFile)
        cookieTime = os.path.getmtime(cookieFile)
        if configTime > cookieTime:
            configModified = True
            os.unlink(cookieFile)
    except:
        pass

    # Load configFile, if available
    try:
        with open(configFile, mode='r') as file:

            csvf = csv.reader(file)
            for lines in csvf:
                if lines[0] == 'username':
                    username = lines[1]
                elif lines[0] == 'password':
                    password = lines[1]
                elif lines[0] == 'auth_2fa':
                    auth_2fa = lines[1]
                elif lines[0] == 'useragent':
                    useragent = lines[1]
                elif lines[0] == 'run_mode':
                    run_mode = lines[1]
                elif lines[0] == 'savehtml':
                    if lines[1] == 'True':
                        saveHTML = True
                    else:
                        saveHTML = False
                elif lines[0] == 'populategooglesheet':
                    if lines[1] == 'True':
                        populateGoogleSheet = True
                    else:
                        populateGoogleSheet = False
                elif lines[0] == 'googlesheet':
                    googleSheet = lines[1]
                elif lines[0] == 'googleworksheet':
                    googleWorksheet = lines[1]
                elif lines[0] == 'savecsv':
                    if lines[1] == 'True':
                        saveCSV = True
                    else:
                        saveCSV = False
                elif lines[0] == 'silenced':
                    if lines[1] == 'True':
                        silentMode = True
                    else:
                        silentMode = False
    except:
        pass

    if gspredDisabledInternal and populateGoogleSheet:
        assert False, "Python 'gspred' and 'google' modules not installed!"

    if configModified and not silentMode:
        print("Notice: Config file was modified, so cookie file removed.")

    if run_mode == "Interactive":
        interactive = True
    elif run_mode == "Automatic":
        interactive = False
        useCookies = True
    else:
        assert False, "Bad Run Mode"

    # Setup TOPT with 2FA Secret, if needed
    if not interactive and auth_2fa != "":
        if pyotpDisabledInternal:
            assert False, "Python 'pyotp' module not installed!"
        else:
            totp = pyotp.TOTP(auth_2fa)

    # Done checking options and modules

    # Initialize Twill Browser
    log.disabled = True
    reset_browser()
    browser.user_agent = useragent

    # See if we can load cached cookies
    if useCookies:
        try:
            load_cookies(cookieFile)
        except:
            pass

    # Do the login and possibly 2FA, if needed
    while browser.url != baseURL or browser.code != 200:
        try:
            retries += 1
        except NameError:
            retries = 0

        # Check for retry failure...
        if retries > 3 and (browser.url != baseURL or browser.code != 200):
            assert False, "Retry max exceeded!"
        elif not silentMode and retries > 0:
            print("Retrying...")
            print(browser.url, "==>", browser.code)

        if browser.url == None:
            if not silentMode:
                print("Accessing", baseURL)
            go(baseURL)

        if browser.code == 200 and browser.url == loginURL:
            assert browser.forms != [], "Login Form Missing!"
            if interactive:
                username = getinput("Username: ")
                password = getpassword("Password: ")
            fv("login", "email",  username)
            fv("login", "password", password)
            if interactive:
                #username = ""
                password = ""
            elif not silentMode:
                print("Logging In...")
            submit("0")
            if browser.code != 200 or browser.url == loginURL:
                if not silentMode:
                    print("Login Failed!")
                if not interactive:
                    if not silentMode:
                        print("Retrying in 30 seconds...")
                        sleep(30)

        if browser.code == 200 and browser.url == auth_2faURL:
            assert browser.forms != [], "2FA Form Missing!"
            if interactive:
                authCode = getinput("2FA Code: ")
            else:
                authCode = str(totp.now())
            fv("authCheck", "authCode", authCode)
            if interactive:
                authCode = ""
            elif not silentMode:
                print("Generating 2FA Code...")
            submit("0")

            # check if code expired
            if browser.code == 422:
                if not silentMode:
                    print("422: 2FA Failed!")
                if not interactive:
                    wait = [1, 30, 31, 31][retries]
                    if not silentMode and wait > 2:
                        print("Retrying in", wait, "seconds...")
                    sleep(wait)

        if browser.code == 500:
            assert False, "500: WInternal Server Error!"

        # Needs better verification via HTML
        if browser.code == 502:
            assert False, "502: Website down for maintence!"

        if browser.code == 504:
            assert False, "504: Gateway Timeout!"

    if saveHTML:
        if not silentMode:
            print("Saving HTML", summaryHtmlFile)
        save_html(summaryHtmlFile)

    #print("Loading Wallet...")
    #go(walletURL)

    if not silentMode:
        print("Loading Transactions...")

    go(transactionURL)
    assert browser.code == 200, "Failed to Load Transactions"

    if saveHTML:
        if not silentMode:
            print("Saving HTML", transactionHtmlFile)
        save_html(transactionHtmlFile)

    if not interactive or useCookies:
        if not silentMode:
            print("Saving Cookies...")
        save_cookies(cookieFile)

    # Parse HTML
    soup = BeautifulSoup(browser.html, "lxml")

    transactions = []
    totalTransactions = 0
    totalBTCdeposited = 0.0
    totalBTCwithdrawn = 0.0
    totalBTCmined = 0.0
    minersBTCmined = {}

    if populateGoogleSheet:
        row = 1  # starting row in the google sheet
        cells = []
        # mark the time in the google sheet
        cells.append(Cell(row=row, col=1, value=datetime))
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

    if populateGoogleSheet and totalTransactions > 0:
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
        if saveCSV:
            if not silentMode:
                print("Saving '"+csvFile+"'")

            with open(csvFile, 'w') as f:
                f.write("SID, Transaction, Date, Type, Miner ID, Amount, Currency\n")
                for transaction in transactions:
                    f.write(re.sub("'", '', str(transaction)[1:-1])+"\n")

        if populateGoogleSheet:
            if not silentMode:
                print("Populating Google Sheet")

            # google sheets scope setup
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/spreadsheets',
                     'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']

            try:
                private_file = open(googleCreds, mode='r')
                creds = service_account.Credentials.from_service_account_file(
                    googleCreds, scopes=scope)
            except FileNotFoundError:
                print(
                    "Google service account credentials file not found ("+googleCreds+")")
                assert False, "Exiting"
            client = gspread.authorize(creds)
            sheet = client.open(googleSheet)  # the spreadhseet name
            # the worksheet name (in the spreadsheet above)
            wksheet = sheet.worksheet(googleWorksheet)
            wksheet.update_cells(cells, value_input_option='USER_ENTERED')

        if not silentMode:
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
    elif not silentMode:
        print("No Transactions!")


if __name__ == "__main__":
    main()
