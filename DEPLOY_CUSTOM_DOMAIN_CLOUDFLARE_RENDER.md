# Custom Domain: Cloudflare + Render

## 1) Add domain in Render
1. After the service exists, open Render -> your service -> **Settings** -> **Custom Domains**.
2. Add `investment.faizkrisnadi.com`.
3. Copy the target hostname Render shows (example: `your-service.onrender.com`).

## 2) Add DNS record in Cloudflare
Create this DNS record:

- Type: `CNAME`
- Name: `investment`
- Target: `<render-hostname-from-render>`
- Proxy status: `DNS only` (gray cloud)
- TTL: `Auto`

If an `AAAA` record exists for `investment.faizkrisnadi.com`, remove it.

## 3) Verify and TLS
1. Return to Render Custom Domains and wait for verification to complete.
2. Render will issue TLS automatically after DNS resolves.

## Basic troubleshooting checklist
- CNAME target exactly matches Render-provided hostname.
- Cloudflare proxy is **DNS only** (not proxied).
- No conflicting `A`/`AAAA`/extra `CNAME` record for `investment`.
- DNS propagation may take time; recheck after a few minutes.
