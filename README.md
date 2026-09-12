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

`dbzero-pro>=0.6.0` is the distribution dependency; runtime code retains `import dbzero as db0`. AWS credentials and the temporary pip token stay outside this repository. Run `bash ../scripts/logout_aws_codeartifacts.sh` from this subproject directory when you want to restore the prior user pip index URL.

### Verify a fresh environment

Use Python 3.12 explicitly. An existing environment containing legacy `dbzero`
can import `dbzero` and run older tests without satisfying this project's
dependencies. Creating a venv over an existing `.venv` does not clean it.

To preserve your current environment, create a fresh local checkout outside the
workspace. Authenticate from the original workspace first, then run the commands
below from the fresh checkout. Keep core and KidLand environments separate;
do not copy packages from an old environment.

Install and verify from the fresh checkout:

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
./.venv/bin/python -m pip check
./.venv/bin/python -c 'from importlib.metadata import version; print("dbzero-pro", version("dbzero-pro")); print("dbzero-modelkit", version("dbzero-modelkit"))'
./.venv/bin/python -c 'import dbzero as db0; print(db0.__name__)'
./.venv/bin/python -m pytest
```

The installed versions must satisfy `pyproject.toml`; a legacy `dbzero`
distribution is not a substitute for `dbzero-pro`. Restore the prior pip index
using the logout helper in the original workspace, including after a failed
installation. Never commit environments, pip configuration, or authentication
output. These checks verify declared dependencies, not exact-version locking.
