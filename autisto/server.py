import os
import time
from filelock import FileLock
from autisto.spreadsheet import SpreadSheet
from autisto.database import Database

try:
    REFRESH_PERIOD = int(os.environ["REFRESH_PERIOD"])
except KeyError:
    REFRESH_PERIOD = 15 * 60


class Server:
    def __init__(self):
        lock_path = "/tmp/autisto.lock"
        if os.path.exists(lock_path):
            os.remove(lock_path)
        self._lock = FileLock(lock_path, timeout=10)
        self.ss = SpreadSheet()
        self.db = Database("mongodb://localhost:27017/")
        self.ss.init_console(self.db)
        self.db.ss = self.ss

    def run(self):
        print("Starting server ...")
        while True:
            start = time.time()
            with self._lock:
                self.db.execute_orders(self.ss.console.get_orders())
                self.ss.inventory.summarize(self.db)
                self.ss.spending.summarize(self.db)
            time.sleep(max(0., REFRESH_PERIOD - (time.time() - start)))


if __name__ == "__main__":
    server = Server()
    server.run()
