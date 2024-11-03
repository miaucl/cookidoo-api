"""Process the extract for a localization table from the cookidoo web application."""
#!/usr/bin/env python3

# Instructions found here: cookidoo-api/docs/localization.md

import json
import os

from bs4 import BeautifulSoup

script_dir = os.path.dirname(__file__)
input_file_path = os.path.join(script_dir, "../raw/localization-extract.html")
output_file_path = os.path.join(script_dir, "../cookidoo_api/localization.json")

# Load the HTML content
with open(input_file_path, encoding="utf-8") as file:
    html_content = file.read()

# Parse the HTML
soup = BeautifulSoup(html_content, "html.parser")

# Extract the data
localization_data = [
    {
        "country_code": li["data-filter"],
        "language": li["data-lang"],
        "url": li.find("input")["value"],
    }
    for li in soup.find_all("li", {"class": "core-dropdown-list__item"})
    if li.find("input", {"type": "checkbox"})
]
print(f"Successfully extract {len(localization_data)} entries")

# Save the extracted data to JSON
with open(output_file_path, "w", encoding="utf-8") as file:
    json.dump(localization_data, file, ensure_ascii=False, indent=4)
