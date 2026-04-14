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

# %% [markdown] _uuid="e855885c-38c9-446b-aadc-183ff5a7091b" _cell_guid="876f834c-3e5d-43fb-b502-a4233f529799" jupyter={"outputs_hidden": false}
# This is standalone validation notebook that takes in a `submission.zip` and returns the same `submission.zip` along with evaluation metrics.
#
# These validation concepts were taken from Kh0a's [notebook](https://www.kaggle.com/code/llkh0a/nemotron-unsloth-sft-training-3-30-2).
#
# I want a notebook that does only validation, and prints a few more metrics that I care about.

# %% _uuid="2242b210-0851-4556-b8b7-a26ace7a2979" _cell_guid="068b9369-6f61-4c59-9803-b147b58eea56" jupyter={"outputs_hidden": false}
import glob
import os

submission_zips = glob.glob("/kaggle/input/**/submission.zip", recursive=True)
if not submission_zips:
    raise FileNotFoundError("Could not find submission.zip anywhere in /kaggle/input/")
SUBMISSION_ZIP_PATH = submission_zips[0]
print(f"Found submission zip dynamically at: {SUBMISSION_ZIP_PATH}")

RUN_EVALUATION = True
EVALUATION_SAMPLE_SIZE = 950

# %% _uuid="af9c7f68-3ca3-4578-9c53-0bc7bc656456" _cell_guid="ee906b0d-45b4-4cdf-960e-9a87190a8f30" jupyter={"outputs_hidden": false}
import zipfile

with zipfile.ZipFile(SUBMISSION_ZIP_PATH, "r") as zip_ref:
    zip_ref.extractall()

# %% [markdown] _uuid="6b221df3-f5f0-45bc-92b3-f1decb5dbe1b" _cell_guid="d916ec56-d9e1-41f4-82c0-6371570b4f2c" jupyter={"outputs_hidden": false}
# # Print configs

# %% _uuid="5c413f61-c8e5-44b9-b30d-7fee8134cd2b" _cell_guid="643ee0b8-caa1-4a9d-91aa-faa5e54f4127" jupyter={"outputs_hidden": false}
import json

with open("adapter_config.json") as f:
    trained_adapter_config = json.load(f)

print(trained_adapter_config)

# %% [markdown] _uuid="d123bd49-0f3e-4095-98d4-15966090eab8" _cell_guid="a0208c2a-24b2-4d76-8d12-f634d47d54d0" jupyter={"outputs_hidden": false}
# # Load model

# %% _uuid="e34ce385-4f6d-47c7-b6b1-b7e7cb7cf96e" _cell_guid="0c42c9c4-ef64-4676-be3c-80a1daf0b694" jupyter={"outputs_hidden": false}
"""Metric for NVIDIA (129716)."""

import subprocess
import sys

# Set up environment
commands = [
    "uv pip uninstall torch torchvision torchaudio",
    "tar -cf - -C /kaggle/usr/lib/notebooks/metric/nvidia_metric_utility_script . | tar -xf - -C /tmp",
    "chmod +x /tmp/triton/backends/nvidia/bin/ptxas",
    "chmod +x /tmp/triton/backends/nvidia/bin/ptxas-blackwell",
]
if RUN_EVALUATION:
    for cmd in commands:
        print(f"Running: {cmd}")
        subprocess.run(cmd, shell=True, check=True)
sys.path.insert(0, "/tmp")

# %% _uuid="e19b9393-8b2d-40cc-83da-bb7c8dee9ae7" _cell_guid="7bade0f9-8566-4d2e-b36d-0166e90a49a6" jupyter={"outputs_hidden": false}
import glob
import math
import multiprocessing
import os
import re
import time
from pathlib import Path

import kagglehub
import pandas as pd
from tqdm import tqdm

# Configuration
MODEL_PATH = kagglehub.model_download(
    "metric/nemotron-3-nano-30b-a3b-bf16/transformers/default"
)


# %% _uuid="fdb6040c-0750-4fc2-8f11-db4d981c8521" _cell_guid="c464e2e5-75a3-4724-9d92-5ef389a1da1a" jupyter={"outputs_hidden": false}
class ParticipantVisibleError(Exception):
    pass


def cache_model(
    path: str | Path,
    exts: tuple[str, ...] = (".bin", ".pt", ".safetensors"),
    num_workers: int | None = None,
    chunk_mb: int = 256,
) -> int:
    """Pre-read model weight files into the OS page cache to speed up later loads.

    Args:
        path        : Directory containing model files, or a single file path.
        exts        : File extensions treated as model weight files.
        num_workers : Number of threads (default = min(CPU cores, 8)).
        chunk_mb    : Size of each read chunk in MB.

    Returns:
        Total bytes read (int).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def warmup_file(fpath: Path) -> tuple[Path, int]:
        """Sequentially read an entire file in chunks."""
        chunk_size = chunk_mb * 1024 * 1024
        total = 0
        try:
            with open(fpath, "rb") as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    total += len(data)
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
        return fpath, total

    path = Path(path)
    # Collect files to read
    files: list[Path] = []
    if path.is_dir():
        files = [p for p in path.rglob("*") if p.is_file() and str(p).endswith(exts)]
        files.sort()
    else:
        files = [path] if path.exists() else []

    if not files:
        print(f"No model files found to cache at: {path}")
        return 0

    # Decide number of worker threads
    if num_workers is None:
        try:
            num_workers = min(multiprocessing.cpu_count(), 8)
        except Exception:
            num_workers = 4

    print(f"[cache_model] {len(files)} file(s), {num_workers} worker(s)")
    t0 = time.time()
    total_bytes = 0
    # Read files in parallel
    with ThreadPoolExecutor(max_workers=num_workers) as pool:
        futures = {pool.submit(warmup_file, f): f for f in files}
        for i, fut in enumerate(as_completed(futures), 1):
            fpath, n = fut.result()
            total_bytes += n
            print(f"[{i}/{len(files)}] cached {fpath.name}")

    elapsed = time.time() - t0
    gb = total_bytes / 1024**3
    speed = gb / elapsed if elapsed > 0 else 0
    print(f"[cache_model] total read ≈ {gb:.2f} GB")
    print(f"[cache_model] elapsed {elapsed:.2f} s, ~{speed:.2f} GB/s")
    return total_bytes


def extract_final_answer(text: str | None) -> str:
    r"""Extracts the final answer from the model response.

    Prioritizes extracting answers inside `\boxed{}`.
    If no `\boxed{}` format is found, attempts to extract numbers from other formats.

    Examples:
        >>> extract_final_answer(r"The answer is \boxed{42}")
        '42'
        >>> extract_final_answer("The final answer is: 3.14")
        '3.14'
        >>> extract_final_answer("Just a number 100 in text")
        '100'
        >>> extract_final_answer(None)
        'NOT_FOUND'
    """
    if text is None:
        return "NOT_FOUND"

    # Search for boxed answer
    # Match all instances of \boxed{...} or unclosed \boxed{ at the end
    matches = re.findall(r"\\boxed\{([^}]*)(?:\}|$)", text)
    if matches:
        non_empty = [m.strip() for m in matches if m.strip()]
        if non_empty:
            return non_empty[-1]
        return matches[-1].strip()

    # Other common formats if \boxed{} is not found
    patterns = [
        r"The final answer is:\s*([^\n]+)",
        r"Final answer is:\s*([^\n]+)",
        r"Final answer\s*[:：]\s*([^\n]+)",
        r"final answer\s*[:：]\s*([^\n]+)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[-1].strip()

    # If no structured format is found, extract the last valid number in the text
    matches = re.findall(r"-?\d+(?:\.\d+)?", text)
    if matches:
        return matches[-1]

    # If no numeric answer is found, return the last line of text as a fallback
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else "NOT_FOUND"


def verify(stored_answer: str, predicted: str) -> bool:
    """Verify if the answer matches.

    For numerical answers, allow them to be judged as equal within a certain relative tolerance (1e-2);
    otherwise, compare strictly as strings (case-insensitive).
    """
    # Clean up strings
    stored_answer = stored_answer.strip()
    predicted = predicted.strip()

    try:
        # Try to convert the answers to floating point numbers
        stored_num = float(stored_answer)
        predicted_num = float(predicted)
        # Use a small absolute tolerance for numbers near zero
        return math.isclose(stored_num, predicted_num, rel_tol=1e-2, abs_tol=1e-5)
    except Exception:
        # Fallback to case-insensitive string comparison
        return predicted.lower() == stored_answer.lower()



def generate_predictions(
    test_df: pd.DataFrame,
    lora_path: str,
    row_id_col: str,
    max_lora_rank: int,
    max_tokens: int,
    top_p: float,
    temperature: float,
    max_num_seqs: int,
    gpu_memory_utilization: float,
    max_model_len: int,
    debug: bool = False,
) -> pd.DataFrame:
    """Load the model and generate predictions for the provided test data.

    Args:
        debug: If True, writes a CSV file with raw model outputs and extracted predictions.
    """
    # Cache Model
    cache_model(MODEL_PATH, num_workers=16, chunk_mb=1024)

    os.environ["TRANSFORMERS_NO_TF"] = "1"
    os.environ["TRANSFORMERS_NO_FLAX"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["TRITON_PTXAS_PATH"] = "/tmp/triton/backends/nvidia/bin/ptxas"

    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    # Initialize vLLM Offline inference Engine
    llm = LLM(
        model=str(MODEL_PATH),
        tensor_parallel_size=1,
        max_num_seqs=max_num_seqs,
        gpu_memory_utilization=gpu_memory_utilization,
        dtype="auto",
        max_model_len=max_model_len,
        trust_remote_code=True,
        enable_lora=True,
        max_lora_rank=max_lora_rank,
        enable_prefix_caching=True,
        enable_chunked_prefill=True,
    )

    sampling_params = SamplingParams(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )

    tokenizer = llm.get_tokenizer()
    prompts = []
    for item in test_df.itertuples(index=False):
        user_content = (
            item.prompt
            + "\nPlease put your final answer inside `\\boxed{}`. For example: `\\boxed{your answer}`"
        )
        # Format using the tokenizer's chat template directly
        try:
            prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": user_content}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=True,
            )
        except Exception:
            # Fallback if chat template fails
            prompt = user_content
        prompts.append(prompt)

    # Generate predictions using continuous batching
    outputs = llm.generate(
        prompts,
        sampling_params=sampling_params,
        lora_request=LoRARequest("adapter", 1, lora_path),
    )

    predictions = []
    debug_records = []
    for item, output in zip(test_df.itertuples(index=False), outputs):
        raw_text = output.outputs[0].text
        extracted_answer = extract_final_answer(raw_text)

        row_id_val = getattr(item, row_id_col)

        predictions.append(
            {
                row_id_col: row_id_val,
                "prediction": extracted_answer,
            }
        )

        if debug:
            debug_records.append(
                {
                    row_id_col: row_id_val,
                    "raw_output": raw_text,
                    "extracted_prediction": extracted_answer,
                }
            )

    # Write debug CSV if requested
    if debug and debug_records:
        debug_df = pd.DataFrame(debug_records)
        debug_df.to_csv("debug_predictions.csv", index=False)
        print("Debug data saved to debug_predictions.csv")

    return pd.DataFrame(predictions)


# %% _uuid="ee19ea9c-dc70-453c-b1f9-6998976c49b9" _cell_guid="ee147d39-2808-4462-879e-55f865be1679" jupyter={"outputs_hidden": false}
# Cache Model
if RUN_EVALUATION:
    cache_model(MODEL_PATH, num_workers=16, chunk_mb=1024)

# %% [markdown] _uuid="7fad0bcf-6a1a-495d-8cdb-b8c433e8a4e4" _cell_guid="f57d7fdc-c321-4fe3-b413-4f2391011a3a" jupyter={"outputs_hidden": false}
# # Init vLLM

# %% _uuid="c104d1d2-fc91-4791-8d5e-8a211d989a15" _cell_guid="3e76e600-c5f4-4f5a-8909-f810e3ed73c0" jupyter={"outputs_hidden": false}
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["TRITON_PTXAS_PATH"] = "/tmp/triton/backends/nvidia/bin/ptxas"

from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

# %% _uuid="b4ccb647-d97d-4338-b016-3c67375a34ec" _cell_guid="176fb728-225b-446a-85e3-74f782e09d6e" jupyter={"outputs_hidden": false}
# www.kaggle.com/competitions/nvidia-nemotron-model-reasoning-challenge/overview/evaluation
max_model_len = 8192
max_lora_rank = 32
max_tokens = 7680
top_p = 1.0
temperature = 0.0
max_num_seqs = 64
gpu_memory_utilization = 0.85
max_model_len = 8192

# %% _uuid="1d75e4f5-f431-4745-98ed-828cd97b0c76" _cell_guid="198ff933-b591-40c3-8ac4-451949d78afd" jupyter={"outputs_hidden": false}
# Initialize vLLM Offline inference Engine

if RUN_EVALUATION:
    llm = LLM(
        model=str(MODEL_PATH),
        tensor_parallel_size=1,
        max_num_seqs=max_num_seqs,
        gpu_memory_utilization=gpu_memory_utilization,
        dtype="auto",
        max_model_len=max_model_len,
        trust_remote_code=True,
        enable_lora=True,
        max_lora_rank=max_lora_rank,
        enable_prefix_caching=True,
        enable_chunked_prefill=True,
    )

    sampling_params = SamplingParams(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        logprobs=1,
    )

# %% [markdown] _uuid="1c075f20-1f03-4195-822b-95ce3bd102ed" _cell_guid="499d37f7-1258-49c3-9b68-867648c2321d" jupyter={"outputs_hidden": false}
# # Test generation

# %% _uuid="f0e14afc-836e-411f-af44-bcc41a135dd3" _cell_guid="9aff11a8-323d-4abf-ab79-4de064a47812" jupyter={"outputs_hidden": false}
import pandas as pd

df = pd.read_csv("/kaggle/input/competitions/nvidia-nemotron-model-reasoning-challenge/train.csv")
df = df.head(EVALUATION_SAMPLE_SIZE).copy()

# %% _uuid="708dd65b-a3df-4307-9c12-34f176d5b84b" _cell_guid="0587419e-0bbe-4fd0-adc9-cb5332e50847" jupyter={"outputs_hidden": false}
problem_texts = list(df["prompt"])

if RUN_EVALUATION:
    tokenizer = llm.get_tokenizer()
    prompts = []
    for problem_text in problem_texts:
        # Format using the tokenizer's chat template directly
        prompt = tokenizer.apply_chat_template(
            [{"role": "user", "content": problem_text}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=True,
        )
        prompts.append(prompt)


# %% _uuid="113ab2c7-6505-499a-ba7a-26db218e0137" _cell_guid="fe60f2ff-b2b9-459a-948c-f6e9e2d4c1e1" jupyter={"outputs_hidden": false}
def detect_category(prompt: str) -> str:
    if "secret bit manipulation rule transforms 8-bit binary numbers" in prompt:
        return "bit_manipulation"
    if "secret encryption rules are used on text" in prompt:
        return "cipher"
    if "secret set of transformation rules is applied to equations" in prompt:
        after_header = prompt.split("Below are a few examples:\n", 1)[1]
        examples_text, rest = after_header.split("\nNow, determine the result for: ", 1)
        question_text = rest.strip()
        if any(c.isdigit() for c in examples_text):
            q_match = re.fullmatch(r"(\d+)(\D)(\d+)", question_text)
            if q_match and re.search(
                r"\d" + re.escape(q_match.group(2)) + r"\d", examples_text
            ):
                return "equation_numeric_deduce"
            return "equation_numeric_guess"
        if len(question_text) == 5:
            q_op = question_text[2]
            for ex_line in examples_text.strip().splitlines():
                inp = ex_line.split(" = ")[0].strip()
                if len(inp) == 5 and inp[2] == q_op:
                    return "cryptarithm_deduce"
        return "cryptarithm_guess"
    if "gravitational constant has been secretly changed" in prompt:
        return "gravity"
    if "converted into a different numeral system" in prompt:
        return "numeral"
    if "secret unit conversion is applied to measurements" in prompt:
        return "unit_conversion"
    raise ValueError("unknown")


# %% _uuid="c17ba376-fc8f-4153-9556-4fb2af798f9a" _cell_guid="627bd51b-35b3-475b-b155-582a7683c267" jupyter={"outputs_hidden": false}
# Generate predictions using continuous batching
lora_path = "/kaggle/working"

if RUN_EVALUATION:
    outputs = llm.generate(
        prompts,
        sampling_params=sampling_params,
        lora_request=LoRARequest("adapter", 1, lora_path),
    )

# %% [markdown] _uuid="17f771cd-f60c-4176-a8b3-32416b001cb6" _cell_guid="207b4174-fa8b-4cdc-ac3e-9804e26b6a2f" jupyter={"outputs_hidden": false}
# # Produce submission

# %% _uuid="d3adc935-1c7a-486c-895c-0653ac7ed2ef" _cell_guid="f8d1be7e-d283-4f7d-8e31-b0bc69306be9" jupyter={"outputs_hidden": false}
import zipfile as _zf

print(os.listdir("."))
with _zf.ZipFile("submission.zip", "w", _zf.ZIP_DEFLATED) as zf:
    for file in os.listdir("."):
        if "adapter" not in file:
            continue
        if not os.path.isfile(file):
            continue
        zf.write(file)
        os.remove(file)

# %% _uuid="89a7714e-4cef-425e-b87d-efd960b14e83" _cell_guid="f262f9ba-a85f-4983-9c5d-eb6f304f26fd" jupyter={"outputs_hidden": false}
print(os.listdir("."))

# %% [markdown] _uuid="510f667b-4748-4ba1-800f-f840ddb8c6be" _cell_guid="4cdd7f7b-722b-4bff-8292-a7c57972a323" jupyter={"outputs_hidden": false}
# # Calculate statistics

# %% _uuid="52dd2ead-4c99-4303-a0f0-8b2af8cbbd9b" _cell_guid="4445ed24-b00b-482f-aeb9-fc1fff04e50f" jupyter={"outputs_hidden": false}
if RUN_EVALUATION:
    df["output"] = [output.outputs[0].text for output in outputs]
    df["category"] = [detect_category(problem_text) for problem_text in problem_texts]
    df["predicted"] = df["output"].apply(extract_final_answer)
    df["correct"] = df.apply(
        lambda row: verify(str(row["answer"]), str(row["predicted"])), axis=1
    )
    df["minlogprob"] = [
        min(
            lp.logprob
            for token_dict in output.outputs[0].logprobs
            for lp in token_dict.values()
        )
        if output.outputs[0].logprobs
        else None
        for output in outputs
    ]

# %% _uuid="125b549e-e004-465f-b972-e61cabe0c81b" _cell_guid="a501f819-2ea7-4b09-8e48-670db6972e26" jupyter={"outputs_hidden": false}
# Save mistakes per category
if RUN_EVALUATION:
    os.makedirs("mistakes", exist_ok=True)
    for category in df["category"].unique():
        cat_mistakes = df[(df["category"] == category) & (~df["correct"])]
        if not cat_mistakes.empty:
            cat_mistakes.to_csv(f"mistakes/{category}.csv", index=False)
    
    # Print results table
    stats = df.groupby("category")["correct"].agg(correct="sum", total="count").sort_index()
    stats["correct"] = stats["correct"].astype("int")
    grand_total = stats["total"].sum()
    stats["weightage"] = (stats["total"] / grand_total * 100).map("{:.1f}%".format)
    stats["percentage"] = (stats["correct"] / stats["total"] * 100).map("{:.1f}%".format)
    stats["contribution"] = (stats["correct"] / grand_total * 100).map("{:.1f}%".format)
    overall_pct = stats["correct"].sum() / grand_total * 100
    totals = pd.DataFrame(
        {
            "correct": [stats["correct"].sum()],
            "total": [grand_total],
            "weightage": ["100.0%"],
            "percentage": [f"{overall_pct:.1f}%"],
            "contribution": [f"{overall_pct:.1f}%"],
        },
        index=["TOTAL"],
    )
    results = pd.concat([stats, totals])
    print(results.to_string())
    results.to_csv("results.csv")
    df.to_csv("validation.csv", index=False)

# %% _uuid="bb082ba8-9e16-4b2b-9e08-5dcb47538152" _cell_guid="1fead1a7-4737-4909-a633-1670061275be" jupyter={"outputs_hidden": false}
