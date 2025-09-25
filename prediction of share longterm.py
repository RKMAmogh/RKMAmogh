import warnings
import time
from datetime import datetime, timedelta
from termcolor import colored
import numpy as np
import pandas as pd
from yahoo_fin import stock_info
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
def get_live_stock_price(symbol):
    try:
        live_price = stock_info.get_live_price(symbol)
        return live_price
    except Exception as e:
        print(f"Error fetching live price for {symbol}: {e}")
        return None
def get_historical_data(symbol, interval='1d', period='1d'):
    try:
        periods = {'1w': 1, '1m': 4, '3m': 12, '6m': 24, '1y': 52, '1d': 1}
        start_date = (datetime.now() - timedelta(weeks=periods.get(period, 1))).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        historical_data = stock_info.get_data(symbol, interval=interval, start_date=start_date, end_date=end_date)
        return historical_data, start_date
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
        return None, None
def is_market_open():
    current_time = datetime.now().time()
    current_day = datetime.now().weekday()
    market_open_time = datetime.strptime("09:15", "%H:%M").time()
    market_close_time = datetime.strptime("15:30", "%H:%M").time()
    valid_trading_days = [0, 1, 2, 3, 4]
    return current_day in valid_trading_days and market_open_time <= current_time <= market_close_time
def predict_price(symbol, historical_data, prediction_period):
    try:
        if historical_data is not None and not historical_data.empty:
            historical_data['close'] = pd.to_numeric(historical_data['close'], errors='coerce')
            historical_data = historical_data.dropna(subset=['close']).copy()
            historical_data['time'] = range(1, len(historical_data) + 1)
            X = historical_data[['time']]
            y = historical_data['close']
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model = LinearRegression()
            model.fit(X_train, y_train)
            future_time = len(historical_data) + np.arange(1, prediction_period + 1)
            future_prices = model.predict(future_time.reshape(-1, 1))
            price_change = future_prices[-1] - historical_data['close'].iloc[-1]
            current_price = get_live_stock_price(symbol)
            return current_price + price_change
    except Exception as e:
        print(f"Error predicting price for {symbol}: {e}")
    return None
def display_prices():
    while True:
        symbol = input("Enter the stock symbol (e.g., TCS.BO for BSE or TCS.NS for NSE): ")
        while True:
            current_price = get_live_stock_price(symbol)
            if current_price is not None:
                market_status = "Open" if is_market_open() else "Closed"
                status_color = 'green' if is_market_open() else 'yellow'
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(colored(f"\n{current_time} | Company: {symbol} | Live Price: {current_price}", status_color))
                print(colored(f"Market Status: {market_status}", status_color))
                periods = {'1d': 'after 1 day', '1w': 'after 1 week', '1m': 'after 1 month', '3m': 'after 3 months', '6m': 'after 6 months', '1y': 'after 1 year'} 
                for period, label in periods.items():
                    historical_data, start_date_price = get_historical_data(symbol, period=period)
                    if historical_data is not None:
                        start_date_price = historical_data['close'].iloc[0]
                        price_difference = current_price - start_date_price    
                        print(f"\nPrice details {label} from {start_date_price} to {datetime.now().strftime('%Y-%m-%d')}")
                        print(f"Start Price: {start_date_price} | Present Price: {current_price}", end=" ") 
                        if price_difference >= 0:
                            colored_diff = colored(f"Price Difference: {price_difference}", 'green')
                        else:
                            colored_diff = colored(f"Price Difference: {price_difference}", 'red')
                        print(colored_diff)
                        prediction_period = {'1d': 1, '1w': 7, '1m': 30, '3m': 90, '6m': 180, '1y': 365}.get(period, 1)
                        predicted_price = predict_price(symbol, historical_data, prediction_period)
                        if predicted_price is not None:
                            colored_predicted_price = colored(f"Predicted Price {label}: {predicted_price:.2f}", 'blue')
                            print(colored_predicted_price)             
            user_input = input("Enter 'exit' to exit or press Enter to display prices for the same stock symbol, or enter a new stock symbol: ")
            if user_input.lower() == 'exit':
                break
            elif user_input.strip():
                symbol = user_input
if __name__ == "__main__":
    display_prices()