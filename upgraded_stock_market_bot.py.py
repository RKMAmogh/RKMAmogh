import os
import warnings
import re
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD
from ta.volatility import BollingerBands
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from functools import lru_cache
import sys
import time
from fuzzywuzzy import process

# Suppress warnings
warnings.filterwarnings('ignore')

class AIMarketAssistant:
    def __init__(self, csv_path):
        print("Initializing AI Market Assistant...")
        self.intents = {
            'recommend': r'(recommend|best|top|performing|good for investment)',
            'long_term': r'(invest|investment|long term|future)',
            'risk': r'(risk level|risk assessment|risky|safe)',
            'price': r'(price|rate|cost|worth|value)',
            'technical': r'(technical|analysis|rsi|macd|indicators)',
            'company': r'(company|stock|share)'
        }
        self.load_company_data(csv_path)
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
        self.load_config()
        self.risk_profiles = {
            'conservative': {'rsi_threshold': 70, 'volatility_threshold': 0.15},
            'moderate': {'rsi_threshold': 60, 'volatility_threshold': 0.25},
            'aggressive': {'rsi_threshold': 50, 'volatility_threshold': 0.35}
        }
        self.indicators = {
            'MACD': MACD,
            'Bollinger': BollingerBands
        }
        self.day_trading_indicators = {
            'Volume': lambda df: df['Volume'],
            'Price_Change': lambda df: df['Close'] - df['Open'],
            'High_Low_Range': lambda df: df['High'] - df['Low'],
            'Price_Momentum': lambda df: df['Close'].pct_change(),
            'VWAP': lambda df: (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        }
        print("AI Market Assistant is ready to help!")

    def load_company_data(self, csv_path):
        """Load company data from CSV file and create company_map"""
        try:
            df = pd.read_csv(csv_path)
            self.company_map = {}
            self.symbol_to_name = {}
            self.name_variations = {}
            
            for _, row in df.iterrows():
                company_name = row['NAME OF COMPANY'].strip()
                symbol = row['SYMBOL'].strip()
                
                # Store original name
                self.company_map[company_name.lower()] = f"{symbol}.NS"
                self.symbol_to_name[symbol.lower()] = company_name
                
                # Create variations
                name_parts = company_name.lower().split()
                for i in range(len(name_parts)):
                    for j in range(i + 1, len(name_parts) + 1):
                        variation = ' '.join(name_parts[i:j])
                        self.name_variations[variation] = company_name
                        
                # Add symbol variations
                self.company_map[symbol.lower()] = f"{symbol}.NS"
                self.name_variations[symbol.lower()] = company_name
                
            print(f"Successfully loaded {len(df)} companies from CSV")
            print("Loaded companies:", list(self.company_map.keys())[:10])
            
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            self.company_map = {}
            self.symbol_to_name = {}
            self.name_variations = {}

    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {
                'default_period': '3mo',
                'default_recommendations': 5,
                'risk_profile': 'moderate'
            }

    def typing_animation(self, text: str, delay: float = 0.03):
        """Faster typing animation with a specified delay between each character."""
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(delay)
        print()

    def detect_temporal_context(self, query: str) -> str:
        """Detect temporal context of the query."""
        normalized_query = query.lower()
        
        for context, details in self.temporal_map.items():
            for keyword in details['keywords']:
                if keyword in normalized_query:
                    return context
        
        return 'future'

    def parse_time_period(self, query: str, temporal_context: str) -> tuple:
        """Parse time period based on temporal context and query."""
        time_patterns = [
            r'(\d+)\s*(day|days)',
            r'(\d+)\s*(week|weeks)',
            r'(\d+)\s*(month|months)',
            r'(\d+)\s*(year|years)'
        ]
        
        default_periods = {
            'past': '3mo',
            'present': '1mo',
            'future': '3mo'
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
        
        return default_periods[temporal_context], None

    def understand_query(self, query: str) -> dict:
        """Enhanced query understanding with temporal context."""
        understanding = {
            'intents': [],
            'symbols': list(self.company_map.values()),
            'timeframe': None,
            'num_recommendations': 5,
            'temporal_context': self.detect_temporal_context(query)
        }

        normalized_query = query.lower()

        for intent, pattern in self.intents.items():
            if re.search(pattern, normalized_query):
                understanding['intents'].append(intent)

        period_str, _ = self.parse_time_period(query, understanding['temporal_context'])
        understanding['timeframe'] = period_str

        num_matches = re.findall(r'(\d+)\s*(?:companies|stocks)', normalized_query)
        if num_matches:
            understanding['num_recommendations'] = int(num_matches[0])

        if not understanding['intents']:
            understanding['intents'].append('recommend')

        return understanding

    @lru_cache(maxsize=100)
    def get_stock_data(self, symbol: str, period: str = '3mo') -> pd.DataFrame:
        """Cached stock data retrieval"""
        try:
            stock = yf.Ticker(symbol)
            return stock.history(period=period)
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()  # Return an empty DataFrame instead of None

    def analyze_stock(self, symbol: str, period: str = '3mo', intent: str = 'recommend') -> dict:
        """Enhanced stock analysis with additional technical indicators"""
        hist = self.get_stock_data(symbol, period)
        if hist is None or hist.empty:
            return None
            
        try:
            rsi = RSIIndicator(hist['Close']).rsi()[-1]
            sma = SMAIndicator(hist['Close'], window=50).sma_indicator()[-1]
            current_price = hist['Close'][-1]
            initial_price = hist['Close'][0]
            percent_return = ((current_price - initial_price) / initial_price) * 100
            future_potential = percent_return * 1.2

            macd = MACD(hist['Close'])
            bb = BollingerBands(hist['Close'])
            volatility = hist['Close'].pct_change().std()

            return {
                'symbol': symbol,
                'current_price': current_price,
                'rsi': rsi,
                'sma': sma,
                'percent_return': percent_return,
                'future_potential': future_potential,
                'macd_signal': macd.macd_signal().iloc[-1],
                'bb_upper': bb.bollinger_hband().iloc[-1],
                'bb_lower': bb.bollinger_lband().iloc[-1],
                'volatility': volatility,
                'volume': hist['Volume'].mean(),
                'price_trend': 'Upward' if hist['Close'].iloc[-1] > hist['Close'].mean() else 'Downward'
            }
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None

    def generate_report(self, symbol: str, period: str = '3mo') -> str:
        """Generate detailed analysis report"""
        analysis = self.analyze_stock(symbol, period)
        if not analysis:
            return "Unable to generate report"
        
        report = f"""
Detailed Analysis Report for {symbol}
{'-'*50}
Price Analysis:
- Current Price: ₹{analysis['current_price']:.2f}
- Return: {analysis['percent_return']:.2f}%
- Future Potential: {analysis['future_potential']:.2f}%

Technical Indicators:
- RSI: {analysis['rsi']:.2f}
- MACD Signal: {analysis['macd_signal']:.2f}
- Bollinger Bands: 
  Upper: ₹{analysis['bb_upper']:.2f}
  Lower: ₹{analysis['bb_lower']:.2f}

Market Metrics:
- Volatility: {analysis['volatility']*100:.2f}%
- Average Volume: {analysis['volume']:,.0f}
- Price Trend: {analysis['price_trend']}

Risk Assessment:
- {'High' if analysis['volatility'] > 0.25 else 'Moderate' if analysis['volatility'] > 0.15 else 'Low'} Risk
- {'Overbought' if analysis['rsi'] > 70 else 'Oversold' if analysis['rsi'] < 30 else 'Neutral'} RSI
"""
        return report

    def recommend_stocks(self, num_recommendations: int = 5, period: str = '3mo') -> list:
        """Recommend top performing stocks based on future potential."""
        stock_performances = []
        
        for symbol in self.company_map.values():
            analysis = self.analyze_stock(symbol, period)
            if analysis:
                stock_performances.append(analysis)
        
        sorted_stocks = sorted(stock_performances, key=lambda x: x['future_potential'], reverse=True)
        return sorted_stocks[:num_recommendations]

    def process_query(self, query: str) -> str:
        """Process user query and return response."""
        budget_keywords = ['invest', 'budget', 'rs', 'inr', '₹']
        is_budget_query = any(keyword in query.lower() for keyword in budget_keywords)
        
        if is_budget_query:
            budget_pattern = r'(?:rs\.?|inr|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)'
            budget_match = re.search(budget_pattern, query)
            if budget_match:
                budget = float(budget_match.group(1).replace(',', ''))
                
                affordable_stocks = []
                for symbol in self.company_map.values():
                    analysis = self.analyze_stock(symbol)
                    if analysis and analysis['current_price'] <= budget:
                        affordable_stocks.append(analysis)
                
                if not affordable_stocks:
                    return f"Sorry, no stocks found within your budget of ₹{budget:,.2f}"
                
                affordable_stocks.sort(key=lambda x: x['future_potential'], reverse=True)
                
                num_pattern = r'(\d+)\s*(?:company|companies|stock|stocks)'
                num_match = re.search(num_pattern, query)
                num_recommendations = int(num_match.group(1)) if num_match else 3
                
                response = f"\nAffordable Stocks within ₹{budget:,.2f}:\n"
                for stock in affordable_stocks[:num_recommendations]:
                    shares = int(budget / stock['current_price'])
                    total_cost = shares * stock['current_price']
                    response += (
                        f"\n{stock['symbol']}:\n"
                        f"Price per share: ₹{stock['current_price']:.2f}\n"
                        f"You can buy: {shares} shares\n"
                        f"Total cost: ₹{total_cost:.2f}\n"
                        f"Expected return: {stock['future_potential']:.2f}%\n"
                    )
                return response
            
        if any(keyword in query.lower() for keyword in ['technical', 'macd', 'rsi', 'analysis']):
            for name, symbol in self.company_map.items():
                if name in query.lower():
                    return self.get_technical_analysis(symbol)

        return self.handle_normal_query(query)

    def find_company_in_query(self, query: str) -> str:
        """Find company name or symbol in query with fuzzy matching"""
        query_lower = query.lower()
        
        # Use fuzzy matching to find the best match
        best_match = process.extractOne(query_lower, self.company_map.keys())
        
        if best_match and best_match[1] > 80:  # Adjust the threshold as needed
            return self.company_map[best_match[0]]
        
        return None

    def handle_normal_query(self, query: str) -> str:
        """Handle normal queries that are not budget-related."""
        query_lower = query.lower()
        symbol = self.find_company_in_query(query_lower)
        
        if not symbol:
            return "I couldn't find a company name in your query. Please mention the company name or symbol you're interested in."
        
        if any(word in query_lower for word in ['price', 'rate', 'cost', 'worth', 'value']):
            analysis = self.analyze_stock(symbol)
            if analysis:
                return f"Current price of {symbol[:-3]} is ₹{analysis['current_price']:.2f}"
                
        elif any(word in query_lower for word in ['rsi', 'technical', 'analysis', 'macd']):
            return self.get_technical_analysis(symbol)
            
        else:
            return self.generate_report(symbol)

    def get_technical_analysis(self, symbol: str) -> str:
        """Get comprehensive technical analysis for a stock"""
        analysis = self.analyze_stock(symbol)
        if not analysis:
            return f"Unable to analyze {symbol} at this time."
        
        return f"""Technical Analysis for {symbol}:
Price Information:
- Current Price: ₹{analysis['current_price']:.2f}
- Price Trend: {analysis['price_trend']}

MACD Analysis:
- MACD Signal: {analysis['macd_signal']:.2f}
- Trend Direction: {'Bullish' if analysis['macd_signal'] > 0 else 'Bearish'}

RSI Analysis:
- RSI Value: {analysis['rsi']:.2f}
- Status: {'Overbought' if analysis['rsi'] > 70 else 'Oversold' if analysis['rsi'] < 30 else 'Neutral'}

Bollinger Bands:
- Upper Band: ₹{analysis['bb_upper']:.2f}
- Lower Band: ₹{analysis['bb_lower']:.2f}
- Volatility: {analysis['volatility']*100:.2f}%

Volume Information:
- Average Volume: {analysis['volume']:,.0f}
"""

    def calculate_risk_level(self, analysis: dict) -> dict:
        """Calculate comprehensive risk assessment"""
        risk_factors = {
            'volatility': {
                'level': 'Low' if analysis['volatility'] < 0.15 else 'High' if analysis['volatility'] > 0.25 else 'Moderate',
                'value': analysis['volatility'] * 100
            },
            'rsi': {
                'level': 'High' if analysis['rsi'] > 70 or analysis['rsi'] < 30 else 'Moderate' if analysis['rsi'] > 60 or analysis['rsi'] < 40 else 'Low',
                'value': analysis['rsi']
            },
            'trend': {
                'level': 'High' if analysis['price_trend'] == 'Downward' else 'Low',
                'direction': analysis['price_trend']
            }
        }
        
        risk_scores = {'Low': 1, 'Moderate': 2, 'High': 3}
        total_score = sum(risk_scores[factor['level']] for factor in risk_factors.values())
        overall_risk = 'Low' if total_score <= 4 else 'High' if total_score >= 7 else 'Moderate'
        
        return {
            'overall': overall_risk,
            'factors': risk_factors
        }

    def get_risk_analysis(self, symbol: str) -> str:
        """Generate comprehensive risk analysis report"""
        analysis = self.analyze_stock(symbol)
        if not analysis:
            return f"Unable to analyze {symbol} at this time."
            
        risk_assessment = self.calculate_risk_level(analysis)
        
        return f"""Risk Analysis for {symbol}:
Overall Risk Level: {risk_assessment['overall']}

Risk Factors:
1. Volatility: {risk_assessment['factors']['volatility']['level']} ({risk_assessment['factors']['volatility']['value']:.2f}%)
2. RSI Status: {risk_assessment['factors']['rsi']['level']} (RSI: {risk_assessment['factors']['rsi']['value']:.2f})
3. Price Trend: {risk_assessment['factors']['trend']['level']} ({risk_assessment['factors']['trend']['direction']})

Additional Metrics:
- Current Price: ₹{analysis['current_price']:.2f}
- Average Volume: {analysis['volume']:,.0f}
- MACD Signal: {analysis['macd_signal']:.2f}
"""

    def get_day_trading_analysis(self, symbol: str) -> dict:
        """Day trading specific analysis"""
        hist = self.get_stock_data(symbol, period='1d', interval='5m')
        if hist.empty:
            return None
            
        analysis = {}
        
        # Calculate day trading indicators
        for name, func in self.day_trading_indicators.items():
            analysis[name] = func(hist).iloc[-1]
            
        # Add support and resistance levels
        highs = hist['High'].nlargest(3)
        lows = hist['Low'].nsmallest(3)
        analysis['resistance_levels'] = highs.tolist()
        analysis['support_levels'] = lows.tolist()
        
        # Add momentum indicators
        analysis['momentum'] = hist['Close'].pct_change().mean() * 100
        analysis['volume_trend'] = (hist['Volume'] > hist['Volume'].mean()).sum() / len(hist)
        
        return analysis

    def process_day_trading_query(self, symbol: str) -> str:
        """Process day trading specific queries"""
        analysis = self.get_day_trading_analysis(symbol)
        if not analysis:
            return "Unable to fetch day trading data"
            
        report = f"""Day Trading Analysis for {symbol}:
Price Action:
- VWAP: ₹{analysis['VWAP']:.2f}
- Price Change: ₹{analysis['Price_Change']:.2f}
- High-Low Range: ₹{analysis['High_Low_Range']:.2f}

Support/Resistance:
- Resistance: ₹{', ₹'.join([f'{x:.2f}' for x in analysis['resistance_levels']])}
- Support: ₹{', ₹'.join([f'{x:.2f}' for x in analysis['support_levels']])}

Momentum:
- Trend: {analysis['momentum']:.2f}%
- Volume Activity: {analysis['volume_trend']*100:.1f}% above average
"""
        return report

    def chat(self):
        """Enhanced chat interface with new command recognition"""
        self.typing_animation("\n💬 Enhanced AI Market Assistant at your service!")
        self.typing_animation("New Features Available:")
        self.typing_animation("- 'Detailed report for [company]'")
        self.typing_animation("- Risk-adjusted recommendations")
        self.typing_animation("- 'Day trading analysis for [company]'")
        
        try:
            while True:
                query = input("\nYou: ")
                
                if query.lower() in ['exit', 'quit', 'bye']:
                    self.typing_animation("\nGoodbye! Happy trading! 👋")
                    break
                    
                response = self.process_query(query)
                if "day trading" in query.lower():
                    symbol = self.find_company_in_query(query)
                    if symbol:
                        response = self.process_day_trading_query(symbol)
                self.typing_animation("\nAI: " + response)

        except KeyboardInterrupt:
            self.typing_animation("\n\nGoodbye! Thanks for using Enhanced AI Market Assistant! 👋")

class BudgetOptimizedMarketAssistant(AIMarketAssistant):
    def __init__(self, csv_path):
        super().__init__(csv_path)
        self.min_investment = 500  # Minimum investment amount in INR
        
    def get_budget_optimized_stocks(self, budget: float, period: str = '3mo') -> tuple:
        """Find the best combination of stocks within the given budget"""
        all_stocks = []
        
        for symbol in self.company_map.values():
            analysis = self.analyze_stock(symbol, period)
            if analysis:
                max_shares = int(budget / analysis['current_price'])
                if max_shares > 0:
                    analysis['possible_shares'] = max_shares
                    analysis['total_cost'] = max_shares * analysis['current_price']
                    analysis['potential_profit'] = (analysis['total_cost'] * 
                                                  (analysis['future_potential'] / 100))
                    all_stocks.append(analysis)
        
        single_stock = sorted(all_stocks, 
                            key=lambda x: x['future_potential'], 
                            reverse=True)
        
        multi_stock_combo = self.optimize_portfolio(all_stocks, budget)
        
        return single_stock, multi_stock_combo
    
    def optimize_portfolio(self, stocks: list, budget: float) -> list:
        """Find the optimal combination of multiple stocks within budget"""
        portfolio = []
        remaining_budget = budget
        
        stocks_by_efficiency = sorted(
            stocks,
            key=lambda x: x['future_potential'] / x['current_price'],
            reverse=True
        )
        
        for stock in stocks_by_efficiency:
            if remaining_budget >= stock['current_price']:
                possible_shares = int(remaining_budget / stock['current_price'])
                
                if possible_shares > 0:
                    stock_allocation = {
                        'symbol': stock['symbol'],
                        'shares': possible_shares,
                        'cost': possible_shares * stock['current_price'],
                        'potential_return': (possible_shares * stock['current_price'] * 
                                          stock['future_potential'] / 100)
                    }
                    portfolio.append(stock_allocation)
                    remaining_budget -= stock_allocation['cost']
        
        return portfolio

    def process_query(self, query: str) -> str:
        """Enhanced query processing with better budget detection"""
        budget_patterns = [
            r'budget\s*(?:of|is|:)?\s*(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:budget|rupees?|rs\.?)',
            r'(?:got|have|with)\s*(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'i\s*(?:got|have)\s*(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        ]
        
        budget = None
        for pattern in budget_patterns:
            budget_match = re.search(pattern, query.lower())
            if budget_match:
                budget = float(budget_match.group(1).replace(',', ''))
                break
        
        if budget:
            understanding = self.understand_query(query)
            single_stocks, multi_stocks = self.get_budget_optimized_stocks(
                budget, 
                understanding['timeframe']
            )
            
            if not single_stocks and not multi_stocks:
                return f"Sorry, no stocks found within your budget of ₹{budget:,.2f}"
            
            response = f"\nBudget-Optimized Recommendations (Budget: ₹{budget:,.2f})\n"
            response += "-" * 50 + "\n"
            
            response += "\nAffordable Single Stock Options:\n"
            affordable_stocks = [
                stock for stock in single_stocks 
                if stock['current_price'] <= budget
            ]
            
            if affordable_stocks:
                for i, stock in enumerate(affordable_stocks[:3], 1):
                    shares = int(budget / stock['current_price'])
                    total_cost = shares * stock['current_price']
                    potential_profit = total_cost * (stock['future_potential'] / 100)
                    
                    response += f"{i}. {stock['symbol']}:\n"
                    response += f"   Shares: {shares} @ ₹{stock['current_price']:.2f}/share\n"
                    response += f"   Total Cost: ₹{total_cost:,.2f}\n"
                    response += f"   Expected Return: {stock['future_potential']:.2f}%\n"
                    response += f"   Potential Profit: ₹{potential_profit:,.2f}\n\n"
            else:
                response += "No single stocks found within your budget.\n"
            
            if multi_stocks:
                response += "\nDiversified Portfolio Option:\n"
                total_investment = 0
                total_potential_return = 0
                
                for stock in multi_stocks:
                    response += f"- {stock['symbol']}: {stock['shares']} shares"
                    response += f" (₹{stock['cost']:,.2f})\n"
                    total_investment += stock['cost']
                    total_potential_return += stock['potential_return']
                
                if total_investment > 0:
                    response += f"\nTotal Investment: ₹{total_investment:,.2f}"
                    response += f"\nPotential Return: ₹{total_potential_return:,.2f}"
                    response += f" ({(total_potential_return/total_investment)*100:.2f}%)"
            
            return response
            
        return super().process_query(query)

    def chat(self):
        """Enhanced chat interface with budget examples"""
        super().typing_animation("\n💬 Budget-Optimized Market Assistant at your service!")
        super().typing_animation("Examples:")
        super().typing_animation("- 'Show me best stocks within budget of ₹10,000'")
        super().typing_animation("- 'What can I buy with ₹5,000 for next 3 months?'")
        super().typing_animation("- 'Recommend stocks within budget ₹20,000 for long term'")
        
        try:
            while True:
                query = input("\nYou: ")
                
                if query.lower() in ['exit', 'quit', 'bye']:
                    super().typing_animation("\nGoodbye! Happy trading! 👋")
                    break
                    
                response = self.process_query(query)
                super().typing_animation("\nAI: " + response)
                
        except KeyboardInterrupt:
            super().typing_animation("\n\nGoodbye! Thanks for using Budget-Optimized Market Assistant! 👋")

class ImprovedMarketAssistant(BudgetOptimizedMarketAssistant):
    def __init__(self, csv_path):
        super().__init__(csv_path)
        # Add common stock symbols mapping
        self.common_symbols = {
            'HDFCBANK': 'HDFCBANK.NS',
            'SBI': 'SBIN.NS',
            'BAJFINANCE': 'BAJFINANCE.NS',
            # Add more common symbols as needed
        }
        
    def find_company_in_query(self, query: str) -> str:
        """Improved company name/symbol detection"""
        query_lower = query.lower()
        
        # First check for common stock symbols
        for symbol, ns_symbol in self.common_symbols.items():
            if symbol.lower() in query_lower:
                return ns_symbol
        
        # Then check company map with fuzzy matching
        best_match = process.extractOne(query_lower, self.company_map.keys())
        if best_match and best_match[1] > 80:
            return self.company_map[best_match[0]]
            
        # Check for partial matches in name variations
        for variation, company in self.name_variations.items():
            if variation in query_lower:
                return self.company_map[company.lower()]
                
        return None

    def process_query(self, query: str) -> str:
        """Enhanced query processing with better intent recognition"""
        # Identify query type
        query_lower = query.lower()
        
        # Intraday trading analysis
        if any(word in query_lower for word in ['intraday', 'today', 'tomorrow']):
            symbol = self.find_company_in_query(query_lower)
            if symbol:
                if 'level' in query_lower or 'support' in query_lower or 'resistance' in query_lower:
                    return self.process_day_trading_query(symbol)
                elif 'momentum' in query_lower or 'movement' in query_lower:
                    analysis = self.get_day_trading_analysis(symbol)
                    if analysis:
                        return f"""Intraday Analysis for {symbol[:-3]}:
Price Momentum: {analysis['momentum']:.2f}%
Volume Trend: {analysis['volume_trend']*100:.1f}% above average
Key Resistance Levels: ₹{', ₹'.join([f'{x:.2f}' for x in analysis['resistance_levels'][:2]])}
Key Support Levels: ₹{', ₹'.join([f'{x:.2f}' for x in analysis['support_levels'][:2]])}"""
        
        # Market overview
        if 'market' in query_lower and 'global' in query_lower:
            return """Note: I can provide real-time analysis for Indian stocks, but for global market impact, please refer to live market data sources. I can analyze specific stocks' technical indicators to help with your trading decisions."""
        
        # Default to parent class processing for other queries
        return super().process_query(query)

    def get_day_trading_analysis(self, symbol: str) -> dict:
        """Enhanced day trading analysis"""
        try:
            hist = self.get_stock_data(symbol, period='1d', interval='5m')
            if hist.empty:
                return None
                
            analysis = {
                'momentum': hist['Close'].pct_change().mean() * 100,
                'volume_trend': (hist['Volume'] > hist['Volume'].mean()).sum() / len(hist),
                'resistance_levels': hist['High'].nlargest(3).tolist(),
                'support_levels': hist['Low'].nsmallest(3).tolist(),
                'price_volatility': hist['Close'].pct_change().std() * 100,
                'current_price': hist['Close'].iloc[-1],
                'vwap': (hist['Close'] * hist['Volume']).sum() / hist['Volume'].sum()
            }
            
            return analysis
        except Exception as e:
            print(f"Error in day trading analysis: {e}")
            return None

if __name__ == "__main__":
    csv_path = r"C:\Users \YourPath\company_data.csv"  # Update with your actual CSV path
    assistant = ImprovedMarketAssistant(csv_path)
    assistant.chat()