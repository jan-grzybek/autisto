import json
import os
import time
import random
import string
import gspread
import signal
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta
from autisto.spreadsheet import get_config, to_1_based, START_ROW, START_COL, CONSOLE_COL_NAMES, INVENTORY_COL_NAMES, \
    SPENDING_COL_NAMES
from autisto.finances import FinanceModule

PATIENCE = 30
REFRESH_PERIOD = int(os.environ.get("REFRESH_PERIOD"))
ALPHABET = list(string.ascii_uppercase)
SHEET_NAMES = ["Console", "Inventory", "Spending"]

finances = FinanceModule()


class Lock:
    def __init__(self):
        self._lock_path = Path("/tmp/autisto.lock")

    def acquire(self):
        x = time.time()
        while self._lock_path.exists():
            time.sleep(0.5)
            if time.time() - x > 15:
                print("Waiting for lock to be released ...")
                x = time.time()
        self._lock_path.touch()

    def release(self):
        self._lock_path.unlink()


lock = Lock()


def handler(_, __):
    raise TimeoutError


def get_spreadsheet():
    print("\nOpening spreadsheet ...")
    config = get_config()
    with open("client_credentials.json", "r") as client_credentials:
        gc = gspread.service_account_from_dict(json.load(client_credentials))
    name = f"Inventory {config['spreadsheet_uuid']}"
    return gc.open(name)


def test_sheets_creation(spreadsheet):
    print("\nTesting sheets creating ...")
    for sheet in SHEET_NAMES:
        _ = spreadsheet.worksheet(sheet)
    print("SUCCESS.")
    assert True


def test_column_titling(spreadsheet):
    print("\nTesting column titling ...")
    sheets_to_titles = {"Console": CONSOLE_COL_NAMES, "Inventory": INVENTORY_COL_NAMES, "Spending": SPENDING_COL_NAMES}
    lock.acquire()
    for sheet, titles in sheets_to_titles.items():
        start_row = to_1_based(START_ROW) + 1 if sheet == "Inventory" else to_1_based(START_ROW)
        row_values = spreadsheet.worksheet(sheet).row_values(start_row)[START_COL:]
        for i, col_name in enumerate(titles):
            assert row_values[i] == col_name, f"{row_values[i]} != {col_name}"
    lock.release()
    print("SUCCESS.")


def test_sheets_maintaining(spreadsheet):
    print("\nTesting sheets maintaining ...")

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
    time.sleep(REFRESH_PERIOD + PATIENCE)

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

    print("SUCCESS.")


def add_remove_item(console, item_data, action_token):
    row_values = []
    for col_name in CONSOLE_COL_NAMES:
        if col_name == "Action <ADD/REMOVE>":
            row_values.append(action_token)
        elif col_name == "Done? <Y>":
            row_values.append("y")
        else:
            try:
                row_values.append(item_data[col_name])
            except KeyError:
                row_values.append("")
    row = random.randint(3, 1000)
    console.update([row_values], f"{ALPHABET[START_COL]}{row}:{ALPHABET[START_COL + len(CONSOLE_COL_NAMES) - 1]}{row}")


example_purchase_0 = {
    "Quantity": "2",
    "Date of purchase [DD-MM-YYYY]": datetime.now().strftime("%d-%m-%Y"),
    "Unit price [PLN]": "3189,99",
    "Item name": "Glock 26, 9mm",
    "Category": "Self-defense only",
    "Life expectancy [months]": "300"
}


def test_adding(spreadsheet):
    print("\nTesting adding items ...")
    console = spreadsheet.worksheet("Console")
    add_remove_item(console, example_purchase_0, "a")
    time.sleep(REFRESH_PERIOD + PATIENCE)

    inventory = spreadsheet.worksheet("Inventory")
    total_value = (int(example_purchase_0["Quantity"]) *
                   float(example_purchase_0["Unit price [PLN]"].replace(",", ".")))
    assert total_value == float(inventory.cell(to_1_based(START_ROW), to_1_based(START_COL) +
                                               INVENTORY_COL_NAMES.index("Total value [PLN]")).value.replace(",", ""))
    row_values = inventory.row_values(to_1_based(START_ROW) + 2)
    for i, col_name in enumerate(INVENTORY_COL_NAMES):
        if col_name in ["Category", "Item name", "Quantity", "Life expectancy [months]"]:
            assert example_purchase_0[col_name] == row_values[i + START_ROW]
        elif col_name == "Latest purchase":
            assert example_purchase_0["Date of purchase [DD-MM-YYYY]"] == row_values[i + START_ROW]
        elif col_name == "Average unit value [PLN]":
            assert (float(example_purchase_0["Unit price [PLN]"].replace(",", "."))
                    == float(row_values[i + START_ROW].replace(",", "")))
        elif col_name == "Total value [PLN]":
            assert total_value == float(row_values[i + START_ROW].replace(",", ""))
        elif col_name == "Depreciation [PLN]":
            assert 0. == float(row_values[i + START_ROW].replace(",", ""))
        elif col_name == "Depreciation [%]":
            assert 0. == float(row_values[i + START_ROW].replace("%", ""))
    print("SUCCESS.")


example_purchase_1 = {
    "ID": None,
    "Quantity": "1",
    "Date of purchase [DD-MM-YYYY]": "28-12-1996",  # nice date
    "Unit price [PLN]": "1570,10"
}


def test_appending(spreadsheet):
    print("\nTesting appending items ...")
    console = spreadsheet.worksheet("Console")
    inventory = spreadsheet.worksheet("Inventory")
    example_purchase_1["ID"] = inventory.cell(to_1_based(START_ROW) + 2, to_1_based(START_COL)).value
    add_remove_item(console, example_purchase_1, "ADD")
    time.sleep(REFRESH_PERIOD + PATIENCE)

    old_one = finances.calc_adjusted_price(
        float(example_purchase_1["Unit price [PLN]"].replace(",", ".")),
        datetime.strptime(example_purchase_1["Date of purchase [DD-MM-YYYY]"], "%d-%m-%Y"))
    total_value = (int(example_purchase_0["Quantity"]) *
                   float(example_purchase_0["Unit price [PLN]"].replace(",", ".")) + old_one)
    row_values = inventory.row_values(to_1_based(START_ROW) + 2)
    for i, col_name in enumerate(INVENTORY_COL_NAMES):
        if col_name == "Quantity":
            assert "3" == row_values[i + START_ROW]
        elif col_name == "Latest purchase":
            assert example_purchase_0["Date of purchase [DD-MM-YYYY]"] == row_values[i + START_ROW]
        elif col_name == "Average unit value [PLN]":
            average_unit_value = round(
                (2 * float(example_purchase_0["Unit price [PLN]"].replace(",", ".")) + old_one) / 3, 2)
            assert average_unit_value == float(row_values[i + START_ROW].replace(",", ""))
        elif col_name == "Total value [PLN]":
            assert round(total_value, 2) == float(row_values[i + START_ROW].replace(",", ""))
        elif col_name == "Depreciation [PLN]":
            assert round(old_one, 2) == float(row_values[i + START_ROW].replace(",", ""))
        elif col_name == "Depreciation [%]":
            assert round((old_one / total_value) * 100, 0) == float(row_values[i + START_ROW].replace("%", ""))
    print("SUCCESS.")


def test_removing(spreadsheet):
    print("\nTesting removing items ...")
    console = spreadsheet.worksheet("Console")
    inventory = spreadsheet.worksheet("Inventory")
    item_data = {
        "ID": example_purchase_1["ID"],
        "Quantity": "2"
    }
    add_remove_item(console, item_data, "r")

    time.sleep(REFRESH_PERIOD + PATIENCE)
    assert "1" == inventory.cell(
        to_1_based(START_ROW) + 2, to_1_based(START_COL) + INVENTORY_COL_NAMES.index("Quantity")).value
    total_value = float(example_purchase_0["Unit price [PLN]"].replace(",", "."))
    assert total_value == float(inventory.cell(to_1_based(START_ROW), to_1_based(START_COL) +
                                               INVENTORY_COL_NAMES.index("Total value [PLN]")).value.replace(",", ""))
    print("SUCCESS.")


def test_spending(spreadsheet):
    print("\nTesting spending reporting ...")
    spending = spreadsheet.worksheet("Spending")
    lock.acquire()
    now = datetime.now()

    date = datetime.strptime(example_purchase_0["Date of purchase [DD-MM-YYYY]"], "%d-%m-%Y")
    offset = (now.year - date.year) * 12 + now.month - date.month
    total_price = (int(example_purchase_0["Quantity"]) *
                   float(example_purchase_0["Unit price [PLN]"].replace(",", ".")))
    assert total_price == float(
        spending.cell(to_1_based(START_ROW) + 1 + offset, to_1_based(START_COL) + 2).value.replace(",", ""))

    date = datetime.strptime(example_purchase_1["Date of purchase [DD-MM-YYYY]"], "%d-%m-%Y")
    offset = (now.year - date.year) * 12 + now.month - date.month
    total_price = (int(example_purchase_1["Quantity"]) *
                   float(example_purchase_1["Unit price [PLN]"].replace(",", ".")))
    adjusted_price = finances.calc_adjusted_price(total_price, date)
    assert round(adjusted_price, 2) == float(
        spending.cell(to_1_based(START_ROW) + 1 + offset, to_1_based(START_COL) + 2).value.replace(",", ""))

    date = datetime(date.year, date.month, 1) + relativedelta(months=11)
    offset = (now.year - date.year) * 12 + now.month - date.month
    adjusted_price_ttm = round(adjusted_price / 12, 2)
    cell_value = float(
        spending.cell(to_1_based(START_ROW) + 1 + offset, to_1_based(START_COL) + 3).value.replace(",", ""))
    assert adjusted_price_ttm == cell_value, f"{adjusted_price_ttm} != {cell_value}"
    lock.release()
    print("SUCCESS.")


def print_autisto_log():
    with open("/tmp/autisto.log", "r") as f:
        x = f.read()
        if len(x) > 0:
            print("\nOutput of Autisto server:")
            print(x)
            print("\nPython traceback:")


def run_test(test, spreadsheet):
    try:
        test(spreadsheet)
    except Exception as e:
        print_autisto_log()
        raise e


if __name__ == "__main__":
    signal.signal(signal.SIGALRM, handler)
    ss = None
    try:
        timeout = 30
        for _ in range(3):
            signal.alarm(timeout)
            try:
                ss = get_spreadsheet()
                break
            except TimeoutError:
                continue
        else:
            assert False, "Couldn't load spreadsheet"
        time.sleep(timeout)
    except TimeoutError:
        assert ss is not None
    run_test(test_sheets_creation, ss)
    run_test(test_sheets_maintaining, ss)
    run_test(test_column_titling, ss)
    run_test(test_adding, ss)
    run_test(test_appending, ss)
    run_test(test_removing, ss)
    run_test(test_spending, ss)
