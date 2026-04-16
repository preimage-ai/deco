# Scripts

## `install.sh`

Common setup entrypoint for this repository.

Examples:

```bash
./scripts/install.sh --venv .venv --with-hunyuan
./scripts/install.sh --venv .venv --with-hunyuan --with-da3
./scripts/install.sh --skip-venv --with-hunyuan
./scripts/install.sh --venv .venv --with-da3
```

Notes:

- installs `requirements.txt` every time
- `--with-hunyuan` installs `requirements-hunyuan.txt`, including `hy3dgen` from PyPI
- `--hunyuan-repo PATH` is only for an explicit local checkout override and adds `pip install -e PATH`
- `--with-da3` installs the published `depth-anything-3` package from `requirements-da3.txt`
- Hunyuan runtime defaults to the pip-installed `hy3dgen` package and Hugging Face model ids
- DA3 runtime defaults to the Hugging Face model `depth-anything/DA3NESTED-GIANT-LARGE-1.1`
- set `DECO_DA3_MODEL` only to override that default with another HF repo id or an explicit local checkpoint path
