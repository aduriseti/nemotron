import os
import sys

os.environ["KAGGLE_API_TOKEN"] = "KGAT_d11076c567327fa93ad173711cf6ef32"

try:
    import kagglehub
    kagglehub.login()
    print("Logged in")
except Exception as e:
    print(f"Failed: {e}")
