---
name: subdomain-setup
description: "Publish a repo on a <name>.garutyunov.com subdomain: create the Cloudflare DNS record and configure the repo's GitHub Pages (enable Pages, custom domain, enforce HTTPS, set it as the repo website). Use when putting a pet project online, wiring a custom subdomain, or fixing Pages/HTTPS config. Examples: \"set up the subdomain for this project\", \"point foo.garutyunov.com at this repo\", \"enable GitHub Pages with the custom domain\"."
---

# Subdomain + GitHub Pages setup

Publish a repo at `https://<name>.garutyunov.com/`. This wires **two** systems:

1. **Cloudflare** — DNS CNAME in the `garutyunov.com` zone pointing at GitHub Pages.
2. **GitHub Pages** — enable Pages, set the custom domain, enforce HTTPS, and set
   the Pages URL as the repo's website (homepage).

Prefer the CLIs/APIs below over the web UI so the steps are reproducible.

## Prerequisites

- `gh` authenticated with `repo` scope (already present in this environment).
- Cloudflare API token with **Zone → DNS → Edit** on the `garutyunov.com` zone,
  exported as `CLOUDFLARE_API_TOKEN`. (No Cloudflare CLI is installed; use the
  v4 REST API via `curl`. `flarectl`/`wrangler` are optional alternatives.)
- The repo must have a deployable site (a `gh-pages` branch, a `/docs` folder,
  or a Pages-publishing GitHub Action).

Set variables used throughout:

```bash
REPO=gaarutyunov/<repo>
NAME=<repo>                       # subdomain label
DOMAIN=$NAME.garutyunov.com
```

## Step 1 — Cloudflare DNS record

Create a **CNAME** `<name>` → `gaarutyunov.github.io`, **DNS-only (not proxied)**
so GitHub can provision its Let's Encrypt certificate and HTTPS enforcement
works. (You may switch the record to proxied/orange-cloud with Full SSL *after*
the GitHub cert is issued, but DNS-only is the reliable default.)

```bash
# Resolve the zone id for garutyunov.com
ZONE_ID=$(curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones?name=garutyunov.com" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result'][0]['id'])")

# Create the CNAME (idempotent-ish: check first)
curl -s -X POST \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -d "{\"type\":\"CNAME\",\"name\":\"$NAME\",\"content\":\"gaarutyunov.github.io\",\"proxied\":false,\"ttl\":1}"
```

If the record already exists, update it instead (find its id via
`GET /zones/$ZONE_ID/dns_records?name=$DOMAIN`, then `PUT` the same body).

### Optional but recommended — domain verification

To prevent subdomain-takeover and get `protected_domain_state: verified`, add
the GitHub-provided challenge TXT record under your GitHub account's
Pages → "Verified domains". GitHub gives a host like
`_github-pages-challenge-gaarutyunov` and a token value; add it as a TXT record
in the same Cloudflare zone.

## Step 2 — Enable GitHub Pages

Create the Pages site. Choose the source matching how the site is built:

```bash
# From a branch (classic — e.g. gh-pages at root):
gh api -X POST repos/$REPO/pages \
  -f 'source[branch]=gh-pages' -f 'source[path]=/' 2>/dev/null \
  || echo "Pages may already be enabled; continuing."

# OR, if built by a GitHub Action:
# gh api -X POST repos/$REPO/pages -f build_type=workflow
```

## Step 3 — Custom domain + enforce HTTPS

Set the custom domain (this writes a `CNAME` file to the Pages source). Then,
**after DNS propagates and GitHub provisions the certificate** (can take minutes
to ~an hour), enforce HTTPS:

```bash
# Set the custom domain
gh api -X PUT repos/$REPO/pages -f cname=$DOMAIN

# Enforce HTTPS (only succeeds once the cert is 'approved')
gh api -X PUT repos/$REPO/pages -F https_enforced=true
```

Poll status until the certificate is approved and HTTPS is enforced:

```bash
gh api repos/$REPO/pages --jq '{cname,https_enforced,cert:.https_certificate.state,status}'
# want: cname=<domain>, https_enforced=true, cert="approved", status="built"
```

If `https_enforced=true` errors with a cert-not-ready message, wait and retry.

## Step 4 — Use GitHub Pages as the repo website

Set the repo's homepage (the "About → Use your GitHub Pages website" checkbox)
to the live URL:

```bash
gh repo edit $REPO --homepage "https://$DOMAIN/"
```

## Verify

```bash
gh api repos/$REPO/pages --jq '{cname,https_enforced,cert:.https_certificate.state,html_url,status}'
gh repo view $REPO --json homepage,hasPages
curl -sSI "https://$DOMAIN/" | head -1     # expect HTTP/2 200 (once live)
```

Reference config from a working project (`stereoscope`):
`cname="stereoscope.garutyunov.com"`, `https_enforced=true`,
`https_certificate.state="approved"`, `protected_domain_state="verified"`,
`source.branch="gh-pages"`, homepage `https://stereoscope.garutyunov.com/`.

## Notes & pitfalls

- **Proxied CNAME breaks cert issuance.** Keep DNS-only until GitHub's cert is
  approved. Enabling Cloudflare proxy too early leaves the cert stuck.
- **`https_enforced` before cert ready fails.** Order matters: DNS → custom
  domain → wait for cert → enforce HTTPS.
- **Buildless sites need `.nojekyll`** at the deploy root (see the
  `pet-project-metadata` skill).
- After this, update the rest of the project metadata (topics, description,
  homepage) via the **`pet-project-metadata`** skill.
