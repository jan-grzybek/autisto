import json
import time
import pytest
import random
import string
import gspread
from pathlib import Path
from datetime import datetime
from autisto.spreadsheet import get_config, to_1_based, START_ROW, START_COL, CONSOLE_COL_NAMES, INVENTORY_COL_NAMES, \
    SPENDING_COL_NAMES
from autisto.daemons import get_platform

REFRESH_PERIOD = 60
ALPHABET = list(string.ascii_uppercase)
SHEET_NAMES = ["Console", "Inventory", "Spending"]


class Lock:
    def __init__(self):
        self._lock_path = Path("/tmp/autisto.lock")

    def acquire(self):
        while self._lock_path.exists():
            time.sleep(0.5)
        self._lock_path.touch()

    def release(self):
        self._lock_path.unlink()


lock = Lock()


@pytest.fixture
def spreadsheet():
    config = get_config()
    with open("client_credentials.json", "r") as client_credentials:
        gc = gspread.service_account_from_dict(json.load(client_credentials))
    name = f"Inventory {config['spreadsheet_uuid']}"
    return gc.open(name)


@pytest.mark.order(1)
def test_sheets_creation(spreadsheet):
    for sheet in SHEET_NAMES:
        _ = spreadsheet.worksheet(sheet)
    assert True


@pytest.mark.order(3)
def test_column_titling(spreadsheet):
    sheets_to_titles = {"Console": CONSOLE_COL_NAMES, "Inventory": INVENTORY_COL_NAMES, "Spending": SPENDING_COL_NAMES}
    lock.acquire()
    for sheet, titles in sheets_to_titles.items():
        start_row = to_1_based(START_ROW) + 1 if sheet == "Inventory" else to_1_based(START_ROW)
        row_values = spreadsheet.worksheet(sheet).row_values(start_row)[START_COL:]
        for i, col_name in enumerate(titles):
            assert row_values[i] == col_name
    lock.release()


@pytest.mark.order(2)
def test_sheets_auto_clean_up(spreadsheet):
    class RandomCoordinates:
        def __init__(self):
            self.row = random.randint(1, 1000)
            self.col = random.randint(1, len(ALPHABET))

    litter = ["She's got the wings and teeth of a African bat",
              "Her middle name is Mudbone and on top of all that",
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
    time.sleep(REFRESH_PERIOD + 10)

    for sheet in SHEET_NAMES:
        worksheet = spreadsheet.worksheet(sheet)
        for i in range(len(litter)):
            cell_coordinates = cells_to_litter[sheet][i]
            if sheet == "Console":
                if cell_coordinates.row == 1:
                    assert worksheet.cell(cell_coordinates.row, cell_coordinates.col).value is None
                elif cell_coordinates.col == 1 or to_1_based(START_COL) + len(
                        CONSOLE_COL_NAMES[:-2]) <= cell_coordinates.col:
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


@pytest.mark.order(4)
def test_adding(spreadsheet):
    console = spreadsheet.worksheet("Console")
    item_data = {
        "Quantity": 2,
        "Date of purchase [DD-MM-YYYY]": datetime.now().strftime("%d-%m-%Y"),
        "Unit price [PLN]": "3189,99",
        "Item name": "Glock 26, 9mm",
        "Category": "Self-defense only",
        "Life expectancy [months]": 300
    }
    row_values = []
    for col_name in CONSOLE_COL_NAMES:
        if col_name == "Action <ADD/REMOVE>":
            row_values.append("a")
        elif col_name == "Done? <Y>":
            row_values.append("y")
        else:
            try:
                row_values.append(item_data[col_name])
            except KeyError:
                row_values.append("")
    console.update(f"{ALPHABET[START_COL]}5:{ALPHABET[START_COL + len(CONSOLE_COL_NAMES) - 1]}5", [row_values])

    time.sleep(REFRESH_PERIOD + 10)
    inventory = spreadsheet.worksheet("Inventory")
    total_value = item_data["Quantity"] * float(item_data["Unit price [PLN]"].replace(",", "."))
    assert total_value == float(inventory.cell(
        to_1_based(START_ROW), to_1_based(START_COL) + INVENTORY_COL_NAMES.index("Total value [PLN]")).value)
    row_values = inventory.row_values(to_1_based(START_ROW) + 2)
    for i, col_name in enumerate(INVENTORY_COL_NAMES):
        if col_name in ["Category", "Item name", "Quantity", "Life expectancy [months]"]:
            assert item_data[col_name] == row_values[i + START_ROW]
        elif col_name == "Average unit value [PLN]":
            assert float(item_data["Unit price [PLN]"].replace(",", ".")) == float(row_values[i + START_ROW])
        elif col_name == "Depreciation [PLN]":
            assert 0. == float(row_values[i + START_ROW])
