# Standard ngx_http_headers_module (built into nginx). Keep CSP in sync with csp.ts.
add_header Content-Security-Policy "default-src 'self' blob:; base-uri 'self'; form-action 'self'; frame-ancestors 'self'; object-src 'none'; script-src 'self'; worker-src 'self' blob:; frame-src 'self' https:; style-src 'self' 'unsafe-inline'; style-src-attr 'unsafe-inline'; font-src 'self' data:; img-src 'self' data: blob: https:; connect-src 'self' https:; manifest-src 'self';" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;