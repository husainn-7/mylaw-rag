import json
import sys

name = sys.argv[1]
page = int(sys.argv[2])

pages = json.load(open(f"data/processed/{name}.json", encoding="utf-8"))
print(pages[page - 1]["text"])