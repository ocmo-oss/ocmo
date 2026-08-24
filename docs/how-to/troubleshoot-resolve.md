# Troubleshoot Resolving

Common errors and diagnostic steps when `~resolve` returns unexpected results or fails.

---

## Trace-only: inspect the dependency chain

Before digging into specific errors, use trace-only to see which configs participate and at which versions:

```bash
ocmo -n prod resolve app/web --trace-only -o json

# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web?trace_only=true" | python3 -m json.tool
```

The `trace` field shows every config that participated, at which version, and nested under its extend chain. Unexpected versions here tell you where the wrong override is coming from.

---

## Error: 404 — config or tag not found

**Symptoms:**

```json
{"error": "Not found", "detail": "Config 'app/web' not found at version 'stable'"}
```

**Check:**
- Does the config exist? `ocmo -n prod get item app/web`
- Does the tag exist? `ocmo -n prod get version app/web --tagged-only`
- Is the correct namespace specified? `ocmo -n prod ls`

For folder resolve with a version tag, configs that lack the tag cause failure unless `--ignore-configs-with-missing-tags` is set.

---

## Error: circular reference

```json
{"error": "Circular reference detected", "chain": ["app/a", "app/b", "app/a"]}
```

Config `a` extends `b`, and `b` extends `a`. Fix: break the cycle by extracting shared data into a third config that neither references back.

---

## Error: max depth exceeded

```json
{"error": "Resolve chain depth limit exceeded (max: 20)"}
```

The extend chain is too deep. Either restructure the hierarchy or increase `OCMO_MAX_CONFIG_RESOLVE_DEPTH`.

---

## Error: 403 on a secret parameter

```json
{"error": "Access denied", "detail": "secret:resolve not granted for secrets/db"}
```

The caller needs `secret:resolve` permission on the referenced secret. Options:
- Grant `secret:resolve` to the caller in `_permissions`
- Use `?no-creds=true` to skip secret resolution (substitutes a placeholder value)
- For resolver tokens, add an explicit policy for the secret path

---

## Unexpected override: wrong value in output

1. Run trace-only and note all participating configs.
2. Check each base config's data manually: `ocmo -n prod get item <path>@<version> --raw`
3. Deep-merge semantics: the **later** config in the accumulate chain wins. The current config's data wins over all bases.
4. Check for typos in extend paths — a misspelled path may silently load a different config.

---

## Placeholder not substituted (`{!name}` appears in output)

The parameter was not declared in `_ocmo.parameters`. Add the declaration:

```yaml
_ocmo:
  parameters:
    name:
      type: dynamic
      value: default-value
```

Or the placeholder is in an unquoted YAML value. Placeholders must always be inside quoted strings:

```yaml
# Wrong
host: {!env}.example.com

# Correct
host: "{!env}.example.com"
```

---

## Rendered template produces wrong output

1. Check template source: `ocmo -n prod get item templates/nginx.conf.j2@<version> --raw`
2. Check what data the config passes: resolve the config with `--cast yaml --no-render` (if supported) or resolve with `trace_only=true` and inspect base configs manually.
3. Verify the template version pin in `_ocmo.render.templates`. If using `@latest`, a recent template update may have changed behavior — pin to a numbered version or custom tag for stability.

---

## Draft resolve returns different output than live resolve

Draft resolve does not use the cache and processes the config exactly as you provide it. If draft and live differ:
- Check which version the live resolve is reading: add `?trace_only=true` to the live call
- Check if the live version has parameter overrides from a resolver's default config
- Check if the cached artifact is stale (shouldn't normally happen — cache is content-addressed)

---

## Cache bypass

To force a fresh resolve (bypassing cache):

```bash
# Add any param that changes the cache key — or change the version
ocmo -n prod resolve app/web --param _cache_bust=$(date +%s)

# Or use a specific version number (not a tag) to see exact content
ocmo -n prod resolve app/web@7
```

---

## HTTP 423 — path is locked

```json
{"error": "Path is locked", "lock_path": "app/prod", "reason": "...", "expires_at": "..."}
```

Reads and resolves are never blocked by locks. If you're getting 423 on a resolve, you're also passing `?mark-stable=true` (which updates a tag). Either wait for the lock to expire, remove it, or resolve without `mark-stable`.

---

## Artifact download URL expired

The signed URL returned by `~resolve` is valid for `OCMO_RESOLVE_URL_TTL` seconds (default 300). If you store the URL and try to use it later, it will be rejected. Always resolve fresh to get a new URL.

---

## Enable verbose logging

On the server: set `DJANGO_LOG_LEVEL=DEBUG` (restart required). Resolve requests will log the full pipeline steps.

On the CLI:

```bash
ocmo --log-level debug -n prod resolve app/web
```

---

## Related

- [Resolving overview](../features/resolving/README.md)
- [Extend](../features/resolving/extend.md)
- [Parameters](../features/resolving/parameters.md)
- [Audit log](../features/audit.md)
