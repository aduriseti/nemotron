import json
from pathlib import Path
from kaggle_utils import get_kaggle_config, push_notebook_to_kaggle

def push_validation():
    # 1. Read config to determine the username
    config = get_kaggle_config()
    username = config['username']
    tinker_slug = f"{username}/notebook-tinker"
    validation_slug = f"{username}/adapter-validation-notebook"

    # 2. Read the original metadata
    meta_path = Path("notebooks_meta/adapter_validation.json")
    with open(meta_path) as f:
        metadata = json.load(f)
        
    # 3. Update the metadata
    metadata["id"] = validation_slug
    metadata["is_private"] = True
    
    if "id_no" in metadata:
        del metadata["id_no"]
    
    if "kernel_sources" not in metadata:
        metadata["kernel_sources"] = []
        
    original_tinker_slug = "huikang/tinker-submission-notebook"
    if original_tinker_slug in metadata["kernel_sources"]:
        metadata["kernel_sources"].remove(original_tinker_slug)
        
    if tinker_slug not in metadata["kernel_sources"]:
        metadata["kernel_sources"].append(tinker_slug)
        
    original_self_slug = "huikang/adapter-validation-notebook"
    if original_self_slug in metadata["kernel_sources"]:
        metadata["kernel_sources"].remove(original_self_slug)
        
    # 4. Push to Kaggle
    push_notebook_to_kaggle(
        py_file="adapter-validation-notebook.py",
        metadata=metadata,
        slug=validation_slug,
        notebook_dir="generated_notebooks/adapter-validation"
    )

if __name__ == "__main__":
    push_validation()
