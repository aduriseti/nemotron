import json
import re
import pandas as pd

def write_cryptarithm_examples(output_file: str, num_examples: int = 30):
    df = pd.read_csv('/workspaces/nemotron/train.csv')
    df['id'] = df['id'].astype(str)
    
    with open('/workspaces/nemotron/problems.jsonl', 'r') as f:
        lines = f.readlines()
        
    crypt_problems = []
    for line in lines:
        p = json.loads(line)
        if p['category'] == 'cryptarithm_deduce':
            ans_row = df[df['id'] == p['id']]
            if not ans_row.empty:
                p['answer'] = str(ans_row.iloc[0]['answer'])
                p['prompt'] = str(ans_row.iloc[0]['prompt'])
            else:
                continue
                
            crypt_problems.append(p)
            if len(crypt_problems) >= num_examples:
                break
                
    with open(output_file, 'w') as out:
        for i, p in enumerate(crypt_problems):
            out.write(f"=== Problem {i+1} | ID: {p['id']} ===\n")
            out.write(f"Target Answer: {p['answer']}\n")
            out.write("-" * 40 + "\n")
            out.write(f"{p['prompt']}\n")
            out.write("-" * 40 + "\n")
            
            # Show the raw examples extracted
            prompt_lines = [l.strip() for l in p['prompt'].split('\n') if '=' in l and 'determine' not in l.lower()]
            out.write("Parsed Equations:\n")
            for l in prompt_lines:
                m = re.search(r'(\S+)\s*=\s*(\S+)', l)
                if m:
                    left, right = m.groups()
                    # Try to see if there's a middle character that acts as an operator
                    if len(left) == 5:
                        op = left[2]
                        op1 = left[:2]
                        op2 = left[3:]
                        out.write(f"  [Len 5] {op1} {op} {op2} = {right}\n")
                    else:
                        out.write(f"  [Len {len(left)}] {left} = {right}\n")
                else:
                    out.write(f"  [Regex Failed] {l}\n")
                    
            # Parse the target question
            q_match = re.search(r'result for:\s*(\S+)', p['prompt'])
            if q_match:
                q_str = q_match.group(1)
                if len(q_str) == 5:
                    out.write(f"Target Question: {q_str[:2]} {q_str[2]} {q_str[3:]}\n")
                else:
                    out.write(f"Target Question (Len {len(q_str)}): {q_str}\n")
            out.write("\n\n")

if __name__ == "__main__":
    write_cryptarithm_examples('/workspaces/nemotron/reasoners/cryptarithm_solver/cryptarithm_samples.txt', 30)
