import sys
import pandas as pd
import json
import re

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)
from reasoners.store_types import Problem

df = pd.read_csv('/workspaces/nemotron/train.csv')
problems = [p for p in Problem.load_all() if p.category == 'cryptarithm_deduce']

all_symbols = set()

for p in problems:
    row = df[df['id'] == p.id]
    if row.empty: continue
    
    prompt = str(row.iloc[0]['prompt'])
    answer = str(row.iloc[0]['answer'])
    
    # Combine prompt and answer
    full_text = prompt + answer
    
    # Extract unique symbols (non-alphanumeric, non-whitespace, non-formatting)
    for char in full_text:
        if not char.isspace() and not char.isalnum() and char not in ['=', ',', '.', ':', ';']:
            all_symbols.add(char)

# Sort by ASCII for consistency
sorted_symbols = sorted(list(all_symbols))
print(f'Total Unique Symbols Found: {len(sorted_symbols)}')
print(f'Symbol Universe: {json.dumps(sorted_symbols)}')
