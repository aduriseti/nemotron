# Dynamic Curriculum Scheduling via Additive Gaussian Learning Rates

This document outlines the theoretical framework and implementation plan for a dynamic curriculum scheduling system. The goal is to maximize training efficiency by dynamically sampling the "learning frontier" (data points that the model is primed to learn fastest) while using Importance Sampling to maintain an unbiased training objective.

## Core Concept: The Learning Frontier
Instead of a static easy-to-hard curriculum, this approach seeks the learning frontier. The system tracks the predicted **learning rate** (the derivative of the loss) for every data point. Data points that have high loss *and* a high predicted rate of improvement are prioritized for compute.

## Modeling the Predicted Learning Rate
The predicted learning rate for any specific example is modeled as an **Additive Mixed-Effects Gaussian Distribution**.

This is calculated as the sum of two independent Gaussians:
1.  **Category Baseline ($\mathcal{N}(\mu_c, \sigma_c^2)$):** The macro-trend of the category the example belongs to.
2.  **Example Offset ($\mathcal{N}(\mu_e, \sigma_e^2)$):** The specific micro-deviation of the individual example from its category average.

Because the sum of two independent Gaussians is a single Gaussian, the total predicted learning rate for Example $i$ in Category $c$ is:
**Total Learning Rate $\sim \mathcal{N}(\mu_c + \mu_e, \sigma_c^2 + \sigma_e^2)$**

This handles "sparse data" elegantly: if an example has never been seen, its offset defaults to $\mu_e=0$ and a high variance, causing it to fall back to the category baseline but with high uncertainty (encouraging exploration).

## Computing the Loss Delta (Time Normalization)
To update the Exponential Moving Averages (EMAs) that track $\mu$ and $\sigma$, we need an observation of the actual learning rate when an example is sampled. 

Because examples are sampled sparsely, there may be a gap of $\Delta t$ batches between observations. To prevent background generalization from contaminating the derivative calculation, we compute the **time-normalized loss delta**:

$$V_{obs} = \frac{L_{old} - L_{new}}{\Delta t}$$

Where:
*   $L_{old}$: The loss of the example the last time it was sampled.
*   $L_{new}$: The loss of the example right now.
*   $\Delta t$: The number of global training steps since the example was last sampled.

$V_{obs}$ represents the average improvement *per global step* during the gap, isolating the velocity.

### Updating the EMAs
1.  **Update Category Baseline:** Use $V_{obs}$ to update $\mu_c$ and $\sigma_c^2$ using standard EMA formulas (e.g., mimicking Adam's moment tracking).
2.  **Calculate Residual:** Find how the specific example differed from its category: $R_{obs} = V_{obs} - \mu_{c\_new}$.
3.  **Update Example Offset:** Use $R_{obs}$ to update $\mu_e$ and $\sigma_e^2$.

## Sampling: Monte Carlo Right-Tail Extraction
To build a batch, we want to sample from the "right tail" of the total distribution—the examples with the absolute highest predicted learning rates. 

Instead of computing complex analytic probabilities, we use a single-stage Monte Carlo simulation:
1.  Generate a matrix of samples from $\mathcal{N}(\mu_{total}, \sigma_{total}^2)$ for all data points.
2.  Sort the matrix and extract the indices of the top $K$ items (where $K$ is the batch size).
3.  By running this simulation multiple times (e.g., $M=1000$), we count how often each example makes it into the top $K$.
4.  The empirical sampling probability ($Q$) for an example is: 
    $$Q = \max\left(\frac{\text{Count}}{M}, \epsilon\right)$$
    (Laplace smoothing $\epsilon$ prevents division-by-zero errors).

## Debbiasing with Importance Sampling
Because we are heavily biasing the dataloader to pick fast-learning examples, we must correct the loss function to prevent catastrophic forgetting and optimizer instability.

We apply an Importance Sampling weight $W$ to the loss of each example before the backward pass:
$$W = \min\left(\frac{1/N}{Q}, W_{max}\right)$$

Where:
*   $1/N$ is the target uniform probability of the original dataset.
*   $Q$ is the empirical sampling probability from the Monte Carlo simulation.
*   $W_{max}$ clips the weight to prevent exploding gradients.

**Result:** The model takes frequent, small, highly optimized steps on the learning frontier, while taking rare, massive steps on converged data to preserve historical knowledge.
