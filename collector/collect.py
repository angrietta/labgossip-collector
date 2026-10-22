"""LAB GOSSIP 수집기 (B안: AI 없음)

매일 실행: RSS는 최근 수십 건만 담고 있어서(ScienceDaily 전체 피드 = 약 5일치) 매일 모아 data/pool.json에 쌓는다.
보드는 쌓인 것 중 최근 8일치로 매일 다시 만든다. '주(WEEK)'는 그 주 월요일 날짜.

RSS 수집 → 최근 기사만 → 같은 소식 묶기(재게재 감지) → 키워드 점수 → 상위 40개
→ 상위 40개는 원문 페이지를 받아 '숫자가 들어간 문장'과 DOI를 그대로 저장
→ docs/index.html(보드), docs/latest.md(Claude가 읽는 요약), data/weeks/<날짜>.json(원문 포함 전체)

실행:  python collector/collect.py
테스트: FIXTURES=tests/fixtures python collector/collect.py   (인터넷 없이 가짜 데이터로)
"""
import os, re, json, html, hashlib, datetime as dt, time
from urllib.parse import urlsplit, urlunsplit

import feedparser, requests
from bs4 import BeautifulSoup

import rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.environ.get("FIXTURES")
KST = dt.timezone(dt.timedelta(hours=9))
NOW = dt.datetime.now(KST)
WEEK = os.environ.get("WEEK_DATE") or (NOW - dt.timedelta(days=NOW.weekday())).strftime("%Y-%m-%d")   # 이번 주 월요일
TODAY = NOW.strftime("%Y-%m-%d")
POOL_DAYS = 30
UA = {"User-Agent": "Mozilla/5.0 (LAB GOSSIP weekly collector; personal research digest)"}

STOP = set("a an the of in on for to and or with by from at as is are was were be been new study shows show "
           "finds find found researchers scientists could may might can how why what that this these those "
           "its it their into about than more most over after".split())

# ---------------------------------------------------------------- fetching
def get(url, timeout=25):
    """Return text or raise. In test mode, read from fixtures instead of the internet."""
    if FIX:
        p = os.path.join(FIX, hashlib.sha1(url.encode()).hexdigest()[:12] + ".txt")
        if not os.path.exists(p):
            raise IOError("no fixture")
        return open(p, encoding="utf-8").read()
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    try:
        return r.content.decode("utf-8")
    except UnicodeDecodeError:
        return r.content.decode(r.apparent_encoding or "latin-1", errors="replace")

def load_feeds():
    out = []
    for line in open(os.path.join(ROOT, "feeds.txt"), encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        name, url = [x.strip() for x in line.split("|", 1)]
        out.append((name, url))
    return out

def clean(s):
    s = BeautifulSoup(s or "", "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def norm_link(u):
    p = urlsplit(u)
    return urlunsplit((p.scheme, p.netloc.lower().replace("www.", ""), p.path.rstrip("/"), "", ""))

def collect_feeds():
    items, status = [], []
    for name, url in load_feeds():
        try:
            fp = feedparser.parse(get(url))
            n_all = len(fp.entries)
            if n_all == 0:
                raise ValueError("항목 0개 (주소 확인 필요)")
            dates = []
            for e in fp.entries:
                t = e.get("published_parsed") or e.get("updated_parsed")
                when = dt.datetime(*t[:6], tzinfo=dt.timezone.utc).astimezone(KST) if t else None
                if when: dates.append(when)
                link = e.get("link", "")
                items.append({"title": clean(e.get("title")), "link": link, "key": norm_link(link),
                              "summary": clean(e.get("summary") or e.get("description"))[:700],
                              "date": when.strftime("%Y-%m-%d") if when else TODAY, "source": name})
            span = (max(dates) - min(dates)).days + 1 if dates else None
            status.append({"feed": name, "url": url, "ok": True, "items": n_all, "span_days": span})
        except Exception as ex:
            status.append({"feed": name, "url": url, "ok": False, "error": str(ex)[:160]})
        time.sleep(0 if FIX else 1)
    return items, status

# ---------------------------------------------------------------- grouping (same story, several outlets)
def tokens(title):
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in STOP and len(w) > 2}

def group(items):
    groups = []
    for it in items:
        tk = tokens(it["title"])
        for g in groups:
            if it["key"] == g["key"] or (tk and len(tk & g["_tk"]) / len(tk | g["_tk"]) >= 0.5):
                if it["source"] not in g["sources"]:
                    g["sources"].append(it["source"]); g["links"].append(it["link"])
                if len(it["summary"]) > len(g["summary"]):
                    g["summary"] = it["summary"]
                g["date"] = min(filter(None, [g["date"], it["date"]]), default="")
                break
        else:
            groups.append(dict(it, sources=[it["source"]], links=[it["link"]], _tk=tk))
    for g in groups:
        g.pop("_tk")
    return groups

# ---------------------------------------------------------------- scoring
def hits(text, words):   # match at the start of a word: "cat" must not hit "indicate", "aging" not "imaging"
    return [w for w in words if re.search(r"\b" + re.escape(w), text)]

def score(g, seen):
    text = (g["title"] + " " + g["summary"]).lower()
    s, why = 0, []
    fmt = {k: len(hits(text, v)) for k, v in rules.FORMATS.items()}
    best = max(fmt, key=fmt.get)
    g["format"] = best if fmt[best] else ""
    if fmt[best]:
        s += 2 + min(fmt[best], 3); why.append(f"형식 {best}")
    h = hits(text, rules.HOOK)
    if h:
        s += min(2 * len(h), 6); why.append("훅: " + ", ".join(h[:3]))
    r = hits(text, rules.RELATABLE)
    if r:
        s += min(len(r), 4); why.append("생활소재: " + ", ".join(r[:3]))
    if re.search(r"\d", g["summary"]):
        s += 1
    if len(g["sources"]) > 1:
        s += 2; why.append(f"{len(g['sources'])}곳 보도")
    if hits(text, rules.PENALTY_HARD):
        s -= 8; why.append("홍보성 글")
    soft = hits(text, rules.PENALTY_SOFT)
    if soft:
        s -= 3; why.append("시각화 어려움: " + soft[0])
    prev = seen.get(g["key"]) or seen.get(" ".join(sorted(tokens(g["title"]))))
    if prev and prev != WEEK:      # re-running the same week must not flag its own items
        g["seen"] = prev
        s -= 4; why.append(f"이미 본 소재({prev})")
    g["catch"] = catches(text)
    g["score"], g["why"] = s, why
    return g

def catches(text):
    c = [k for k, v in rules.CATCH_SIGNS.items() if hits(text, v)]
    t = text
    for x in rules.NOT_ANIMAL:          # "fish oil" is not a fish study
        t = t.replace(x, " ")
    if hits(t, rules.ANIMALS) and not hits(t, rules.HUMANS):
        c.insert(0, "동물 실험")
    return c

# ---------------------------------------------------------------- article details (top N only)
NUMWORD = r"\b(twice|double[ds]?|half|tripl\w*|quarter|third|percent|fold|times)\b"
SAMPLE = re.compile(r"\b(\d+(?:,\d{3})*)\s+(?:healthy\s+|older\s+|young\s+)?(adults?|participants?|people|patients?|volunteers?|"
                    r"women|men|children|students|mice|rats|subjects|individuals|infants|babies|dogs|chicks|fish|birds)\b", re.I)
DOI = re.compile(r"\b10\.\d{4,9}/[^\s\"'<>,;()]+[^\s\"'<>,;().]")

def article(g):
    try:
        soup = BeautifulSoup(get(g["link"]), "html.parser")
    except Exception as ex:
        g["fetch_error"] = str(ex)[:120]
        return g
    for t in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        t.decompose()
    box = soup.select_one("#story_text, #text, article, .article-main, .entry-content, main") or soup
    paras = [re.sub(r"\s+", " ", p.get_text(" ")).strip() for p in box.find_all("p")]
    body = " ".join(p for p in paras if len(p) > 60)[:15000]
    full = soup.get_text(" ")
    g["text"] = body[:8000]
    dois = sorted(set(d.rstrip(".") for d in DOI.findall(full)))
    g["doi"] = dois[:3]
    jr = soup.select_one("#journal_references, .journal-references, .article-journal")
    if jr:
        g["journal_ref"] = re.sub(r"\s+", " ", jr.get_text(" ")).strip()[:400]
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", body)
    facts = []
    for x in sents:
        if (re.search(r"\d", x) or re.search(NUMWORD, x, re.I)) and 30 < len(x) < 400 and x not in facts:
            facts.append(x)
    g["facts"] = facts[:10]
    g["sample"] = sorted({f"{m.group(1)} {m.group(2).lower()}" for m in SAMPLE.finditer(body)})[:4]
    if not g["doi"]:
        g["catch"].append("DOI 못 찾음")
    return g

# ---------------------------------------------------------------- output
def pick(groups):
    out, per = [], {}
    for g in sorted(groups, key=lambda x: -x["score"]):
        if g["score"] < rules.MIN_SCORE:
            break
        src = g["sources"][0]
        if per.get(src, 0) >= rules.SOURCE_CAP:
            continue
        per[src] = per.get(src, 0) + 1
        out.append(g)
        if len(out) >= rules.TOP_N:
            break
    return out

def write_md(top, status, path):
    L = [f"# LAB GOSSIP 후보 {WEEK}", "",
         f"최근 {rules.DAYS}일 누적 {N_WINDOW}건 → 상위 {len(top)}건 (AI 없이 키워드 점수). "
         "숫자 문장은 원문에서 글자 그대로 가져온 것.", ""]
    bad = [s["feed"] for s in status if not s["ok"]]
    if bad:
        L += [f"수집 실패 피드: {', '.join(bad)}", ""]
    for i, g in enumerate(top, 1):
        L.append(f"## {i}. {g['title']}")
        meta = [f"점수 {g['score']}", g["format"] or "형식?", " / ".join(g["sources"]), g["date"]]
        L.append("- " + " · ".join(x for x in meta if x))
        L.append(f"- {g['link']}")
        if g.get("doi"): L.append(f"- DOI: {', '.join(g['doi'])}")
        if g.get("sample"): L.append(f"- 대상: {', '.join(g['sample'])}")
        if g["catch"]: L.append(f"- 주의: {', '.join(g['catch'])}")
        if g.get("seen"): L.append(f"- 이미 본 소재: {g['seen']} 보드에 있었음")
        if g.get("fetch_error"): L.append("- 원문 페이지를 못 받음 (요약만 있음)")
        L.append(f"- 요약: {g['summary'][:300]}")
        for f in g.get("facts", [])[:5]:
            L.append(f"  - \"{f}\"")
        L.append("")
    open(path, "w", encoding="utf-8").write("\n".join(L))

def write_board(top, status, weeks, path):
    tpl = open(os.path.join(ROOT, "collector", "board.html"), encoding="utf-8").read()
    slim = [{k: v for k, v in g.items() if k != "text"} for g in top]
    data = json.dumps({"week": WEEK, "items": slim, "status": status, "weeks": weeks,
                       "total": N_WINDOW, "updated": NOW.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False)
    open(path, "w", encoding="utf-8").write(tpl.replace("/*DATA*/null", data.replace("</", "<\\/")))

N_WINDOW = 0

def main():
    global N_WINDOW
    os.makedirs(os.path.join(ROOT, "data", "weeks"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "docs", "weeks"), exist_ok=True)
    jp = lambda *a: os.path.join(ROOT, "data", *a)
    load = lambda p, d: json.load(open(p, encoding="utf-8")) if os.path.exists(p) else d
    seen, pool = load(jp("seen.json"), {}), load(jp("pool.json"), {})

    # 1) today's feeds -> pool (keeps everything for 30 days)
    items, status = collect_feeds()
    added = 0
    for it in items:
        if it["key"] not in pool:
            pool[it["key"]] = dict(it, first_seen=TODAY); added += 1
    cut_pool = (NOW - dt.timedelta(days=POOL_DAYS)).strftime("%Y-%m-%d")
    pool = {k: v for k, v in pool.items() if v["date"] >= cut_pool}

    # 2) last 8 days from the pool -> group, score, pick
    cut = (NOW - dt.timedelta(days=rules.DAYS)).strftime("%Y-%m-%d")
    window = [dict(v) for v in pool.values() if v["date"] >= cut]
    N_WINDOW = len(window)
    groups = [score(g, seen) for g in group(window)]
    top = pick(groups)

    # 3) article details (cached in the pool so each page is fetched once)
    for g in top:
        cached = pool.get(g["key"], {})
        if "facts" in cached or "fetch_error" in cached:
            for k in ("text", "facts", "doi", "sample", "journal_ref", "fetch_error"):
                if k in cached: g[k] = cached[k]
            g["catch"] += [c for c in cached.get("catch_extra", []) if c not in g["catch"]]
        else:
            before = list(g["catch"])
            article(g)
            for k in ("text", "facts", "doi", "sample", "journal_ref", "fetch_error"):
                if k in g: cached[k] = g[k]
            cached["catch_extra"] = [c for c in g["catch"] if c not in before]
            time.sleep(0 if FIX else 1)

    json.dump(pool, open(jp("pool.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"week": WEEK, "updated": TODAY, "status": status, "top": top},
              open(jp("weeks", f"{WEEK}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for g in top:                                   # remember what was shown, to flag old news in later weeks
        seen.setdefault(g["key"], WEEK); seen.setdefault(" ".join(sorted(tokens(g["title"]))), WEEK)
    json.dump(seen, open(jp("seen.json"), "w", encoding="utf-8"), ensure_ascii=False)

    weeks = sorted((f[:-5] for f in os.listdir(jp("weeks")) if f.endswith(".json")), reverse=True)
    write_md(top, status, os.path.join(ROOT, "docs", "latest.md"))
    write_md(top, status, os.path.join(ROOT, "docs", "weeks", f"{WEEK}.md"))
    write_board(top, status, weeks, os.path.join(ROOT, "docs", "index.html"))
    write_board(top, status, weeks, os.path.join(ROOT, "docs", "weeks", f"{WEEK}.html"))
    ok = sum(s["ok"] for s in status)
    print(f"[{TODAY} / week {WEEK}] feeds ok {ok}/{len(status)}, new {added}, pool {len(pool)}, "
          f"last {rules.DAYS} days {N_WINDOW}, stories {len(groups)}, top {len(top)}")
    for s in status:
        print(("  OK  " if s["ok"] else "  FAIL") + f" {s['feed']}: " +
              (f"{s['items']} items, covers {s['span_days']} days" if s["ok"] else s["error"]))

if __name__ == "__main__":
    main()
