import json
import os
import subprocess
import time
from pathlib import Path

def auth_kaggle():
    """Authenticates with Kaggle using env.json."""
    with open("env.json") as f:
        env = json.load(f)
    
    kaggle_api_token = env["KAGGLE_API_TOKEN"]
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(exist_ok=True)
    
    token_file = kaggle_dir / "kaggle.json"
    
    # Check if access_token was previously used, we'll write kaggle.json which is standard
    if not isinstance(kaggle_api_token, dict):
        # Fallback if it's just the token string (though usually kaggle.json needs username/key)
        # Assuming the user has a proper format or we just write it.
        # Actually, if env["KAGGLE_API_TOKEN"] is a string containing json:
        try:
            token_dict = json.loads(kaggle_api_token)
        except json.JSONDecodeError:
            # If it's literally just the token string, it might have been saved as access_token for an older CLI
            with open(kaggle_dir / "access_token", "w") as f:
                f.write(kaggle_api_token)
            return

        with open(token_file, "w") as f:
            json.dump(token_dict, f)
    else:
        with open(token_file, "w") as f:
            json.dump(kaggle_api_token, f)

def get_kaggle_config():
    """Returns the kaggle_config.json as a dict."""
    with open("kaggle_config.json") as f:
        return json.load(f)

def poll_kaggle_status(slug: str, download_dir: Path, max_retries: int = 120, sleep_time: int = 30):
    """Polls Kaggle for notebook completion status."""
    for i in range(max_retries):
        result = subprocess.run(["uv", "run", "kaggle", "kernels", "status", slug], capture_output=True, text=True)
        status_line = result.stdout.strip()
        print(f"Status: {status_line}")
        
        if "complete" in status_line.lower():
            print(f"Notebook {slug} run completed successfully!")
            return
        elif "error" in status_line.lower():
            print(f"Notebook {slug} run failed with an error.")
            subprocess.run(["uv", "run", "kaggle", "kernels", "output", slug, "-p", str(download_dir)], check=False)
            
            # Check for a .log file in the output
            for log_file in download_dir.glob("*.log"):
                print(f"\n--- {log_file.name} Logs ---")
                print(log_file.read_text())
                
            raise RuntimeError(f"Kaggle notebook {slug} failed.")
        
        time.sleep(sleep_time)
    
    raise TimeoutError(f"Kaggle notebook {slug} timed out after {max_retries * sleep_time / 60} minutes.")

def push_notebook_to_kaggle(py_file: str, metadata: dict, slug: str, notebook_dir: str = "generated_notebooks"):
    """Converts a .py file to a notebook, adds metadata, and pushes it to Kaggle."""
    out_dir = Path(notebook_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Write metadata
    with open(out_dir / "kernel-metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    # 2. Convert .py to .ipynb
    notebook_file = out_dir / metadata["code_file"]
    print(f"Converting {py_file} to .ipynb...")
    subprocess.run([
        "uv", "run", "jupytext", "--to", "notebook", 
        py_file, "-o", str(notebook_file)
    ], check=True)
    
    # Add Jupyter kernel metadata
    import nbformat
    nb = nbformat.read(notebook_file, as_version=4)
    nb.metadata['kernelspec'] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    }
    nbformat.write(nb, notebook_file)
    
    # 3. Auth with Kaggle
    auth_kaggle()
    
    # 4. Push to Kaggle
    print(f"Pushing notebook to Kaggle as {slug}...")
    subprocess.run(["uv", "run", "kaggle", "kernels", "push", "-p", str(out_dir)], check=True)
    print("Notebook pushed successfully. Waiting for completion...")
    
    # 5. Poll for status
    poll_kaggle_status(slug, out_dir)

