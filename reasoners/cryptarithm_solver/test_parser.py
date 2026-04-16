import sys
import os
import pytest
import re
import json

WORKSPACE_DIR = '/workspaces/nemotron'
if WORKSPACE_DIR not in sys.path: sys.path.append(WORKSPACE_DIR)

from reasoners.store_types import Problem

def extract_examples(prompt: str):
    """Extracts the target operator, examples for that operator, and the target question."""
    lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
    all_examples = []
    
    for line in lines:
        m = re.search(r'^(\S{2})(\S)(\S{2})\s*=\s*(\S+)$', line)
        if m: all_examples.append(m.groups())
            
    target_m = re.search(r'result for:\s*(\S{2})(\S)(\S{2})', prompt)
    if not target_m: return None, [], ("", "")
    
    tA_str, tgt_op, tB_str = target_m.groups()
    
    return tgt_op, all_examples, (tA_str, tB_str)

def test_extract_examples_basic():
    prompt = r"""In Alice's Wonderland, a secret set of transformation rules is applied to equations. Below are a few examples:
`!*[{ = '"[`
\'*'> = ![@
\'-!` = \\
`!*\& = '@'{
Now, determine the result for: [[-!'"""
    
    tgt_op, op_examples, (tA, tB) = extract_examples(prompt)
    
    assert tgt_op == "-"
    assert tA == "[["
    assert tB == "!'"
    
    assert len(op_examples) == 4
    assert op_examples[0] == ("`!", "*", "[{", "'\"[`")
    assert op_examples[1] == ("\\'", "*", "'>", "![@")
    assert op_examples[2] == ("\\'", "-", "!`", "\\\\")
    assert op_examples[3] == ("`!", "*", "\\&", "'@'{")

def test_extract_examples_all_operators():
    prompt = r"""In Alice's Wonderland, a secret set of transformation rules is applied to equations. Below are a few examples:
}`]?( = ())
}#<)\ = #?
?(!&& = #@@#
(?!@` = )#))
Now, determine the result for: ))!\)"""
    
    tgt_op, op_examples, (tA, tB) = extract_examples(prompt)
    
    assert tgt_op == "!"
    assert tA == "))"
    assert tB == "\\)"
    
    assert len(op_examples) == 4
    assert op_examples[0] == ("}`", "]", "?(", "())")
    assert op_examples[1] == ("}#", "<", ")\\", "#?")
    assert op_examples[2] == ("?(", "!", "&&", "#@@#")
    assert op_examples[3] == ("(?", "!", "@`", ")#))")

def test_extract_examples_no_examples():
    prompt = r"""In Alice's Wonderland, a secret set of transformation rules is applied to equations. Below are a few examples:
Now, determine the result for: 12+34"""
    
    tgt_op, op_examples, (tA, tB) = extract_examples(prompt)
    
    assert tgt_op == "+"
    assert tA == "12"
    assert tB == "34"
    assert len(op_examples) == 0

def test_all_cryptarithm_prompts():
    problems = [p for p in Problem.load_all() if p.category == 'cryptarithm_deduce']
    
    for p in problems:
        prompt = p.prompt
        tgt_op, op_examples, (tA, tB) = extract_examples(prompt)
        
        # Determine how many equation lines exist in the prompt
        lines = [l.strip() for l in prompt.split('\n') if '=' in l and 'determine' not in l.lower()]
        
        # Assert that our regex successfully extracted every single equation line
        assert len(op_examples) == len(lines), f"Failed to extract all examples for problem {p.id}. Extracted {len(op_examples)} out of {len(lines)}. Prompt:\n{prompt}"
        
        # Assert target was extracted
        assert tgt_op is not None, f"Failed to extract target operator for problem {p.id}"
        assert len(tA) == 2, f"Target operand A is not length 2 for problem {p.id}"
        assert len(tB) == 2, f"Target operand B is not length 2 for problem {p.id}"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
