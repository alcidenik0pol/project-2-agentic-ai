# Docker Commands

> **These instructions are for Claude Code (running in Git Bash).**
> Docker CLI stdout is silently dropped in MSYS2/Git Bash terminals, so all commands use a Python wrapper to capture output.
> Normal users should use the commands in README.md instead — they work fine in cmd.exe, PowerShell, and standard terminals.

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

Docker CLI output (stdout) is silently dropped in Git Bash / MSYS2 terminals — commands succeed but produce no visible output. You have two options:

### Option A: Python wrapper (recommended for Claude Code)

Wrap any `docker compose` command in this Python one-liner. Replace the command inside `subprocess.run([...])` with whatever you need:

```bash
python -c "
import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
r = subprocess.run(['docker', 'compose', 'ps'], capture_output=True)
print(r.stdout.decode('utf-8', errors='replace'))
print(r.stderr.decode('utf-8', errors='replace'))
"
```

**Full rebuild and restart with visible output:**

```bash
python -c "
import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
r = subprocess.run(['docker', 'compose', '-f', 'F:/_Dev/_Columbia/Agentic AI/project 2/docker-compose.yml', 'up', '-d', '--build'], capture_output=True)
print(r.stdout.decode('utf-8', errors='replace'))
print(r.stderr.decode('utf-8', errors='replace'))
"
```

**Rebuild just frontend:**

```bash
python -c "
import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
r = subprocess.run(['docker', 'compose', '-f', 'F:/_Dev/_Columbia/Agentic AI/project 2/docker-compose.yml', 'up', '-d', '--build', 'frontend'], capture_output=True)
print(r.stdout.decode('utf-8', errors='replace'))
print(r.stderr.decode('utf-8', errors='replace'))
"
```

**Check container status:**

```bash
python -c "
import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
r = subprocess.run(['docker', 'compose', '-f', 'F:/_Dev/_Columbia/Agentic AI/project 2/docker-compose.yml', 'ps'], capture_output=True)
print(r.stdout.decode('utf-8', errors='replace'))
"
```

**View logs:**

```bash
python -c "
import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
r = subprocess.run(['docker', 'compose', '-f', 'F:/_Dev/_Columbia/Agentic AI/project 2/docker-compose.yml', 'logs', '--tail=50'], capture_output=True)
print(r.stdout.decode('utf-8', errors='replace'))
"
```

### Option B: Use cmd.exe or PowerShell directly

Run these in a native Windows terminal (not Git Bash):

```cmd
cd /d "F:\_Dev\_Columbia\Agentic AI\project 2"
docker compose up -d --build
```
