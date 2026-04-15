import json
from collections import defaultdict

def derive_markov():
    with open('/workspaces/nemotron/reasoners/equation_numeric_grammar/pipeline_frequencies.json', 'r') as f:
        pipeline_freqs = json.load(f)
        
    count_total = 0.0
    count_pre = defaultdict(float)
    count_pre_mid = defaultdict(float)
    count_mid = defaultdict(float)
    count_mid_post = defaultdict(float)
    count_post = defaultdict(float)
    count_post_ctx = defaultdict(float)
    
    for pipeline, freq in pipeline_freqs.items():
        parts = pipeline.split(' -> ')
        if len(parts) != 4:
            continue
        
        pre, mid, post, ctx = parts
        
        count_total += freq
        count_pre[pre] += freq
        count_pre_mid[(pre, mid)] += freq
        count_mid[mid] += freq
        count_mid_post[(mid, post)] += freq
        count_post[post] += freq
        count_post_ctx[(post, ctx)] += freq
        
    markov_probs = {
        "P_pre": {},
        "P_mid_given_pre": {},
        "P_post_given_mid": {},
        "P_ctx_given_post": {}
    }
    
    for pre, count in count_pre.items():
        markov_probs["P_pre"][pre] = count / count_total if count_total > 0 else 0
        
    for (pre, mid), count in count_pre_mid.items():
        markov_probs["P_mid_given_pre"][f"{pre} -> {mid}"] = count / count_pre[pre] if count_pre[pre] > 0 else 0
        
    for (mid, post), count in count_mid_post.items():
        markov_probs["P_post_given_mid"][f"{mid} -> {post}"] = count / count_mid[mid] if count_mid[mid] > 0 else 0
        
    for (post, ctx), count in count_post_ctx.items():
        markov_probs["P_ctx_given_post"][f"{post} -> {ctx}"] = count / count_post[post] if count_post[post] > 0 else 0
        
    with open('/workspaces/nemotron/reasoners/equation_numeric_grammar/markov_frequencies.json', 'w') as f:
        json.dump(markov_probs, f, indent=2)

if __name__ == "__main__":
    derive_markov()
    print("Markov frequencies derived and saved to reasoners/equation_numeric_grammar/markov_frequencies.json")
