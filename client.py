import requests

api_secret =


def get_earnings(symbol):
    url = 'https://www.alphavantage.co/query?' + 'function=EARNINGS' + '&' + 'symbol=' + symbol + '&' + 'apikey=' + api_secret
    return requests.get(url).json()


def get_historical_price(symbol):
    url = 'https://www.alphavantage.co/query?' + 'function=TIME_SERIES_DAILY' + '&' + 'symbol=' + symbol + '&' 'outputsize=full' + '&' + 'apikey=' + api_secret
    return requests.get(url).json()
