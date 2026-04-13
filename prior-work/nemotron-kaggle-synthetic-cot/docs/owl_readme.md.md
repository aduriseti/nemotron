# Goal
Want to train AI to solve puzzles in https://www.kaggle.com/competitions/nvidia-nemotron-model-reasoning-challenge

Strategy is to produce algorithms where total # of operations fit w/in 7000 token budget allowed in competition

We will then train AI to replcate this algorithm when producing final answer

The list of operations in these algorithms are called chain-of-thought (COT) or "reasoning traces"

# Reading list
Overview of puzzle types in this competition: https://www.kaggle.com/code/mohankrishnathalla/nemotron-6-puzzle-types-decoded-rule-solvers ([nemotron-6-puzzle-types-decoded-rule-solvers.py](../kaggle_notebooks/nemotron-6-puzzle-types-decoded-rule-solvers.py))

A post by someone claiming to have 100% accurate solver for puzzle types - they descibe their algorithm to produce COT but do not implement it - I'm a little skeptical their solver is actually 100% accurate but the writeup is valuable anyways : [puzzle_types_reverse_engineered_unwrapped_lines.md](../kaggle_notebooks/puzzle_types_reverse_engineered.md)

Here is an implementation someone made of the proposed algorithm for solving equation based puzzles: https://www.kaggle.com/code/optiminist/equation-eda-operator-operation-84-solve-rate

I also implemented a solver for the bit manipulation puzzles: [bit_solver.py](../src/synthetic_cot/solvers/bit_solver.py)

However I think that this writeup is the best post describing how to write an algorithm for an LLM to replicate after training - it explains the competition leaders's approach to the bit manipulation problems and how he fits his algorithm w/in 7000 tokens: https://www.kaggle.com/competitions/nvidia-nemotron-model-reasoning-challenge/discussion/690307 ([bit_manipulation_strategy_85_accuracy.md](../kaggle_notebooks/bit_manipulation_strategy_85_accuracy.md))

# Less important reading:
Here is the overall writeup by competition leader on his solution beyond generating COT traces: https://www.kaggle.com/competitions/nvidia-nemotron-model-reasoning-challenge/discussion/689915 ([open_progress_prize_sft_maximize_min_logprob.md](../kaggle_notebooks/open_progress_prize_sft_maximize_min_logprob.md))

Here is a solver someone wrote for all puzzle types - however it requires the answer to determine the required operations - so I'm not sure if it is actually useful - maybe better just for inspiration: https://www.kaggle.com/code/pjt222/nemotron-cot-review ([nemotron-cot-review.py](../kaggle_notebooks/nemotron-cot-review.py))


