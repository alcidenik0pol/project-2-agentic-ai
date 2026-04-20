# 2026-04-18: Docker Complexity Root Cause - MSYS2/Git Bash Incompatibility

## What
Investigation into why Docker commands require Python subprocess wrappers in Git Bash instead of working directly.

## Why
`docker compose` commands in Git Bash execute successfully but produce **no visible output**. Users must wrap commands in Python subprocess calls to see results. Understanding the root cause explains whether this is a Docker configuration issue or an environment limitation.

## Root Cause

This is **not a Docker issue** - it's a fundamental incompatibility between **Git Bash (MSYS2) and native Windows executables**.

### The Technical Problem

```
Git Bash (MSYS2) → [Pseudo-Terminal Layer] → Windows Console API
     ↓                                                      ↓
  POSIX I/O                                          Docker.exe (native)
```

When running `docker compose` in Git Bash:

1. MSYS2 spawns the native Windows `docker.exe`
2. Docker writes output to Windows console handles (`WriteConsole`)
3. MSYS2's pseudo-terminal translation layer fails to bridge this output back to the terminal
4. **Result: Commands succeed but stdout is silently dropped**

### Why Python Wrapper Works

```python
subprocess.run(['docker', 'compose', 'ps'], capture_output=True)
print(r.stdout.decode('utf-8', errors='replace'))
```

This bypasses the broken MSYS2 translation layer by:
- Directly spawning the Windows process (not through pty)
- Capturing stdout/stderr at the source before MSYS2 touches it
- Explicitly handling UTF-8 encoding with error replacement
- Writing output through Python's configured stdout

## Simpler Alternatives (Interactive Use)

| Method | Command | Works? |
|--------|---------|--------|
| **winpty** | `winpty docker compose up` | ✅ Built into Git for Windows |
| **cmd.exe** | `cmd.exe //C "docker compose up"` | ✅ Native Windows terminal |
| **PowerShell** | Run in PS terminal | ✅ Most reliable |
| **Pipe through cat** | `docker compose up \| cat` | ⚠️ Not always works |

## Changes

None - this is an investigation trace. The Docker configuration is correct; the complexity comes from the terminal environment.

## Takeaways

- **Python wrapper is the right choice for Claude Code/automation** - reliable, programmatic, bypasses broken layers
- **winpty is simpler for interactive Git Bash sessions** - just prefix commands with `winpty`
- **PowerShell or CMD is simplest of all** - native Windows terminals don't have this issue
- **No Docker configuration changes needed** - `docker-compose.yml` is standard and correct

## Future Consideration

Update `docs/docker.md` to present `winpty` as the primary option for interactive Git Bash use, with Python wrapper as the automation fallback.

## Conclusion (2026-04-18)

This issue only affects **Claude Code running in Git Bash** — not real users. A user running `docker compose ps` in their terminal sees output fine. The MSYS2 stdout-dropping happens inside Claude Code's Bash tool specifically.

**What we did:**
- `docs/docker.md` now has a clear header: these Python wrapper instructions are for Claude Code only.
- `README.md` has no Git Bash caveat — it just shows normal `docker compose` commands that work for users.
- The two audiences are separated: `docs/docker.md` for agents, `README.md` for humans.
