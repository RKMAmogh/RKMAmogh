import os
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import time
from colorama import init, Fore
import random

init(autoreset=True)

# List of NSE stocks to analyze
STOCKS = [
    "TCS.NS", "INFY.NS", "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "M&M.NS", 
    "ITC.NS", "BAJAJ-AUTO.NS", "SBIN.NS", "MUTHOOTFIN.NS", "MARUTI.NS", "TATAMOTORS.NS", "ADANIGREEN.NS", 
    "SHREECEM.NS", "BHARTIARTL.NS", "BAJAJFINSV.NS", "HINDUNILVR.NS", "WIPRO.NS", "GRASIM.NS"
]
   
# Strategy Parameters
PERCENT_CHANGE_BUY = 0.25 
PERCENT_CHANGE_SELL = -0.25
MOVING_AVERAGE_PERIODS = [20, 50]  # Short and long-term moving averages
RSI_PERIOD = 14
BOLLINGER_BANDS_PERIOD = 20
BOLLINGER_BANDS_STD_DEV = 2

def fetch_live_data():
    """Fetch historical data for defined stocks with additional analysis."""
    live_data = []
    for stock in STOCKS:
        try:
            ticker = yf.Ticker(stock)
            # Fetch last 5 days of data with 5-minute intervals
            hist = ticker.history(period='5d', interval='5m')
            if not hist.empty:
                # Get the last day's data
                last_day = hist.iloc[-100:]  # Last 100 5-minute candles
                
                # Basic price data
                current_price = last_day['Close'].iloc[-1]
                previous_close = last_day['Close'].iloc[0]
                percent_change = ((current_price - previous_close) / previous_close) * 100
                
                # Moving Average Crossover Analysis
                ma_short = last_day['Close'].rolling(window=MOVING_AVERAGE_PERIODS[0]).mean().iloc[-1]
                ma_long = last_day['Close'].rolling(window=MOVING_AVERAGE_PERIODS[1]).mean().iloc[-1]
                
                # Gap Analysis
                today_open = last_day['Open'].iloc[0]
                gap_percentage = ((today_open - previous_close) / previous_close) * 100
                
                # Momentum and Volatility Indicators
                volatility = last_day['Close'].pct_change().std() * 100
                momentum = percent_change
                
                # RSI calculation
                delta = last_day['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                # Bollinger Bands
                moving_avg = last_day['Close'].rolling(window=BOLLINGER_BANDS_PERIOD).mean()
                moving_std = last_day['Close'].rolling(window=BOLLINGER_BANDS_PERIOD).std()
                upper_band = moving_avg + (moving_std * BOLLINGER_BANDS_STD_DEV)
                lower_band = moving_avg - (moving_std * BOLLINGER_BANDS_STD_DEV)
                price_position = "Neutral"
                if current_price > upper_band.iloc[-1]:
                    price_position = "Overbought"
                elif current_price < lower_band.iloc[-1]:
                    price_position = "Oversold"
                
                # Volume Analysis
                volume_avg = last_day['Volume'].rolling(window=50).mean()
                current_volume = last_day['Volume'].iloc[-1]
                volume_strength = "Normal"
                if current_volume > volume_avg.iloc[-1] * 1.5:
                    volume_strength = "High Volume"
                elif current_volume < volume_avg.iloc[-1] * 0.5:
                    volume_strength = "Low Volume"
                
                live_data.append({
                    'Stock': stock,
                    'Current Price': round(current_price, 2),
                    'Previous Close': round(previous_close, 2),
                    'Change (%)': round(percent_change, 2),
                    'Gap (%)': round(gap_percentage, 2),
                    'Short MA': round(ma_short, 2),
                    'Long MA': round(ma_long, 2),
                    'Volatility (%)': round(volatility, 2),
                    'Momentum (%)': round(momentum, 2),
                    'RSI': round(rsi, 2),
                    'Bollinger Position': price_position,
                    'Volume Strength': volume_strength
                })
        except Exception as e:
            print(f"Error fetching data for {stock}: {e}")
    return pd.DataFrame(live_data)

def analyze_data(df):
    """Advanced strategy-based recommendations."""
    recommendations = []
    for _, row in df.iterrows():
        score = 0
        # Momentum Strategy Scoring
        if row['Change (%)'] >= PERCENT_CHANGE_BUY:
            score += 2
        elif row['Change (%)'] <= PERCENT_CHANGE_SELL:
            score -= 2
        
        # Moving Average Crossover Strategy
        if row['Short MA'] > row['Long MA']:
            score += 1
        elif row['Short MA'] < row['Long MA']:
            score -= 1
        
        # Breakout Strategy
        if row['Gap (%)'] > 1:  # Significant gap up
            score += 1
        elif row['Gap (%)'] < -1:  # Significant gap down
            score -= 1
        
        # RSI Strategy (Overbought/Oversold)
        if row['RSI'] < 30:  # Oversold (Buy signal)
            score += 1
        elif row['RSI'] > 70:  # Overbought (Sell signal)
            score -= 1
        
        # Bollinger Bands Strategy
        if row['Bollinger Position'] == "Oversold":
            score += 1
        elif row['Bollinger Position'] == "Overbought":
            score -= 1
        
        # Volume Analysis Strategy
        if row['Volume Strength'] == "High Volume":
            score += 1
        elif row['Volume Strength'] == "Low Volume":
            score -= 1
        
        # Final Recommendation
        if score > 1:
            recommendation = Fore.GREEN + 'Strong Buy'
        elif score > 0:
            recommendation = Fore.GREEN + 'Buy'
        elif score < -1:
            recommendation = Fore.RED + 'Strong Sell'
        elif score < 0:
            recommendation = Fore.RED + 'Sell'
        else:
            recommendation = Fore.YELLOW + 'Hold'  
        recommendations.append(recommendation)
    
    df['Recommendation'] = recommendations
    return df

def predict_prices(stock):
    """Enhanced price prediction with multiple strategies."""
    try:
        ticker = yf.Ticker(stock)
        hist = ticker.history(period='5d', interval='5m')
        if len(hist) < 15:
            return ["Insufficient Data"] * 5
        
        # Use the last day's data for predictions
        last_day = hist.iloc[-100:]
        
        # Multiple prediction techniques
        price_changes = last_day['Close'].pct_change().dropna()
        
        # Calculate average price change and volatility
        avg_change = price_changes.mean()
        volatility = price_changes.std()
        
        # Current price as starting point
        current_price = last_day['Close'].iloc[-1]
        
        # Generate predictions with randomness and trend
        predictions = []
        for i in range(1, 6):
            # Combine trend and volatility for prediction
            trend = avg_change * i
            random_factor = np.random.normal(0, volatility)
            predicted_change = trend + random_factor
            predicted_price = current_price * (1 + predicted_change)
            predictions.append(round(predicted_price, 2))
        
        return predictions
    except Exception as e:
        print(f"Error predicting prices for {stock}: {e}")
        return ["Error"] * 5

def display_data(df, predictions):
    """Enhanced display with multi-strategy insights."""
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear the terminal screen
    
    # Column headers for the main data table
    header = (
        f"{'Stock':<15} {'Price':<10} {'Prev Close':<12} {'Change%':<10} {'Gap%':<10} "
        f"{'ShortMA':<10} {'LongMA':<10} {'Volatility%':<12} {'RSI':<8} "
        f"{'Bollinger':<12} {'Volume Strength':<15} {'Recommendation'}"
    )
    
    # Print the header
    print("-" * len(header)) 
    print("Advanced Stock Market Analysis (Historical Data):")
    print("Last Updated:", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(header)
    print("-" * len(header))
    
    # Print each row of stock data
    for index, row in df.iterrows():
        print(f"{row['Stock']:<15} "
              f"{row['Current Price']:<10.2f} "
              f"{row['Previous Close']:<12.2f} "
              f"{row['Change (%)']:<10.2f} "
              f"{row['Gap (%)']:<10.2f} "
              f"{row['Short MA']:<10.2f} "
              f"{row['Long MA']:<10.2f} "
              f"{row['Volatility (%)']:<12.2f} "
              f"{row['RSI']:<8.2f} "
              f"{row['Bollinger Position']:<12} "
              f"{row['Volume Strength']:<15} "
              f"{row['Recommendation']}")
    
    # Divider line
    print("-" * len(header))

    # Print the prediction table
    print("\nPrice Predictions for the Next 25 Minutes (5-minute intervals):")
    print(f"{'Stock':<15} {'5 Min':<10} {'10 Min':<10} {'15 Min':<10} {'20 Min':<10} {'25 Min':<10}")
    print("-" * 72)
    # Print each stock's predictions
    for stock, pred in zip(STOCKS, predictions):
        if pred[0] == "Insufficient Data" or pred[0] == "Error":
            print(f"{stock:<15} {'Insufficient Data/Error':<50}")
        else:
            prev_price = df.loc[df['Stock'] == stock, 'Current Price'].iloc[0]
            prediction_str = f"{stock:<15}"
            for price in pred:
                if price > prev_price:
                    prediction_str += f"{Fore.GREEN}{price:<10.2f}"
                else:
                    prediction_str += f"{Fore.RED}{price:<10.2f}"
                prev_price = price
            print(prediction_str)

    print("-" * 72)
    print("\nNote: This analysis is based on historical data. For live trading, please run during market hours (9:15 AM - 3:30 PM IST)")
    print("Update Frequency: Data refreshes every 60 seconds")

def main():
    print("Initiating Advanced Stock Market Analysis System...\n")
    print("Loading historical data for analysis...\n")
    while True:
        try:
            stock_data = fetch_live_data()
            if not stock_data.empty:
                analyzed_data = analyze_data(stock_data)
                predictions = [predict_prices(stock) for stock in STOCKS]
                display_data(analyzed_data, predictions)
            else:
                print("No data available. Retrying...\n")
        except Exception as e:
            print(f"An error occurred: {e}")
        
        print("\nWaiting for next update...")
        time.sleep(60)  # Update every 60 seconds
if __name__ == "__main__":
    main()
    