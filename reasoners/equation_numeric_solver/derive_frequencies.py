import sys
import os
import pandas as pd
import tqdm
from collections import Counter
import json

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem
from reasoners.equation_numeric_solver.grammar_solver import extract_examples, get_base_math_ops, get_base_formatters, build_pipelines, RawOperands, FormattedAnswer

def get_successful_pipelines(prompt, target_answer):
    tgt_op, op_examples, (tA, tB) = extract_examples(prompt)
    if not tgt_op: return []
    
    pipelines = build_pipelines(get_base_math_ops(), get_base_formatters())
    
    successful = []
    
    for pipeline in pipelines:
        math_symbol = pipeline.symbol
        
        def encrypt(formatted_val_str, t_op, m_sym):
            if m_sym and m_sym != "":
                if m_sym == '-':
                    return formatted_val_str.replace('-', t_op)
                else:
                    return formatted_val_str.replace(m_sym, t_op)
            return formatted_val_str

        if op_examples:
            match_all = True
            for exA, exB, ex_res in op_examples:
                res = pipeline(RawOperands(exA, exB))
                if res is None:
                    match_all = False
                    break
                encrypted_output = encrypt(str(res.value), tgt_op, math_symbol)
                if encrypted_output != ex_res:
                    match_all = False
                    break
            if not match_all: continue
                
        ans_obj = pipeline(RawOperands(tA, tB))
        if ans_obj is not None:
            encrypted_ans = encrypt(str(ans_obj.value), tgt_op, math_symbol)
            if encrypted_ans == target_answer:
                successful.append(pipeline.name)
            
    return successful

if __name__ == "__main__":
    print("Loading problems...")
    problems = [p for p in Problem.load_all() if p.category.startswith('equation_numeric')]
    df = pd.read_csv('/workspaces/nemotron/train.csv')
    
    pipeline_counts = Counter()
    
    print("Deriving rule frequencies...")
    for p_obj in tqdm.tqdm(problems):
        row = df[df['id'] == p_obj.id].iloc[0]
        p_text, a = row['prompt'], str(row['answer'])
        succ = get_successful_pipelines(p_text, a)
        
        weight = 1.0 / len(succ) if succ else 0
        for s in succ:
            pipeline_counts[s] += weight
            
    # Save the frequencies as proportions/ratios
    total_weight = sum(pipeline_counts.values())
    freq_dict = {k: float(v) / total_weight for k, v in pipeline_counts.most_common()} if total_weight > 0 else {}
    with open('/workspaces/nemotron/reasoners/equation_numeric_solver/pipeline_frequencies.json', 'w') as f:
        json.dump(freq_dict, f, indent=2)
        
    print("\nTop 20 most frequent pipelines:")
    for p, c in pipeline_counts.most_common(20):
        print(f"{c:6.2f} : {p}")
