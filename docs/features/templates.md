# Templates

A **Template** (CustomConfigTemplate) is a Jinja2 document stored in the OCMO tree. Templates are not resolved on their own — a Config references them via `_ocmo.render` and provides the data context.

Use templates when you need OCMO to generate configuration files in non-YAML formats: Nginx configs, Dockerfiles, HCL, INI, TOML, systemd units, shell scripts, etc.

---

## Create

Send the Jinja2 source as the raw body (not a JSON envelope). Supported Content-Types: `text/plain`, `text/x-jinja2`, `application/octet-stream`.

```bash
# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~template/~create/templates/nginx.conf.j2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/plain" \
  --data-binary @nginx.conf.j2

# CLI
ocmo -n prod create template templates/nginx.conf.j2 -f nginx.conf.j2

# SDK
prod.create_template("templates/nginx.conf.j2", content=open("nginx.conf.j2").read())
```

- OCMO validates the body as valid Jinja2 at save time. Invalid syntax → HTTP 422.
- First version (1) created; `latest` tag points to it.

## Example template

```jinja2
server {
    listen {% if ssl_enabled %}443 ssl{% else %}80{% endif %};
    server_name {{ domain }};

    {% for upstream in upstreams %}
    location {{ upstream.path | default('/') }} {
        proxy_pass http://{{ upstream.host }}:{{ upstream.port }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    {% endfor %}
}
```

## Update

```bash
# REST
curl -X PUT "https://ocmo.example.com/api/v1/ns/prod/~template/~update/templates/nginx.conf.j2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/plain" \
  --data-binary @nginx.conf.j2

# CLI
ocmo -n prod update template templates/nginx.conf.j2 -f nginx.conf.j2

# SDK
prod.update_template("templates/nginx.conf.j2", content=updated_source)
```

## Read

```bash
# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~get/templates/nginx.conf.j2?version=latest"

# CLI
ocmo -n prod get item templates/nginx.conf.j2
ocmo -n prod get item templates/nginx.conf.j2@v2
```

## Tags

Templates support the same custom tag operations as Configs. `latest` is reserved and auto-managed. `stable` does not exist for templates — use custom tags (`release`, `v1.0.0`, `tested`) to mark promoted versions.

```bash
# Set a tag to version 3
ocmo -n prod tag item templates/nginx.conf.j2 --tag release --version 3

# Delete a tag
ocmo -n prod untag item templates/nginx.conf.j2 --tag release
```

Pin templates in `_ocmo.render` with a tag or version number:

```yaml
_ocmo:
  render:
    templates:
      - templates/nginx.conf.j2@release   # pinned to "release" tag
      - templates/supervisor.conf.j2@3    # pinned to version 3
      - templates/other.j2                # uses latest (default)
```

## Upload size limit

Default: 1 MiB (`OCMO_MAX_TEMPLATE_UPLOAD_BYTES`). Returns HTTP 413 if exceeded.

## Required permissions

| Operation | Permission |
|-----------|-----------|
| Read | `template:read` |
| Create / update | `template:write` |
| Delete | `template:delete` |
| Tag | `template:tag` |
| Set description | `template:describe` |

## Related

- [Render](resolving/render.md)
- [Configs](configs.md)
- [Versions and tags](../concepts/versions-and-tags.md)
