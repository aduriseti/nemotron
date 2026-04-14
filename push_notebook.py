import json
from pathlib import Path
from kaggle_utils import get_kaggle_config, push_notebook_to_kaggle

def push_notebook():
    config = get_kaggle_config()
    actual_version = config["latest_version"]

    slug = f"{config['username']}/notebook-tinker"
    model_source = f"{config['model_owner']}/{config['model_slug']}/{config['framework']}/{config['instance_slug']}/{actual_version}"

    meta_path = Path("notebooks_meta/notebook_tinker.json")
    with open(meta_path) as f:
        metadata = json.load(f)
        
    metadata["id"] = slug
    
    if "model_sources" not in metadata:
        metadata["model_sources"] = []
    if model_source not in metadata["model_sources"]:
        metadata["model_sources"].append(model_source)

    push_notebook_to_kaggle(
        py_file="notebook_tinker.py",
        metadata=metadata,
        slug=slug,
        notebook_dir="generated_notebooks/notebook-tinker"
    )

if __name__ == "__main__":
    push_notebook()
