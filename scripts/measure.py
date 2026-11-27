import collections, json, re
from pathlib import Path

ROOT = Path('/workspace/JDhe'); SRC = ROOT/'src'
CJK = re.compile(r'^[\u3400-\u9fff]$'); ALPHA = re.compile(r'^[a-z]{1,6}$')

entries = collections.defaultdict(list)
for ln in (SRC/'jde.dict.yaml').read_text().splitlines():
    p = ln.split('\t')
    if len(p) < 3 or not CJK.match(p[0]) or not ALPHA.match(p[1]): continue
    try: w = int(float(p[2]))
    except ValueError: continue
    if w > 0: entries[p[0]].append((w, p[1]))

freq, fullpinyin = {}, {}
for ch, items in entries.items():
    top = max(w for w, _ in items)
    freq[ch] = top
    fullpinyin[ch] = max((c for w, c in items if w == top), key=len)

yin4, yinshort = collections.defaultdict(set), collections.defaultdict(set)
for ln in (SRC/'jdh_dict_multi.txt').read_text().splitlines():
    p = ln.split('\t')
    if len(p) < 2 or not re.fullmatch(r'[a-z]{1,4}', p[0]): continue
    for w in p[1].split():
        if CJK.match(w):
            (yin4 if len(p[0]) == 4 else yinshort)[w].add(p[0])

def t9(py):
    tbl = {}
    for d, ls in [('2','abc'),('3','def'),('4','ghi'),('5','jkl'),('6','mno'),('7','pqrs'),('8','tuv'),('9','wxyz')]:
        for L in ls: tbl[L] = d
    return ''.join(tbl.get(c,c) for c in py)

def evaluate(mapping, chars):
    buckets = collections.defaultdict(set)
    for ch in chars:
        for c in mapping.get(ch, ()): buckets[c].add(ch)
    total=hit1=rank_sum=wlen=0.0
    for ch in chars:
        w = freq.get(ch,0)
        codes = [c for c in mapping.get(ch,()) if buckets.get(c)]
        if not w or not codes: continue
        best=None
        for c in codes:
            peers = sorted(buckets[c], key=lambda x:-freq.get(x,0))
            r = peers.index(ch)+1
            if best is None or (r,len(c)) < best: best=(r,len(c))
        r,ln = best
        total += w; rank_sum += w*r; wlen += w*ln
        if r==1: hit1 += w
    multi=[v for v in buckets.values() if len(v)>1]
    return dict(acc=hit1/total*100, mean_rank=rank_sum/total, code_len=wlen/total,
                codes=len(buckets), collision_codes=len(multi), collision_extra=sum(len(v)-1 for v in multi))

ordered=[c for c,_ in sorted(freq.items(), key=lambda kv:-kv[1])]
tiers=[('前1500',ordered[:1500]),('前3000',ordered[:3000]),('前4000',ordered[:4000])]
schemes={
 '简单鹤': {c: yin4.get(c,set()) for c in ordered},
 '简单鹤出简': {c: yin4.get(c,set())|yinshort.get(c,set()) for c in ordered},
 '全拼26键': {c: ({fullpinyin[c]} if c in fullpinyin else set()) for c in ordered},
 '全拼9键': {c: ({t9(fullpinyin[c])} if c in fullpinyin else set()) for c in ordered},
}
out={}
for name, mp in schemes.items():
    out[name]=[]
    print(f'== {name} ==')
    for label, chars in tiers:
        r=evaluate(mp, chars); r['tier']=label; r['n']=len(chars)
        out[name].append(r)
        print(f"  {label:7s} 首选 {r['acc']:5.2f}%  平均位次 {r['mean_rank']:.3f}  码长 {r['code_len']:.2f}  "
              f"重码码位 {r['collision_codes']:4d}  多出 {r['collision_extra']:4d} 字")
(ROOT/'metrics.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print('\nwritten metrics.json')
