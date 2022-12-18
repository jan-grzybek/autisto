import os
import sys
import json
import uuid
import pymongo
from autisto.daemons import get_platform
from autisto.database import Database

CONFIG_DIR = "~/.config/autisto/"
CONFIG_FILE_NAME = "config.json"


def to_1_based(index):
    return index + 1


class FaultyOrder(Exception):
    pass


def check_for_positive_int(value):
    value = float(value)
    if value % 1 != 0 or value < 1:
        raise ValueError
    return int(value)


def check_for_positive_float(value):
    value = float(value)
    if value < 0.:
        raise ValueError
    return value


class Order:
    def __init__(self, row, action, identifier, quantity,
                 date=None, price=None, item_name=None, category=None, life_expectancy=None):
        self.action = action
        self.id = identifier
        self.quantity = quantity
        self.date = date
        self.price = price
        self.item_name = item_name
        self.category = category
        self.life_expectancy = life_expectancy
        self.row = row


def get_config():
    with open(os.path.expanduser(os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)), "r") as config_file:
        config = json.load(config_file)
    if "refresh_period" not in config.keys():
        config["refresh_period"] = 900
        with open(os.path.expanduser(os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)), "w") as config_file:
            config_file.write(json.dumps(config))
    return config


def do_config():
    print("Attempting connection to mongoDB ...")
    try:
        for _ in Database("mongodb://localhost:27017/").get_assets():
            break
        print("Success.")
    except pymongo.errors.ServerSelectionTimeoutError as e:
        print(e)
        print("Is mongoDB installed on the system?")
        sys.exit(1)
    print("\nChecking for root privileges ...")
    if os.geteuid() == 0:
        print("Success.")
    else:
        print("Please rerun with sudo.")
        print("   sudo autisto")
        sys.exit(1)
    print("\nHello. Looks like Autisto personal accountant has not been set up yet.")
    print("Have you already set up a Google Service Account? If not, please first follow instructions here: "
          "https://docs.gspread.org/en/latest/oauth2.html")
    print("\nPlease provide path to the .json file with Service Account credentials.")
    while True:
        path = input("Path to credentials: ")
        try:
            credentials = json.load(open(os.path.expanduser(path), "r"))
            break
        except FileNotFoundError as e:
            print(e)
    print("\nPlease provide email address that you want to access spreadsheet with.")
    email = input("Email address: ")
    print("\nWhat should be the refresh period for the spreadsheet?")
    refresh_period = None
    while refresh_period is None:
        try:
            refresh_period = int(input("Refresh period in seconds [recommended: 900]: "))
        except ValueError:
            continue
    config = {
        "user_email": email,
        "spreadsheet_uuid": str(uuid.uuid4()),
        "refresh_period": refresh_period,
        "credentials": credentials
    }
    os.makedirs(os.path.expanduser(CONFIG_DIR), exist_ok=True)
    with open(os.path.expanduser(os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)), "w") as config_file:
        config_file.write(json.dumps(config))
    print(f"\nThank you. Your config has been saved under {CONFIG_DIR}")
    print("\nSetting system daemon ...")
    get_platform().set_service()
    print("All done.")
    sys.exit(0)


def check_setup():
    try:
        get_config()
        get_platform().service_active()
    except FileNotFoundError:
        do_config()
