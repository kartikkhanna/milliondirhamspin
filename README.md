# The Million Dirham Spin: Performance Tracker

Dashboard for the Emirates NBD SHARE Visa Credit Card activation.

- `index.html` is the dashboard. It is passphrase-protected: all figures are stored encrypted (`data.enc.json`, `config.enc.json`) and unlocked in the browser.
- `scripts/fetch_spin_data.py` downloads the Emirates NBD reporting sheet and rewrites `data.enc.json`.
- `.github/workflows/spin-data.yml` runs that script every 30 minutes. Use **Actions > Million Dirham Spin data refresh > Run workflow** for a refresh on demand.

The reporting sheet must stay shared as "anyone with the link can view".
