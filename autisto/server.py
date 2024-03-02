import time
from pathlib import Path
from autisto.spreadsheet import SpreadSheet
from autisto.database import Database
from autisto.utils import get_config
from autisto.finances import FinanceModule


class Server:
    def __init__(self):
        self._lock_path = Path("/tmp/autisto.lock")
        if self._lock_path.exists():
            self._lock_path.unlink()
        self._refresh_period = get_config()["refresh_period"]
        self.ss = SpreadSheet()
        self.db = Database("mongodb://localhost:27017/")
        self.ss.init_console(self.db)
        self.db.ss = self.ss

    def run(self):
        print("Starting server ...")
        while True:
            start = time.time()
            if not self._lock_path.exists():
                self._lock_path.touch()
                finance_module = FinanceModule()
                self.db.execute_orders(self.ss.console.get_orders())
                self.ss.inventory.summarize(self.db, finance_module)
                self.ss.spending.summarize(self.db, finance_module)
                self._lock_path.unlink()
            time.sleep(max(0., self._refresh_period - (time.time() - start)))


if __name__ == "__main__":
    server = Server()
    server.run()
