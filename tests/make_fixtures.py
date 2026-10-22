"""인터넷 없이 수집기 전체 흐름을 시험하기 위한 가짜 RSS/기사 페이지 생성."""
import os, hashlib, datetime as dt, sys
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
now = dt.datetime.now(dt.timezone.utc)
def rfc(days): return (now - dt.timedelta(days=days)).strftime("%a, %d %b %Y %H:%M:%S +0000")
def save(url, text):
    open(os.path.join(OUT, hashlib.sha1(url.encode()).hexdigest()[:12] + ".txt"), "w", encoding="utf-8").write(text)

SD = "https://www.sciencedaily.com/releases/2026/10/"
stories = {  # feed url -> [(title, link, summary, days_ago)]
 "https://www.sciencedaily.com/rss/all.xml": [
  ("Alzheimer's plaques stayed, but sleep came back in mice", SD + "261014.htm",
   "Removing most brain immune cells restored more than two hours of sleep per day in an Alzheimer's mouse model, even though plaques were not cleared.", 2),
  ("Baby birds carrying tiny backpacks burn more energy later", SD + "261015.htm",
   "Guinea fowl chicks raised without added weight used 23% more energy when given the same load, a surprising result.", 3),
  ("University announces new grant for quantum materials center", SD + "261016.htm",
   "The center will receive funding to study perovskite and quantum lattice materials.", 1),
  ("A 1960 doomsday prediction says the world ends in November 2026", SD + "261017.htm",
   "A famous Science paper projected population would go to infinity on Friday, November 13, 2026.", 4),
  ("Old story from last month about coffee", SD + "260901.htm", "Coffee and memory.", 40),
 ],
 "https://www.sciencedaily.com/rss/strange_offbeat.xml": [
  ("Psilocybin calms aggressive mangrove fish", SD + "261018.htm",
   "A low dose of psilocybin reduced aggression in mangrove rivulus fish within 20 minutes.", 2),
 ],
 "https://phys.org/rss-feed/": [
  ("Baby birds carrying tiny backpacks burn more energy later in life", "https://phys.org/news/2026-10-baby-birds.html",
   "Chicks raised without weights used 23% more energy carrying the same load.", 3),
  ("New catalyst improves semiconductor electrolyte stability", "https://phys.org/news/2026-10-catalyst.html",
   "A polymer catalyst for batteries.", 2),
 ],
 "https://medicalxpress.com/rss-feed/": [
  ("Blueberries did not lift mood in older adults, trial finds", "https://medicalxpress.com/news/2026-10-blueberries.html",
   "In 18 adults aged 65 and over, 48 g of blueberry powder for three months versus placebo made no difference to mood.", 5),
 ],
}
for feed, items in stories.items():
    xml = "".join(f"<item><title>{t}</title><link>{l}</link><description>{s}</description><pubDate>{rfc(d)}</pubDate></item>"
                  for t, l, s, d in items)
    save(feed, f'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>{xml}</channel></rss>')
save("https://www.eurekalert.org/rss.xml", "<html>404 not found</html>")   # a dead feed

save(SD + "261014.htm", """<html><body><nav>menu 123</nav><div id="story_text">
<p>Researchers at the University of Kentucky gave an Alzheimer's mouse model a drug in their food for 14 days, which depleted about 87% of microglia in the brain.</p>
<p>The treatment restored more than two hours of sleep per day, yet the amyloid plaques were not cleared, the team reported in the journal.</p>
<p>The findings are in mice and have not been tested in people, the authors cautioned in their statement to reporters.</p></div>
<div id="journal_references">Journal Reference: Alzheimer's &amp; Dementia, 2026; DOI: 10.1002/alz.71579</div></body></html>""")
save(SD + "261015.htm", """<html><body><div id="story_text">
<p>Twelve guinea fowl chicks wore weights equal to 4% of body mass as they grew up on the research farm in the study.</p>
<p>Birds raised without the weights used 23% more energy when they later carried the same load, the scientists measured.</p>
</div><div id="journal_references">Proceedings of the Royal Society B, 2026. DOI: 10.1098/rspb.2026.0199</div></body></html>""")
print("fixtures ->", OUT)
