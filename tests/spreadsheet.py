import pytest
import gspread
from autisto.spreadsheet import get_config


@pytest.fixture
def spreadsheet():
    config = get_config()
    gc = gspread.service_account_from_dict(config["credentials"])
    name = f"Inventory {config['spreadsheet_uuid']}"
    return gc.open(name)


def test_worksheets_generation(spreadsheet):
    for name in ["Console", "Inventory", "Spending"]:
        _ = spreadsheet.worksheet(name)
    assert True
