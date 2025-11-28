
from bs4 import BeautifulSoup

with open("backend/test/crunchbase/ai-a-2025/div15", "r") as f:
    content = f.read()

soup = BeautifulSoup(content, 'html.parser')
first_row = soup.find('grid-row')

if first_row:
    print("Row found.")
    cells = first_row.find_all('grid-cell')
    for cell in cells:
        col_id = cell.get('data-columnid')
        text = cell.get_text(strip=True)
        print(f"Column ID: {col_id}, Text: {text[:50]}...")
else:
    print("No row found.")

