import json
from reasoners.store_types import Problem

problems = [p for p in Problem.load_all() if p.category == 'cryptarithm_deduce']

print("Prompt for 00c032a8:")
for p in problems:
    if p.id == '00c032a8':
        print(p.prompt)
        
print("Prompt for 012cab1f:")
for p in problems:
    if p.id == '012cab1f':
        print(p.prompt)
