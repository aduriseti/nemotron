import pytest
import math
from dynamic_sampler import DynamicSampler

def test_dynamic_sampler():
    examples = [
        {'id': f'prob_{i}', 'category': 'cat1' if i < 50 else 'cat2'}
        for i in range(100)
    ]
    
    batch_size = 10
    sampler = DynamicSampler(
        examples=examples,
        batch_size=batch_size,
        half_life_cat_batches=10.0,
        max_is_weight=5.0,
        mc_simulations=100
    )
    
    assert sampler.N == 100
    assert set(sampler.categories) == {'cat1', 'cat2'}
    
    # Get first batch
    batch_indices, batch_weights = sampler.get_next_batch()
    assert len(batch_indices) == batch_size
    assert len(batch_weights) == batch_size
    
    # Update with some dummy losses
    losses = [3.0] * batch_size
    sampler.update(batch_indices, losses)
    
    # Get second batch
    batch_indices_2, batch_weights_2 = sampler.get_next_batch()
    assert len(batch_indices_2) == batch_size
    
    # Update with lower losses to simulate learning
    losses_2 = [1.0] * batch_size
    sampler.update(batch_indices_2, losses_2)
    
    # Check if EMAs are updated (not zero and not prior)
    assert any(mu != 0.0 for mu in sampler.mu_c)
    assert any(sigma != 1.0 for sigma in sampler.sigma_c_sq)

    stats = sampler.get_stats()
    assert "=== Category Training Proportions & Predicted Learning Rates ===" in stats
    assert "=== Top 10 Most Trained Examples ===" in stats

def test_category_stats_update():
    examples = [
        {'id': f'prob_{i}', 'category': 'cat1'}
        for i in range(10)
    ]
    
    sampler = DynamicSampler(
        examples=examples,
        batch_size=3,
        half_life_cat_batches=10.0,
        max_is_weight=5.0,
        mc_simulations=10
    )
    
    # Step 1: Update with first set of examples
    sampler.current_step = 1
    batch_1 = [0, 1, 2]
    losses_1 = [3.0, 3.0, 3.0]
    sampler.update(batch_1, losses_1)
    
    # Category stats should still be prior since it's the first time seeing this category
    c_idx = sampler.cat_to_idx['cat1']
    assert sampler.mu_c[c_idx] == 0.0
    assert sampler.sigma_c_sq[c_idx] == 1.0
    
    # Step 2: Update with a second set of DIFFERENT examples
    sampler.current_step = 2
    batch_2 = [3, 4, 5]
    losses_2 = [0.0, 0.0, 0.0] # Simulate learning (loss dropped from avg 3.0 to avg 0.0, V_obs = 3.0)
    sampler.update(batch_2, losses_2)
    
    # Category stats MUST have updated (pulled towards 3.0)
    assert sampler.mu_c[c_idx] > 0.0  # Mean learning rate should be positive
    assert sampler.sigma_c_sq[c_idx] != 1.0 # Variance should have changed
