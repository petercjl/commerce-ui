# Commerce UI

`@petercjl/commerce-ui` independently distributes the `commerce-ui` CLI, the exact portable Skill `compact-commerce-ui`, and nine versioned reusable HTML template packs. Domain management shells can register this package without copying its implementation.

## Install and update

```sh
npm install -g @petercjl/commerce-ui@latest
commerce-ui runtime install --yes
commerce-ui skill install --agent codex
commerce-ui doctor --json
commerce-ui update check
commerce-ui update install --agent codex --yes
```

Use `--agent sealseek` for SealSeek, or `--target-dir DIR` for an explicit Skill root. Node.js 20+ and Python 3.10+ are required. `runtime install` creates a user-owned virtual environment and installs the declared Python dependencies there; it does not modify a protected system Python. Runtime discovery checks configured `COMMERCE_UI_PYTHON`, Agent-managed runtimes, the managed environment and working PATH candidates. No service account or credential is required to render local files.

## Reports

```sh
commerce-ui templates list --json
commerce-ui schema --template compact-workbench
commerce-ui render --input report.json --output report.html
commerce-ui validate report.html --json
commerce-ui self-test
```

Output paths must be new. The Skill maps source evidence to the live ViewModel contract; deterministic renderers and validators preserve structure, emphasis, navigation and images. Host browser inspection is a separate Agent capability.

## Template ownership

Bundled defaults belong to the npm package. Custom packs installed with `templates install` and edited through `templates update` live under the user data root, outside the package. Set `COMMERCE_UI_DATA_ROOT` to override it. A custom pack can shadow a bundled default of the same ID and contract; duplicate contracts under different IDs are refused. Package updates preserve custom packs. Editing executable packs requires explicit local-code trust.

## Management shell

`taobao-ai-ops` registers this package as `html-report`. Its unified update installs current stable components and synchronizes managed Skills. Shell runs delegate to this package's CLI; the component remains independently versioned. A Git source checkout is updated through Git, while registry-installed packages use their owning installer.

## Compatibility

Portable core and installation adapters cover Codex and SealSeek. macOS/Windows CI checks npm installation mechanics, UTF-8 rendering, runtime discovery, lifecycle and template isolation. Native Agent discovery and browser inspection need host-specific evidence; CI alone does not establish them. Publication uses GitHub Actions npm Trusted Publishing.
