import json
import os
import subprocess
from pathlib import Path

def push_notebook():
    notebook_dir = Path("generated_notebooks")
    notebook_dir.mkdir(exist_ok=True)
    
    # 1. Read config to determine the path
    with open("kaggle_config.json") as f:
        config = json.load(f)
    
    # The uploaded version is just config['latest_version']
    actual_version = config["latest_version"]

    slug = f"{config['username']}/notebook-tinker"
    model_source = f"{config['model_owner']}/{config['model_slug']}/{config['framework']}/{config['instance_slug']}/{actual_version}"

    metadata = {
        "id": slug,
        "title": "Nemotron Evaluation Notebook",
        "code_file": "notebook_tinker.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_tpu": "false",
        "enable_internet": "false",
        "dataset_sources": [],
        "competition_sources": [
            "nvidia-nemotron-model-reasoning-challenge"
        ],
        "model_sources": [
            "metric/nemotron-3-nano-30b-a3b-bf16/Transformers/default/1",
            model_source
        ],
        "kernel_sources": [
            "metric/nvidia-metric-utility-script",
            "huikang/nvidia-nemotron-all-linear",
            "ryanholbrook/nvidia-utility-script"
        ]
    }
    
    with open(notebook_dir / "kernel-metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
    
    # 2. Convert .py to .ipynb
    print("Converting notebook_tinker.py to .ipynb...")
    subprocess.run([
        "uv", "run", "jupytext", "--to", "notebook", 
        "notebook_tinker.py", "-o", str(notebook_dir / "notebook_tinker.ipynb")
    ], check=True)
    
    # Add Jupyter kernel metadata
    import nbformat
    nb_path = notebook_dir / "notebook_tinker.ipynb"
    nb = nbformat.read(nb_path, as_version=4)
    nb.metadata['kernelspec'] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    }
    nbformat.write(nb, nb_path)
    
    # 3. Auth with Kaggle
    with open("env.json") as f:
        env = json.load(f)
    
    kaggle_api_token = env["KAGGLE_API_TOKEN"]
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(exist_ok=True)
    with open(kaggle_dir / "access_token", "w") as f:
        f.write(kaggle_api_token)

    # 4. Push to Kaggle
    print(f"Pushing notebook to Kaggle as {slug} with model source {model_source}...")
    subprocess.run(["uv", "run", "kaggle", "kernels", "push", "-p", str(notebook_dir), "--accelerator", "NvidiaRtxPro6000"], check=True)
    print("Notebook pushed successfully. Waiting for completion...")

    # 5. Poll for status
    import time
    max_retries = 120
    for i in range(max_retries):
        result = subprocess.run(["uv", "run", "kaggle", "kernels", "status", slug], capture_output=True, text=True)
        status_line = result.stdout.strip()
        print(f"Status: {status_line}")
        
        if "complete" in status_line.lower():
            print("Notebook run completed successfully!")
            return
        elif "error" in status_line.lower():
            print("Notebook run failed with an error.")
            subprocess.run(["uv", "run", "kaggle", "kernels", "output", slug, "-p", str(notebook_dir)], check=False)
            log_file = notebook_dir / "notebook_tinker.log"
            if log_file.exists():
                print("\n--- Notebook Logs ---")
                print(log_file.read_text())
            raise RuntimeError(f"Kaggle notebook {slug} failed.")
        
        time.sleep(30)
    
    raise TimeoutError(f"Kaggle notebook {slug} timed out after 60 minutes.")

if __name__ == "__main__":
    push_notebook()