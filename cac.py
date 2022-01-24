#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 25 19:28:42 2021

@author: Jeffrey Paul Machado

@license: see MIT license
"""

from datetime import datetime, timedelta
import calendar
from time import time, localtime, strftime, strptime, mktime, sleep
import os
import sys
import csv
import re
from getpass import getpass as getpassword

assert sys.version_info[0] == 3 and sys.version_info[1] > 5, "Python 3.6+ required."


# (Required) external modules
try:
    from twill.commands import reset_browser, log, go, fv, submit, save_html, browser, load_cookies, save_cookies, getinput
    from bs4 import BeautifulSoup
except:
    assert False, "Install requirements.txt Python modules first..."


# (Optional) Time Zone Support
try:
    from time import tzset
    tzsetDisabledInternal = False
except:
    tzsetDisabledInternal = True

try:
    import pytz
    pytzDisabledInternal = False
except:
    pytzDisabledInternal = True


# (Optional) 2FA Support
try:
    import pyotp
    pyotpDisabledInternal = False
except:
    pyotpDisabledInternal = True


# (Optional) Google Sheets Support
try:
    import gspread
    from gspread import Cell
    from google.oauth2 import service_account
    gspredDisabledInternal = False
except:
    gspredDisabledInternal = True

try:
    import coinbasepro as cbp
    cbpDisabledInternal = False
    cbp_client = cbp.PublicClient()
except:
    cbpDisabledInternal = True


default_timezone = "America/Toronto"
configs = []
args = {}
bitcoin = {}
bitcoin_loaded = False
bitcoin_currancy = ""


def main():
    # Process Command Line Arguments
    global args
    args = process_command_arguments()

    # Load Bitcoin Prices
    global bitcoin_currancy

    file_name = "coinbasepro.csv"
    if not cbpDisabledInternal and os.path.exists(file_name):
        update_coinbasepro_usd(file_name)
        bitcoin_currancy = "$"
    if not bitcoin_loaded:
        for year in ["2021", "2022", "2023"]:
            file_name = "Bitstamp_BTCUSD_"+year+"_minute.csv"
            if os.path.exists(file_name):
                load_bitcoin_usd(file_name)
                bitcoin_currancy = "$"
    if not bitcoin_loaded:
        for year in ["2021", "2022", "2023"]:
            file_name = "Bitstamp_BTCEUR_"+year+"_minute.csv"
            if os.path.exists(file_name):
                load_bitcoin_usd(file_name)
                bitcoin_currancy = "€"

    new_config = False
    for file_number in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        if os.path.exists("config"+file_number+".csv"):
            new_config = True
            config = {"new_config": True}
            # Set defaults
            set_defaults(config, file_number)
            # Load Config file
            load_config(config)
            # Update with command line arguments
            config.update(args)
            # Push config
            configs.append(config)

    if new_config:
        for config in configs:
            if not config["silentMode"]:
                print("Config file", config["configFile"], "loaded...")
            html = load_transactions(config)
            process_transactions(config, html)
    else:
        config = {}
        set_defaults(config)
        load_config(config)
        config.update(args)
        configs.append(config)
        html = load_transactions(config)
        process_transactions(config, html)


def convert_timezones(timestamp_string, timezone_src, timezone_dest):
    local_tz = pytz.timezone(timezone_src)
    dest_tz = pytz.timezone(timezone_dest)
    UTC_tz = pytz.timezone("UTC")
    ts = datetime.strptime(timestamp_string, '%Y-%m-%d %H:%M:%S')
    ts = local_tz.localize(ts)
    tz_dest = ts.astimezone(dest_tz)
    ts_dest = str(tz_dest)
    ts_dest = ts_dest[0:19]+" "+tz_dest.tzname()+ts_dest[19:]
    ts_UTC = str(ts.astimezone(UTC_tz))[0:19]
    timestamp = datetime.strptime(ts_UTC, '%Y-%m-%d %H:%M:%S')
    epoch = int(calendar.timegm(timestamp.utctimetuple()))

    return ts_dest, epoch


def get_epoch_from_utc(timestamp_string):
    return int(datetime.fromisoformat(timestamp_string+"+00:00").timestamp())


def process_command_arguments():
    cl_config = {}
    for arg in sys.argv:
        if len(arg) > 1 and arg[0:2] == "--":
            lines = arg[2:].split('=', 1)
            if len(lines) < 2:
                assert False, f"Argument '{arg}' not valid!"

            if tzsetDisabledInternal and pytzDisabledInternal and lines[0] == "timezone":
                print("This platform does not support time zone changing!")
                assert False, "Install 'pytz' module to fix..."

            if lines[1] == "False":
                cl_config[lines[0]] = False
            elif lines[1] == "True":
                cl_config[lines[0]] = True
            else:
                cl_config[lines[0]] = lines[1]

        elif len(arg) > 1 and arg[0] == "-":
            if arg[1:] == "init-cbp":
                bootstrap_coinbasepro_usd(file_name="coinbasepro.csv")
                sys.exit()
            if arg[1:] == "exit":
                sys.exit()

    return cl_config


def load_bitcoin_usd(file_name, bitcoin=bitcoin):
    global bitcoin_loaded
    print(f"Loading '{file_name}'...")
    with open(file_name, mode='r') as file:
        bitcoin_csv = csv.reader(file)
        counter = -1
        for line in bitcoin_csv:
            if counter > 0:
                bitcoin[line[0]] = line[1:]
            counter += 1
        bitcoin_loaded = True


def bootstrap_coinbasepro_usd(file_name="coinbasepro.csv"):
    print(f"Initializing '{file_name}'...")
    with open(file_name, "w") as f:
        f.write(
            "1609372800,2020-12-31 00:00:00,BTC/USD,28897.42,28934.56,28891.76,28934.56,10.46338356\n")
    update_coinbasepro_usd(file_name)


def load_coinbasepro_usd(file_name, bitcoin=bitcoin):
    global bitcoin_loaded
    print(f"Loading '{file_name}'...")
    with open(file_name, mode='r') as file:
        bitcoin_csv = csv.reader(file)
        for line in bitcoin_csv:
            bitcoin[line[0]] = line[1:]
            last = line
        bitcoin_loaded = True
        return last


def update_coinbasepro_usd(file_name="coinbasepro.csv", bitcoin=bitcoin):
    last = load_coinbasepro_usd(file_name, bitcoin)

    print(f"Updating '{file_name}'...", end='', flush=True)
    start = datetime.fromisoformat(last[1]) + timedelta(seconds=60)
    end = start + timedelta(minutes=299)

    try:
        result = cbp_client.get_product_historic_rates(
            "BTC-USD", start.isoformat(), end.isoformat())
    except:
        print()
        print("Warning: Unable to download from Coinbase Pro", end="")
        result = []

    previous = []

    while len(result) > 0:
        sleep(0.34)
        print(".", end='', flush=True)

        start += timedelta(minutes=300)
        end += timedelta(minutes=300)

        previous = result
        try:
            result = cbp_client.get_product_historic_rates(
                "BTC-USD", start.isoformat(), end.isoformat())
        except:
            print()
            print("Warning: Disconnected from Coinbase Pro", end="")
            result = []

        if len(result) == 0:
            break

        result = result + previous

    result = previous
    result.reverse()
    print("loaded", len(result)-1, "records.")
    #print("")

    with open(file_name, 'a') as f:
        for x in range(0, len(result)-1):
            timestamp = result[x]["time"].isoformat().replace("T", " ")
            #_, epoch = convert_timezones(timestamp, "UTC", "UTC")
            epoch = get_epoch_from_utc(timestamp)
            bitcoin[str(epoch)] = [timestamp, 'BTC/USD', str(float(result[x]["open"])), str(float(result[x]["high"])), str(
                float(result[x]["low"])), str(float(result[x]["close"])), str(float(result[x]["volume"]))]
            f.write(str(epoch)+','+timestamp+','+'BTC/USD,'+str(float(result[x]["open"]))+','+str(float(result[x]["high"]))+','+str(
                float(result[x]["low"]))+','+str(float(result[x]["close"]))+','+str(float(result[x]["volume"]))+"\n")


def set_defaults(config, file_number=""):
    config["pythonScriptName"] = os.path.basename(__file__).lower()

    config["timezone"] = default_timezone

    config["useragent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36 Edg/90.0.818.46"

    config["file_number"] = file_number

    # CloudAtCost.com URLs or Swivel.run
    if config["pythonScriptName"] == "swivel.py":
        config["baseURL"] = "https://wallet.swivel.run/"
        config["prefix"] = "swi"
    else:
        config["baseURL"] = "https://wallet.cloudatcost.com/"
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
    # The name of the Google Sheet to populate
    config["googleSheet"] = "CloudAtCost"
    # The name of the google worksheet tab inside the above Spreadsheet

    if file_number == "":
        config["googleWorksheet"] = "Sheet1"
    else:
        config["googleWorksheet"] = "Sheet"+file_number

    # Filenames
    if file_number == "":
        config["configFile"] = config["prefix"]+"-config"+".csv"
        config["cookieFile"] = config["prefix"]+"-cookie"+".bin"
    else:
        config["configFile"] = "config"+file_number+".csv"
        config["cookieFile"] = "cookie"+file_number+".bin"

    if config["addDateTime"]:
        config["summaryHtmlFile"] = "Summary "+config["datetime"]+".html"
        config["transactionHtmlFile"] = "Transactions " + \
            config["datetime"]+".html"
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
                llen = len(lines)
                if llen == 0 or (llen == 1 and len(lines[0].strip(" \t")) == 0):
                    break
                if llen == 1 and lines[0].strip(" \t")[0] == '#':
                    break
                if llen != 2:
                    assert False, f"Config file {config['configFile']} corrupt!"
                #lines[1].replace('“','')

                if tzsetDisabledInternal and pytzDisabledInternal and lines[0] == "timezone":
                    print("This platform does not support time zone changing!")
                    assert False, "Install 'pytz' module to fix..."

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
        config["summaryHtmlFile"] = config["saveFilePrefix"] + \
            config["summaryHtmlFile"]
        config["transactionHtmlFile"] = config["saveFilePrefix"] + \
            config["transactionHtmlFile"]
        config["csvFile"] = config["saveFilePrefix"] + config["csvFile"]
    elif "new_config" in config and config["file_number"] != "":
        config["summaryHtmlFile"] = config["file_number"] + \
            " " + config["summaryHtmlFile"]
        config["transactionHtmlFile"] = config["file_number"] + \
            " " + config["transactionHtmlFile"]
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
    #retries = -1
    while browser.url != config["baseURL"] or browser.code != 200:
        if browser.code in [200, None]:
            retries = -1
        retries += 1
        # Check for retry failure...
        if retries > 3 and (browser.url != config["baseURL"] or browser.code != 200):
            assert False, "Retry max exceeded!"
        elif not config["silentMode"] and retries > 0:
            print(browser.url, "==>", browser.code)
            print("Retrying...")

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

        if browser.code in [200, 422] and browser.url == config["auth_2faURL"]:
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
                    wait = [2, 30, 31, 31][retries]
                    if not config["silentMode"]:
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
    totalBTCminedUSD = 0.0
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
                if not tzsetDisabledInternal:
                    os.environ['TZ'] = default_timezone
                    tzset()
                ttime = strptime(res[1], "%b %d, %Y %I:%M %p")

                transaction_epoch = int(mktime(ttime))

                # Optionally output Date/Time in alternate timezone
                date_time_fmt = "%Y-%m-%d %H:%M"

                if not tzsetDisabledInternal:
                    os.environ['TZ'] = config["timezone"]
                    tzset()
                    date_time_fmt = "%Y-%m-%d %H:%M %Z%z"

                transaction_time = strftime(
                    date_time_fmt, localtime(transaction_epoch))

                if tzsetDisabledInternal and not pytzDisabledInternal:
                    transaction_time, transaction_epoch = convert_timezones(
                        transaction_time+":00", default_timezone, config["timezone"])

                if "year" in config and transaction_time[0:4] != config["year"]:
                    continue

                # Line 3
                line3 = res[2].split(" ")
                transaction_amount = line3[0]
                transaction_amount_type = line3[1]

                fmv_cur = 0.0
                if str(transaction_epoch) in bitcoin:
                    btc = bitcoin[str(transaction_epoch)]
                    #fmv_cur = (float(btc_USD[3])+float(btc_USD[4]))/2.0
                    fmv_cur = float(btc[2])

                transaction_amount_cur = float(transaction_amount) * fmv_cur

                if transaction_type == "Withdraw":
                    totalBTCwithdrawn += float(transaction_amount)
                elif len(line1) == 3:  # Miner Deposit
                    totalBTCmined += float(transaction_amount)
                    totalBTCminedUSD += float(transaction_amount) * fmv_cur
                    try:
                        minersBTCmined[miner_id] += float(transaction_amount)
                    except:
                        minersBTCmined[miner_id] = float(transaction_amount)
                elif len(line1) == 2:  # BTC deposit
                    totalBTCdeposited += float(transaction_amount)

                transaction = []
                transaction.append(transaction_epoch)
                transaction.append(transaction_id)
                transaction.append(transaction_time)
                transaction.append(transaction_type)
                transaction.append(miner_id)
                transaction.append(transaction_amount)
                transaction.append(transaction_amount_type)
                if bitcoin_loaded:
                    transaction.append(
                        bitcoin_currancy+str(transaction_amount_cur))
                    transaction.append(bitcoin_currancy+str(fmv_cur))

                transactions.insert(0, transaction)

    if config["populategooglesheet"] and totalTransactions > 0:
        cells.append(Cell(row=row, col=1, value="Miner ID"))
        cells.append(Cell(row=row, col=2, value="Epoch"))
        cells.append(Cell(row=row, col=3, value="Transcation"))
        cells.append(Cell(row=row, col=4, value="Amount"))
        cells.append(Cell(row=row, col=5, value="Date"))
        cells.append(Cell(row=row, col=6, value="Type"))
        cells.append(Cell(row=row, col=7, value="Currency"))
        if bitcoin_loaded:
            cells.append(Cell(row=row, col=8, value="FMV"))
            cells.append(Cell(row=row, col=9, value="Bitcoin"))

        row += 1
        for transaction in transactions:
            cells.append(Cell(row=row, col=1, value=transaction[4]))
            cells.append(Cell(row=row, col=2, value=transaction[0]))
            cells.append(Cell(row=row, col=3, value=transaction[1]))
            cells.append(Cell(row=row, col=4, value=transaction[5]))
            cells.append(Cell(row=row, col=5, value=transaction[2]))
            cells.append(Cell(row=row, col=6, value=transaction[3]))
            cells.append(Cell(row=row, col=7, value=transaction[6]))
            if bitcoin_loaded:
                cells.append(Cell(row=row, col=8, value=transaction[7]))
                cells.append(Cell(row=row, col=9, value=transaction[8]))
            row += 1

    if totalTransactions > 0:
        if config["saveCSV"]:
            if not config["silentMode"]:
                print("Saving '"+config["csvFile"]+"'")

            with open(config["csvFile"], 'w') as f:
                if bitcoin_loaded:
                    f.write(
                        "Epoch, Transaction, Date, Type, Miner ID, Amount, Currency, FMV, Bitcoin\n")
                else:
                    f.write(
                        "Epoch, Transaction, Date, Type, Miner ID, Amount, Currency\n")

                for transaction in transactions:
                    f.write(re.sub("'", '', str(transaction)[1:-1])+"\n")

        if config["populategooglesheet"]:
            if not config["silentMode"]:
                print("Populating Google Sheet")

            # google sheets scope setup
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/spreadsheets',
                     'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']

            if not os.path.exists(config["googleCreds"]):
                assert False, "Google service account credentials file not found (" + \
                    config["googleCreds"]+")"
            creds = service_account.Credentials.from_service_account_file(
                config["googleCreds"], scopes=scope)
            client = gspread.authorize(creds)
            sheet = client.open(config["googleSheet"])  # the spreadhseet name
            # the worksheet name (in the spreadsheet above)
            wksheet = sheet.worksheet(config["googleWorksheet"])
            wksheet.update_cells(cells, value_input_option='USER_ENTERED')

        if not config["silentMode"]:
            print("")
            print("Total Transactions   =", totalTransactions)
            print("")
            print("Total BTC Deposited  =", round(totalBTCdeposited, 8))
            print("Total BTC Withdrawn  =", round(totalBTCwithdrawn, 8))
            print("")
            print("Total BTC Mined      =", round(totalBTCmined, 8))
            if bitcoin_loaded:
                print("Total BTC Mined Fiat = "+bitcoin_currancy +
                      str(round(totalBTCminedUSD, 2)))
            print("")
            for miner in sorted(minersBTCmined.keys()):
                print(f'Miner {miner} = {minersBTCmined[miner]:.8f} BTC')
            print("")
    elif not config["silentMode"]:
        print("No Transactions!")


if __name__ == "__main__":
    main()
