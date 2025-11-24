import logging
import sys
import json
from obp.agents.foundational_gatherer import FoundationalGatherer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def run_tests():
    gatherer = FoundationalGatherer()
    
    test_cases = [
        ("Text Research", "Recent advances in quantum computing 2024", "text"),
        ("Medical Case Reports", "Case reports about type 2 diabetes complications", "text"),
        ("Breaking News", "Latest significant earthquakes worldwide", "news"),
        ("Code Snippets", "Python implementation of Dijkstra algorithm", "code"),
        ("Direct Answer (QnA)", "What is the boiling point of liquid nitrogen?", "qna"),
        ("Numerical Data - Emissions", "Global CO2 emissions by country 2023 table", "numerical"),
        ("Numerical Data - Finance", "Bitcoin price history 2020-2024 csv", "numerical"),
        ("Image Class - People", "high quality portrait photos of people", "image"),
        ("Image Class - Cars", "high quality car photos", "image"),
        ("Image Class - Books", "high quality photos of books on shelves", "image"),
        ("Image Class - Dogs", "high quality dog photos", "image"),
        ("Image Class - Mountains", "high quality mountain landscape photos", "image"),
    ]
    
    results_summary = []

    print(f"\n{'='*60}")
    print(f"🚀 STARTING FOUNDATIONAL AGENT TESTS (10+ CASES)")
    print(f"{'='*60}\n")

    for name, query, modality in test_cases:
        print(f"🔹 Testing: {name} [{modality}]")
        print(f"   Query: {query}")
        
        try:
            result = gatherer.gather(query, modality=modality, limit=3)
            
            # Validate result
            status = "✅ Success"
            details = ""
            
            if modality == "qna":
                if result.get("answer"):
                    details = f"Answer: {result['answer'][:100]}..."
                else:
                    status = "❌ Failed (Empty Answer)"
            else:
                count = result.get("count", 0)
                if count > 0:
                    details = f"Found {count} items"
                    # Print first item title/url
                    first = result['data'][0]
                    title = first.get('title', 'No Title')
                    url = first.get('url', 'No URL')
                    details += f" | Sample: {title[:30]}... ({url})"
                else:
                    status = "⚠️ Warning (0 items)"
            
            print(f"   Status: {status}")
            print(f"   Details: {details}")
            results_summary.append((name, status))
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results_summary.append((name, f"Error: {str(e)}"))
            
        print(f"{'-'*60}")

    print(f"\n{'='*60}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*60}")
    for name, status in results_summary:
        print(f"{name:<20} : {status}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_tests()
