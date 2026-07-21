# FamilyGuild Core

Planned thin foundation app for FamilyGuild.

## Purpose

FamilyGuild Core should provide the shared family shell that modules connect to.

Initial responsibilities:

- one family workspace,
- family/member setup,
- trusted member switching for the private MVP test,
- settings shell,
- module navigation,
- general dashboard shell,
- enabled module entry for KidLand.

## MVP Constraint

Do not build production login/authentication for the first private family test.

Do not turn the foundation into a hidden monolith. Keep domain workflows inside modules.

## Source of Truth

Canonical architecture and MVP scope live in `../fg-docs`.

## Development

Run tests from this directory:

```bash
./.venv/bin/python -m pytest
```

Install development dependencies first if needed:

```bash
cd ..
bash scripts/login_aws_codeartifacts.sh
cd fg-core
python3.12 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
```

`dbzero-pro>=0.6.0` is the distribution dependency; runtime code retains `import dbzero as db0`. AWS credentials and the temporary pip token stay outside this repository. Run `bash ../scripts/logout_aws_codeartifacts.sh` from the workspace root when you want to restore the prior user pip index URL.
