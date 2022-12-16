import time
from spreadsheet import SpreadSheet
from database import Database
from utils import check_setup

REFRESH_PERIOD = 15 * 60


class Server:
    def __init__(self):
        self.ss = SpreadSheet()
        self.db = Database("mongodb://localhost:27017/")
        self.ss.init_console(self.db)
        self.db.ss = self.ss

    def run(self):
        print("Starting server ...")
        while True:
            start = time.time()
            self.db.execute_orders(self.ss.console.get_orders())
            self.ss.inventory.summarize(self.db)
            self.ss.spending.summarize(self.db)
            time.sleep(REFRESH_PERIOD - (time.time() - start))


def entry():
    check_setup()
    server = Server()
    server.run()


if __name__ == "__main__":
    entry()
