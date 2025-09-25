import os
import warnings
import re
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from datetime import datetime, timedelta
import string
import sys
import time
import pandas as pd

# Suppress warnings
warnings.filterwarnings('ignore')

class AIMarketAssistant:
    def __init__(self):
        print("Initializing AI Market Assistant...")
        self.company_map = {
            "reliance": "RELIANCE.NS",
            "tata steel": "TATASTEEL.NS",
            "infosys": "INFY.NS",
            "hdfc bank": "HDFCBANK.NS",
            "sbi": "SBIN.NS",
            "tcs": "TCS.NS",
            "icici bank": "ICICIBANK.NS",
            "maruti suzuki": "MARUTI.NS",
            "bajaj auto": "BAJAJ-AUTO.NS",
            "bajaj finserv": "BAJFINANCE.NS",
            "bharat petroleum": "BPCL.NS",
            "wipro": "WIPRO.NS",
            "adani ports": "ADANIPORTS.NS",
            "coal india": "COALINDIA.NS",
            "dr. reddy's": "DRREDDY.NS",
            "gail": "GAIL.NS",
            "hero motocorp": "HEROMOTOCO.NS",
            "hindalco": "HINDALCO.NS",
            "sun pharma": "SUNPHARMA.NS",
            "ultratech cement": "ULTRACEMCO.NS"
        }
        self.temporal_map = {
            'past': {
                'keywords': [
                    'last', 'previous', 'earlier', 'ago', 
                    'historical', 'before', 'past performance'
                ],
                'period': 'past'
            },
            'present': {
                'keywords': [
                    'now', 'current', 'today', 'right now', 
                    'present', 'ongoing', 'currently'
                ],
                'period': 'present'
            },
            'future': {
                'keywords': [
                    'next', 'coming', 'upcoming', 'will', 
                    'forecast', 'predict', 'future', 'expected',
                    'invest in', 'good for investment'
                ],
                'period': 'future'
            }
        }
        self.intents = {
            'recommend': r'(recommend|best|top|performing|good for investment)',
            'long_term': r'(invest|investment|long term|future)'
        }
        print("AI Market Assistant is ready to help!")

    def typing_animation(self, text: str, delay: float = 0.03):
        """Faster typing animation with a specified delay between each character."""
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(delay)
        print()  # To move to the next line after finishing the animation

    def detect_temporal_context(self, query: str) -> str:
        """Detect temporal context of the query."""
        normalized_query = query.lower()
        
        for context, details in self.temporal_map.items():
            for keyword in details['keywords']:
                if keyword in normalized_query:
                    return context
        
        return 'future'  # Default to future for investment queries

    def parse_time_period(self, query: str, temporal_context: str) -> tuple:
        """Parse time period based on temporal context and query."""
        time_patterns = [
            r'(\d+)\s*(day|days)',
            r'(\d+)\s*(week|weeks)',
            r'(\d+)\s*(month|months)',
            r'(\d+)\s*(year|years)'
        ]
        
        # Default periods based on temporal context
        default_periods = {
            'past': '3mo',    # Look back 3 months for past context
            'present': '1mo',  # Current month's data
            'future': '3mo'   # Forecast/prediction for next 3 months
        }
        
        for pattern in time_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                unit = match.group(2).lower()
                
                if 'day' in unit:
                    return f"{value}d", timedelta(days=value)
                elif 'week' in unit:
                    return f"{value}wk", timedelta(weeks=value)
                elif 'month' in unit:
                    return f"{value}mo", timedelta(days=value*30)
                elif 'year' in unit:
                    return f"{value}y", timedelta(days=value*365)
        
        # Return default period based on temporal context
        return default_periods[temporal_context], None

    def understand_query(self, query: str) -> dict:
        """Enhanced query understanding with temporal context."""
        understanding = {
            'intents': [],
            'symbols': list(self.company_map.values()),  # Default to all stocks
            'timeframe': None,
            'num_recommendations': 5,
            'temporal_context': self.detect_temporal_context(query)
        }

        normalized_query = query.lower()

        # Identify intents
        for intent, pattern in self.intents.items():
            if re.search(pattern, normalized_query):
                understanding['intents'].append(intent)

        # Parse time period
        period_str, _ = self.parse_time_period(
            query, 
            understanding['temporal_context']
        )
        understanding['timeframe'] = period_str

        # Number of recommendations
        num_matches = re.findall(r'top\s*(\d+)', normalized_query)
        if num_matches:
            understanding['num_recommendations'] = int(num_matches[0])

        # Default fallbacks
        if not understanding['intents']:
            understanding['intents'].append('recommend')

        return understanding

    def analyze_stock(self, symbol: str, period: str = '3mo', intent: str = 'recommend') -> dict:
        """Analyze a single stock based on the intent and time period."""
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period=period)

            rsi = RSIIndicator(hist['Close']).rsi()[-1]
            sma = SMAIndicator(hist['Close'], window=50).sma_indicator()[-1]
            current_price = hist['Close'][-1]
            initial_price = hist['Close'][0]
            
            # Calculate percentage return and future potential
            percent_return = ((current_price - initial_price) / initial_price) * 100
            
            # Simple future potential estimation
            future_potential = percent_return * 1.2  # Slightly optimistic projection

            return {
                'symbol': symbol,
                'current_price': current_price,
                'rsi': rsi,
                'sma': sma,
                'percent_return': percent_return,
                'future_potential': future_potential
            }
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None

    def recommend_stocks(self, num_recommendations: int = 5, period: str = '3mo') -> list:
        """Recommend top performing stocks based on future potential."""
        stock_performances = []
        
        for symbol in self.company_map.values():
            analysis = self.analyze_stock(symbol, period)
            if analysis:
                stock_performances.append(analysis)
        
        # Sort stocks by future potential in descending order
        sorted_stocks = sorted(stock_performances, key=lambda x: x['future_potential'], reverse=True)
        return sorted_stocks[:num_recommendations]

    def process_query(self, query: str) -> str:
        """Process user query and generate a targeted response."""
        understanding = self.understand_query(query)

        # Handle specific stock queries
        for name, symbol in self.company_map.items():
            if name in query.lower():
                # If a specific company is mentioned, focus only on that stock
                analysis = self.analyze_stock(symbol, understanding['timeframe'])
                
                if analysis:
                    return (
                        f"Investment Analysis for {name.title()} ({understanding['timeframe']}):\n"
                        f"Current Price: ₹{analysis['current_price']:.2f} | "
                        f"Current Return: {analysis['percent_return']:.2f}% | "
                        f"Future Potential: {analysis['future_potential']:.2f}% | "
                        f"RSI: {analysis['rsi']:.2f}"
                    )

        # Existing general recommendation logic
        temporal_context = understanding['temporal_context']
        response_prefix = f"Investment Recommendations ({understanding['timeframe']}):\n"

        recommendations = self.recommend_stocks(
            understanding['num_recommendations'], 
            understanding['timeframe']
        )
        
        response = response_prefix
        for stock in recommendations:
            response += (
                f"{stock['symbol']}: "
                f"₹{stock['current_price']:.2f} | "
                f"Current Return: {stock['percent_return']:.2f}% | "
                f"Future Potential: {stock['future_potential']:.2f}% | "
                f"RSI: {stock['rsi']:.2f}\n"
            )
        return response

    def chat(self):
        """Interactive chat interface with typing animation."""
        self.typing_animation("\n💬 Hi! I'm your AI Market Assistant. Ask me anything about stocks!")
        self.typing_animation("Examples:")
        self.typing_animation("- 'Which 5 stocks are good for investment?'")
        self.typing_animation("- 'Top companies to invest in for next 3 months'")
        self.typing_animation("- 'What is the current price of Reliance?'")

        try:
            while True:
                query = input("\nYou: ")

                if query.lower() in ['exit', 'quit', 'bye']:
                    self.typing_animation("\nGoodbye! Happy trading! 👋")
                    break

                response = self.process_query(query)
                self.typing_animation("\nAI: " + response)

        except KeyboardInterrupt:
            self.typing_animation("\n\nGoodbye! Thanks for using AI Market Assistant! 👋")

if __name__ == "__main__":
    assistant = AIMarketAssistant()
    assistant.chat()
    
