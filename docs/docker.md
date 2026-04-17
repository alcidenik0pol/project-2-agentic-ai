# Docker Commands

**Rebuild and restart (no cache):**
```
docker compose down && docker compose build --no-cache && docker compose up -d
```

**View running containers:**
```
docker compose ps
```

**View logs:**
```
docker compose logs -f
```

## Windows / Git Bash Note

Docker CLI output (stdout) is silently dropped in Git Bash / MSYS2 terminals — commands succeed but produce no visible output. To see output, use `cmd.exe` or PowerShell instead, or wrap with Python:

```bash
python -c "
import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
r = subprocess.run(['docker', 'compose', 'ps'], capture_output=True)
print(r.stdout.decode('utf-8', errors='replace'))
"
```
