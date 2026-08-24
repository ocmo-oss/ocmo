# CLI Reference

Command grammar: `ocmo [global-flags] <action> [resource-type] [path[@version]] [flags]`

---

## Global flags

| Flag | Short | Description |
|------|-------|-------------|
| `--namespace <name>` | `-n` | Namespace to operate in |
| `--server <url>` | `-s` | OCMO server URL (overrides config) |
| `--context <name>` | | Use this context from the config file |
| `--output <format>` | `-o` | Output format: `table`, `yaml`, `json`, `wide`, `raw` |
| `--token <token>` | | Override auth token for this invocation |
| `--log-level <level>` | | `debug`, `info`, `warning`, `error` |
| `--no-color` | | Disable ANSI colors |
| `--version` | | Print CLI and server versions |
| `--help` | `-h` | Show help for any command |

---

## Auth commands

| Command | Description |
|---------|-------------|
| `ocmo auth login` | OIDC device code flow |
| `ocmo auth login --browser` | PKCE browser flow |
| `ocmo auth status` | Show current auth state and token expiry |
| `ocmo auth logout` | Clear cached OIDC token |
| `ocmo auth logout --all` | Clear all cached tokens |
| `ocmo whoami` | Show identity the server sees |
| `ocmo can-i <action> [--resource <path>] -n <ns>` | Check permissions |

---

## Config commands

| Command | Description |
|---------|-------------|
| `ocmo -n <ns> create config <path> -f <file>` | Create config from file |
| `ocmo -n <ns> update config <path> -f <file>` | Update config from file |
| `ocmo -n <ns> get item <path>[@version]` | Get config with content |
| `ocmo -n <ns> get item <path> --raw` | Get raw YAML body |
| `ocmo -n <ns> get version <path>` | List version history |
| `ocmo -n <ns> get version <path> --tagged-only` | Only tagged versions |
| `ocmo -n <ns> delete item <path> [-y]` | Delete config (prompts unless `-y`) |
| `ocmo -n <ns> delete item <path> --preview` | Preview deletion |
| `ocmo -n <ns> delete version <path> --version <n> [-y]` | Soft-delete one version |
| `ocmo -n <ns> move item <path> <target>` | Move config |
| `ocmo -n <ns> copy item <path> <target>` | Copy config |
| `ocmo -n <ns> diff <path> --from <v> --to <v>` | Diff two versions |
| `ocmo -n <ns> diff <path>@<v1>..<v2>` | Same, shorthand |
| `ocmo -n <ns> tag item <path> --tag <name> [--version <n>]` | Set a tag |
| `ocmo -n <ns> untag item <path> --tag <name>` | Delete a tag |
| `ocmo -n <ns> describe <path> --description <text>` | Set description |
| `ocmo -n <ns> propagate <path>` | Trigger manual propagation |

---

## Template commands

| Command | Description |
|---------|-------------|
| `ocmo -n <ns> create template <path> -f <file>` | Create template |
| `ocmo -n <ns> update template <path> -f <file>` | Update template |
| `ocmo -n <ns> get item <path>` | Get template with content |
| `ocmo -n <ns> tag item <path> --tag <name>` | Set a tag |

---

## Secret commands

| Command | Description |
|---------|-------------|
| `ocmo -n <ns> create secret <path> -f <file>` | Create secret |
| `ocmo -n <ns> update secret <path> -f <file>` | Update secret |
| `ocmo -n <ns> get item <path>` | Get metadata only |
| `ocmo -n <ns> get item <path> --reveal` | Get decrypted content |
| `ocmo -n <ns> tag item <path> --tag <name>` | Set a tag |
| `ocmo -n <ns> delete item <path> [-y]` | Delete secret |

---

## Resolver commands

| Command | Description |
|---------|-------------|
| `ocmo -n <ns> create resolver <path>` | Create resolver |
| `ocmo -n <ns> update resolver <path>` | Update description or config |
| `ocmo -n <ns> rotate resolver <path> --slot <1\|2>` | Rotate a token slot |
| `ocmo -n <ns> get item <path>` | Get resolver metadata |
| `ocmo -n <ns> delete item <path> [-y]` | Delete resolver |

---

## Navigation and search

| Command | Description |
|---------|-------------|
| `ocmo -n <ns> ls [path]` | List immediate children |
| `ocmo -n <ns> ls [path] -R` | List recursively |
| `ocmo -n <ns> tree [path] [--depth <n>]` | ASCII tree view |
| `ocmo -n <ns> search tree --q <query>` | Search by name/path |
| `ocmo -n <ns> search tree --q <query> --type config` | Filter by type |

---

## Resolve commands

| Command | Description |
|---------|-------------|
| `ocmo -n <ns> resolve <path>` | Resolve and print |
| `ocmo -n <ns> resolve <path> --version stable` | At a tag |
| `ocmo -n <ns> resolve <path> --cast json` | Cast format |
| `ocmo -n <ns> resolve <path> -O <dir>` | Save artifacts to directory |
| `ocmo -n <ns> resolve <path> --param <k>=<v>` | Dynamic parameter override |
| `ocmo -n <ns> resolve <path> --trace-only` | Trace only (no artifact) |
| `ocmo -n <ns> resolve <path> --no-creds` | Skip secret params |
| `ocmo -n <ns> resolve <path> --mark-stable` | Advance stable tag after resolve |
| `ocmo -n <ns> resolve <path> --ignore-missing-tags` | Folder: skip configs without tag |
| `ocmo -n <ns> resolve draft <path> -f <file>` | Draft resolve from file |
| `ocmo -n <ns> resolve parameters <path>` | Inspect effective parameters |

---

## Lock commands

| Command | Description |
|---------|-------------|
| `ocmo -n <ns> lock <path> --reason <text> [--expires-at <ISO8601>]` | Create lock |
| `ocmo -n <ns> update lock <path>` | Replace lock |
| `ocmo -n <ns> delete lock <path>` | Remove lock |
| `ocmo -n <ns> get lock [path]` | List or get lock(s) |

---

## Audit

| Command | Description |
|---------|-------------|
| `ocmo -n <ns> get audit [--path <p>] [--actor <a>] [--action <a>] [--from <dt>] [--to <dt>] [--limit <n>]` | Query audit log |

---

## Namespace commands

| Command | Description |
|---------|-------------|
| `ocmo create namespace <name> [--description <text>]` | Create namespace |
| `ocmo update namespace <name> [--description <text>] [--permissions-tag <tag>]` | Update |
| `ocmo delete namespace <name> [-y]` | Delete namespace |
| `ocmo get namespace` | List namespaces |
| `ocmo get namespace <name>` | Get namespace details |

---

## Config file commands

| Command | Description |
|---------|-------------|
| `ocmo config set <key> <value>` | Set a config value |
| `ocmo config set-context <name> --server ... --namespace ... --auth ...` | Create a context |
| `ocmo config set-auth <name> --mode ... --issuer ...` | Define an auth profile |
| `ocmo config use-context <name>` | Switch active context |
| `ocmo config current-context` | Print active context name |
| `ocmo config view` | Show full config file |

---

## Shell completion

```bash
ocmo completion bash >> ~/.bashrc
ocmo completion zsh >> ~/.zshrc
ocmo completion fish > ~/.config/fish/completions/ocmo.fish
ocmo completion powershell >> $PROFILE
```

---

## Related

- [Install the CLI](../quickstart/install-cli.md)
- [CI/CD guide](../how-to/ci-cd.md)
