import gspread
from bson.errors import InvalidId
from autisto.utils import *
from datetime import datetime
from dateutil.relativedelta import relativedelta

BEGINNING_OF_TIME = datetime(1900, 1, 1)

START_ROW = 1
START_COL = 1

CONSOLE_COL_NAMES = ["Action <ADD/REMOVE>", "ID", "Quantity", "Date of purchase [DD-MM-YYYY]", "Unit price [PLN]",
                     "Item name", "Category", "Life expectancy [months]", "Done? <Y>", "", "Status"]
INVENTORY_COL_NAMES = ["ID", "Category", "Item name", "Latest purchase", "Quantity", "Life expectancy [months]",
                       "Average unit value [PLN]", "Total value [PLN]", "Depreciation [PLN]", "Depreciation [%]"]
SPENDING_COL_NAMES = ["Year", "Month", "Amount spent [PLN, inflation-adjusted]",
                      "Amount spent TTM per month [PLN, inflation-adjusted]"]


class SpreadSheet:
    def __init__(self):
        config = get_config()
        gc = gspread.service_account_from_dict(config["credentials"])
        name = f"Inventory {config['spreadsheet_uuid']}"
        try:
            self._file = gc.open(name)
        except gspread.exceptions.SpreadsheetNotFound:
            self._file = gc.create(name)
            self._file.add_worksheet("Console", rows=1000, cols=26)
            self._file.add_worksheet("Inventory", rows=1000, cols=26)
            self._file.add_worksheet("Spending", rows=1000, cols=26)
            self._file.del_worksheet(self._file.worksheet("Sheet1"))
            self._file.share(config["user_email"], perm_type="user", role="writer")
        self.console = None
        self.inventory = InventorySheet(self._file)
        self.spending = SpendingSheet(self._file)

    def init_console(self, database):
        self.console = Console(self._file, database)


class Console:
    def __init__(self, spreadsheet, database):
        self._sheet = spreadsheet.worksheet("Console")
        self._start_row = to_1_based(START_ROW)
        self._start_col = START_COL
        self._column_names = CONSOLE_COL_NAMES
        self._orders = []
        self.db = database

    def clean_up(self, orders_only=False):
        if not orders_only:
            self._sheet.batch_clear(["A1:A", "A1:Z2", "K1:Z"])
            self._sheet.format("A1:Z", {"textFormat": {"bold": False}})
            self._sheet.format(f"B{self._start_row}:Z{self._start_row}", {"textFormat": {"bold": True}})
            self._sheet.update([self._column_names], f"B{self._start_row}:L{self._start_row}")
        for order in self._orders:
            self._sheet.batch_clear([f"B{order.row}:Z{order.row}"])
        self._orders = []

    def _get_col_index(self, col_name):
        return self._start_col + self._column_names.index(col_name)

    def _get_ready_rows(self):
        confirmation_tokens = self._sheet.col_values(to_1_based(self._get_col_index("Done? <Y>")))[self._start_row:]
        ready_rows = []
        for i, token in enumerate(confirmation_tokens):
            if token in ["y", "yes", "Y", "YES"]:
                ready_rows.append(self._start_row + i)
            elif token != "":
                self._sheet.update_cell(self._start_row + i + 1, to_1_based(self._get_col_index("Status")),
                                        f"Wrong confirmation token: '{confirmation_tokens[i]}' "
                                        f"(should be 'Y' instead)")
        return ready_rows

    def _get_id(self, row, value):
        try:
            return self.db.get_id_object(value)
        except (InvalidId, ValueError):
            self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                    f"Wrong ID value - must be a 12-byte input or a 24-character hex string")
            raise FaultyOrder

    def _get_quantity(self, row, value):
        try:
            return check_for_positive_int(value)
        except ValueError:
            self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                    f"Wrong quantity value - must be a positive integer")
        raise FaultyOrder

    def _get_expectancy(self, row, value, assert_empty=False):
        if assert_empty:
            if value == "":
                return None
            else:
                self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                        f"Modifying life expectancy when adding by ID is not allowed")
        else:
            try:
                return check_for_positive_int(value)
            except ValueError:
                self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                        f"Wrong life expectancy value - must be a positive integer")
        raise FaultyOrder

    def _get_date(self, row, value):
        try:
            date = datetime.strptime(value, '%d-%m-%Y')
        except ValueError:
            self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                    f"Wrong date - must be 'DD-MM-YYYY'")
            raise FaultyOrder
        if datetime.now() < date or date < BEGINNING_OF_TIME:
            self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                    f"Wrong date - must be after/at Jan 1, 1900 and not in the future")
            raise FaultyOrder
        return date

    def _get_price(self, row, value):
        try:
            value = value.replace(",", ".")
            return check_for_positive_float(value)
        except ValueError:
            self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                    f"Wrong price value - must be a non-negative float")
        raise FaultyOrder

    def _get_item_name(self, row, value, assert_empty=False):
        if value == "":
            if assert_empty:
                return None
            else:
                self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                        f"Either item name or id of an existing item must be provided")
        else:
            if assert_empty:
                self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                        f"Modifying item name when adding by ID is not allowed")
            elif self.db.name_already_used(value):
                self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                        f"Item name must be unique")
            else:
                return value
        raise FaultyOrder

    def _get_category(self, row, value, assert_empty=False):
        if value == "":
            if assert_empty:
                return None
            else:
                self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                        f"Category name must be provided")
        else:
            if assert_empty:
                self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                        f"Modifying category when adding by ID is not allowed")
            else:
                return value
        raise FaultyOrder

    def _process_add_order(self, row, values):
        if values[self._column_names.index("ID")] == "":
            identifier = None
            item_name = self._get_item_name(row, values[self._column_names.index("Item name")])
            category = self._get_category(row, values[self._column_names.index("Category")])
            life_expectancy = self._get_expectancy(row, values[self._column_names.index("Life expectancy [months]")])
        else:
            identifier = self._get_id(row, values[self._column_names.index("ID")])
            item_name = self._get_item_name(row, values[self._column_names.index("Item name")], assert_empty=True)
            category = self._get_category(row, values[self._column_names.index("Category")], assert_empty=True)
            life_expectancy = self._get_expectancy(
                row, values[self._column_names.index("Life expectancy [months]")], assert_empty=True)
        return Order(
            row=to_1_based(row),
            action="add",
            identifier=identifier,
            quantity=self._get_quantity(row, values[self._column_names.index("Quantity")]),
            date=self._get_date(row, values[self._column_names.index("Date of purchase [DD-MM-YYYY]")]),
            price=self._get_price(row, values[self._column_names.index("Unit price [PLN]")]),
            item_name=item_name,
            category=category,
            life_expectancy=life_expectancy
        )

    def _process_remove_order(self, row, values):
        if values[self._column_names.index("Date of purchase [DD-MM-YYYY]")] != "":
            self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                    "Cannot remove by date")
        elif values[self._column_names.index("Unit price [PLN]")] != "":
            self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                    "Cannot remove by price")
        elif values[self._column_names.index("Item name")] != "":
            self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                    "Cannot remove by item name")
        elif values[self._column_names.index("Category")] != "":
            self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                    "Cannot remove by category")
        elif values[self._column_names.index("Life expectancy [months]")] != "":
            self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                    "Cannot remove by life expectancy")
        else:
            identifier = self._get_id(row, values[self._column_names.index("ID")])
            requested_quantity = self._get_quantity(row, values[self._column_names.index("Quantity")])
            quantity = self.db.get_quantity(identifier)
            if quantity >= requested_quantity:
                return Order(
                    row=to_1_based(row),
                    action="remove",
                    identifier=identifier,
                    quantity=requested_quantity
                )
            else:
                self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                        f"Number of items requested to be removed exceeds the available pool "
                                        f"({requested_quantity} > {quantity})")
        raise FaultyOrder

    def get_orders(self):
        self.clean_up()
        for row in self._get_ready_rows():
            row_values = self._sheet.row_values(to_1_based(row))[self._start_col:]
            action_token = row_values[self._column_names.index("Action <ADD/REMOVE>")]
            try:
                if action_token in ["a", "add", "A", "ADD"]:
                    self._orders.append(self._process_add_order(row, row_values))
                elif action_token in ["r", "remove", "R", "REMOVE"]:
                    self._orders.append(self._process_remove_order(row, row_values))
                else:
                    self._sheet.update_cell(to_1_based(row), to_1_based(self._get_col_index("Status")),
                                            f"Wrong action token: '{action_token}' "
                                            f"(should be one of 'ADD/REMOVE')")
            except FaultyOrder:
                continue
        return self._orders


class InventorySheet:
    def __init__(self, spreadsheet):
        self._sheet = spreadsheet.worksheet("Inventory")
        self._start_row = to_1_based(START_ROW)
        self._start_col = START_COL
        self._column_names = INVENTORY_COL_NAMES

    def summarize(self, database, finance_module):
        self._sheet.clear()
        self._sheet.format(f"H{self._start_row}:J{self._start_row}", {"horizontalAlignment": "RIGHT"})
        self._sheet.format(f"I{self._start_row}:J{self._start_row}",
                           {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}})
        self._sheet.format(f"H{self._start_row+2}:J", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}})
        self._sheet.format(f"K{self._start_row+2}:K", {"numberFormat": {"type": "NUMBER", "pattern": "0%"}})
        self._sheet.format("A1:Z", {"textFormat": {"bold": False}})
        self._sheet.format(f"B{self._start_row}:Z{self._start_row + 1}", {"textFormat": {"bold": True}})
        summary_table = \
            [[None for _ in range(len(self._column_names) - 4)] + ["SUM=", 0., 0., None], self._column_names]
        for document in database.get_assets(sort_by_latest=True):
            total_value, depreciation = finance_module.calc_adjusted_value_and_depreciation(document)
            summary_table[0][-3] += total_value
            summary_table[0][-2] += depreciation
            summary_table.append([
                str(document["_id"]),
                document["category"],
                document["item_name"],
                document["dates_of_purchase"][-1],
                document["quantity"],
                document["life_expectancy_months"],
                round(total_value / document["quantity"], 2),
                round(total_value, 2),
                round(depreciation, 2),
                depreciation / total_value
            ])
        summary_table[0][-3] = round(summary_table[0][-3], 2)
        summary_table[0][-2] = round(summary_table[0][-2], 2)
        self._sheet.update(summary_table, f"B2:K{to_1_based(len(summary_table))}")


class SpendingSheet:
    def __init__(self, spreadsheet):
        self._sheet = spreadsheet.worksheet("Spending")
        self._start_row = to_1_based(START_ROW)
        self._start_col = START_COL
        self._column_names = SPENDING_COL_NAMES

    def summarize(self, database, finance_module):
        current_time = datetime.now()
        month_to_month_spending = {}
        month_to_month_spending_ttm = {}
        for year in range(BEGINNING_OF_TIME.year, current_time.year + 1):
            month_to_month_spending[str(year)] = {}
            month_to_month_spending_ttm[str(year)] = {}
            for month in range(1, 13):
                month_to_month_spending[str(year)][str(month)] = 0.
                month_to_month_spending_ttm[str(year)][str(month)] = 0.

        most_distant_date_observed = current_time
        for collection in [database.get_assets(), database.get_decommissioned()]:
            for document in collection:
                for i, date in enumerate(document["dates_of_purchase"]):
                    purchase_date = datetime.strptime(date, "%d-%m-%Y")
                    if purchase_date < most_distant_date_observed:
                        most_distant_date_observed = purchase_date
                    adjusted_price = finance_module.calc_adjusted_price(document["prices"][i], purchase_date)
                    month_to_month_spending[str(purchase_date.year)][str(purchase_date.month)] += adjusted_price
                    for j in range(12):
                        target_date = purchase_date + relativedelta(months=j)
                        try:
                            month_to_month_spending_ttm[str(target_date.year)][str(target_date.month)] += adjusted_price
                        except KeyError:
                            break

        self._sheet.clear()
        self._sheet.format("A1:Z", {"textFormat": {"bold": False}})
        self._sheet.format(f"D{self._start_row + 1}:E", {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}})
        self._sheet.format(f"B{self._start_row}:E{self._start_row}", {"textFormat": {"bold": True}})
        summary_table = [self._column_names]
        enter_ttm_date = (datetime(most_distant_date_observed.year, most_distant_date_observed.month, 1)
                          + relativedelta(months=11))
        for year in reversed(range(most_distant_date_observed.year, current_time.year + 1)):
            if year == current_time.year:
                for month in reversed(range(1, current_time.month + 1)):
                    spending_ttm = None
                    if enter_ttm_date <= datetime(year, month, 1):
                        spending_ttm = round(month_to_month_spending_ttm[str(year)][str(month)] / 12, 2)
                    summary_table.append(
                        [year, month, round(month_to_month_spending[str(year)][str(month)], 2), spending_ttm])
            elif year == most_distant_date_observed.year:
                for month in reversed(range(most_distant_date_observed.month, 13)):
                    spending_ttm = None
                    if enter_ttm_date <= datetime(year, month, 1):
                        spending_ttm = round(month_to_month_spending_ttm[str(year)][str(month)] / 12, 2)
                    summary_table.append(
                        [year, month, round(month_to_month_spending[str(year)][str(month)], 2), spending_ttm])
            else:
                for month in reversed(range(1, 13)):
                    spending_ttm = None
                    if enter_ttm_date <= datetime(year, month, 1):
                        spending_ttm = round(month_to_month_spending_ttm[str(year)][str(month)] / 12, 2)
                    summary_table.append(
                        [year, month, round(month_to_month_spending[str(year)][str(month)], 2), spending_ttm])

        self._sheet.update(summary_table, f"B{self._start_row}:E{to_1_based(len(summary_table))}")
