import os
import sys
import json
import uuid
from autisto.daemons import get_platform

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
        return json.load(config_file)


def do_config():
    print("Hello. Looks like Autisto personal accountant has not been set up yet.")
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
    config = {
        "user_email": email,
        "spreadsheet_uuid": str(uuid.uuid4()),
        "credentials": credentials
    }
    os.makedirs(os.path.expanduser(CONFIG_DIR), exist_ok=True)
    with open(os.path.expanduser(os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)), "w") as config_file:
        config_file.write(json.dumps(config))
    print(f"\nThank you. Your config has been saved under {CONFIG_DIR}\n")
    print("Setting system daemon ...")
    get_platform().set_service()
    sys.exit(0)


def check_setup():
    try:
        get_config()
        get_platform().service_active()
    except FileNotFoundError:
        do_config()
