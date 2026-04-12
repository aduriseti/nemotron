# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% _uuid="8f2839f25d086af736a60e9eeb907d3b93b6e0e5" _cell_guid="b1076dfc-b9ad-4769-8c92-a6c4dae69d19"
"""
Synthetic Dataset Generator for NVIDIA Nemotron Reasoning Competition
=====================================================================
Kaggle Notebook version — edit the CONFIG cell below and Run All.

Generates puzzles matching all 6 types found in train.csv:

  1. Bit Manipulation      – 8-bit binary transformation via secret bitwise ops
  2. Text Encryption       – per-puzzle substitution cipher on a fixed vocabulary
  3. Numeral Conversion    – decimal to Roman numerals (1–100)
  4. Unit Conversion       – linear scaling with a hidden multiplier
  5. Gravity               – infer modified g from d=0.5*g*t² examples
  6. Symbol Transformation – character-level positional/substitution rules on symbols

Each row: id, prompt, answer, cot  (same schema as train.csv / test.csv).
The `cot` column holds chain-of-thought traces for SFT training.
"""

# ╔══════════════════════════════════════════════════════════╗
# ║                      CONFIG                              ║
# ║  Edit these values, then Kernel → Restart & Run All     ║
# ╚══════════════════════════════════════════════════════════╝

# Asymmetric counts based on combinatorial breadth of each puzzle type.
# High-variance types (huge rule space) get more rows;
# low-variance types (small answer space, model converges fast) get fewer.
N_PER_TYPE = {
    "bit":     9000,   # largest space: 2-4 ops from pool of 10, each parameterised
    "symbol":  7000,   # large char-map space, only 3-5 examples given per puzzle
    "encrypt": 5000,   # 26! substitution space, partial map revealed in examples
    "gravity": 2500,   # low variance: model just needs to learn g = 2d/t^2
    "unit":    2500,   # low variance: linear fit from examples
    "numeral": 1500,   # only 100 possible answers; model likely pre-knows Roman numerals
}
# Total: 27,500 synthetic rows.
# Combine with real train.csv (9,500 rows) -> ~37,000 training examples total.

OUTPUT_PATH = "synthetic_train.csv"   # saved to Kaggle working dir /kaggle/working/
SEED        = 42            # random seed for full reproducibility
INCLUDE_COT = True          # True -> add chain-of-thought column; False -> omit it

# ────────────────────────────────────────────────────────────

import csv
import random
import string
import math
import itertools
from typing import Optional

# ── shared constants ──────────────────────────────────────────────────────────

ALICE_HEADER = "In Alice's Wonderland, "

# Vocabulary observed in the real encryption puzzles (77 words)
NOUNS = [
    "alice", "hatter", "knight", "rabbit", "mouse", "turtle",
    "bird", "cat", "princess", "queen", "king", "wizard",
    "dragon", "student", "teacher",
]
VERBS = [
    "creates", "dreams", "found", "studies", "draws", "writes",
    "follows", "sees", "reads", "chases", "imagines", "discovers",
    "watches", "explores",
]
ADJECTIVES = [
    "colorful", "hidden", "silver", "dark", "bright", "wise",
    "strange", "curious", "clever", "golden", "magical", "mysterious",
    "ancient",
]
LOCATIONS = [
    "garden", "castle", "forest", "key", "puzzle", "book", "treasure",
    "mirror", "crystal", "door", "potion", "map", "story", "message",
    "cave", "island", "ocean", "palace", "valley", "village",
    "mountain", "library", "school", "tower",
]
PREPOSITIONS = ["in", "near", "inside", "through", "under", "above",
                "around", "beyond"]

# Symbol charset from real puzzles
SYMBOL_CHARS = list("!\"#$%&'()*+-/:;<>?@[\\]^`{|}")
# Digit chars for the arithmetic-style symbol puzzles
DIGIT_CHARS = list("0123456789")

# ── helpers ───────────────────────────────────────────────────────────────────

def rand_bit8(rng: random.Random) -> str:
    return format(rng.randint(0, 255), "08b")


def int_to_roman(n: int) -> str:
    """Convert integer 1-100 to Roman numeral string."""
    vals = [
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"),  (9, "IX"),  (5, "V"),  (4, "IV"), (1, "I"),
    ]
    result = ""
    for v, sym in vals:
        while n >= v:
            result += sym
            n -= v
    return result


def rotate_left(x: int, n: int, bits: int = 8) -> int:
    n %= bits
    return ((x << n) | (x >> (bits - n))) & 0xFF


def rotate_right(x: int, n: int, bits: int = 8) -> int:
    n %= bits
    return ((x >> n) | (x << (bits - n))) & 0xFF


# ── Type 1: Bit Manipulation ──────────────────────────────────────────────────

class BitManipOp:
    """A single atomic bitwise operation that can be applied to an 8-bit int."""

    def __init__(self, name: str, fn):
        self.name = name
        self.fn   = fn

    def apply(self, x: int) -> int:
        return self.fn(x) & 0xFF


def _make_bit_ops(rng: random.Random) -> list:
    """Pool of all parameterised bit ops."""
    xor_mask  = rng.randint(1, 255)
    and_mask  = rng.randint(1, 254)
    or_mask   = rng.randint(1, 255)
    rot_l_n   = rng.randint(1, 7)
    rot_r_n   = rng.randint(1, 7)
    shift_l_n = rng.randint(1, 4)
    shift_r_n = rng.randint(1, 4)

    ops = [
        BitManipOp(f"XOR 0x{xor_mask:02X}",        lambda x, m=xor_mask:  x ^ m),
        BitManipOp(f"AND 0x{and_mask:02X}",         lambda x, m=and_mask:  x & m),
        BitManipOp(f"OR  0x{or_mask:02X}",          lambda x, m=or_mask:   x | m),
        BitManipOp("NOT",                            lambda x:              (~x) & 0xFF),
        BitManipOp(f"ROTATE LEFT  {rot_l_n}",       lambda x, n=rot_l_n:  rotate_left(x,  n)),
        BitManipOp(f"ROTATE RIGHT {rot_r_n}",       lambda x, n=rot_r_n:  rotate_right(x, n)),
        BitManipOp(f"SHIFT LEFT  {shift_l_n}",      lambda x, n=shift_l_n: (x << n) & 0xFF),
        BitManipOp(f"SHIFT RIGHT {shift_r_n}",      lambda x, n=shift_r_n:  x >> n),
        # SHA-like: majority & choice (need 3 words – use x with itself rotated)
        BitManipOp("MAJORITY(x, ROTL1, ROTR1)",
                   lambda x: (x & rotate_left(x,1)) | (x & rotate_right(x,1))
                           | (rotate_left(x,1) & rotate_right(x,1))),
        BitManipOp("CHOICE(x, ROTL2, NOT)",
                   lambda x: (x & rotate_left(x,2)) | ((~x & 0xFF) & rotate_right(x,2))),
    ]
    return ops


def make_bit_puzzle(rng: random.Random) -> tuple:
    """
    Returns (prompt, answer, cot).
    The 'secret rule' is a composition of 2-4 randomly chosen ops.
    """
    ops    = _make_bit_ops(rng)
    n_ops  = rng.randint(2, 4)
    chosen = rng.sample(ops, n_ops)

    def transform(x: int) -> int:
        for op in chosen:
            x = op.apply(x)
        return x

    # Number of examples: 8-11 (matching training distribution)
    n_examples = rng.randint(8, 11)
    seen_inputs: set = set()
    examples   : list = []
    while len(examples) < n_examples:
        inp = rng.randint(0, 255)
        if inp in seen_inputs:
            continue
        seen_inputs.add(inp)
        examples.append((inp, transform(inp)))

    query_val = rng.randint(0, 255)
    while query_val in seen_inputs:
        query_val = rng.randint(0, 255)
    answer_val = transform(query_val)

    ex_lines = "\n".join(
        f"{format(i,'08b')} -> {format(o,'08b')}" for i, o in examples
    )
    prompt = (
        f"{ALICE_HEADER}a secret bit manipulation rule transforms 8-bit binary numbers. "
        "The transformation involves operations like bit shifts, rotations, XOR, AND, OR, "
        "NOT, and possibly majority or choice functions.\n\n"
        f"Here are some examples of input -> output:\n{ex_lines}\n\n"
        f"Now, determine the output for: {format(query_val,'08b')}"
    )
    answer = format(answer_val, "08b")

    ops_str = " -> ".join(op.name for op in chosen)
    cot = (
        f"The hidden rule applies these operations in sequence: {ops_str}.\n"
        f"Input {format(query_val,'08b')} ({query_val}):\n"
    )
    x = query_val
    for op in chosen:
        prev = x
        x = op.apply(x)
        cot += f"  After {op.name}: {format(x,'08b')} ({x})\n"
    cot += f"Final answer: {format(x,'08b')}"

    return prompt, answer, cot


# ── Type 2: Text Encryption (substitution cipher) ─────────────────────────────

def _random_substitution(rng: random.Random) -> dict:
    """Return a random bijective char->char map for a-z."""
    alphabet = list(string.ascii_lowercase)
    shuffled = alphabet[:]
    rng.shuffle(shuffled)
    return dict(zip(alphabet, shuffled))


def _encrypt_word(word: str, sub: dict) -> str:
    return "".join(sub.get(c, c) for c in word)


def _make_sentence(rng: random.Random, n_words: int) -> list:
    """
    Build an n_words sentence from the fixed Wonderland vocabulary.
    Structures mirror those seen in train.csv:
      3 words: [noun] [verb] [noun/location]
      4 words: [noun/the] [adj?] [verb] [noun] or [noun] [verb] [prep] [location]
      5 words: [noun] [verb] [adj] [noun] or [noun] [verb] [the] [adj] [noun]
    """
    if n_words == 3:
        subj = rng.choice(NOUNS)
        verb = rng.choice(VERBS)
        obj  = rng.choice(LOCATIONS + NOUNS)
        return [subj, verb, obj]
    elif n_words == 4:
        template = rng.choice(["the", "subj_verb_adj_obj", "subj_verb_prep_loc"])
        if template == "the":
            subj = rng.choice(NOUNS)
            verb = rng.choice(VERBS)
            obj  = rng.choice(LOCATIONS)
            return [subj, verb, "the", obj]
        elif template == "subj_verb_adj_obj":
            subj = rng.choice(NOUNS)
            verb = rng.choice(VERBS)
            adj  = rng.choice(ADJECTIVES)
            obj  = rng.choice(LOCATIONS)
            return [subj, verb, adj, obj]
        else:
            subj = rng.choice(NOUNS)
            verb = rng.choice(VERBS)
            prep = rng.choice(PREPOSITIONS)
            loc  = rng.choice(LOCATIONS)
            return [subj, verb, prep, loc]
    else:  # 5 words
        template = rng.choice(["subj_verb_the_adj_obj", "subj_verb_adj_noun_noun"])
        if template == "subj_verb_the_adj_obj":
            subj = rng.choice(NOUNS)
            verb = rng.choice(VERBS)
            adj  = rng.choice(ADJECTIVES)
            obj  = rng.choice(LOCATIONS)
            return [subj, verb, "the", adj, obj]
        else:
            subj = rng.choice(NOUNS)
            verb = rng.choice(VERBS)
            adj  = rng.choice(ADJECTIVES)
            n1   = rng.choice(NOUNS)
            loc  = rng.choice(LOCATIONS)
            return [subj, verb, adj, n1, loc]


def make_encryption_puzzle(rng: random.Random) -> tuple:
    sub = _random_substitution(rng)
    # Inverse: cipher -> plain
    inv = {v: k for k, v in sub.items()}

    n_examples = rng.randint(3, 5)
    n_words_list = [rng.choice([3, 4, 5]) for _ in range(n_examples)]
    examples = []
    for nw in n_words_list:
        plain_words  = _make_sentence(rng, nw)
        cipher_words = [_encrypt_word(w, sub) for w in plain_words]
        examples.append((cipher_words, plain_words))

    # Query
    q_nw         = rng.choice([3, 4, 5])
    q_plain      = _make_sentence(rng, q_nw)
    q_cipher     = [_encrypt_word(w, sub) for w in q_plain]

    ex_lines = "\n".join(
        f"{' '.join(c)} -> {' '.join(p)}" for c, p in examples
    )
    query_str = " ".join(q_cipher)
    prompt = (
        f"{ALICE_HEADER}secret encryption rules are used on text. "
        f"Here are some examples:\n{ex_lines}\n"
        f"Now, decrypt the following text: {query_str}"
    )
    answer = " ".join(q_plain)

    cot = (
        "Each letter is substituted by a fixed letter. "
        "Recovering the mapping from examples:\n"
    )
    for c, p in examples[:2]:
        for cw, pw in zip(c, p):
            for cc, pc in zip(cw, pw):
                cot += f"  '{cc}' -> '{pc}'\n"
    cot += f"Applying map to query '{query_str}': {answer}"

    return prompt, answer, cot


# ── Type 3: Numeral System (Roman Numerals) ───────────────────────────────────

def make_numeral_puzzle(rng: random.Random) -> tuple:
    n_examples = rng.randint(3, 5)
    pool = list(range(1, 101))
    rng.shuffle(pool)
    example_nums = pool[:n_examples]
    query_num    = pool[n_examples]

    ex_lines = "\n".join(
        f"{n} -> {int_to_roman(n)}" for n in example_nums
    )
    prompt = (
        f"{ALICE_HEADER}numbers are secretly converted into a different numeral system. "
        f"Some examples are given below:\n{ex_lines}\n"
        f"Now, write the number {query_num} in the Wonderland numeral system."
    )
    answer = int_to_roman(query_num)

    cot = (
        f"The examples show decimal -> Roman numeral conversion.\n"
        f"{query_num} in Roman numerals is {answer}."
    )
    return prompt, answer, cot


# ── Type 4: Unit Conversion (linear scaling) ──────────────────────────────────

def make_unit_puzzle(rng: random.Random) -> tuple:
    # Multiplier in [0.50, 2.00] rounded to 4 decimal places
    multiplier = round(rng.uniform(0.50, 2.00), 4)

    n_examples = rng.randint(3, 5)
    # Input values: 2-digit-ish floats with 2 dp
    example_inputs = [round(rng.uniform(1.0, 50.0), 2) for _ in range(n_examples)]
    query_input    = round(rng.uniform(1.0, 50.0), 2)

    ex_lines = "\n".join(
        f"{v} m becomes {round(v * multiplier, 2)}"
        for v in example_inputs
    )
    prompt = (
        f"{ALICE_HEADER}a secret unit conversion is applied to measurements. "
        f"For example:\n{ex_lines}\n"
        f"Now, convert the following measurement: {query_input} m"
    )
    answer = str(round(query_input * multiplier, 2))

    cot = (
        f"Dividing outputs by inputs gives the multiplier:\n"
        f"  {round(example_inputs[0]*multiplier,2)} / {example_inputs[0]} "
        f"= {multiplier}\n"
        f"Applying to {query_input}: {query_input} × {multiplier} = {answer}"
    )
    return prompt, answer, cot


# ── Type 5: Gravity (infer g from d = 0.5*g*t²) ──────────────────────────────

def make_gravity_puzzle(rng: random.Random) -> tuple:
    # g in [4.91, 19.58] (from training data range)
    g = round(rng.uniform(4.91, 19.58), 2)

    n_examples = rng.randint(3, 5)
    # t values: 1.0 – 5.0 s, rounded to 2 dp
    example_ts = [round(rng.uniform(1.0, 5.0), 2) for _ in range(n_examples)]
    query_t    = round(rng.uniform(1.0, 5.0), 2)

    def dist(t): return round(0.5 * g * t**2, 2)

    ex_lines = "\n".join(
        f"For t = {t}s, distance = {dist(t)} m" for t in example_ts
    )
    prompt = (
        f"{ALICE_HEADER}the gravitational constant has been secretly changed. "
        f"Here are some example observations:\n{ex_lines}\n"
        f"Now, determine the falling distance for t = {query_t}s "
        f"given d = 0.5*g*t^2."
    )
    answer_val = round(0.5 * g * query_t**2, 2)
    answer = str(answer_val)

    # CoT: show how to infer g from first two examples
    t0, d0 = example_ts[0], dist(example_ts[0])
    cot = (
        f"From d = 0.5*g*t², we get g = 2d / t².\n"
        f"Using t={t0}s, d={d0}m: g = 2×{d0} / {t0}² = {g}\n"
        f"For t={query_t}s: d = 0.5 × {g} × {query_t}² = {answer}"
    )
    return prompt, answer, cot


# ── Type 6: Symbol Transformation ─────────────────────────────────────────────
#
# We implement two sub-variants that appear in training data:
#
#   6a. Pure character substitution
#       A random bijection maps each symbol char to another. Input & output
#       have variable length because the mapping can reduce sequences (some
#       output chars are the same as another, so not all inputs survive).
#       Actually in training data output length < input length often, which
#       suggests a positional DELETION or SELECTION rule.
#
#   6b. Operator-based (arithmetic-looking)
#       Strings like "34/44" get transformed by rules where the middle
#       operator determines what happens to the surrounding digits/chars.
#
# For clean synthetic data we implement the positional-deletion variant
# (6a) and a char-map variant (6b). Each puzzle is self-consistent.

def _random_sym_map(rng: random.Random, charset: list) -> dict:
    """Random surjective map: each source char maps to one target char.
    Some target chars may appear multiple times (non-injective on purpose,
    so that output can 'lose' chars as in training data)."""
    targets = rng.choices(charset, k=len(charset))
    return dict(zip(charset, targets))


def _apply_sym_map(s: str, char_map: dict) -> str:
    return "".join(char_map.get(c, c) for c in s)


def _gen_sym_string(rng: random.Random, length: int,
                    charset: list = SYMBOL_CHARS) -> str:
    return "".join(rng.choices(charset, k=length))


def make_symbol_puzzle(rng: random.Random) -> tuple:
    """
    Variant: fixed character-substitution map applied to 5-char symbol strings.
    Outputs may be shorter because mapped chars can collapse (dedup consecutive
    identical chars) – this produces the variable-length outputs seen in training.
    We dedup consecutive identical chars to mimic the training pattern.
    """
    charset    = SYMBOL_CHARS
    char_map   = _random_sym_map(rng, charset)

    def apply_and_dedup(s: str) -> str:
        mapped = _apply_sym_map(s, char_map)
        # Deduplicate consecutive identical chars (mimics training observation)
        result = mapped[0] if mapped else ""
        for c in mapped[1:]:
            if c != result[-1]:
                result += c
        return result

    n_examples = rng.randint(3, 5)
    examples   = []
    seen       = set()
    while len(examples) < n_examples:
        inp = _gen_sym_string(rng, 5)
        if inp in seen:
            continue
        seen.add(inp)
        out = apply_and_dedup(inp)
        examples.append((inp, out))

    q_inp = _gen_sym_string(rng, 5)
    while q_inp in seen:
        q_inp = _gen_sym_string(rng, 5)
    q_out = apply_and_dedup(q_inp)

    ex_lines = "\n".join(f"{i} = {o}" for i, o in examples)
    prompt = (
        f"{ALICE_HEADER}a secret set of transformation rules is applied to equations. "
        f"Below are a few examples:\n{ex_lines}\n"
        f"Now, determine the result for: {q_inp}"
    )
    answer = q_out

    cot = "Each character is mapped to another by a fixed secret substitution.\n"
    for i, o in examples[:2]:
        for ci, co in zip(i, _apply_sym_map(i, char_map)):
            cot += f"  '{ci}' -> '{co}'\n"
    cot += f"Applying to '{q_inp}': {answer}"

    return prompt, answer, cot


# ── Main generator ────────────────────────────────────────────────────────────

PUZZLE_MAKERS = {
    "bit":      make_bit_puzzle,
    "encrypt":  make_encryption_puzzle,
    "numeral":  make_numeral_puzzle,
    "unit":     make_unit_puzzle,
    "gravity":  make_gravity_puzzle,
    "symbol":   make_symbol_puzzle,
}

# Approximate proportions from training data (out of 9500):
#   bit=1602, encrypt=1576, numeral=1576, unit=1594, gravity=1597, symbol=1555
PROPORTIONS = {
    "bit":     1602,
    "encrypt": 1576,
    "numeral": 1576,
    "unit":    1594,
    "gravity": 1597,
    "symbol":  1555,
}
TOTAL_TRAIN = sum(PROPORTIONS.values())  # 9500


def generate(n_per_type: dict,
             output_path: str = "synthetic_train.csv",
             seed: int = 42,
             include_cot: bool = True) -> None:
    """
    n_per_type : dict mapping puzzle-type name -> number of puzzles to generate.
                 Keys must match PUZZLE_MAKERS (bit, encrypt, numeral, unit, gravity, symbol).
    """
    rng  = random.Random(seed)
    rows = []

    for ptype, maker in PUZZLE_MAKERS.items():
        target = n_per_type[ptype]
        print(f"  Generating {target:,} x {ptype} puzzles ...")
        attempts  = 0
        generated = 0
        while generated < target:
            attempts += 1
            if attempts > target * 10:
                print(f"    WARNING: could only generate {generated} for {ptype}")
                break
            try:
                prompt, answer, cot = maker(rng)
            except Exception:
                continue  # skip malformed draws

            row = {
                "id":     f"syn_{ptype}_{generated:06d}",
                "prompt": prompt,
                "answer": str(answer),
            }
            if include_cot:
                row["cot"] = cot
            rows.append(row)
            generated += 1

    # Shuffle so all types are interleaved throughout the file
    rng.shuffle(rows)

    fieldnames = ["id", "prompt", "answer"] + (["cot"] if include_cot else [])
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    print(f"\nSaved {total:,} rows to '{output_path}'")
    print("  Breakdown:")
    for ptype, n in n_per_type.items():
        print(f"    {ptype:<10} {n:>6,}  ({100*n/total:.1f}%)")


# ── Run ─────────────────────────────────────────────────────────────────────────────────

print("Generating synthetic dataset ...")
print(f"  output     : {OUTPUT_PATH}")
print(f"  seed       : {SEED}")
print(f"  include_cot: {INCLUDE_COT}")
print("  counts     :")
for k, v in N_PER_TYPE.items():
    print(f"    {k:<10} {v:>6,}")
print(f"  total      : {sum(N_PER_TYPE.values()):,}")
print()

generate(
    n_per_type  = N_PER_TYPE,
    output_path = OUTPUT_PATH,
    seed        = SEED,
    include_cot = INCLUDE_COT,
)
