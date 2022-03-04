from client import *
from collections import deque
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd


class Stock:
    def __init__(self, ticker):
        self.ticker = ticker
        self.quarterly_earnings = self.update_quarterly_earnings()
        self.historical_price = self.update_historical_price()
        self.pe_ratios = self.update_pe_ratios()

    # retrieve and convert quarterly earnings portion of earnings JSON into DataFrame, reverse order, reset index, and rename columns
    def update_quarterly_earnings(self):
        earnings_json = get_earnings(symbol=self.ticker)
        quarterly_earnings = pd.json_normalize(earnings_json, record_path='quarterlyEarnings')
        quarterly_earnings = quarterly_earnings.loc[::-1]
        quarterly_earnings = quarterly_earnings.reset_index(drop=True)
        quarterly_earnings = quarterly_earnings.rename(columns={'fiscalDateEnding': 'date_ending',
                                                                'reportedDate': 'date',
                                                                'reportedEPS': 'eps_reported',
                                                                'estimatedEPS': 'eps_estimated',
                                                                'surprise': 'surprise',
                                                                'surprisePercentage': 'surprise_percentage'
                                                                })
        return quarterly_earnings

    def update_historical_price(self):
        historical_price_json = get_historical_price(symbol=self.ticker)['Time Series (Daily)']  # import historical_price JSON string from API client
        historical_price = pd.DataFrame(columns=['date', 'open', 'low', 'close', 'volume'])  # Final DataFrame of flattened historical_price_json

        for key in historical_price_json:
            entry = pd.DataFrame(data={'date':   key,
                                       'open':   [historical_price_json[key]['1. open']],
                                       'high':   [historical_price_json[key]['2. high']],
                                       'low':    [historical_price_json[key]['3. low']],
                                       'close':  [historical_price_json[key]['4. close']],
                                       'volume': [historical_price_json[key]['5. volume']]
                                       })
            historical_price = pd.concat([entry, historical_price], axis=0)  # Add item to final DataFrame
        historical_price = historical_price.reset_index(drop=True)
        return historical_price

    def update_pe_ratios(self):
        start_date_trim = (date.today() - relativedelta(years=10)).strftime('%Y-%m-%d')  # 10y for relevant data
        start_date_calc = (date.today() - relativedelta(years=11, months=3)).strftime('%Y-%m-%d')  # 11y 3m to ensure a full 4 periods are in queue
        end_date = date.today().strftime('%Y-%m-%d')

        historical_price_trimmed = self.historical_price
        combined_price_earnings = pd.merge(historical_price_trimmed, self.quarterly_earnings, how='left', on='date')
        combined_price_earnings['date_ending'] = combined_price_earnings['date_ending'].ffill()
        combined_price_earnings['eps_reported'] = combined_price_earnings['eps_reported'].ffill()

        # Subset of combined_price_earnings DataFrame for quicker calcs (necessary iteration)
        pe_ratios = pd.DataFrame(data={'date': pd.to_datetime(combined_price_earnings['date'], format='%Y-%m-%d'),
                                       'date_ending': pd.to_datetime(combined_price_earnings['date_ending'], format='%Y-%m-%d'),
                                       'close': pd.to_numeric(combined_price_earnings['close']),
                                       'eps_reported': pd.to_numeric(combined_price_earnings['eps_reported'])
                                       })

        # Remove extraneous rows from pe_ratios
        pe_ratios_mask = (pe_ratios['date'] >= start_date_calc) & (pe_ratios['date'] <= end_date)
        pe_ratios = pe_ratios.loc[pe_ratios_mask]

        # Simultaneous deque structures to store date_ending and eps_reported for 4 most recent deltas in date_ending
        prior_4q_date_ending = deque([])
        prior_4q_eps = deque([])

        ttm_earnings = []
        for entry in pe_ratios.itertuples():
            if len(prior_4q_date_ending) < 4:
                if entry[2] in prior_4q_date_ending:
                    ttm_earnings.append(0)
                    continue
                else:
                    ttm_earnings.append(0)
                    prior_4q_date_ending.append(entry[2])
                    prior_4q_eps.append(entry[4])
            else:
                if entry[2] in prior_4q_date_ending:
                    if sum(prior_4q_eps) < 0:
                        ttm_earnings.append(0)
                    else:
                        ttm_earnings.append(sum(prior_4q_eps))
                    continue
                else:
                    prior_4q_date_ending.popleft()
                    prior_4q_date_ending.append(entry[2])
                    prior_4q_eps.popleft()
                    prior_4q_eps.append(entry[4])
                    if sum(prior_4q_eps) < 0:
                        ttm_earnings.append(0)
                    else:
                        ttm_earnings.append(sum(prior_4q_eps))

        # Add final list as column in pe_ratios
        pe_ratios['ttm_earnings'] = pd.to_numeric(ttm_earnings)
        pe_ratios.insert(loc=pe_ratios.columns.get_loc('ttm_earnings') + 1, column='ttm_price_to_earnings', value=(pe_ratios['close'] / pe_ratios['ttm_earnings']))
        pe_ratios['ttm_price_to_earnings'] = pd.to_numeric(pe_ratios['ttm_price_to_earnings'])

        # Subset of pe_ratios for display (>= current date - 10 yrs)
        pe_ratios_mask = (pe_ratios['date'] >= start_date_trim) & (pe_ratios['date'] <= end_date)
        pe_ratios = pe_ratios.loc[pe_ratios_mask]
        pe_ratios = pe_ratios.reset_index(drop=True)

        # Format and return finished DataFrame
        pd.set_option("display.max_rows", None, "display.max_columns", None)
        return pe_ratios
