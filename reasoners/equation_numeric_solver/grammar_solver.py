import re
import pandas as pd
import tqdm
from dataclasses import dataclass
from typing import Callable, Any, Tuple, Optional, List, TypeVar, Generic, Type

# =============================================================================
# TYPES (STATE DEFINITIONS)
# =============================================================================

@dataclass(frozen=True)
class RawOperands:
    """Unparsed string operands extracted directly from the equation."""
    A: str
    B: str

@dataclass(frozen=True)
class ParsedOperands:
    """Operands that have been reordered and parsed into integers for math operations."""
    L: int
    R: int
    d1: int
    d2: int
    d3: int
    d4: int

@dataclass(frozen=True)
class MathResult:
    """The raw integer result of a mathematical operation."""
    value: int

@dataclass(frozen=True)
class FormattedAnswer:
    """The mathematical result formatted as a string (e.g. padded, reversed)."""
    value: str

@dataclass(frozen=True)
class ContextualAnswer:
    """The final answer string with any operator symbols (prefix/suffix) restored."""
    value: str


# =============================================================================
# TYPE-SAFE GRAMMAR RULES
# =============================================================================

I = TypeVar('I')
O = TypeVar('O')
C = TypeVar('C')

class GrammarRule(Generic[I, O]):
    """
    A strongly-typed rule that transitions state from input_type to output_type.
    """
    def __init__(self, name: str, input_type: Type[I], output_type: Type[O], fn: Callable[[I], Optional[O]]):
        self.name = name
        self.input_type = input_type
        self.output_type = output_type
        self.fn = fn

    def __call__(self, inp: I) -> Optional[O]:
        if not isinstance(inp, self.input_type):
            raise TypeError(f"Rule '{self.name}' expected {self.input_type.__name__}, got {type(inp).__name__}")
        try:
            return self.fn(inp)
        except Exception:
            return None

def compose(rule1: GrammarRule[I, O], rule2: GrammarRule[O, C]) -> GrammarRule[I, C]:
    """Composes two rules if their types align: A->B and B->C becomes A->C."""
    if rule1.output_type != rule2.input_type:
        raise TypeError(f"Cannot compose {rule1.output_type.__name__} with {rule2.input_type.__name__}")
    
    def composed_fn(inp: I) -> Optional[C]:
        res1 = rule1(inp)
        if res1 is None: return None
        return rule2(res1)
        
    return GrammarRule(
        name=f"{rule1.name} -> {rule2.name}",
        input_type=rule1.input_type,
        output_type=rule2.output_type,
        fn=composed_fn
    )

def build_pipelines(rules: List[GrammarRule], start_type: Type, end_type: Type) -> List[GrammarRule]:
    """
    Finds all valid paths through the grammar from start_type to end_type 
    by dynamically chaining rules whose input/output types match.
    """
    pipelines = [r for r in rules if r.input_type == start_type]
    completed = []
    
    while pipelines:
        current = pipelines.pop(0)
        if current.output_type == end_type:
            completed.append(current)
            # Assuming acyclic grammar for simplicity
        else:
            # Find what remaining rules can be applied to the current state
            for rule in rules:
                if rule.input_type == current.output_type:
                    pipelines.append(compose(current, rule))
                
    return completed


# =============================================================================
# RULE FACTORIES
# =============================================================================

def make_parser(name: str, fn: Callable[[str, str], Tuple[int, int, int, int, int, int]]) -> GrammarRule[RawOperands, ParsedOperands]:
    return GrammarRule(name, RawOperands, ParsedOperands, lambda raw: ParsedOperands(*fn(raw.A, raw.B)))

def make_math(name: str, fn: Callable[[int, int, int, int, int, int], Optional[int]]) -> GrammarRule[ParsedOperands, MathResult]:
    def wrapper(p: ParsedOperands) -> Optional[MathResult]:
        val = fn(p.L, p.R, p.d1, p.d2, p.d3, p.d4)
        return MathResult(val) if val is not None else None
    return GrammarRule(name, ParsedOperands, MathResult, wrapper)

def make_formatter(name: str, fn: Callable[[int], Optional[str]]) -> GrammarRule[MathResult, FormattedAnswer]:
    def wrapper(m: MathResult) -> Optional[FormattedAnswer]:
        val = fn(m.value)
        return FormattedAnswer(val) if val is not None else None
    return GrammarRule(name, MathResult, FormattedAnswer, wrapper)

def make_contextualizer(name: str, fn: Callable[[str, str], str], tgt_op: str) -> GrammarRule[FormattedAnswer, ContextualAnswer]:
    def wrapper(f: FormattedAnswer) -> Optional[ContextualAnswer]:
        val = fn(f.value, tgt_op)
        return ContextualAnswer(val) if val is not None else None
    return GrammarRule(name, FormattedAnswer, ContextualAnswer, wrapper)


# =============================================================================
# POPULATE GRAMMAR POOL
# =============================================================================

def get_base_rules() -> List[GrammarRule]:
    """Returns the pool of all available, unordered grammar rules (Parsers, Math, Formatters)."""
    rules = []
    
    # 1. Parsers (RawOperands -> ParsedOperands)
    rules.append(make_parser('ABCD', lambda A, B: (int(A), int(B), int(A[0]), int(A[1]), int(B[0]), int(B[1]))))
    rules.append(make_parser('BADC', lambda A, B: (int(A[::-1]), int(B[::-1]), int(A[1]), int(A[0]), int(B[1]), int(B[0]))))
    rules.append(make_parser('CDAB', lambda A, B: (int(B), int(A), int(B[0]), int(B[1]), int(A[0]), int(A[1]))))
    rules.append(make_parser('DCBA', lambda A, B: (int(B[::-1]), int(A[::-1]), int(B[1]), int(B[0]), int(A[1]), int(A[0]))))
    rules.append(make_parser('AB_DC', lambda A, B: (int(A), int(B[::-1]), int(A[0]), int(A[1]), int(B[1]), int(B[0]))))
    rules.append(make_parser('BA_CD', lambda A, B: (int(A[::-1]), int(B), int(A[1]), int(A[0]), int(B[0]), int(B[1]))))
    rules.append(make_parser('AD_BC', lambda A, B: (int(A[0]+B[1]), int(A[1]+B[0]), int(A[0]), int(B[1]), int(A[1]), int(B[0]))))
    rules.append(make_parser('DA_CB', lambda A, B: (int(B[1]+A[0]), int(B[0]+A[1]), int(B[1]), int(A[0]), int(B[0]), int(A[1]))))

    # 2. Math Operations (ParsedOperands -> MathResult)
    rules.append(make_math('add', lambda L, R, d1, d2, d3, d4: L + R))
    rules.append(make_math('sub', lambda L, R, d1, d2, d3, d4: L - R))
    rules.append(make_math('sub_rev', lambda L, R, d1, d2, d3, d4: R - L))
    rules.append(make_math('mul', lambda L, R, d1, d2, d3, d4: L * R))
    rules.append(make_math('cat', lambda L, R, d1, d2, d3, d4: int(str(L) + str(R))))
    rules.append(make_math('div', lambda L, R, d1, d2, d3, d4: L // R if R != 0 else None))
    rules.append(make_math('mod', lambda L, R, d1, d2, d3, d4: L % R if R != 0 else None))
    rules.append(make_math('max_mod_min', lambda L, R, d1, d2, d3, d4: max(L, R) % min(L, R) if min(L, R) != 0 else max(L, R)))
    rules.append(make_math('add1', lambda L, R, d1, d2, d3, d4: L + R + 1))
    rules.append(make_math('addm1', lambda L, R, d1, d2, d3, d4: L + R - 1))
    rules.append(make_math('sub1', lambda L, R, d1, d2, d3, d4: L - R + 1))
    rules.append(make_math('subm1', lambda L, R, d1, d2, d3, d4: L - R - 1))
    rules.append(make_math('mul1', lambda L, R, d1, d2, d3, d4: L * R + 1))
    rules.append(make_math('mulm1', lambda L, R, d1, d2, d3, d4: L * R - 1))
    rules.append(make_math('sub_abs', lambda L, R, d1, d2, d3, d4: abs(L - R)))
    rules.append(make_math('sub_neg_abs', lambda L, R, d1, d2, d3, d4: -abs(L - R)))
    rules.append(make_math('max', lambda L, R, d1, d2, d3, d4: max(L, R)))
    rules.append(make_math('min', lambda L, R, d1, d2, d3, d4: min(L, R)))
    
    # Digit-level math
    rules.append(make_math('digit_absdiff', lambda L, R, d1, d2, d3, d4: int(str(abs(d1 - d3)) + str(abs(d2 - d4)))))
    rules.append(make_math('digit_add_mod10', lambda L, R, d1, d2, d3, d4: int(str((d1 + d3) % 10) + str((d2 + d4) % 10))))
    rules.append(make_math('digit_sub_mod10', lambda L, R, d1, d2, d3, d4: int(str((d1 - d3) % 10) + str((d2 - d4) % 10))))
    rules.append(make_math('cross_mul', lambda L, R, d1, d2, d3, d4: (d1 * d3) + (d2 * d4)))
    rules.append(make_math('cross_mul_rev', lambda L, R, d1, d2, d3, d4: (d1 * d4) + (d2 * d3)))
    rules.append(make_math('digit_mul', lambda L, R, d1, d2, d3, d4: int(str(d1 * d3) + str(d2 * d4))))
    rules.append(make_math('digit_mul_rev', lambda L, R, d1, d2, d3, d4: int(str(d1 * d4) + str(d2 * d3))))
    rules.append(make_math('digit_sum_diff', lambda L, R, d1, d2, d3, d4: (d1 + d2) - (d3 + d4)))
    rules.append(make_math('digit_sum_sum', lambda L, R, d1, d2, d3, d4: (d1 + d2) + (d3 + d4)))
    rules.append(make_math('digit_prod_diff', lambda L, R, d1, d2, d3, d4: (d1 * d2) - (d3 * d4)))
    rules.append(make_math('digit_prod_sum', lambda L, R, d1, d2, d3, d4: (d1 * d2) + (d3 * d4)))
    rules.append(make_math('det', lambda L, R, d1, d2, d3, d4: (d1 * d4) - (d2 * d3)))
    rules.append(make_math('abs_det', lambda L, R, d1, d2, d3, d4: abs((d1 * d4) - (d2 * d3))))

    # 3. Formatters (MathResult -> FormattedAnswer)
    rules.append(make_formatter('raw', lambda val: str(val)))
    rules.append(make_formatter('rev', lambda val: str(val)[::-1]))
    rules.append(make_formatter('swap', lambda val: ('-' + str(val)[1:][::-1] if str(val).startswith('-') else str(val)[::-1])))
    rules.append(make_formatter('abs', lambda val: str(abs(val))))
    rules.append(make_formatter('dsum', lambda val: ("-" if val < 0 else "") + str(sum(int(c) for c in str(val) if c.isdigit()))))
    rules.append(make_formatter('zpad2', lambda val: f"{val:02d}"))
    rules.append(make_formatter('zpad3', lambda val: f"{val:03d}"))
    rules.append(make_formatter('zpad4', lambda val: f"{val:04d}"))

    return rules

def get_contextualizers(tgt_op: str) -> List[GrammarRule[FormattedAnswer, ContextualAnswer]]:
    """Returns contextualizer rules that incorporate the target operator."""
    rules = []
    rules.append(make_contextualizer("identity", lambda s, op: s, tgt_op))
    rules.append(make_contextualizer("replace_minus", lambda s, op: s.replace('-', op), tgt_op))
    rules.append(make_contextualizer("prefix", lambda s, op: op + s, tgt_op))
    rules.append(make_contextualizer("suffix", lambda s, op: s + op, tgt_op))
    return rules

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
        with open('/workspaces/nemotron/reasoners/equation_numeric_grammar/pipeline_frequencies.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

pipeline_freqs = load_frequencies()

def solve_with_type_safe_grammar(prompt: str, target_answer: str = None, mode: str = 'greedy') -> Any:
    tgt_op, op_examples, (tA, tB) = extract_examples(prompt)
    if not tgt_op: return False if mode == 'theoretical' else None
    
    # Initialize the unordered pool of grammar rules
    rule_pool = get_base_rules()
    
    if op_examples:
        possible_answers = set()
        
        # Add dynamic contextualizers for this specific operator
        rule_pool.extend(get_contextualizers(tgt_op))
        
        # DYNAMICALLY BUILD PIPELINES based on types
        # Raw -> Parsed -> Math -> Formatted -> Contextual
        pipelines = build_pipelines(rule_pool, start_type=RawOperands, end_type=ContextualAnswer)
        
        # SORT PIPELINES BY EXACT FREQUENCY
        pipelines.sort(key=lambda p: pipeline_freqs.get(p.name, 0.0), reverse=True)

        # Evaluate the valid pipelines
        for pipeline in pipelines:
            match_all = True
            for exA, exB, ex_res in op_examples:
                res = pipeline(RawOperands(exA, exB))
                if res is None or res.value != ex_res:
                    match_all = False
                    break
                    
            if match_all:
                ans_obj = pipeline(RawOperands(tA, tB))
                if ans_obj is None: continue
                ans = ans_obj.value
                
                if mode == 'greedy': return ans
                possible_answers.add(ans)
                
        if mode == 'theoretical':
            return str(target_answer) in possible_answers

    # Fallback for unseen operators (Guessing)
    if not op_examples:
        possible_answers = set()
        
        rule_pool.extend(get_contextualizers(tgt_op))
        pipelines = build_pipelines(rule_pool, start_type=RawOperands, end_type=ContextualAnswer)
        pipelines.sort(key=lambda p: pipeline_freqs.get(p.name, 0.0), reverse=True)
        
        for pipeline in pipelines:
            ans_obj = pipeline(RawOperands(tA, tB))
            if ans_obj is None: continue
            ans = ans_obj.value
            
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
