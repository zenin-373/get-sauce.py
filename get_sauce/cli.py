from pathlib import Path
import argparse, concurrent.futures, json
import requests
from .config import Config
from .request import HttpClient
from .utils import safe_filename, filename_from_url, format_bytes
from .parsers.hls import is_hls
from .merger.ffmpeg import ffmpeg_available, remux

CHUNK=262144

def headers(values):
    out={}
    for v in values:
        if ":" in v:
            k,x=v.split(":",1); out[k.strip()]=x.strip()
    return out

def urls_from(args):
    result=list(args.urls)
    if args.file:
        result += [x.strip() for x in Path(args.file).read_text(encoding="utf8").splitlines()
                   if x.strip() and not x.lstrip().startswith("#")]
    return result

def inspect(client,url):
    with client.get(url,stream=True) as r:
        r.raise_for_status()
        c=r.headers.get("Content-Type","")
        n=r.headers.get("Content-Length")
        return {"url":url,"final_url":r.url,"content_type":c,
                "content_length":int(n) if n and n.isdigit() else None,
                "filename":filename_from_url(r.url) or "download",
                "is_hls":is_hls(r.url,c)}

def download(client,url,out,resume=True,name=None,quiet=False):
    info=inspect(client,url)
    dest=out/safe_filename(name or info["filename"])
    out.mkdir(parents=True,exist_ok=True)
    if info["is_hls"]:
        if not ffmpeg_available(): raise RuntimeError("HLS requires FFmpeg.")
        remux(info["final_url"],dest); return dest
    existing=dest.stat().st_size if resume and dest.exists() else 0
    h={}
    if existing: h["Range"]=f"bytes={existing}-"
    with client.get(info["final_url"],stream=True,headers=h) as r:
        if existing and r.status_code != 206:
            existing=0
        r.raise_for_status()
        total=info["content_length"]
        if existing and total: total+=existing
        mode="ab" if existing else "wb"
        done=existing
        with open(dest,mode) as f:
            for chunk in r.iter_content(CHUNK):
                if chunk:
                    f.write(chunk); done+=len(chunk)
                    if not quiet and total:
                        print(f"\r{dest.name}: {done*100/total:6.2f}%",end="",flush=True)
    if not quiet: print()
    return dest

def main(argv=None):
    p=argparse.ArgumentParser(prog="get-sauce")
    p.add_argument("urls",nargs="*")
    p.add_argument("-F","--file")
    p.add_argument("-i","--info",action="store_true")
    p.add_argument("-j","--json",action="store_true")
    p.add_argument("-O","--output",default="downloads")
    p.add_argument("-o","--name")
    p.add_argument("-w","--workers",type=int,default=1)
    p.add_argument("-T","--timeout",type=int,default=30)
    p.add_argument("-H","--header",action="append",default=[])
    p.add_argument("-t","--truncate",action="store_true")
    p.add_argument("-q","--quiet",action="store_true")
    p.add_argument("-v","--version",action="version",version="get-sauce.py 0.2.0")
    a=p.parse_args(argv)
    urls=urls_from(a)
    if not urls: p.error("no URLs supplied")
    if a.workers<1: p.error("workers must be >= 1")
    client=HttpClient(a.timeout,headers(a.header))
    if a.info or a.json:
        data=[]
        for u in urls:
            try: data.append(inspect(client,u))
            except requests.RequestException as e: data.append({"url":u,"error":str(e)})
        print(json.dumps(data,indent=2) if a.json else "\n".join(
            f"{x.get('url')} -> {x.get('final_url','')} | {x.get('content_type','')} | {format_bytes(x.get('content_length'))}"
            for x in data))
        return 0
    out=Path(a.output); resume=not a.truncate
    def one(item):
        i,u=item
        try: return f"[{i}] OK: {download(client,u,out,resume,a.name if len(urls)==1 else None,a.quiet)}"
        except Exception as e: return f"[{i}] ERROR: {u}: {e}"
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for result in ex.map(one,enumerate(urls,1)): print(result)
    return 0
