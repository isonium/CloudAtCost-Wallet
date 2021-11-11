#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 25 19:28:42 2021

@author: Jeffrey Paul Machado

@license: see MIT license
"""

import os

from time import time, localtime, strftime, strptime, mktime, sleep

import csv
import re

from twill.commands import reset_browser, log, go, fv, submit, save_html,\
                           browser, load_cookies, save_cookies, getinput

from getpass import getpass as getpassword

import pyotp

from bs4 import BeautifulSoup

pythonScriptName = os.path.basename(__file__).lower()

# CloudAtCost.com URLs or Swivel.run
if pythonScriptName == "swivel.py":
    baseURL = "https://wallet.swivel.run/"
    prefix = "swi"
else:
    baseURL = "https://wallet.cloudatcost.com/"    # Summary Page
    prefix = "cac"

loginURL = baseURL+"login"
auth_2faURL = baseURL+"auth"
walletURL = baseURL+"wallet"
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
silentMode = False
addDateTime = True

# Filenames
configFile = prefix+"-config.csv"
cookieFile = prefix+"-cookie.txt"
summaryHtmlFile = "Summary "+datetime+".html"
transactionHtmlFile = "Transactions "+datetime+".html"
csvFile = "Transactions "+datetime+".csv"

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
            elif lines[0] == 'run_mode':
                run_mode = lines[1]
            elif lines[0] == 'savehtml':
                if lines[1] == 'True':
                    saveHTML = True
                else:
                    saveHTML = False
            elif lines[0] == 'silenced':
                if lines[1] == 'True':
                    silentMode = True
                else:
                    silentMode = False
except:
    pass


if run_mode == "Interactive":
    interactive = True
elif run_mode == "Automatic":
    interactive = False
    useCookies = True
else:
    assert False, "Bad Run Mode"

# Setup TOPT with 2FA Secret, if needed
if not interactive and auth_2fa != "":
    totp = pyotp.TOTP(auth_2fa)

# Initialize Twill Browser
log.disabled = True
reset_browser()

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
                print("2FA Failed!")
            if not interactive:
                wait = [1, 30, 31, 31][retries]
                if not silentMode and wait > 2:
                    print("Retrying in", wait, "seconds...")
                sleep(wait)

    # Needs better verification via HTML
    if browser.code == 502:
        assert False, "Website down for maintence!"


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
            transactions.append(transaction)

transactions = transactions[::-1]


if totalTransactions > 0:
    if not silentMode:
        print("Saving '"+csvFile+"'")

    with open(csvFile, 'w') as f:
        f.write("SID, Transaction, Date, Type, Miner ID, Amount, Currency\n")
        for transaction in transactions:
            f.write(re.sub("'", '', str(transaction)[1:-1])+"\n")

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
