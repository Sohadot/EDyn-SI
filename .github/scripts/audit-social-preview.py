import json
import re
import socket
import struct
import ssl
import urllib.error
import urllib.request
from html.parser import HTMLParser
from datetime import datetime, timezone

DOMAINS = ["dyba.si", "evdy.si", "agns.si", "orches.si", "edyn.si", "cupy.si", "infs.si"]
USERS = {
  "browser": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36",
  "facebook": "facebookexternalhit/1.1",
  "x": "Twitterbot/1.0",
  "linkedin": "LinkedInBot/1.0",
}

class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        a = dict(attrs)
        k = a.get("property", a.get("name", "")).lower()
        if k:
            self.meta[k] = a.get("content", "")

def request(url, ua, limit=1000000):
    headers = {"User-Agent": ua, "Accept": "text/html,image/png,*/*"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl.create_default_context()) as r:
            blob = r.read(limit)
            return {"status": r.status, "final_url": r.url, "content_type": r.headers.get("content-type", ""), "size": len(blob), "body":blob}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": str(e), "final_url":e.url, "content_type": e.headers.get("content-type",""), "size":0}
    except Exception as e:
        return {"status": None, "error":type(e).__name__ + ": " + str(e), "size":0}

report = {"checked_at":datetime.now(timezone.utc).isoformat(), "results":[]}
for domain in DOMAINS:
    record={"domain":domain}
    try:
        record["dns"] = sorted(set(z[4][0] for z in socket.getaddrinfo(domain,443,type=socket.SOCK_STREAM)))
    except Exception as e:
        record["dns_error"] = type(e).__name__ + ": " + str(e)
    pages={}
    for bot,ua in USERS.items():
        data = request("https://"+domain+"/",ua)
        html = data.pop("body",b"").decode("utf-8",errors="replace")
        if html:
            tags=Metadata()
            try:
                tags.feed(html)
                data["og_image"]=tags.meta.get("og:image")
                data["twitter_image"]=tags.meta.get("twitter:image")
                data["twitter_card"]=tags.meta.get("twitter:card")
                data["og_title"]=tags.meta.get("og:title")
            except Exception as e:
                data["parse_error"]=str(e)
        pages[bot]=data
    record["pages"]=pages
    expected="https://"+domain+"/assets/social-card.png"
    img = request(expected,USERS["facebook"])
    blob=img.pop("body",b"")
    img["png_signature_ok"]=blob.startswith(b"\x89PNG\r\n\x1a\n")
    if img["png_signature_ok"] and len(blob)>=24:
        img["dimensions"]=list(struct.unpack(">II",blob[16:24]))
    record["image"]=img
    record["success"] = all(x.get("status")==200 and x.get("og_image")==expected for x in pages.values()) and img.get("status")==200 and img["png_signature_ok"] and img.get("dimensions")==[1200,630] and "image/png" in img.get("content_type","")
    report["results"].append(record)
    print(json.dumps(record, ensure_ascii=False))
with open("social-preview-live-report.json","w",encoding="utf-8") as f:
    json.dump(report,f,indent=2,ensure_ascii=False)
print("OVERALL_SUCCESS",all(r["success"] for r in report["results"]))
