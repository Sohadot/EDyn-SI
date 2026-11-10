import json, re, struct, ssl, urllib.request, urllib.error, sys, time
from html.parser import HTMLParser
from datetime import datetime,timezone
DOMAINS=["dyba.si","evdy.si","agns.si","orches.si","edyn.si","cupy.si","infs.si"]
BOTS={
    "facebook":"facebookexternalhit/1.1",
    "x":"Twitterbot/1.0",
    "linkedin":"LinkedInBot/1.0",
    "whatsapp":"WhatsApp/2.24.24 i",
}
class Tags(HTMLParser):
    def __init__(self):super().__init__();self.m={}
    def handle_starttag(self,tag,attrs):
        if tag=="meta":
            d=dict(attrs);k=d.get("property") or d.get("name")
            if k:self.m[k]=d.get("content","")
def get(url,agent):
    try:
        r=urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":agent,"Accept":"*/*"}),timeout=14,context=ssl.create_default_context())
        with r:
            b=r.read(400000)
            return {"status":r.status,"final_url":r.url,"mime":r.headers.get("content-type",""),"body":b}
    except urllib.error.HTTPError as e:return {"status":e.code,"error":str(e),"body":b""}
    except Exception as e:return {"status":None,"error":type(e).__name__+": "+str(e),"body":b""}
def retry(url,agent):
    v=get(url,agent)
    if v["status"] in (500,502,503,504):
        time.sleep(2);v=get(url,agent)
    return v
reports=[]
for d in DOMAINS:
    expected=f"https://{d}/assets/social-card.png?v=20261110"
    q={"domain":d,"bots":{},"expected":expected}
    for n,ua in BOTS.items():
        resp=retry(f"https://{d}/",ua)
        page=resp.pop("body",b"")
        if resp["status"]==200:
            p=Tags();p.feed(page.decode("utf-8","replace"))
            resp["og_image"]=p.m.get("og:image")
            resp["twitter_image"]=p.m.get("twitter:image")
            resp["twitter_card"]=p.m.get("twitter:card")
            resp["og_site_name"]=p.m.get("og:site_name")
        q["bots"][n]=resp
    img=retry(expected,BOTS["facebook"]);raw=img.pop("body",b"")
    img["signature"]=raw.startswith(b"\x89PNG\r\n\x1a\n")
    if img["signature"] and len(raw)>=24:img["dimensions"]=list(struct.unpack(">II",raw[16:24]))
    q["image"]=img
    rob=retry(f"https://{d}/robots.txt",BOTS["facebook"]);b=rob.pop("body",b"")
    rob["allows_all"]=b"User-agent: *" in b and b"Allow: /" in b
    q["robots"]=rob
    q["pass"]=all(v.get("status")==200 and v.get("og_image")==expected and v.get("twitter_image")==expected and v.get("twitter_card")=="summary_large_image" for v in q["bots"].values()) and img.get("status")==200 and "image/png" in img.get("mime","") and img.get("dimensions")==[1200,630] and rob.get("status")==200 and rob.get("allows_all")
    reports.append(q)
    print(json.dumps(q,ensure_ascii=False))
with open("social-preview-live-report.json","w") as f:json.dump({"checked_at":datetime.now(timezone.utc).isoformat(),"results":reports},f,indent=2)
print("SUCCESS",sum(x["pass"] for x in reports),"/",len(reports))
sys.exit(0 if all(x["pass"] for x in reports) else 1)
