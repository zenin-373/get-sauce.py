import sys
def show(done, total, label):
    if total:
        pct=min(100, done*100/total)
        msg=f"\r{label}: {pct:6.2f}%"
    else:
        msg=f"\r{label}: {done:,} bytes"
    print(msg,end="",flush=True)
def finish():
    print(file=sys.stdout)
