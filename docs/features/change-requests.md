# Change requests

In OCMO, each **config**, **template**, or **secret** has a **version history**. Normally, when you save, the new content becomes the next published version right away.

**Change requests** add a review step: someone proposes new content in a **draft** (the change request), others can discuss and approve it, and only then does a user with merge rights **apply** it so it becomes a real new version.

Nothing changes for consumers until apply. Until then, the live item still uses the last published version.

---

## How change requests fit together

A typical flow looks like this:

1. An administrator turns on change requests for the namespace and sets policy (how many approvals are required, and so on).
2. A contributor edits a config in the web UI and chooses **Create change request** instead of **Save** (or uses Save only when they are allowed to publish directly).
3. Reviewers open the change request, read the diff, comment, and **Approve** if they agree.
4. Someone with write access on that item clicks **Apply** to publish the proposed content as the next version.

Each change request has a number on that item only, shown as `~1`, `~2`, and so on. For example, `app/web@~2` means “change request 2 on path `app/web`.”

---

## Who can do what

Access follows the same path-based rules as the rest of OCMO. In practice:

| If you want to… | You usually need… |
|-----------------|-------------------|
| Open a change request from the editor, edit your own draft, comment on an open CR | **Read** access on that config, template, or secret |
| Approve, remove your approval, reject someone else’s CR, apply (merge) | **Write** access on that item |
| Turn change requests on or off and edit namespace CR policy | **Global write** on the namespace (web UI **Namespace settings** or `ocmo update namespace`) |

Rules the product enforces:

- The **author cannot approve their own** change request.
- **Apply** needs enough approvals if the namespace requires them.
- **Apply** is blocked if the path is **locked**, if the draft is identical to what is already published, or if the draft still references other open change requests in YAML (see [References between drafts](#references-between-drafts)).
- Builtin namespace paths such as `_permissions` and `_webhooks` **cannot** have change requests.

---

## Validation and size limits

The API validates change-request **metadata and JSON bodies** strictly (unknown fields are rejected). Draft **content** is the raw config, template, or secret body and is limited by the same per-type upload caps as a normal save (see [Limits](../reference/limits.md)).

### Metadata and messages

| Field | When | Limit |
|-------|------|--------|
| **Title** | Create (required) or metadata patch | Non-empty after trimming whitespace; **1–200** characters. |
| **Description** | Create or metadata patch (optional) | **4096** characters max; leading/trailing whitespace is trimmed. |
| **Reject reason** | Reject request body (`reason`) | **4096** characters max; may be empty. |
| **Comment body** | Create or update comment | Non-empty after trim; **1–8192** characters. |
| **Line anchor** | Optional on new comment (`anchor`) | `start_line` ≥ **1**; optional `end_line` ≥ **1** and must not be less than `start_line`. |

Metadata **PATCH** must include at least one of `title` or `description`. Patching with only whitespace for `title` is rejected.

### Create query parameters

| Parameter | Limit |
|-----------|--------|
| `title` | Required; same rules as table above. |
| `description` | Optional; **4096** characters max. |
| `base_version` | Optional tag or version ref; **64** characters max after trim. |

### Listing change requests

List is **per item path** only (`GET …/~change-requests/{path}/~list/`).

| Query parameter | Limit |
|-----------------|--------|
| `status` | One of `open`, `rejected`, `withdrawn`, `applied`, or omit for all statuses on that path. |
| `created_by` | Optional filter; **1–512** characters when set. |
| `limit` | **1–500**, default **100**. |
| `offset` | **≥ 0**, default **0**. |

### Namespace CR policy (when patching the namespace)

| Field | Allowed range |
|-------|-----------------|
| `change_requests_required_approvals` | **0–100** |
| `change_requests_max_open_per_user_per_resource` | **1–100** |

Other `change_requests_*` policy fields are booleans.

---

## Turn on change requests

Change requests are **disabled by default** for each namespace.

### Web UI

Enable them in the web UI:

1. Sign in and open the namespace (for example **project-acme**).
2. Go to **Namespace settings** — from the namespace list, use the gear icon on the row, or open `…/ns/<namespace>/settings` in the browser.
3. Find the **Change requests** section.
4. Turn on **Enable change requests**.
5. Adjust **Policy** fields if needed (explained in the table below).
6. Click **Save settings** at the bottom of the page.

You need permission to edit namespace settings (Global **write**). If the section is missing or read-only, ask an administrator to grant that access.

### Policy fields (same names as in the UI)

| UI label | Default | What it means |
|----------|---------|----------------|
| **Enable change requests** | Off | When off, change request features are hidden and the API behaves as if CRs do not exist. |
| **Required approvals** | `1` | How many distinct approvers must click **Approve** before **Apply** is allowed. Use `0` to allow apply with no approvals. |
| **Max open change requests per user per resource** | `1` | How many open drafts one user may have at once on the same item path. |
| **Auto-reject on new version** | On | If someone publishes a new version **without** going through a change request (a normal **Save**), all open CRs on that item are closed as rejected by the system. |
| **Reset approvals on content change** | On | When the author saves **substantive** edits to the draft body, existing approvals are cleared so reviewers must approve again. |

API and YAML field names use the same meaning with underscores, for example `change_requests_enabled` for **Enable change requests**.

### Command line (CLI)

Namespace commands are **not** scoped with `-n`: they apply to the namespace name you pass as the address.

1. Inspect current settings (includes all `change_requests_*` fields when the server is up to date):

```bash
ocmo get namespace project-acme
```

2. Patch policy by sending a YAML or JSON body. Only include fields you want to change:

```bash
ocmo update namespace project-acme -f cr-policy.yaml
```

Example `cr-policy.yaml`:

```yaml
change_requests_enabled: true
change_requests_required_approvals: 1
change_requests_auto_reject_on_new_version: true
change_requests_max_open_per_user_per_resource: 1
change_requests_reset_approvals_on_change: true
```

You can combine change-request fields with other namespace patch fields in the same file (for example `description` or `permissions_tag`).

Use your configured OCMO context or `--server` / auth flags like any other CLI command. You need the same **Global write** permission as for **Save settings** in the UI.

For the full change-request command set (`create change-request`, `approve`, `apply-cr`, and so on), see [Command line reference](#command-line-reference) below and [CLI reference](../reference/cli.md).

<details>
<summary>Enable and configure via REST API or SDK</summary>

```bash
# REST
curl -X PATCH "https://ocmo.example.com/api/v1/ns/project-acme" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "change_requests_enabled": true,
    "change_requests_required_approvals": 1,
    "change_requests_auto_reject_on_new_version": true,
    "change_requests_max_open_per_user_per_resource": 1,
    "change_requests_reset_approvals_on_change": true
  }'
```

```python
# SDK (namespace client on a Namespace handle)
client.update_namespace(
    "project-acme",
    body={
        "change_requests_enabled": True,
        "change_requests_required_approvals": 1,
    },
)
```

See [REST API](../reference/rest-api.md) — **Namespace** and **Change request** operations.

</details>

---

## Propose a change (web UI — configs)

Today, the full create-and-list workflow in the web UI is built around **config** items. The server also supports change requests on **templates** and **secrets**; use the API, CLI, or SDK for those until the UI catches up.

For a **config**:

1. Open the config in the editor (tree → click the item).
2. Edit the YAML in the **Editor** tab so it reflects what you want to propose. The editor must differ from what you are comparing against (usually the version you have selected).
3. Start a change request:
   - If you have **write** access: open the **Save** dropdown and choose **Create change request**, or use the shortcut hint (**Ctrl/Cmd+S** may focus **Create change request** when you cannot save directly).
   - If you have **read** only: use the primary **Create change request** button when your draft is valid.
4. In the dialog, enter a **Title** (required, up to **200** characters) and optional **Description** (markdown, up to **4096** characters). The description is stored on the CR and appears as the first discussion message when non-empty.
5. Click **Create**. You are taken to the **change request detail** page for that draft.

The draft is tied to the **base version** you had selected in the version picker when you created the CR (often `latest`).

**Tips**

- You cannot create a CR whose body is **identical** to the base version — change something meaningful first.
- If you only have read access, you cannot **Save** a new published version; change requests are how you contribute proposed changes.

<details>
<summary>Create via REST API, CLI, or SDK</summary>

```bash
curl -X POST "https://ocmo.example.com/api/v1/ns/project-acme/~change-requests/app/web?title=Increase+replicas" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/plain" \
  --data-binary @draft.yaml

# CLI — body from file; title is required (see `ocmo create change-request --help` for flags)
ocmo -n project-acme create change-request app/web -f draft.yaml --title "Increase replicas"
```

```python
# SDK (when wired in your client version)
client.create_change_request(
    "app/web",
    content=open("draft.yaml").read(),
    title="Increase replicas",
    description="Optional context",
)
```

</details>

---

## See change requests for one item (web UI)

On a config (when CRs are enabled for the namespace):

1. Open the config.
2. Open the **Change requests** tab (URL hash `#change-requests`).
3. Open CRs are listed first; click a row to open the detail view.

Writers can select multiple open CRs and **Reject** them in bulk from this tab.

---

## Review a change request (web UI)

The detail page shows:

- **Title** and status badge (Open, Applied, Rejected, Withdrawn).
- A **side-by-side diff**: proposed content on the right, compared to **Base** or **Latest** (toggle in the header).
- **Discussion** below the diff (comments and system messages for approvals, apply, reject).
- A sidebar with metadata: id `~N`, author, base version, approval count, **Depends on** / **Referenced by** links to other open CRs, and **Known issues** (validation warnings while drafting).

### If you are the author (open CR)

- Edit the proposed content in the diff editor, then click **Save** (content must still differ from the base version).
- Click the pencil next to the title to rename the CR.
- Resolve preview (configs only): **Resolve** opens the resolve panel for `path@~N`, including unsaved editor text when relevant.

### If you are a reviewer (open CR, write access)

- **Approve** — records your approval (you cannot approve your own CR).
- **Remove approval** — undo your approval while the CR is still open.
- **Reject** — closes the CR with an optional reason (modal; reason up to **4096** characters on the API).

### Apply

When policy and checks pass, **Apply** publishes the draft as the next version. The sidebar shows which version number will be created (“If applied, this change will be published as version **N**”).

After apply, the CR status becomes **Applied** and the sidebar shows who applied it and the new version number.

<details>
<summary>Review actions via REST API, CLI, or SDK</summary>

```bash
# Approve
curl -X POST ".../~change-requests/app/web/~approve/?number=2" -H "Authorization: Bearer $TOKEN"

# Unapprove
curl -X POST ".../~change-requests/app/web/~unapprove/?number=2" ...

# Reject
curl -X POST ".../~change-requests/app/web/~reject/?number=2" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Needs staging validation"}'

# Withdraw (author only)
curl -X POST ".../~change-requests/app/web/~withdraw/?number=2" ...

# Apply
curl -X POST ".../~change-requests/app/web/~apply/?number=2" ...

# CLI
ocmo -n project-acme approve change-request app/web --number 2
ocmo -n project-acme reject change-request app/web --number 2 --reason "..."
ocmo -n project-acme withdraw change-request app/web --number 2
ocmo -n project-acme apply-cr app/web@~2
```

```python
client.approve_change_request("app/web", number=2)
client.apply_change_request("app/web", number=2)
```

</details>

---

## Discussion

On the change request detail page, use the discussion thread under the diff:

- Post comments while the CR is **open**.
- Reference lines in the diff when the UI supports line-anchored comments.
- Read timeline entries when someone approves, applies, rejects, or withdraws.

Comments cannot be added on closed change requests. Each comment is **1–8192** characters (non-whitespace after trim). Optional **anchors** tie a comment to diff lines (`start_line`, optional `end_line`).

JSON bodies for metadata patch, reject, and comments must use only the documented fields; extra keys return **422**.

<details>
<summary>Comments via REST API, CLI, or SDK</summary>

```bash
curl -X POST ".../~change-requests/app/web/~comments/?number=2" \
  -H "Content-Type: application/json" \
  -d '{"body": "Can we default replicas to 3?"}'
```

CLI: `ocmo create change-request-comment` (see `ocmo create change-request-comment --help`).

</details>

---

## Read a draft without opening the CR page

In the item editor or any client that reads versions, use `@~N` as the version:

- Web UI: version picker or URL with `@~2` when supported.
- Same content as the open change request body (secrets require appropriate reveal permissions).

<details>
<summary>Read via REST API, CLI, or SDK</summary>

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/project-acme/~get/app/web?version=~2"

ocmo -n project-acme get item app/web@~2
ocmo -n project-acme get change-request app/web --number 2
```

```python
client.get_item("app/web", version="~2")
client.get_change_request("app/web", number=2, include_content=True)
```

List CRs for **one item path** (listing all paths in a namespace is not supported):

```bash
curl ".../api/v1/ns/project-acme/~change-requests/app/web/~list/?status=open"
ocmo -n project-acme get change-request app/web --status open
```

</details>

---

## Update draft content or metadata

**Author only**, while status is **open**:

- **Content**: on the CR detail page, edit the right-hand side of the diff and **Save**.
- **Title / description**: pencil on the title (metadata patch on the server; same length limits as create; send at least one field).

Substantive content changes may clear approvals when **Reset approvals on content change** is enabled.

<details>
<summary>Update via REST API, CLI, or SDK</summary>

```bash
# Body
curl -X PUT ".../~change-requests/app/web?number=2" \
  -H "Content-Type: text/plain" --data-binary @draft-v2.yaml

# Metadata
curl -X PATCH ".../~change-requests/app/web?number=2" \
  -H "Content-Type: application/json" \
  -d '{"title": "Replicas + resources"}'

ocmo -n project-acme update change-request app/web --number 2 -f draft-v2.yaml
```

</details>

---

## Diff API (outside the UI)

The detail page loads diff data from the API. You can also fetch it directly (`against=base` or `against=latest`; for secrets use `reveal=true` when allowed).

<details>
<summary>Diff via REST API or CLI</summary>

```bash
curl ".../~change-requests/app/web/~diff/?number=2&against=latest"
ocmo -n project-acme diff change-request app/web --number 2 --against latest
```

</details>

---

## When a change request ends

| Status | Meaning |
|--------|---------|
| **Open** | Draft is active; author can edit; reviewers can approve or reject; apply is available when allowed. |
| **Applied** | Merged; a new item version was created. |
| **Rejected** | Closed without merge — by a reviewer, or by the system when **Auto-reject on new version** fires. |
| **Withdrawn** | Author cancelled the draft (via API/CLI; withdrawn CRs show in history like other closed states). |

Published versions **never** use `~N` in YAML references. Only open change request bodies may reference `other/path@~N` for testing.

---

## References between drafts

While a config change request is **open**, you may point at another **open** change request in YAML, for example:

```yaml
_ocmo:
  extend:
    configs:
      - shared/base@~1
replicas: 3
```

- On the CR detail page, **Depends on** and **Referenced by** list these relationships.
- **Resolve** on a config CR can use `path@~N` to preview with draft overlay content.
- **Apply** is blocked until `path@~N` references to **other open** CRs are gone or rewritten. When a referenced CR is applied, peers may get automatic rewrites from `@~N` to a real version number.

<details>
<summary>Machine-oriented rules (validation and apply)</summary>

- Published configs cannot store `~N` refs in `_ocmo` extend/parameters (only numeric versions or tags).
- Apply runs full validation; drafting may surface **Known issues** without blocking edits.
- See [Validation](validation.md) and [Resolving overview](resolving/README.md).

</details>

---

## What items support change requests

| Item | Server (API) | Web UI create / list tab |
|------|----------------|---------------------------|
| Config | Yes | Yes |
| Template | Yes | Use API / CLI / SDK |
| Secret | Yes | Use API / CLI / SDK |
| Builtin paths (`_permissions`, `_webhooks`, …) | No | No |
| Folders, resolvers | No | No |

CR **detail** URLs work under `configs/`, `templates/`, or `secrets/` paths when you navigate from links (for example **Depends on**).

---

## Command line reference

All change-request commands below use **`-n <namespace>`** except [namespace update](#command-line-cli), which uses `ocmo update namespace <name>` without `-n`.

| Goal | Example |
|------|---------|
| Enable policy | `ocmo update namespace project-acme -f cr-policy.yaml` |
| Show namespace + CR flags | `ocmo get namespace project-acme` |
| List CRs on one item | `ocmo -n project-acme get change-request app/web` (see `--help` for filters) |
| Open one CR | `ocmo -n project-acme get change-request app/web --number 2` |
| Create CR (config/template/secret path) | `ocmo -n project-acme create change-request app/web -f draft.yaml --title "…"` |
| Update draft body | `ocmo -n project-acme update change-request app/web --number 2 -f draft.yaml` |
| Read draft as item version | `ocmo -n project-acme get item app/web@~2` |
| Diff | `ocmo -n project-acme diff change-request app/web --number 2 --against latest` |
| Approve / unapprove | `ocmo -n project-acme approve change-request app/web --number 2` |
| Reject | `ocmo -n project-acme reject change-request app/web --number 2 --reason "…"` |
| Withdraw (author) | `ocmo -n project-acme withdraw change-request app/web --number 2` |
| Apply (merge) | `ocmo -n project-acme apply-cr app/web@~2` or `ocmo -n project-acme apply-cr app/web --number 2` |

Run `ocmo <action> change-request --help` (and `ocmo apply-cr --help`) for exact flags on your CLI version. Templates and secrets use the same `create change-request` / `update change-request` commands with the appropriate path.

---

## Notifications and audit

### Audit

Change request operations (create, approve, apply, reject, comments, and so on) are recorded in the namespace **audit** log like any other API action. Use audit when you need a durable history for compliance or post-incident review. See [Audit](audit.md).

### Webhooks and automation

Each namespace can declare outbound **webhooks** in the `_webhooks` config. Besides the usual `config.updated` events (which fire only when a version is **published**), OCMO emits a dedicated **`change_request.*`** family so external systems can react while a CR is still **open**.

Typical events for automation:

| Event | Useful for |
|--------|------------|
| `change_request.created` | Start verification when a new draft appears |
| `change_request.updated` | Re-run checks when the author changes content (`details.update_kind`) |
| `change_request.approved` / `unapproved` | Track review progress; gate custom “ready to merge” dashboards |
| `change_request.rejected` | Close tickets, notify author (`details.reject_kind`: user, system, withdrawn) |
| `change_request.applied` | Trigger deploy or post-merge jobs (`details.applied_version`) |
| `change_request.comment.created` | Ping reviewers when discussion adds context |

Webhook payloads use the item **path** for filtering (`filter.paths` globs in `_webhooks`) and put the CR number in **`version`** (the same `~N` as in `path@~N`). **`details`** carries `node_type`, `number`, `status`, `title`, approval counts on approve events, and similar metadata—without embedding full config bodies. See [Webhooks](webhooks.md) for signing, presets, and the full event list.

#### Example: CI or verification on new change requests

A common pattern is to treat **`change_request.created`** (and **`change_request.updated`** when content changes) as the trigger for pipelines that **do not** wait for apply:

1. Receive the signed webhook POST.
2. Read `namespace`, `path`, and CR number from `version` / `details.number`.
3. Fetch draft content with the API or CLI, for example `GET .../~get/app/web?version=~2` or `ocmo -n project-acme get item app/web@~2`.
4. Run your checks: JSON Schema validation, `ocmo resolve` on `path@~N`, custom linters, policy tests, or a staging resolver that already allows `~N` references.
5. Post results back into your process (Slack, ticket system, or a comment via `change_request.comment.created` / discussion API)—OCMO does not run your CI; it only notifies you.

Use path filters so only relevant trees invoke the hook, for example `app/**`. Subscribe separately to **`change_request.applied`** if the **merge** should start deployment; that event tells you the new published version in `details.applied_version`. Until apply, **`config.updated`** will **not** fire for the draft, so pipelines that only listen for `config.updated` will miss in-review work.

Minimal `_webhooks` sketch (signing key and URL are namespace-specific):

```yaml
webhooks:
  - id: cr-verify
    enabled: true
    url: https://ci.example.com/hooks/ocmo-change-request
    events:
      - change_request.created
      - change_request.updated
      - change_request.applied
    filter:
      paths:
        - app/**
    signature_key: "{!hmac_signing_key}"
    payload:
      preset: ocmo
```

For broader CI patterns (deploy on tag, resolve in jobs), see [CI/CD](../how-to/ci-cd.md).

---

## Related documentation

- [Configs](configs.md) — saving versions without a change request
- [Authorization](authorization.md) — read vs write on paths
- [Locks](locks.md) — apply is blocked on locked paths
- [Validation](validation.md) — schema checks on save and apply
- [CLI reference](../reference/cli.md) — global flags and command grammar
- [REST API](../reference/rest-api.md) — OpenAPI **Change request** group