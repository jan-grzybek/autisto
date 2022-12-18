import pytest
import gspread
from autisto.spreadsheet import get_config, to_1_based, START_ROW, START_COL, CONSOLE_COL_NAMES, INVENTORY_COL_NAMES, \
    SPENDING_COL_NAMES


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
    for sheet, titles in \
            {"Console": CONSOLE_COL_NAMES, "Inventory": INVENTORY_COL_NAMES, "Spending": SPENDING_COL_NAMES}.items():
        start_row = to_1_based(START_ROW) + 1 if sheet == "Inventory" else to_1_based(START_ROW)
        row_values = spreadsheet.worksheet(sheet).row_values(start_row)[START_COL:]
        for i, col_name in enumerate(titles):
            assert row_values[i] == col_name
