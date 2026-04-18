import json
from collections import defaultdict

def derive_independent_frequencies():
    with open('/workspaces/nemotron/reasoners/equation_numeric_solver/pipeline_frequencies.json', 'r') as f:
        pipeline_freqs = json.load(f)
        
    count_total = 0.0
    component_counts = defaultdict(float)
    
    for pipeline, freq in pipeline_freqs.items():
        parts = pipeline.split(' -> ')
        
        count_total += freq
        for part in parts:
            component_counts[part] += freq
            
    # Convert absolute counts to independent probabilities and sort descending
    independent_probs = {}
    for component, count in sorted(component_counts.items(), key=lambda x: x[1], reverse=True):
        independent_probs[component] = count / count_total if count_total > 0 else 0.0
        
    with open('/workspaces/nemotron/reasoners/equation_numeric_solver/independent_frequencies.json', 'w') as f:
        json.dump(independent_probs, f, indent=2)

if __name__ == "__main__":
    derive_independent_frequencies()
    print("Independent component frequencies derived and saved to reasoners/equation_numeric_grammar/independent_frequencies.json")
