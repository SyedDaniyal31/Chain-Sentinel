# ChainSentinel Scripts

| Script | Purpose | Admin Required |
|--------|---------|----------------|
| `verify-environment.ps1` | Check all prerequisites | No |
| `setup-windows.ps1` | Install missing tools via winget | **Yes** |
| `init-project.ps1` | Scaffold frontend/backend/contracts | No |

## Usage

```powershell
# 1. Verify
.\scripts\verify-environment.ps1

# 2. Install (Administrator PowerShell)
.\scripts\setup-windows.ps1

# 3. Reboot if Docker/WSL installed, then verify again
.\scripts\verify-environment.ps1

# 4. Initialize project scaffolds
.\scripts\init-project.ps1
```
