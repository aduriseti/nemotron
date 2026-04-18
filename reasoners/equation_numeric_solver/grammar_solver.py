import re
import pandas as pd
import tqdm
from dataclasses import dataclass
from typing import Callable, Any, Tuple, Optional, List

# =============================================================================
# TYPES (STATE DEFINITIONS)
# =============================================================================

@dataclass(frozen=True)
class RawOperands:
    """Unparsed string operands extracted directly from the equation."""
    A: str
    B: str

@dataclass(frozen=True)
class FormattedAnswer:
    """The mathematical result formatted as a string."""
    value: str

# =============================================================================
# UNIFIED PIPELINE ARCHITECTURE
# =============================================================================

@dataclass
class MathOp:
    name: str
    fn: Callable[[int, int, int, int, int, int], Optional[int]]
    symbol: str = ""

@dataclass
class Formatter:
    name: str
    preprocess: Callable[[str, str], Tuple[int, int, int, int, int, int]]
    postprocess: Callable[[int], str]

class Pipeline:
    def __init__(self, math_op: MathOp, formatter: Formatter):
        self.name = f"{formatter.name} -> {math_op.name}"
        self.math_op = math_op
        self.formatter = formatter
        self.symbol = math_op.symbol

    def __call__(self, raw: RawOperands) -> Optional[FormattedAnswer]:
        try:
            L, R, d1, d2, d3, d4 = self.formatter.preprocess(raw.A, raw.B)
            val = self.math_op.fn(L, R, d1, d2, d3, d4)
            if val is None: return None
            return FormattedAnswer(self.formatter.postprocess(val))
        except Exception:
            return None

def get_base_math_ops() -> List[MathOp]:
    ops = []
    ops.append(MathOp('add', lambda L, R, d1, d2, d3, d4: L + R, symbol='+'))
    ops.append(MathOp('sub', lambda L, R, d1, d2, d3, d4: L - R, symbol='-'))
    ops.append(MathOp('mul', lambda L, R, d1, d2, d3, d4: L * R, symbol='*'))
    ops.append(MathOp('cat', lambda L, R, d1, d2, d3, d4: int(str(L) + str(R)), symbol='||'))
    ops.append(MathOp('max_mod_min', lambda L, R, d1, d2, d3, d4: max(L, R) % min(L, R) if min(L, R) != 0 else max(L, R)))
    ops.append(MathOp('add1', lambda L, R, d1, d2, d3, d4: L + R + 1))
    ops.append(MathOp('addm1', lambda L, R, d1, d2, d3, d4: L + R - 1, symbol='-'))
    ops.append(MathOp('mul1', lambda L, R, d1, d2, d3, d4: L * R + 1))
    ops.append(MathOp('mulm1', lambda L, R, d1, d2, d3, d4: L * R - 1, symbol='-'))
    ops.append(MathOp('sub_abs', lambda L, R, d1, d2, d3, d4: abs(L - R)))
    ops.append(MathOp('sub_neg_abs', lambda L, R, d1, d2, d3, d4: -abs(L - R), symbol='-'))
    return ops

def get_base_formatters() -> List[Formatter]:
    formatters = []
    formatters.append(Formatter(
        'raw', 
        preprocess=lambda A, B: (int(A), int(B), int(A[0]), int(A[1]), int(B[0]), int(B[1])),
        postprocess=lambda val: str(val)
    ))
    formatters.append(Formatter(
        'swap', 
        preprocess=lambda A, B: (int(A[::-1]), int(B[::-1]), int(A[1]), int(A[0]), int(B[1]), int(B[0])),
        postprocess=lambda val: ('-' + str(val)[1:][::-1] if str(val).startswith('-') else str(val)[::-1])
    ))
    formatters.append(Formatter(
        'rev', 
        preprocess=lambda A, B: (int(B[::-1]), int(A[::-1]), int(B[1]), int(B[0]), int(A[1]), int(A[0])),
        postprocess=lambda val: str(val)[::-1]
    ))
    return formatters

def build_pipelines(math_ops: List[MathOp], formatters: List[Formatter]) -> List[Pipeline]:
    pipelines = []
    for math_op in math_ops:
        for fmt in formatters:
            pipelines.append(Pipeline(math_op, fmt))
    return pipelines

# =============================================================================
# SOLVER IMPLEMENTATION
# =============================================================================

def extract_examples(prompt: str) -> Tuple[Optional[str], List[Tuple[str, str, str]], Tuple[str, str]]:
    """Extracts the target operator, examples for that operator, and the target question."""
    lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
    all_examples = []
    for line in lines:
        m = re.search(r'(\d{2})([^\d\s])(\d{2})\s*=\s*(-?\d+[^\d\s]*|[^\d\s]*-?\d+)', line)
        if m: all_examples.append(m.groups())
            
    target_m = re.search(r'result for:\s*(\d{2})([^\d\s])(\d{2})', prompt)
    if not target_m: return None, [], ("", "")
    
    tA, tgt_op, tB = target_m.groups()
    op_examples = [(ex[0], ex[2], ex[3]) for ex in all_examples if ex[1] == tgt_op]
    
    return tgt_op, op_examples, (tA, tB)

import json

def load_frequencies():
    try:
        with open('/workspaces/nemotron/reasoners/equation_numeric_solver/pipeline_frequencies.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

pipeline_freqs = load_frequencies()

def solve_with_type_safe_grammar(prompt: str, target_answer: str = None, mode: str = 'greedy') -> Any:
    tgt_op, op_examples, (tA, tB) = extract_examples(prompt)
    if not tgt_op: return False if mode == 'theoretical' else None
    
    pipelines = build_pipelines(get_base_math_ops(), get_base_formatters())
    
    if op_examples:
        possible_answers = set()
        
        # SORT PIPELINES BY EXACT FREQUENCY
        pipelines.sort(key=lambda p: pipeline_freqs.get(p.name, 0.0), reverse=True)

        # Evaluate the valid pipelines
        for pipeline in pipelines:
            math_symbol = pipeline.symbol
            
            def encrypt(formatted_val_str, t_op, m_sym):
                if m_sym and m_sym != "":
                    if m_sym == '-':
                        return formatted_val_str.replace('-', t_op)
                    else:
                        return formatted_val_str.replace(m_sym, t_op)
                return formatted_val_str
            
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
                    
            if match_all:
                ans_obj = pipeline(RawOperands(tA, tB))
                if ans_obj is None: continue
                ans = encrypt(str(ans_obj.value), tgt_op, math_symbol)
                
                if mode == 'greedy': return ans
                possible_answers.add(ans)
                
        if mode == 'theoretical':
            return str(target_answer) in possible_answers

    # Fallback for unseen operators (Guessing)
    if not op_examples:
        possible_answers = set()
        
        pipelines.sort(key=lambda p: pipeline_freqs.get(p.name, 0.0), reverse=True)
        
        for pipeline in pipelines:
            math_symbol = pipeline.symbol
            def encrypt(formatted_val_str, t_op, m_sym):
                if m_sym and m_sym != "":
                    if m_sym == '-':
                        return formatted_val_str.replace('-', t_op)
                    else:
                        return formatted_val_str.replace(m_sym, t_op)
                return formatted_val_str
                    
            ans_obj = pipeline(RawOperands(tA, tB))
            if ans_obj is None: continue
            
            ans = encrypt(str(ans_obj.value), tgt_op, math_symbol)
            
            if mode == 'greedy': return ans
            possible_answers.add(ans)
            
        if mode == 'theoretical':
            return str(target_answer) in possible_answers
                
    return None if mode == 'greedy' else False

if __name__ == "__main__":
    import sys
    import os
    
    WORKSPACE_DIR = '/workspaces/nemotron'
    if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)
    
    from reasoners.store_types import Problem
    
    print("Loading equation problems...")
    problems = [p for p in Problem.load_all() if p.category.startswith('equation_numeric')]
    df = pd.read_csv('/workspaces/nemotron/train.csv')
    
    results = []
    # Test on a small subset to verify the type-safe grammar execution
    for p_obj in tqdm.tqdm(problems[:100]):
        row = df[df['id'] == p_obj.id].iloc[0]
        p_text, a = row['prompt'], str(row['answer'])
        
        greedy_ans = solve_with_type_safe_grammar(p_text, mode='greedy')
        greedy_ok = (str(greedy_ans) == a)
        
        theo_ok = solve_with_type_safe_grammar(p_text, target_answer=a, mode='theoretical')
        
        results.append({
            'id': p_obj.id,
            'category': p_obj.category,
            'typesafe_greedy': greedy_ok,
            'typesafe_theoretical': theo_ok
        })

    res_df = pd.DataFrame(results)
    print("\nAccuracy Breakdown (Type-Safe Builder):")
    print(res_df[['typesafe_greedy', 'typesafe_theoretical']].mean() * 100)
    
    print("\nCategory Breakdown (Type-Safe Builder):")
    print(res_df.groupby('category')[['typesafe_greedy', 'typesafe_theoretical']].mean() * 100)
