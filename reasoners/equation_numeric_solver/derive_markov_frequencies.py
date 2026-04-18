import json
from collections import defaultdict

def derive_markov():
    with open('/workspaces/nemotron/reasoners/equation_numeric_solver/pipeline_frequencies.json', 'r') as f:
        pipeline_freqs = json.load(f)
        
    count_total = 0.0
    count_pre = defaultdict(float)
    count_pre_post = defaultdict(float)
    count_post = defaultdict(float)
    
    for pipeline, freq in pipeline_freqs.items():
        parts = pipeline.split(' -> ')
        
        pre, post = parts
        
        count_total += freq
        count_pre[pre] += freq
        count_pre_post[(pre, post)] += freq
        count_post[post] += freq
        
    markov_probs = {
        "P_pre": {},
        "P_post_given_pre": {}
    }
    
    for pre, count in sorted(count_pre.items(), key=lambda x: x[1], reverse=True):
        markov_probs["P_pre"][pre] = count / count_total if count_total > 0 else 0
        
    for (pre, post), count in sorted(count_pre_post.items(), key=lambda x: x[1], reverse=True):
        markov_probs["P_post_given_pre"][f"{pre} -> {post}"] = count / count_pre[pre] if count_pre[pre] > 0 else 0
        
    with open('/workspaces/nemotron/reasoners/equation_numeric_solver/markov_frequencies.json', 'w') as f:
        json.dump(markov_probs, f, indent=2)

if __name__ == "__main__":
    derive_markov()
    print("Markov frequencies derived and saved to reasoners/equation_numeric_solver/markov_frequencies.json")