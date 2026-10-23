# FamilyGuild Core

Thin foundation app for FamilyGuild.

## Purpose

FamilyGuild Core should provide the shared family shell that modules connect to.

Initial responsibilities:

- one-household app state,
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

## Run the private MVP shell

The NiceGUI shell requires a secret for signing the browser session cookie used
to identify one browser profile. Generate a local secret and keep it outside the
repository:

```bash
python3.12 -c 'import secrets; print(secrets.token_urlsafe(32))'
export FG_STORAGE_SECRET='<generated value>'
```

Start the application on the default local address and port:

```bash
./.venv/bin/python -m web_ui.main
```

Open <http://localhost:8090>. The port is intentionally different from the
local chat stack ports. Runtime settings can be overridden when needed:

```bash
./.venv/bin/python -m web_ui.main \
  --state-dir ./app-data \
  --host 127.0.0.1 \
  --port 8090
```

### Prepare and manage a local household

Open the application with a fresh state directory. The initial setup form asks
for the family name, first parent name, currency label (default `FamCoins`) and
language preference (`en` or `pl`). Saving configures the household atomically
and selects that parent only in the current browser profile. No preparation
script is required. Startup never creates demonstration members or overwrites
the household, and an outdated setup form cannot reinitialize it.

With a parent selected, open **Members** (`/members`) to add parents or children,
rename them, or deactivate/reactivate them. Members retain their UUIDs and
relationships; permanent deletion and role changes are not offered. The last
active parent cannot be deactivated. Deactivating your own profile clears your
selection if another active parent remains. Adding a child here does not create
a KidLand profile.

Open **Settings** (`/settings`) to change the family display name, currency label
or language preference. Currency renaming does not change balances; full shell
translation is still pending. The household key and runtime settings are not
editable here. All writes recheck the current active parent, including forms
opened before a profile switch. This is trusted switching, not authentication.

Initial setup is available only when there are no members at all. Existing
households retain their data. If an older or manually modified state has members
but no active parent, stop the application and repair the local state manually;
the UI intentionally does not offer a reset or unauthenticated recovery flow.

### Trusted member behavior

- Each browser profile or device keeps its own selected member.
- Tabs in the same browser profile share the selection.
- Choosing a member opens Home (`/`), including when the selection is synchronized
  to another tab. Reloading a page without changing the selection preserves its route.
- The selected member is revalidated against current active household members
  whenever the shell is opened.
- Selecting a profile does not require a password. This is trusted switching
  for private MVP testing, not production authentication.

For testing from another device on a trusted local network, start with
`--host 0.0.0.0` and open `http://<computer-ip>:8090`. Do not expose this
unauthenticated MVP directly to the internet.

### Enable local module navigation

Stop the application before updating the same state directory from a separate
process. For an initialized household, enable KidLand with the existing command:

```bash
./.venv/bin/python - <<'PY'
import dbzero as db0

from fg_core.commands import enable_module
from fg_core.queries import get_app_state

db0.init("app-data/dbzero", prefix="core")
enable_module(get_app_state(), "kidland", "KidLand")
db0.close()
PY
```

Restart the application, choose a member and open KidLand from the navigation.
The local entry URL is `/modules/kidland`; it currently renders a temporary entry
page, not KidLand workflows or a module dashboard. Home returns to `/`.

Household registrations own labels and enabled state; `web_ui/module_navigation.py`
only maps locally integrated keys to routes. Enabled registrations without local
routes appear without links. Disabled modules are hidden and their entry pages
are unavailable, including through direct URLs. Registration changes are read on
render and route entry, not polled in already open views. Startup never enables
modules automatically. Full translated label selection is deferred.
