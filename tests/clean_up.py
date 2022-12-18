import sys
import json
import time
import gspread


def attempt_clean_up():
    gc = gspread.service_account_from_dict(json.loads(sys.argv[1]))
    file_names = None
    attempts = 0
    while file_names is None:
        try:
            file_names = [sh.title for sh in gc.openall()]
        except gspread.exceptions.APIError as e:
            attempts += 1
            if attempts == 10:
                print("Can't pull a list of existing file names, aborting ...")
                return
            time.sleep(15)
    if len(file_names) > 0:
        print("\nFound following spreadsheets on the account:")
        for name in file_names:
            print(f"   {name}")
        time.sleep(15)
        print("\nDeleting ...")
        for name in file_names:
            try:
                gc.del_spreadsheet(name)
                print(f"   deleting of {name} succeeded")
            except gspread.exceptions.APIError:
                print(f"   deleting of {name} failed")
        print("\nDONE.")


if __name__ == "__main__":
    attempt_clean_up()
