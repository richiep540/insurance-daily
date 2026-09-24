"""Offline checks for every part of the pipeline that does not need API keys.

Run with:  python tests/test_offline.py
"""
import sys, os, json, datetime, tempfile, xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import generate_episode as g

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}\n   got:  {got!r}\n   want: {want!r}")
    else:
        print(f"  ok  {name}")


print("\n-- config sanity --")
cfg = g.load_config()
hosts = [h["name"] for h in cfg["hosts"]]
check("two hosts", len(hosts), 2)
check("segment words total matches target_word_count",
      sum(s["words"] for s in cfg["segments"]), cfg["target_word_count"])
SLOTS = {"lead", "deep", "headline", "quick"}
slots_used = {x for seg in cfg["segments"] for x in seg["slots"]}
check("segments only use known slots", slots_used - SLOTS, set())
check("every slot has a segment to land in", SLOTS - slots_used, set())
check("every feed has a url", all(f.get("url") for f in cfg["feeds"]), True)
check("audience and editorial brief are set",
      bool(cfg.get("audience")) and bool(cfg.get("editorial_brief")), True)

print("\n-- number/speech normalisation --")
cases = [
    ("It dropped 12% overnight.", "It dropped twelve percent overnight."),
    ("The board costs £320.", "The board costs three hundred and twenty pounds."),
    ("A $1,250 frame.", "A one thousand two hundred and fifty dollars frame."),
    ("He took 3rd in 2026.", "He took third in twenty twenty six."),
    ("29.5 inches of travel.", "twenty nine point five inches of travel."),
    ("Back in 2009 and 2005.", "Back in two thousand and nine and two thousand and five."),
    ("A £2.5m deal.", "A two point five million pounds deal."),
    ("See https://example.com/x now", "See now"),
    ("**bold** and [x] gone", "bold and x gone"),
    ("Burton & Capita", "Burton and Capita"),
    ("140mm travel", "one hundred and forty millimetres travel"),
    ("A 29.5in wheel and 12 kg bike.", "A twenty nine point five inches wheel and twelve kilograms bike."),
    ("Hit 45mph on the 2.4km run.", "Hit forty five miles per hour on the two point four kilometres run."),
    ("Nothing to change here.", "Nothing to change here."),
    ("Turn 900 into words", "Turn nine hundred into words"),
]
for src, want in cases:
    check(repr(src), g.normalize_for_speech(src), want)

print("\n-- number_to_words --")
for n, want in [(0, "zero"), (7, "seven"), (21, "twenty one"), (100, "one hundred"),
                (115, "one hundred and fifteen"), (1000, "one thousand"),
                (1_250_000, "one million two hundred and fifty thousand")]:
    check(f"number_to_words({n})", g.number_to_words(n), want)

print("\n-- triage parsing --")
check("plain json array", g.parse_json_array('[{"index":3,"slot":"lead","why":"x"}]', "t"),
      [{"index": 3, "slot": "lead", "why": "x"}])
check("fenced array", g.parse_json_array('```json\n[{"index":0}]\n```', "t"), [{"index": 0}])
check("non-dict rows dropped", g.parse_json_array('[1,"x",{"index":2}]', "t"), [{"index": 2}])

print("\n-- turn parsing --")
check("fenced json", g.parse_turns('```json\n[{"speaker":"Mackie","text":"Hi"}]\n```', "t"),
      [{"speaker": "Mackie", "text": "Hi"}])
check("prose either side",
      g.parse_turns('Sure!\n[{"speaker":"Tess","text":"Yo"}]\nHope that helps.', "t"),
      [{"speaker": "Tess", "text": "Yo"}])
check("drops empty turns",
      g.parse_turns('[{"speaker":"Tess","text":""},{"speaker":"Tess","text":"A"}]', "t"),
      [{"speaker": "Tess", "text": "A"}])

print("\n-- tts chunking --")
long_text = ("This is a sentence about snowboarding. " * 400).strip()
chunks = g.chunk_text(long_text)
check("all chunks under the byte limit",
      all(len(c.encode()) <= g.TTS_MAX_BYTES for c in chunks), True)
check("nothing dropped", "".join(chunks).replace(" ", ""), long_text.replace(" ", ""))
check("short text stays one chunk", len(g.chunk_text("Just one.")), 1)

print("\n-- interleave --")
check("round robin", g.interleave([[1, 2, 3], ["a"], ["x", "y"]]), [1, "a", "x", 2, "y", 3])

print("\n-- aggregator titles --")
check("google news publisher split",
      g.split_aggregator_title("Chloe Kim wins big air - ESPN", "'q' - Google News"),
      ("Chloe Kim wins big air", "ESPN"))
check("normal feed untouched",
      g.split_aggregator_title("HUF x Spitfire", "Free Skate Magazine"),
      ("HUF x Spitfire", "Free Skate Magazine"))

print("\n-- download tracking prefix --")
check("prefix wraps an absolute url",
      g.tracked_url("https://example.github.io/x/ep.mp3", {"download_prefix": "https://op3.dev/e/"}),
      "https://op3.dev/e/https://example.github.io/x/ep.mp3")
check("no prefix configured leaves the url alone",
      g.tracked_url("https://example.github.io/x/ep.mp3", {}), "https://example.github.io/x/ep.mp3")
check("relative url is never wrapped",
      g.tracked_url("episodes/ep.mp3", {"download_prefix": "https://op3.dev/e/"}), "episodes/ep.mp3")
check("trailing slash on the prefix is not doubled",
      g.tracked_url("https://a/b.mp3", {"download_prefix": "https://op3.dev/e"}),
      "https://op3.dev/e/https://a/b.mp3")

print("\n-- feed.xml / index.html / covered_links --")
tmp = tempfile.mkdtemp(prefix="flatspot-test-")
g.DOCS_DIR, g.FEED_XML = tmp, os.path.join(tmp, "feed.xml")
g.EPISODES_JSON = os.path.join(tmp, "episodes.json")
g.INDEX_HTML = os.path.join(tmp, "index.html")
g.COVERED_JSON = os.path.join(tmp, "covered_links.json")
g.PUBLIC_BASE_URL = "https://example.github.io/insurance-daily"

ep = {
    "title": "9 September 2026 — Insurance Daily",
    "description": 'Ampersands & "quotes" <tags> should not break the XML',
    "pub_date": "Wed, 09 Sep 2026 10:30:00 GMT",
    "audio_url": "https://example.github.io/insurance-daily/episodes/2026-09-09.mp3",
    "file_size": 28311552,
    "duration": "10:24",
    "guid": "insurance-daily-2026-09-09",
}
episodes = g.save_episodes(ep)
g.save_episodes(dict(ep, guid="insurance-daily-2026-09-09"))  # same guid twice
with open(g.EPISODES_JSON) as f:
    check("re-running the same day does not duplicate", len(json.load(f)), 1)

g.write_feed(cfg, episodes)
g.write_index(cfg, episodes)
root = ET.parse(g.FEED_XML).getroot()
check("feed parses as XML", root.tag, "rss")
ch = root.find("channel")
itunes = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
check("channel title", ch.find("title").text, cfg["podcast_title"])
check("itunes:image present",
      ch.find(f"{itunes}image").get("href"),
      "https://example.github.io/insurance-daily/cover.jpg")
check("itunes category", ch.find(f"{itunes}category").get("text"), cfg["podcast_category"])
check("one item", len(ch.findall("item")), 1)
enc = ch.find("item").find("enclosure")
check("enclosure carries the tracking prefix",
      enc.get("url").startswith("https://op3.dev/e/https://"), True)
check("enclosure type", enc.get("type"), "audio/mpeg")
check("enclosure length", enc.get("length"), "28311552")
check("item duration", ch.find("item").find(f"{itunes}duration").text, "10:24")
check("special chars survived escaping", ch.find("item").find("description").text,
      'Ampersands & "quotes" <tags> should not break the XML')
check("index.html written", os.path.exists(g.INDEX_HTML), True)

today = datetime.date.today()
old = (today - datetime.timedelta(days=90)).isoformat()
with open(g.COVERED_JSON, "w") as f:
    json.dump([{"link": "http://old", "date": old}, {"link": "http://keep", "date": today.isoformat()}], f)
g.save_covered(["http://new", "http://keep"], cfg["history_days"])
with open(g.COVERED_JSON) as f:
    links = {r["link"] for r in json.load(f)}
check("prunes stale links", "http://old" in links, False)
check("keeps recent + adds new", links, {"http://keep", "http://new"})

pool = [{"link": "http://a", "title": "A"}]
covered = [{"link": "http://a", "date": today.isoformat()}]
check("falls back rather than returning an empty show",
      [i["link"] for i in g.drop_covered(pool, covered, 5)], ["http://a"])
pool.append({"link": "http://c", "title": "C"})
check("covered story dropped when alternatives exist",
      [i["link"] for i in g.drop_covered(pool, covered, 5)], ["http://c"])

print("\n-- AI disclaimer --")
check("disclaimer is configured", bool(cfg.get("disclaimer_text")), True)
d = cfg["disclaimer_text"]
for phrase in ("AI-generated", "synthetic", "get things wrong", "Verify"):
    check(f"disclaimer says {phrase!r}", phrase in d, True)
spoken = g.normalize_for_speech(d)
check("disclaimer survives speech normalisation intact", spoken.strip() == d.strip(), True)
check("disclaimer is one TTS chunk", len(g.chunk_text(spoken)), 1)
check("show notes disclosure is configured", bool(cfg.get("show_notes_disclosure")), True)

print("\n-- show notes --")
sel = [{"title": "Carrier exits Florida", "source": "Insurance Journal", "slot": "lead", "why": ""},
       {"title": "Broker M&A round-up", "source": "Coverager", "slot": "quick", "why": ""}]
notes = g.write_episode_description(cfg, sel, "Wednesday 9 September 2026")
check("show notes name the lead story and its source",
      "Carrier exits Florida (Insurance Journal)" in notes, True)
check("quick hits land in the Also line", "Also: Broker M&A round-up" in notes, True)
check("show notes carry the AI disclosure", cfg["show_notes_disclosure"] in notes, True)

print("\n-- multi-speaker batching --")
mk = lambda seg, txt: {"speaker": "Mackie", "text": txt, "spoken": txt, "segment": seg}
turns = [mk("open", "word " * 100) for _ in range(10)]
batches = g.batch_turns(turns, 3200)
check("batches respect the byte cap",
      all(sum(len(t["spoken"].encode()) for t in b) <= 3200 for b in batches), True)
check("no turn lost in batching", sum(len(b) for b in batches), len(turns))
mixed = [mk("open", "hello"), mk("open", "again"), mk("skate", "new bit")]
check("batches never straddle a segment",
      [[t["segment"] for t in b] for b in g.batch_turns(mixed, 3200)],
      [["open", "open"], ["skate"]])
check("a single oversized turn still gets its own batch",
      len(g.batch_turns([mk("open", "x" * 9000)], 3200)), 1)

print("\n-- tts config --")
check("engine is known", cfg.get("tts_engine") in ("gemini", "chirp3"), True)
check("every host has a gemini voice",
      all(h.get("gemini_voice") for h in cfg["hosts"]), True)
check("gemini voices are bare names, not Chirp3 ids",
      all("-" not in h["gemini_voice"] for h in cfg["hosts"]), True)
check("style prompt is under the 4000 byte API limit",
      len(cfg["gemini_tts_style_prompt"].encode()) <= 4000, True)
check("batch bytes leave room for the prompt",
      cfg["multispeaker_batch_bytes"] + len(cfg["gemini_tts_style_prompt"].encode()) <= 8000, True)

print("\n-- duration formatting --")
for ms, want in [(1000, "0:01"), (61_000, "1:01"), (624_000, "10:24"), (3_661_000, "1:01:01")]:
    check(f"format_duration({ms})", g.format_duration(ms), want)

print("\n" + ("=" * 60))
if fails:
    print(f"{len(fails)} FAILURE(S):")
    for f_ in fails:
        print(" - " + f_)
    sys.exit(1)
print("All offline checks passed.")
