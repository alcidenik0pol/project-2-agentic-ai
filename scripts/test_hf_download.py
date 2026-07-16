"""Test downloading Parquet from HuggingFace Hub."""
from huggingface_hub import hf_hub_download
import os

# Download a single parquet file from the dataset
# This uses proper HF authentication
file_path = hf_hub_download(
    repo_id='fddemarco/pushshift-reddit',
    filename='data/RS_2018-01_00.parquet',
    repo_type='dataset',
    cache_dir='data/hf_cache'
)
print(f'Downloaded to: {file_path}')
print(f'File size: {os.path.getsize(file_path)} bytes')
