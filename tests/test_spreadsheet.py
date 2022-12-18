import time
import pytest
import random
import string
import gspread
from filelock import FileLock
from autisto.spreadsheet import get_config, to_1_based, START_ROW, START_COL, CONSOLE_COL_NAMES, INVENTORY_COL_NAMES, \
    SPENDING_COL_NAMES
from autisto.daemons import get_platform

ALPHABET = list(string.ascii_uppercase)
SHEET_NAMES = ["Console", "Inventory", "Spending"]

lock = FileLock("/tmp/autisto.lock", timeout=10)


@pytest.fixture
def spreadsheet():
    config = get_config()
    gc = gspread.service_account_from_dict(config["credentials"])
    name = f"Inventory {config['spreadsheet_uuid']}"
    return gc.open(name)


@pytest.mark.order2
def test_sheets_creation(spreadsheet):
    for sheet in SHEET_NAMES:
        _ = spreadsheet.worksheet(sheet)
    assert True


@pytest.mark.order4
def test_column_titling(spreadsheet):
    sheets_to_titles = {"Console": CONSOLE_COL_NAMES, "Inventory": INVENTORY_COL_NAMES, "Spending": SPENDING_COL_NAMES}
    with lock:
        for sheet, titles in sheets_to_titles.items():
            start_row = to_1_based(START_ROW) + 1 if sheet == "Inventory" else to_1_based(START_ROW)
            row_values = spreadsheet.worksheet(sheet).row_values(start_row)[START_COL:]
            for i, col_name in enumerate(titles):
                assert row_values[i] == col_name


@pytest.mark.order1
def test_server_alive():
    platform = get_platform()
    assert platform.service_active()


@pytest.mark.order3
def test_sheets_auto_clean_up(spreadsheet):
    class RandomCoordinates:
        def __init__(self):
            self.row = random.randint(1, 1000)
            self.col = random.randint(1, len(ALPHABET))

    litter = ["She's got the wings and teeth of a African bat"
              "Her middle name is Mudbone and on top of all that"
              "Your mama got a glass eye with the fish in it"]
    cells_to_litter = {sheet: [] for sheet in SHEET_NAMES}
    for sheet in cells_to_litter.keys():
        for _ in range(len(litter)):
            cells_to_litter[sheet].append(RandomCoordinates())
    for sheet in SHEET_NAMES:
        worksheet = spreadsheet.worksheet(sheet)
        for i in range(len(litter)):
            worksheet.update_cell(
                cells_to_litter[sheet][i].row,
                cells_to_litter[sheet][i].col,
                litter[i]
            )
    time.sleep(10)

    for sheet in SHEET_NAMES:
        worksheet = spreadsheet.worksheet(sheet)
        for i in range(len(litter)):
            cell_coordinates = cells_to_litter[sheet][i]
            if sheet == "Console":
                if cell_coordinates.row == 1:
                    assert worksheet.cell(cell_coordinates.row, cell_coordinates.col).value is None
                elif cell_coordinates.col == 1 or to_1_based(START_COL) + len(
                        CONSOLE_COL_NAMES) <= cell_coordinates.col:
                    assert worksheet.cell(cell_coordinates.row, cell_coordinates.col).value is None
                elif cell_coordinates.row != 2:
                    assert worksheet.cell(cell_coordinates.row, cell_coordinates.col).value == litter[i]
            elif sheet == "Inventory":
                if cell_coordinates.row == 1 or to_1_based(START_ROW) + 2 <= cell_coordinates.row:
                    assert worksheet.cell(cell_coordinates.row, cell_coordinates.col).value is None
                elif cell_coordinates.col == 1 or \
                        to_1_based(START_COL) + len(INVENTORY_COL_NAMES) <= cell_coordinates.col:
                    assert worksheet.cell(cell_coordinates.row, cell_coordinates.col).value is None
            elif sheet == "Spending":
                if cell_coordinates.row == 1 or to_1_based(START_ROW) + 1 <= cell_coordinates.row:
                    assert worksheet.cell(cell_coordinates.row, cell_coordinates.col).value is None
                elif cell_coordinates.col == 1 or \
                        to_1_based(START_COL) + len(SPENDING_COL_NAMES) <= cell_coordinates.col:
                    assert worksheet.cell(cell_coordinates.row, cell_coordinates.col).value is None
            else:
                assert False
