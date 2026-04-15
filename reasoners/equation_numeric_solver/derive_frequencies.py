import sys
import os
import pandas as pd
import tqdm
from collections import Counter
import json

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem
from grammar_solver import extract_examples, get_base_rules, get_contextualizers, build_pipelines, RawOperands, ContextualAnswer

def get_successful_pipelines(prompt, target_answer):
    tgt_op, op_examples, (tA, tB) = extract_examples(prompt)
    if not tgt_op: return []
    
    rule_pool = get_base_rules()
    
    if op_examples:
        ex_res_0 = op_examples[0][2]
        prefix = tgt_op if ex_res_0.startswith(tgt_op) else ""
        suffix = tgt_op if ex_res_0.endswith(tgt_op) else ""
        rule_pool.extend(get_contextualizers(tgt_op))
        
        cleaned_examples = [(exA, exB, ex_res.replace(tgt_op, '')) for exA, exB, ex_res in op_examples]
        pipelines = build_pipelines(rule_pool, start_type=RawOperands, end_type=ContextualAnswer)
        
        successful = []
        for pipeline in pipelines:
            match_all = True
            for exA, exB, _ in cleaned_examples:
                expected_out = prefix + cleaned_examples[cleaned_examples.index((exA, exB, _))][2] + suffix
                res = pipeline(RawOperands(exA, exB))
                if res is None or res.value != expected_out:
                    match_all = False
                    break
                    
            if match_all:
                ans_obj = pipeline(RawOperands(tA, tB))
                if ans_obj is not None and ans_obj.value == target_answer:
                    successful.append(pipeline.name)
        return successful
    else:
        # Guess category (no examples)
        rule_pool.extend(get_contextualizers(tgt_op))
        pipelines = build_pipelines(rule_pool, start_type=RawOperands, end_type=ContextualAnswer)
        
        successful = []
        for pipeline in pipelines:
            ans_obj = pipeline(RawOperands(tA, tB))
            if ans_obj is not None and ans_obj.value == target_answer:
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
        
        # If multiple pipelines perfectly match the examples AND the golden answer, 
        # we add a fractional count to avoid over-weighting highly degenerate/ambiguous puzzles
        weight = 1.0 / len(succ) if succ else 0
        for s in succ:
            pipeline_counts[s] += weight
            
    # Save the frequencies
    freq_dict = {k: float(v) for k, v in pipeline_counts.most_common()}
    with open('/workspaces/nemotron/reasoners/equation_numeric_grammar/pipeline_frequencies.json', 'w') as f:
        json.dump(freq_dict, f, indent=2)
        
    print("\nTop 20 most frequent pipelines:")
    for p, c in pipeline_counts.most_common(20):
        print(f"{c:6.2f} : {p}")
