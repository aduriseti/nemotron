import math
import numpy as np
from typing import List, Dict, Tuple, Optional

class DynamicSampler:
    def __init__(
        self,
        examples: List[dict],  # list of dicts with 'id', 'category'
        batch_size: int,
        half_life_cat_batches: float = 10.0,
        sigma_sq_min: float = 1e-4,
        max_is_weight: float = 5.0,
        mc_simulations: int = 100
    ):
        self.examples = examples
        self.N = len(examples)
        self.batch_size = batch_size
        self.alpha_cat = math.pow(0.5, 1.0 / half_life_cat_batches) if half_life_cat_batches > 0 else 0.0
        self.sigma_sq_min = sigma_sq_min
        self.max_is_weight = max_is_weight
        self.mc_simulations = mc_simulations

        self.categories = list(set(ex['category'] for ex in examples))
        self.cat_to_idx = {c: i for i, c in enumerate(self.categories)}

        # State tracking
        self.train_counts = np.zeros(self.N, dtype=np.int32)
        self.current_step = 0

        self.last_cat_loss = np.full(len(self.categories), np.nan, dtype=np.float32)
        self.last_cat_step = np.full(len(self.categories), -1, dtype=np.int32)
        self.cat_updated = np.zeros(len(self.categories), dtype=bool)

        # EMAs (Unit Gaussian prior: mu=0.0, sigma^2=1.0)
        self.mu_c = np.zeros(len(self.categories), dtype=np.float32)
        self.sigma_c_sq = np.ones(len(self.categories), dtype=np.float32)

        # Map category indices for all examples
        self.cat_indices = np.array([self.cat_to_idx[ex['category']] for ex in self.examples], dtype=np.int32)

    def get_next_batch(self) -> Tuple[List[int], List[float]]:
        self.current_step += 1
        
        # Total mean and variance
        mu_total = self.mu_c[self.cat_indices]
        
        effective_sigma_c_sq = self.sigma_c_sq.copy()
        if np.any(self.cat_updated):
            effective_sigma_c_sq[~self.cat_updated] = np.max(self.sigma_c_sq[self.cat_updated])
            
        sigma_total_sq = effective_sigma_c_sq[self.cat_indices]
        std_total = np.sqrt(sigma_total_sq)
        
        # Monte Carlo simulation
        # Shape: (M, N)
        samples = np.random.normal(
            loc=np.broadcast_to(mu_total, (self.mc_simulations, self.N)),
            scale=np.broadcast_to(std_total, (self.mc_simulations, self.N))
        )
        
        # Get top K indices for each simulation
        # Using argpartition for faster top-K, then sorting the top K just in case we want them ordered
        # Shape: (M, K)
        # Note: argpartition puts the K smallest elements at the beginning, so we use -samples to get top K
        topk_indices = np.argpartition(-samples, self.batch_size - 1, axis=1)[:, :self.batch_size]
        
        # Calculate empirical probabilities Q
        # Flatten and count
        flat_indices = topk_indices.ravel()
        counts = np.bincount(flat_indices, minlength=self.N)
        
        # Laplace smoothing
        Q = (counts.astype(np.float32) + 1.0) / (self.mc_simulations + self.N)
        
        # Pick the first simulation's top K as our actual batch
        # (This is equivalent to sampling from the joint distribution of top-K)
        # We can just take the first row of topk_indices.
        batch_indices = topk_indices[0].tolist()
        
        # Calculate Importance Weights
        # W = (K / N) / Q
        target_prob = self.batch_size / self.N
        weights = target_prob / Q[batch_indices]
        weights = np.clip(weights, a_min=None, a_max=self.max_is_weight).tolist()
        
        # Record training counts
        self.train_counts[batch_indices] += 1
            
        return batch_indices, weights

    def update(self, batch_indices: List[int], losses: List[float]):
        indices = np.array(batch_indices, dtype=np.int32)
        L_new = np.array(losses, dtype=np.float32)
        
        # 1. Update Category Stats using the current batch averages
        unique_cats = np.unique(self.cat_indices[indices])
        batch_len = len(indices)
        for c_idx in unique_cats:
            cat_mask = self.cat_indices[indices] == c_idx
            N_cat = np.sum(cat_mask)
            cat_L_new = np.mean(L_new[cat_mask])
            
            L_cat_old = self.last_cat_loss[c_idx]
            t_cat_old = self.last_cat_step[c_idx]
            
            # If we've seen this category before, compute its drop
            if not np.isnan(L_cat_old) and t_cat_old >= 0 and self.current_step > t_cat_old:
                # We assume that if we train on N_cat cipher problems, their impact on loss
                # will be N_cat times the impact of the average cipher problem.
                # So we divide by N_cat to find the normalized per-example learning rate.
                V_cat_obs = (L_cat_old - cat_L_new) / N_cat
                
                mu_c_old = self.mu_c[c_idx]
                sigma_c_sq_old = self.sigma_c_sq[c_idx]
                
                mu_c_new = self.alpha_cat * mu_c_old + (1 - self.alpha_cat) * V_cat_obs
                sigma_c_sq_new = self.alpha_cat * sigma_c_sq_old + (1 - self.alpha_cat) * ((V_cat_obs - mu_c_new) ** 2)
                
                self.mu_c[c_idx] = mu_c_new
                self.sigma_c_sq[c_idx] = max(sigma_c_sq_new, self.sigma_sq_min)
                self.cat_updated[c_idx] = True
                
            # Save state for next time
            self.last_cat_loss[c_idx] = cat_L_new
            self.last_cat_step[c_idx] = self.current_step

    def get_short_stats(self) -> str:
        import pandas as pd
        cat_counts = {c: 0 for c in self.categories}
        for idx, count in enumerate(self.train_counts):
            cat = self.examples[idx]['category']
            cat_counts[cat] += count
            
        data = []
        for cat in sorted(self.categories):
            c_idx = self.cat_to_idx[cat]
            mu = self.mu_c[c_idx]
            std = np.sqrt(self.sigma_c_sq[c_idx])
            data.append({
                "Category": cat,
                "Samples": cat_counts[cat],
                "LR Mean": f"{mu:+.4f}",
                "LR Std": f"{std:.4f}"
            })
            
        df = pd.DataFrame(data)
        return "\n" + df.to_string(index=False)

    def get_stats(self):
        cat_counts = {c: 0 for c in self.categories}
        cat_total = {c: 0 for c in self.categories}
        
        for idx, count in enumerate(self.train_counts):
            cat = self.examples[idx]['category']
            cat_counts[cat] += count
            cat_total[cat] += 1
            
        total_trains = int(np.sum(self.train_counts))
        
        stats = []
        stats.append("=== Category Training Proportions & Predicted Learning Rates ===")
        for cat in self.categories:
            c_idx = self.cat_to_idx[cat]
            mu = self.mu_c[c_idx]
            std = np.sqrt(self.sigma_c_sq[c_idx])
            pct = (cat_counts[cat] / total_trains) * 100 if total_trains > 0 else 0
            stats.append(
                f"{cat}: {cat_counts[cat]} / {total_trains} ({pct:.1f}%) "
                f"[Unique: {cat_total[cat]}] "
                f"| LR Mean: {mu:.4f}, Std: {std:.4f}"
            )
            
        stats.append("\n=== Top 10 Most Trained Examples ===")
        # Use np.argsort for top 10
        top_indices = np.argsort(-self.train_counts)[:10]
        for i in top_indices:
            ex = self.examples[i]
            count = self.train_counts[i]
            stats.append(f"ID: {ex['id']}, Category: {ex['category']}, Count: {count}")
            
        return "\n".join(stats)
