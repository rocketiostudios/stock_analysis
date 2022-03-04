import stock as s
import matplotlib.pyplot as plt

if __name__ == '__main__':
    intel = s.Stock('INTC')
    intel.pe_ratios.plot(x='date', y='ttm_price_to_earnings')
    plt.grid(axis='both', aa=True, linestyle='-')
    plt.show()
