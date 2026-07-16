from huggingface_hub import list_repo_files, hf_hub_url, get_hf_file_metadata

repo_id = 'fddemarco/pushshift-reddit'
all_files = [f for f in list_repo_files(repo_id, repo_type='dataset') if f.startswith('data/RS_')]
print(f'Total parquet files: {len(all_files)}')
sorted_files = sorted(all_files)
print(f'Date range: {sorted_files[0]} to {sorted_files[-1]}')
print()
print('2018 files (latest year):')
for f in [x for x in sorted_files if 'RS_2018-' in x]:
    print(f'  {f}')
print()
print('File sizes:')
for f in ['data/RS_2018-12_00.parquet', 'data/RS_2018-01_00.parquet']:
    meta = get_hf_file_metadata(hf_hub_url(repo_id, f, repo_type='dataset'))
    print(f'  {f}: {meta.size / (1024**3):.2f} GB')

