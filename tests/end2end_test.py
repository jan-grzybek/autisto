import pytest
import gspread
from autisto.spreadsheet import get_config

def test_spreadsheet_generation():
    config = get_config()
    gc = gspread.service_account_from_dict(config["credentials"])
    name = f"Inventory {config['spreadsheet_uuid']}"
    gc.open(name)
