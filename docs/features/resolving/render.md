# Render

`_ocmo.render` uses the config's data (after parameters and extend have run) as Jinja2 context to render one or more **templates** (CustomConfigTemplate items). The template output is the artifact — any text format: Nginx config, HCL, INI, TOML, shell scripts, Dockerfile fragments, etc.

> **Mutually exclusive with `cast`** — a config uses one or the other, not both.

---

## Quick example

Config (`project/prod/nginx`):

```yaml
_ocmo:
  render:
    templates:
      - ../templates/nginx.conf.j2@stable

domain: myapp.prod.example.com
backend_host: 127.0.0.1
backend_port: 8080
ssl_enabled: true
```

Template (`project/templates/nginx.conf.j2`):

```jinja2
server {
    listen {% if ssl_enabled %}443 ssl{% else %}80{% endif %};
    server_name {{ domain }};

    location / {
        proxy_pass http://{{ backend_host }}:{{ backend_port }};
        proxy_set_header Host $host;
    }
}
```

Resolved output:

```nginx
server {
    listen 443 ssl;
    server_name myapp.prod.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
    }
}
```

---

## Configuration syntax

```yaml
_ocmo:
  render:
    templates:
      - path/to/template.j2@tag
      - path: another/template.j2
        key: .services.nginx      # use only this subtree as context
        as: {}                    # (unused for render)
    mode: distribute              # distribute | align
    by: .some.list               # used in align mode
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `templates` | Yes | List of Template paths. Supports `@latest`, `@<tag>`, `@<version>`. Relative paths from the config's folder. |
| `mode` | No | Default: `distribute`. |
| `by` | No | JSON path into config data. For `align`: must point to a list. |

---

## Modes

### `distribute` (default)

All templates rendered against **the same data context**. One output per template.

```
templates[0] rendered with data  →  output[0]
templates[1] rendered with data  →  output[1]
```

Use when you want multiple output files (nginx + supervisor + systemd) from one config:

```yaml
_ocmo:
  render:
    templates:
      - templates/nginx.conf.j2
      - templates/supervisor.conf.j2
    mode: distribute

domain: myapp.example.com
workers: 4
```

### `align`

`by` must point to a list in the config data. Each template is paired with the corresponding list element. One output per pair. List length must equal `templates` length.

```
templates[0] rendered with by[0]  →  output[0]
templates[1] rendered with by[1]  →  output[1]
```

Use when you have per-template data:

```yaml
_ocmo:
  render:
    templates:
      - templates/frontend.conf.j2
      - templates/backend.conf.j2
    mode: align
    by: .vhosts

vhosts:
  - server_name: frontend.example.com
    port: 443
    upstream: 127.0.0.1:3000
  - server_name: api.example.com
    port: 443
    upstream: 127.0.0.1:8000
```

---

## Output naming

The `name` of each rendered artifact defaults to the last segment of the **template** path (e.g., `nginx.conf.j2` → artifact name `nginx.conf.j2`). Override per-output using `_ocmo.name` on the **config**, or via [output naming](output-naming.md) conventions.

---

## Jinja2 features available

Templates use full Jinja2. The entire resolved config data (after parameters and extend) is passed as the root context:

```jinja2
{{ key }}                      {# direct access #}
{{ nested.key }}               {# dot access #}
{{ list | join(', ') }}        {# Jinja2 filter #}
{% for svc in services %}      {# loop #}
  {{ svc.name }}: {{ svc.port }}
{% endfor %}
{% if debug %}                 {# conditional #}
log_level = debug
{% endif %}
{% set x = value | upper %}   {# variable assignment #}
```

All standard Jinja2 filters are available. Templates are validated as valid Jinja2 at save time; invalid templates are rejected with HTTP 422.

---

## Walkthrough

### REST

```bash
# Resolve — get download URL(s)
RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve/project/prod/nginx")

# Download each artifact
echo $RESPONSE | python3 -c "
import sys, json, urllib.request
resp = json.load(sys.stdin)
for item in resp['items']:
    data = urllib.request.urlopen(item['url']).read()
    with open(item['name'].split('/')[-1], 'wb') as f:
        f.write(data)
    print('Wrote', item['name'])
"
```

### Web UI

Navigate to the config → **Resolve** → the panel lists all output items. Click each item to download or preview.

### CLI

```bash
ocmo -n prod resolve project/prod/nginx -O ./nginx/
# writes: ./nginx/nginx.conf.j2 (or custom name if _ocmo.name is set)
```

### SDK

```python
result = prod.resolve("project/prod/nginx")
result.prefetch()
for name, item in result.items():
    print(name, item.text)
result.save_all("./nginx/")
```

---

## Limits

| Limit | Default | Env var |
|-------|---------|---------|
| Max templates in one `render.templates` | 50 | `OCMO_MAX_RENDER_TEMPLATES` |

---

## Related

- [Extend](extend.md) — applied before render; the merged data becomes render context
- [Output naming](output-naming.md)
- [Templates](../templates.md)
