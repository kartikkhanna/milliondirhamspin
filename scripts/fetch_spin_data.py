#!/usr/bin/env python3
"""The Million Dirham Spin: read the Emirates NBD reporting workbook and write data.enc.json (encrypted).

Runs in GitHub Actions on a schedule (see .github/workflows/spin-data.yml).
The workbook is shared as "anyone with the link can view", so no login is needed.
It only holds date, cardholder yes/no, location and prize: no personal data.

Usage: python scripts/fetch_spin_data.py [local.xlsx]
"""
import io, json, os, re, sys, urllib.request
from datetime import datetime, date, timezone
import openpyxl

FILE_ID = os.environ.get("SPIN_SHEET_ID", "1WodmsjxqciwGBg8goHZgCVUGRBD5gDn4")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")
URLS = [
    "https://docs.google.com/spreadsheets/d/%s/export?format=xlsx" % FILE_ID,
    "https://drive.google.com/uc?export=download&id=%s" % FILE_ID,
]
LOCS = {"MOE": "Mall of the Emirates", "MCC": "City Centre Mirdif", "DCC": "City Centre Deira"}


def download():
    last = None
    for u in URLS:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            b = urllib.request.urlopen(req, timeout=60).read()
            if b[:2] == b"PK":
                return b
            last = "not an Excel file (is the sheet still shared by link?)"
        except Exception as e:  # try the next address
            last = str(e)
    sys.exit("ABORT: could not download the workbook: %s" % last)


def to_date(v):
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v or "").strip()
    for f in ("%d-%b-%y", "%d-%b-%Y", "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d %b %Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, f).date().isoformat()
        except ValueError:
            pass
    return None


def parse(blob):
    wb = openpyxl.load_workbook(io.BytesIO(blob), data_only=True, read_only=True)
    rows, skipped = [], []
    for ws in wb.worksheets:
        col, start = None, None
        for i, r in enumerate(ws.iter_rows(min_row=1, max_row=15, values_only=True), 1):
            h = [str(c or "").strip().lower() for c in r]
            if any("date" in c for c in h) and any("prize" in c for c in h):
                find = lambda k: next((j for j, c in enumerate(h) if k in c), None)
                col = dict(d=find("date"), c=find("cardholder"), l=find("location"), p=find("prize"))
                start = i + 1
                break
        if not col:
            continue
        sheet_is_non = "non" in ws.title.lower()
        for n, r in enumerate(ws.iter_rows(min_row=start, values_only=True), start):
            get = lambda k: r[col[k]] if col[k] is not None and col[k] < len(r) else None
            prize = str(get("p") or "").strip()
            loc = str(get("l") or "").strip()
            if not prize and not loc and not get("d"):
                continue  # pre-numbered empty row
            d = to_date(get("d"))
            code = loc[:3].upper()
            ch = str(get("c") or "").strip().lower()
            if ch not in ("yes", "no"):
                ch = "no" if sheet_is_non else "yes"
            if not d or code not in LOCS or not prize:
                skipped.append("%s row %d" % (ws.title, n))
                continue
            prize = prize.replace("—", "-").replace("–", "-")
            rows.append({"d": d, "c": 1 if ch == "yes" else 0, "l": code, "p": prize})
    rows.sort(key=lambda r: (r["d"], r["l"], -r["c"], r["p"]))
    return rows, skipped


def main():
    import hashlib, spincrypt
    root = os.path.dirname(OUT)
    enc_path, keys = os.path.join(root, "data.enc.json"), os.path.join(root, "keys.json")
    blob = open(sys.argv[1], "rb").read() if len(sys.argv) > 1 else download()
    rows, skipped = parse(blob)
    old = {}
    if os.path.exists(enc_path):
        try:
            old = json.load(open(enc_path))
        except Exception:
            pass
    old_n = int(old.get("n", 0))
    if not rows or len(rows) < 0.8 * old_n:
        sys.exit("ABORT: parsed %d plays but the dashboard holds %d. Left unchanged; check the sheet layout." % (len(rows), old_n))
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    if digest == old.get("h"):
        print("No change: %d plays." % len(rows))
        return
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = spincrypt.seal({
        "updated": updated,
        "source": "Emirates NBD reporting sheet (SHARE Spin the Wheel - MAF reporting)",
        "skipped": skipped,
        "rows": rows,
    }, keys)
    out.update(h=digest, n=len(rows), updated=updated)  # h and n let the next run spot changes without the passphrase
    json.dump(out, open(enc_path, "w"), separators=(",", ":"))
    print("Wrote %d plays (was %d), encrypted. Skipped rows: %s" % (len(rows), old_n, skipped or "none"))


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
