import pytest
import pandas as pd
import numpy as np
from transformers import AutoTokenizer
from src.synthetic_cot.donald_solvers import solve_bit_manipulation

MODEL_ID = "hf-internal-testing/tiny-random-LlamaForCausalLM"

@pytest.fixture(scope="module")
def tokenizer():
    return AutoTokenizer.from_pretrained(MODEL_ID)

@pytest.fixture(scope="module")
def bit_manipulation_samples():
    """Load exactly 30 Bit Manipulation samples directly from the train dataset."""
    df = pd.read_csv("data/train.csv")
    bit_df = df[df['prompt'].str.contains('bit manipulation', case=False, na=False)].head(30)
    return bit_df

def test_bit_manipulation_sft_trace_and_accuracy(tokenizer, bit_manipulation_samples):
    """
    Tests that the dynamic backtracking Bit Manipulation solver:
    1) Achieves 100% accuracy on the target answers across the 30 samples.
    2) Successfully generates a CoT trace for SFT.
    3) Computes and prints the tokenizer length statistics for the generated traces.
    """
    assert len(bit_manipulation_samples) == 30, "Failed to load 30 Bit Manipulation samples."
    
    trace_lengths = []
    
    for idx, row in bit_manipulation_samples.iterrows():
        prompt = row['prompt']
        expected_ans = str(row['answer']).strip().zfill(8)
        
        # Run the solver
        predicted_ans, cot_trace = solve_bit_manipulation(prompt)
        
        # 1. Assert Accuracy
        assert predicted_ans == expected_ans, f"Sample ID {row['id']}: Expected {expected_ans}, but predicted {predicted_ans}"
        
        # 2. Assert Trace Generation
        assert cot_trace is not None and len(cot_trace) > 100, f"Sample ID {row['id']}: Failed to generate valid trace."
        
        # 3. Tokenize Trace
        tokens = tokenizer.encode(cot_trace)
        trace_len = len(tokens)
        trace_lengths.append(trace_len)
        print(f"Sample {idx} (ID: {row['id']}): Correct={predicted_ans == expected_ans}, Trace Length={trace_len} tokens")
        
        if idx in [0, 6, 20]:  # Save a small, medium, and large trace
            with open(f"trace_sample_{idx}.txt", "w", encoding="utf-8") as f:
                f.write(cot_trace)
                
    # Calculate Token Statistics
    min_len = np.min(trace_lengths)
    max_len = np.max(trace_lengths)
    avg_len = np.mean(trace_lengths)
    
    print(f"\n--- Bit Manipulation SFT Trace Stats (30 Samples) ---")
    print(f"100% Accuracy Confirmed (30/30 Correct)")
    print(f"Min Trace Tokens: {min_len}")
    print(f"Max Trace Tokens: {max_len}")
    print(f"Avg Trace Tokens: {avg_len:.1f}")