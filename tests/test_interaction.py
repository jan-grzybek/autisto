import time
import pytest
from datetime import datetime
from autisto.spreadsheet import get_config, to_1_based, START_ROW, START_COL, CONSOLE_COL_NAMES, INVENTORY_COL_NAMES, \
    SPENDING_COL_NAMES
from test_maintenance import ALPHABET


@pytest.mark.order(5)
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
    console.update(f"{ALPHABET[START_COL]}5:{ALPHABET[START_COL+len(CONSOLE_COL_NAMES)-1]}5", [row_values])

    time.sleep(20)
    inventory = spreadsheet.worksheet("Inventory")
    total_value = item_data["Quantity"] * float(item_data["Unit price [PLN]"].replace(",", "."))
    assert total_value == inventory.cell(to_1_based(START_ROW), START_COL+len(INVENTORY_COL_NAMES))
    row_values = inventory.row_values[to_1_based(START_ROW)+2]
    for i, col_name in enumerate(INVENTORY_COL_NAMES):
        if col_name in ["Category", "Item name", "Quantity", "Life expectancy [months]"]:
            assert item_data[col_name] == row_values[i+START_ROW]
        elif col_name == "Average unit value [PLN]":
            assert float(item_data["Unit price [PLN]"].replace(",", ".")) == float(row_values[i+START_ROW])
        elif col_name == "Total value [PLN]":
            assert total_value == float(row_values[i + START_ROW])
