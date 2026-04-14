.PHONY: all reasoning corpus train upload setup help

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Default target: run the full pipeline
all: reasoning corpus train upload notebook

# 1. Generate reasoning traces
reasoning:
	uv run reasoning.py

# 2. Build training corpus (depends on reasoning traces)
corpus:
	uv run corpus.py

# 3. Run SFT training on Tinker (depends on corpus)
train:
	uv run python3 -m train_sft

# 4. Upload adapter to Kaggle via Modal
# Note: Requires Modal setup and Kaggle/Tinker keys in env.json
upload:
	uv run modal run upload_adapter.py

# 5. Push and run the evaluation notebook on Kaggle
notebook:
	uv run python3 push_notebook.py

# 6. Push and run the validation notebook on Kaggle
validate:
	uv run python3 push_validation.py

# Helper: Set up Modal authentication
setup:
	uv run modal setup

# Help documentation
help:
	@echo "Nemotron SFT Workflow Automation"
	@echo "--------------------------------"
	@echo "make reasoning - Generate CoT reasoning traces from problems.jsonl"
	@echo "make corpus    - Tokenize and package traces into corpus.jsonl"
	@echo "make train     - Execute LoRA SFT training on the Tinker backend"
	@echo "make upload    - Push the trained adapter to Kaggle using Modal"
	@echo ""
	@echo "make all       - Run the complete end-to-end pipeline"
	@echo "make setup     - Authenticate the local Modal client"
	@echo ""
	@echo "Requirements:"
	@echo "  - env.json with TINKER_API_KEY and KAGGLE_API_TOKEN"
	@echo "  - uv (Python package manager)"
	@echo "  - Modal account for cloud uploads"
