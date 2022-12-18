import time
import pytest
import random
import string
import gspread
from autisto.spreadsheet import get_config, to_1_based, START_ROW, START_COL, CONSOLE_COL_NAMES, INVENTORY_COL_NAMES, \
    SPENDING_COL_NAMES

ALPHABET = list(string.ascii_uppercase)
SHEET_NAMES = ["Console", "Inventory", "Spending"]


@pytest.fixture
def spreadsheet():
    config = get_config()
    gc = gspread.service_account_from_dict(config["credentials"])
    name = f"Inventory {config['spreadsheet_uuid']}"
    return gc.open(name)


def test_sheets_creation(spreadsheet):
    for sheet in SHEET_NAMES:
        _ = spreadsheet.worksheet(sheet)
    assert True


def test_column_titling(spreadsheet):
    for sheet, titles in \
            {"Console": CONSOLE_COL_NAMES, "Inventory": INVENTORY_COL_NAMES, "Spending": SPENDING_COL_NAMES}.items():
        start_row = to_1_based(START_ROW) + 1 if sheet == "Inventory" else to_1_based(START_ROW)
        row_values = spreadsheet.worksheet(sheet).row_values(start_row)[START_COL:]
        for i, col_name in enumerate(titles):
            assert row_values[i] == col_name


def test_sheets_auto_clean_up(spreadsheet):
    def get_random_cell_coordinates():
        return random.randint(1, 1000), random.randint(1, len(ALPHABET))
    cells_to_litter_per_sheet = 10
    cells_to_litter = {sheet: [] for sheet in SHEET_NAMES}
    for sheet in cells_to_litter.keys():
        for _ in range(cells_to_litter_per_sheet):
            cells_to_litter[sheet].append(get_random_cell_coordinates())
    for sheet in SHEET_NAMES:
        worksheet = spreadsheet.worksheet(sheet)
        for i in range(cells_to_litter_per_sheet):
            worksheet.update_cell(
                *cells_to_litter[sheet][i],
                "She's got the wings and teeth of a African bat; "
                "Her middle name is Mudbone and on top of all that; "
                "Your mama got a glass eye with the fish in it"
            )
    time.sleep(10)
    for sheet in SHEET_NAMES:
        worksheet = spreadsheet.worksheet(sheet)
        for i in range(cells_to_litter_per_sheet):
            cell_coordinates = cells_to_litter[sheet][i]
            if cell_coordinates[0] in [to_1_based(START_ROW), to_1_based(START_ROW)+1] or \
                    cell_coordinates[1] == to_1_based(START_COL):
                continue
            assert worksheet.cell(*cell_coordinates).value == ""
    test_column_titling(spreadsheet)
