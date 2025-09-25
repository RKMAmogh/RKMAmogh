import wikipedia
import re
import time
import textwrap
import sys
import os
from difflib import get_close_matches
from spellchecker import SpellChecker
from fuzzywuzzy import process

class ResearchAI:
    def __init__(self):
        self.spell_checker = SpellChecker()
        self.knowledge_domains = {
            'science': ['physics', 'biology', 'chemistry', 'technology', 'astronomy', 'electrons'],
            'history': ['world history', 'ancient civilizations', 'wars', 'historical figures'],
            'arts': ['literature', 'music', 'painting', 'cinema', 'culture'],
            'technology': ['artificial intelligence', 'computing', 'robotics', 'innovation']
        }

    def extract_keywords(self, query):
        stop_words = set(['what', 'who', 'where', 'when', 'why', 'how', 'tell', 'me', 'about'])
        return [word.lower() for word in query.split() if word.lower() not in stop_words]

    def correct_spelling(self, query):
        science_corrections = {
            'electon': 'electron',
            'electros': 'electrons',
            'elektron': 'electron'
        }
        
        words = query.split()
        corrected_query = []
        for word in words:
            corrected_word = science_corrections.get(word.lower(), word)
            corrected_word = self.spell_checker.correction(word) or word
            corrected_query.append(corrected_word)
        return ' '.join(corrected_query)

    def typing_animation(self, text, delay=0.03, width=80):
        """Simulate typing animation with configurable speed and width."""
        try:
            wrapped_text = textwrap.fill(text, width=width)
            for line in wrapped_text.splitlines():
                for char in line:
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    time.sleep(delay)
                print()
            return True
        except KeyboardInterrupt:
            print("\n\n[Research interrupted by user]")
            return False

    def get_summary(self, query, depth=15):
        try:
            science_queries = {
                'electrons': 'Electron',
                'electron': 'Electron'
            }
            
            precise_query = science_queries.get(query.lower(), query)
            
            try:
                summary = wikipedia.summary(precise_query, sentences=depth)
                return summary
            except wikipedia.DisambiguationError as e:
                scientific_options = [opt for opt in e.options if 'physics' in opt.lower() or 'science' in opt.lower()]
                options = scientific_options or e.options[:3]
                
                for option in options:
                    try:
                        summary = wikipedia.summary(option, sentences=depth)
                        return f"Information about {option}:\n\n{summary}"
                    except:
                        continue
                return "Unable to resolve disambiguation."
            
            except wikipedia.PageError:
                search_results = wikipedia.search(query, results=5)
                if search_results:
                    for result in search_results:
                        match = process.extractOne(query, [result])
                        if match and match[1] > 80:
                            try:
                                summary = wikipedia.summary(match[0], sentences=depth)
                                return f"Research on '{match[0]}':\n\n{summary}"
                            except:
                                continue
                return "No precise information found."
        
        except Exception as e:
            search_results = wikipedia.search(query, results=3)
            if search_results:
                close_matches = get_close_matches(query, search_results, n=3, cutoff=0.6)
                if close_matches:
                    return f"No direct match found. Suggestions: {', '.join(close_matches)}"
            return f"Research encountered an issue: {e}"

    def contextual_research(self, query):
        keywords = self.extract_keywords(query)
        
        for domain, topics in self.knowledge_domains.items():
            if any(keyword in topics for keyword in keywords):
                try:
                    summary = self.get_summary(query)
                    return f"Domain Context: {domain.capitalize()}\n\n{summary}"
                except:
                    break
        
        return self.get_summary(query)

    def advanced_research(self, query):
        corrected_query = self.correct_spelling(query)
        initial_summary = self.contextual_research(corrected_query)
        
        try:
            related_topics = wikipedia.search(corrected_query, results=3)
            related_info = "\n\nRelated Topics:\n" + "\n".join(related_topics)
        except:
            related_info = ""
        
        return initial_summary + related_info

    def handle_user_query(self, user_input):
        if user_input.lower() == 'exit':
            return "Exiting the program. Goodbye!"
        
        try:
            response = self.advanced_research(user_input)
            # Use typing animation for gradual text display
            self.typing_animation(response)
            return response
        except Exception as e:
            error_msg = f"An unexpected error occurred: {e}"
            self.typing_animation(error_msg)
            return error_msg

def main():
    research_ai = ResearchAI()
    print("Research AI Assistant. Type 'exit' to quit.")
    print("This is a research AI not all data shown can be up to date for knowing about your givien topic please be specific.")
    print("Press Ctrl+C to interrupt typing and return to query.")
    
    while True:
        try:
            user_input = input("Enter your research query: ")
            
            # Exit program completely
            if user_input.lower() == 'exit':
                print("Goodbye!")
                break
            
            # If user just presses Enter, continue the loop
            if user_input.strip() == '':
                print("Returning to query input...")
                continue
            
            # Process the research query
            research_ai.handle_user_query(user_input)
        
        except KeyboardInterrupt:
            print("\nReturning to query input...")
            continue
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
    