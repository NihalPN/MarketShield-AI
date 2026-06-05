from curl_cffi import requests
from bs4 import BeautifulSoup

test_url = "https://www.wired.com/story/ai-agents-math-doesnt-add-up/"

print("Connecting and downloading full webpage layout...")

try:
    response = requests.get(test_url, impersonate="chrome", timeout=15)
    
    # Pass the 1.34 MB string to the HTML parser
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract the main headline text
    headline_node = soup.find("h1")
    headline = headline_node.get_text(strip=True) if headline_node else "Headline Not Found"
    
    # Locate the article body and extract text paragraphs
    article_body = soup.find("article")
    paragraphs = article_body.find_all("p") if article_body else soup.find_all("p")
    
    print("\n--- HTML Parsing Complete ---")
    print(f"Verified Headline: {headline}")
    print("\n--- Displaying First 3 Article Paragraphs ---")
    
    displayed_count = 0
    for p in paragraphs:
        paragraph_text = p.get_text(strip=True)
        
        # Filter out empty strings or tiny layout artifacts
        if len(paragraph_text) > 40:
            print(f"\n[Paragraph {displayed_count + 1}]: {paragraph_text}")
            displayed_count += 1
            
        if displayed_count >= 3:
            break

except Exception as e:
    print(f"\n[ERROR] Connection or parsing failed: {e}")