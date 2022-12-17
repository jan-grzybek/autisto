import sys
import json
import time
import gspread


def clean_up():
    gc = gspread.service_account_from_dict(json.loads(sys.argv[1]))
    file_names = None
    attempts = 0
    while file_names is None:
        try:
            file_names = [sh.title for sh in gc.openall()]
        except gspread.exceptions.APIError as e:
            attempts += 1
            if attempts == 10:
                raise e
            print(e)
            time.sleep(15)
    for name in file_names:
        try:
            gc.del_spreadsheet(name)
            print(f"Deleted spreadsheet '{name}'")
        except gspread.exceptions.APIError:
            pass
    print("DONE.")


if __name__ == "__main__":
    clean_up()
