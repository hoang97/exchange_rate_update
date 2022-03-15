import string
import requests
import xml.etree.ElementTree as ET

url = 'https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx'


x = requests.get(url)
stringData = x.text.split('\n', 2)[2]
root = ET.fromstring(stringData)
price_sell = {}
price_buy =  {}
for child in root:
    data = child.attrib
    if data != {} and data['CurrencyCode'] == 'USD':
        price_sell = {
            "exchange": "VietcomBank",
            "tradeType": "SELL",
            "asset": "USD",
            "fiat": "VND",
            "price": data['Sell'],
            "tradeMethods": [],
            "minSingleTransAmount": 0.0,
            "maxSingleTransAmount": 10000000000000.0,
            "monthFinishRate": 1.0,
            "monthOrderCount": 100000
        }
        price_buy = {
            "exchange": "VietcomBank",
            "tradeType": "BUY",
            "asset": "USD",
            "fiat": "VND",
            "price": data['Buy'],
            "tradeMethods": [],
            "minSingleTransAmount": 0.0,
            "maxSingleTransAmount": 10000000000000.0,
            "monthFinishRate": 1.0,
            "monthOrderCount": 100000
        }
        break

print(price_buy)
print(price_sell)
# data = json.loads(x.text)
# with open('data.json', 'w') as f:
#     json.dump(data, f)