import sys
import json
import gspread


def clean_up():
    gc = gspread.service_account_from_dict(json.loads(sys.argv[1]))
    for title in [sh.title for sh in gc.openall()]:
        print(title)
        gc.del_spreadsheet(title)


if __name__ == "__main__":
    clean_up()
