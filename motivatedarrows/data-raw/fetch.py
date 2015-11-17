import json
import gspread
import pandas
from oauth2client.client import SignedJwtAssertionCredentials as Credentials

json_key = json.load(open('drive-api-creds.json'))
scope = ['https://spreadsheets.google.com/feeds', ]

credentials = Credentials(json_key['client_email'],
                          json_key['private_key'].encode(),
                          scope)
gc = gspread.authorize(credentials)

def fetch_subj_info():
    workbook = gc.open('SPC Subject Info')
    worksheet = workbook.worksheet('motivated-arrows')
    records = worksheet.get_all_records()
    subj_info = pandas.DataFrame.from_records(records)
    subj_info = subj_info[worksheet.row_values(1)]  # set column order
    subj_info.to_csv('subj_info.csv', index=False)

if __name__ == '__main__':
    fetch_subj_info()
