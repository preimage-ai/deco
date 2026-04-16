# Scripts

## `install.sh`

Common setup entrypoint for this repository.

Examples:

```bash
./scripts/install.sh --venv .venv --with-hunyuan
./scripts/install.sh --venv .venv --with-hunyuan --with-da3
./scripts/install.sh --skip-venv --with-hunyuan
```

Notes:

- installs `requirements.txt` every time
- `--with-hunyuan` installs `requirements-hunyuan.txt` and `pip install -e external/Hunyuan3D-2`
- if `external/Hunyuan3D-2` is missing, the script clones it first
- `--with-da3` installs `requirements-da3.txt`
