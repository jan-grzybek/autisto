import pytest
import gspread
from autisto.spreadsheet import get_config, CONSOLE_COLUMN_NAMES, CONSOLE_START_ROW, CONSOLE_START_COL


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


def test_column_titling(spreadsheet):
    row_values = spreadsheet.worksheet("Console").row_values(CONSOLE_START_ROW)[CONSOLE_START_COL:]
    for i, col_name in enumerate(CONSOLE_COLUMN_NAMES):
        assert row_values[i] == col_name
