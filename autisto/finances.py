import csv
import urllib.request
from datetime import datetime
from dateutil.relativedelta import relativedelta

URL = "https://stat.gov.pl/download/gfx/portalinformacyjny/pl/defaultstronaopisowa/4741/1/1/miesieczne_wskazniki_cen_" \
      "towarow_i_uslug_konsumpcyjnych_od_1982_roku.csv"


class FinanceModule:
    def __init__(self):
        self._calc_accumulated_inflation(self._extract_month_over_month_inflation(self._load_inflation_data()))

    def _load_inflation_data(self):
        response = urllib.request.urlopen(URL)
        return csv.reader([line.decode("iso-8859-2") for line in response.readlines()], delimiter=";")

    def _extract_month_over_month_inflation(self, raw_inflation_data):
        month_over_month_inflation_data = {}
        for row in raw_inflation_data:
            if "Poprzedni" in row[2]:
                try:
                    inflation_rate = float(row[5].replace(",", ".")) / 100
                except ValueError:
                    continue
                if row[3] in month_over_month_inflation_data.keys():
                    month_over_month_inflation_data[row[3]][row[4]] = inflation_rate
                else:
                    month_over_month_inflation_data[row[3]] = {row[4]: float(row[5].replace(",", ".")) / 100}
        return month_over_month_inflation_data

    def _calc_accumulated_inflation(self, month_over_month_inflation_data):
        self._current_time = datetime.now()
        self._accumulated_inflation = {}
        accumulated_inflation = 1.
        for year in reversed(range(1982, self._current_time.year + 1)):
            self._accumulated_inflation[str(year)] = {}
            for month in reversed(range(1, 13)):
                try:
                    accumulated_inflation *= month_over_month_inflation_data[str(year)][str(month)]
                except KeyError:
                    pass
                self._accumulated_inflation[str(year)][str(month)] = accumulated_inflation

    def calc_adjusted_price(self, original_price, purchase_date):
        try:
            adjusted_value = original_price * self._accumulated_inflation[
                str(purchase_date.year)][str(purchase_date.month)]
        except KeyError:
            adjusted_value = original_price * self._accumulated_inflation["1983"]["1"]
        return adjusted_value

    def calc_adjusted_value_and_depreciation(self, document):
        total_value = 0.
        depreciation = 0.
        for i in range(document["quantity"]):
            purchase_date = datetime.strptime(document["dates_of_purchase"][i], "%d-%m-%Y")
            value = self.calc_adjusted_price(document["prices"][i], purchase_date)
            total_value += value
            relative_delta = relativedelta(self._current_time, purchase_date)
            months_passed = relative_delta.years * 12 + relative_delta.months
            depreciation_ratio = min(1., months_passed / document["life_expectancy_months"])
            depreciation += value * depreciation_ratio
        return total_value, depreciation
