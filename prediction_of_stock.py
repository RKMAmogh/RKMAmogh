import os
import yfinance as yf
import pandas as pd
import numpy as np
from tkinter import *
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random
from colorama import init, Fore

init(autoreset=True)

# List of default NSE stocks
STOCKS = [
    "TCS.NS", "INFY.NS", "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "M&M.NS",
    "ITC.NS", "BAJAJ-AUTO.NS", "SBIN.NS", "MARUTI.NS", "TATAMOTORS.NS", "ADANIGREEN.NS"
]

# Corrected Time Periods to match yfinance intervals
TIME_PERIODS = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]

# Function to fetch live data
def fetch_live_data(selected_time):
    live_data = []
    for stock in STOCKS:
        try:
            ticker = yf.Ticker(stock)
            
            # Adjust period based on interval
            if selected_time in ["1m", "2m", "5m", "15m", "30m"]:
                hist = ticker.history(period='1d', interval=selected_time)
            elif selected_time in ["60m", "90m", "1h"]:
                hist = ticker.history(period='5d', interval=selected_time)
            else:
                hist = ticker.history(period='1mo', interval=selected_time)
            
            if not hist.empty:
                last_day = hist.iloc[-100:]
                current_price = last_day['Close'].iloc[-1]
                previous_close = last_day['Close'].iloc[0]
                percent_change = ((current_price - previous_close) / previous_close) * 100
                
                # Avoid errors with insufficient data for moving averages
                ma_short = last_day['Close'].rolling(window=min(20, len(last_day))).mean().iloc[-1]
                ma_long = last_day['Close'].rolling(window=min(50, len(last_day))).mean().iloc[-1]
                
                today_open = last_day['Open'].iloc[0]
                gap_percentage = ((today_open - previous_close) / previous_close) * 100
                
                volatility = last_day['Close'].pct_change().std() * 100
                
                live_data.append({
                    'Stock': stock.replace('.NS', ''),
                    'Current Price': round(current_price, 2),
                    'Previous Close': round(previous_close, 2),
                    'Change (%)': round(percent_change, 2),
                    'Gap (%)': round(gap_percentage, 2),
                    'Short MA': round(ma_short, 2),
                    'Long MA': round(ma_long, 2),
                    'Volatility (%)': round(volatility, 2),
                })
        except Exception as e:
            print(f"Error fetching data for {stock}: {e}")
    return pd.DataFrame(live_data)

# Function to add stock
def add_stock(symbol):
    global STOCKS
    # Remove any existing .NS and convert to uppercase
    symbol = symbol.replace('.NS', '').upper()
    full_symbol = symbol + '.NS'
    
    if full_symbol not in STOCKS:
        try:
            # Verify the stock exists by fetching its data
            ticker = yf.Ticker(full_symbol)
            hist = ticker.history(period='1d')
            
            if not hist.empty:
                STOCKS.append(full_symbol)
                messagebox.showinfo("Success", f"Stock {symbol} added successfully.")
                update_table()
            else:
                messagebox.showerror("Error", f"No data found for stock {symbol}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not add stock {symbol}: {str(e)}")
    else:
        messagebox.showwarning("Warning", f"Stock {symbol} already exists.")

# Function to remove stock
def remove_stock():
    stock_symbol = entry_remove_symbol.get().replace('.NS', '').upper() + '.NS'
    if stock_symbol in STOCKS:
        STOCKS.remove(stock_symbol)
        messagebox.showinfo("Success", f"Stock {stock_symbol} removed successfully.")
        update_table()
    else:
        messagebox.showerror("Error", f"Stock {stock_symbol} not found.")

# Function to update table data
def update_table():
    try:
        selected_time = time_period_var.get()
        stock_data = fetch_live_data(selected_time)
        if not stock_data.empty:
            table.delete(*table.get_children())  # Clear table
            for _, row in stock_data.iterrows():
                table.insert("", "end", values=list(row.values))
        else:
            messagebox.showwarning("No Data", "Could not fetch stock data. Please check your internet connection.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    # Auto-refresh based on selected interval
    if auto_refresh_var.get():
        # Set refresh interval based on time period
        refresh_intervals = {
            "1m": 60000,   # 1 minute
            "2m": 120000,  # 2 minutes
            "5m": 300000,  # 5 minutes
            "15m": 900000, # 15 minutes
            "30m": 1800000,# 30 minutes
            "60m": 3600000,# 1 hour
            "1h": 3600000, # 1 hour
            "1d": 86400000 # 1 day
        }
        interval = refresh_intervals.get(selected_time, 300000)  # default to 5 minutes
        root.after(interval, update_table)

# Toggle auto-refresh
def toggle_auto_refresh():
    if auto_refresh_var.get():
        update_table()  # Start immediate refresh
    else:
        # Cancel any pending updates
        root.after_cancel(update_table)

# Function to display pop-up with graph and analysis
def show_details():
    selected_item = table.selection()
    if not selected_item:
        messagebox.showwarning("No Selection", "Please select a stock to view details.")
        return
    
    stock_data = table.item(selected_item)['values']
    stock_name = stock_data[0] + '.NS'

    popup = Toplevel(root)
    popup.title(f"Details for {stock_data[0]}")
    popup.geometry("900x500")
    
    try:
        # Create a frame for the graph
        graph_frame = Frame(popup)
        graph_frame.pack(side=LEFT, fill=BOTH, expand=True)

        fig, ax = plt.subplots(figsize=(6, 4))
        ticker = yf.Ticker(stock_name)
        
        # Use the same interval logic as in fetch_live_data
        selected_time = time_period_var.get()
        if selected_time in ["1m", "2m", "5m", "15m", "30m"]:
            hist = ticker.history(period='1d', interval=selected_time)
        elif selected_time in ["60m", "90m", "1h"]:
            hist = ticker.history(period='5d', interval=selected_time)
        else:
            hist = ticker.history(period='1mo', interval=selected_time)
        
        hist['Close'].plot(ax=ax, title=f"Stock Price for {stock_data[0]}")
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=True)
        
        # Create a frame for analysis
        analysis_frame = Frame(popup)
        analysis_frame.pack(side=RIGHT, fill=BOTH, expand=True)
        
        Label(analysis_frame, text="Analysis and News", font=("Arial", 16)).pack(pady=10)
        analysis_text = Text(analysis_frame, wrap=WORD, height=20, width=40)
        analysis_text.insert(END, f"Stock: {stock_data[0]}\n\n")
        analysis_text.insert(END, f"Current Price: {stock_data[1]}\n")
        analysis_text.insert(END, f"Previous Close: {stock_data[2]}\n")
        analysis_text.insert(END, f"Change (%): {stock_data[3]}\n")
        analysis_text.insert(END, f"Gap (%): {stock_data[4]}\n")
        analysis_text.insert(END, f"Short MA: {stock_data[5]}\n")
        analysis_text.insert(END, f"Long MA: {stock_data[6]}\n")
        analysis_text.insert(END, "\nImportant News:\n- Placeholder for company news.")
        analysis_text.pack()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load details: {str(e)}")

# GUI Setup
root = Tk()
root.title("Stock Market Analysis")
root.geometry("1000x500")  # Reduced height and width

# Frame for top controls
top_frame = Frame(root)
top_frame.pack(pady=5, padx=5, fill=X)

# Dropdown for time period selection
time_period_label = Label(top_frame, text="Time Period:")
time_period_label.pack(side=LEFT, padx=(0,5))
time_period_var = StringVar(value="5m")
time_period_menu = ttk.Combobox(top_frame, textvariable=time_period_var, values=TIME_PERIODS, state="readonly", width=10)
time_period_menu.pack(side=LEFT, padx=(0,10))

# Auto-refresh checkbox
auto_refresh_var = BooleanVar(value=False)
auto_refresh_check = Checkbutton(top_frame, text="Auto Refresh", variable=auto_refresh_var, command=toggle_auto_refresh)
auto_refresh_check.pack(side=LEFT, padx=(10,0))

# Add/Remove stock frame
stock_frame = Frame(top_frame)
stock_frame.pack(side=RIGHT)

entry_remove_symbol = Entry(stock_frame, width=10)
entry_remove_symbol.pack(side=LEFT, padx=(0,5))
remove_button = Button(stock_frame, text="Remove", command=remove_stock, width=6)
remove_button.pack(side=LEFT, padx=(0,5))
add_button = Button(stock_frame, text="Add", command=lambda: add_stock(entry_remove_symbol.get()), width=6)
add_button.pack(side=LEFT)

# Table to display stock data
columns = ["Stock", "Current Price", "Previous Close", "Change (%)", "Gap (%)", "Short MA", "Long MA", "Volatility (%)"]
table = ttk.Treeview(root, columns=columns, show="headings", height=15)
table.pack(fill=BOTH, expand=True, padx=5, pady=5)

# Configure column widths to make data more compact
column_widths = [50, 80, 90, 70, 60, 70, 70, 80]
for col, width in zip(columns, column_widths):
    table.heading(col, text=col)
    table.column(col, width=width, anchor='center')

# Bottom buttons frame
bottom_frame = Frame(root)
bottom_frame.pack(pady=5, fill=X)

details_button = Button(bottom_frame, text="View Details", command=show_details, width=10)
details_button.pack(side=LEFT, padx=5)

refresh_button = Button(bottom_frame, text="Manual Refresh", command=update_table, width=10)
refresh_button.pack(side=LEFT, padx=5)

# Initialize table with data
update_table()

root.mainloop()