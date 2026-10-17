# Chrome extension tools

Tools for installing and managing extensions in **your own Google Chrome on macOS**.

## Programmatic installation without a folder picker

`bin/chrome-ext-offline` registers an unpacked Manifest V3 extension directly in an existing Chrome profile. Chrome must be **fully quit** during installation; it loads the extension when reopened. No device management, browser automation, startup flags, or Keychain access is required.

```sh
# Read-only plan; safe while Chrome is running:
python3 bin/chrome-ext-offline /absolute/path/to/extension

# Quit Chrome (Command-Q), then install:
python3 bin/chrome-ext-offline /absolute/path/to/extension --apply
# Reopen Chrome normally.
```

Default profile: `~/Library/Application Support/Google/Chrome/Default`. For another profile, pass `--profile /absolute/path/to/Chrome/Profile\ 1`.

### How it works

Chrome stores installed-extension registrations in `Secure Preferences`. The tool discovers Chrome's preference-signing seed from its installed `resources.pak`, combines it with the machine's `IOPlatformUUID`, and reproduces Chrome's HMAC-SHA256 signatures. It validates the existing overall signature and every installed-extension entry before adding one registration and updating its signature and the overall signature. Existing encrypted hashes are preserved, not decrypted or replaced.

Safety measures:
- Read-only by default; writing requires `--apply`.
- Refuses writes while the target Chrome profile is open or has a remaining lock file.
- Refuses if existing signatures do not validate or the profile changes during the operation.
- Creates a timestamped sibling backup of `Secure Preferences` before an atomic replacement.
- Does not quit, restart, or weaken the running browser, or modify policy.
- Repeated installs of the same folder do not duplicate its registration.

**Experimental and unsupported.** Tested on Google Chrome 155 on macOS with disposable headless profiles: two newly registered extension service workers loaded, including one using storage and host permissions. This is not a guarantee for every Chrome release, permission, or real-world profile. Chrome's internal formats can change. Keep a separate profile backup and use only extensions you trust. The tool grants the manifest's requested permissions to the installed extension.

Limitations: macOS and the standard Google Chrome application path only; an initialized existing profile is required. Manifest V2, custom manifest keys, optional permissions, and complex manifest permissions are not supported. A stale `SingletonLock` causes refusal; do not remove a lock unless you have confirmed that profile's Chrome is stopped. To restore a backup, fully quit Chrome first and replace `Secure Preferences` with the backup.

## Manage an already installed extension

`bin/chrome-ext` uses AppleScript to call Chrome's internal extensions-page API. Requires **View → Developer → Allow JavaScript from Apple Events** in Chrome. This setting allows local programs to execute JavaScript in browser tabs; enable it only if that tradeoff is acceptable.

```sh
bin/chrome-ext list
bin/chrome-ext reload 'My Extension'
bin/chrome-ext disable 'My Extension'
bin/chrome-ext enable 'My Extension'
bin/chrome-ext remove 'My Extension'  # Uninstalls without a confirmation prompt.
bin/chrome-ext install /path/to/extension  # Opens the normal folder picker.
```

Targets accept an extension ID, name, or folder as reported by `list`. The `install` command still uses a folder picker; use `chrome-ext-offline` for picker-free installation while Chrome is closed.

Optional remote use: place `chrome-ext` at `~/.local/bin/chrome-ext` on the remote Mac, then use `bin/chrome-ext --host your-ssh-alias list`. For the offline installer, invoke it over SSH directly.

## Tests

Python 3, Bash and macOS's built-in `osascript` are used; there are no package dependencies.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/chrome-ext-offline.test.py
bash -n bin/chrome-ext
```

Unit tests cover serialization, seed discovery, read-only planning, backups, idempotence, signature validation and refusal to write to an open profile. They do not open Chrome or contact external services.
