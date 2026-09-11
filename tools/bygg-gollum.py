#!/usr/bin/env python3
"""Bygger Gollum-testet som statisk sajt.

Logiken och texterna är extraherade ur den gamla Next-appen med
extrahera-gollum.mjs och ligger i gollum-data.json. Gränssnittet är byggt
i den nya designen.

Skapar:
  site/gollum/index.html            quizen, hanterar även ?r=<slug>
  site/gollum/<arketyp>.html        fyra delbara resultatsidor med egen metadata
"""

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "https://opensverige.se"
DISCORD = "https://discord.gg/ZbV4qB34um"

DATA = json.loads((ROOT / "tools" / "gollum-data.json").read_text(encoding="utf-8"))

ARKETYPER = ["gollum", "dreambuilder", "speedrunner", "shipper"]

# Metadata per resultat, från gamla sajtens RESULT_META
RESULTAT_META = {
    "gollum": {
        "titel": "Du är Gollum — Gollum-testet",
        "beskrivning": "Du hoardar koden, låter AI:n validera varje beslut och vägrar exponera det du bygger. Din precious håller dig fast i dopaminloopen.",
    },
    "dreambuilder": {
        "titel": "Du är Drömbyggaren — Gollum-testet",
        "beskrivning": "Episka roadmaps, briljanta idéer — men ingenting shippat. Du planerar som en gud och levererar som ett spöke. Dags att deploya.",
    },
    "speedrunner": {
        "titel": "Du är Speedrunnern — Gollum-testet",
        "beskrivning": "Du shippar snabbt men har outsourcat tänkandet till din AI. Velocity utan förståelse. Kan du förklara rad 47 utan att fråga din copilot?",
    },
    "shipper": {
        "titel": "Du är Shipparen — Gollum-testet",
        "beskrivning": "Du söker friktion, inte bekräftelse. Bygger, exponerar och validerar med riktiga människor. Du är den andra behöver lära av.",
    },
}

CSS = """
:root{--bg:#fbfaf7;--surface:#fff;--ink:#151515;--body:#2b2724;--muted:#5b5651;--faint:#918b83;--hair:#e4e2dc;
--accent:#b72c07;--discord:#5865F2;
--sans:'Familjen Grotesk',-apple-system,Helvetica,sans-serif;--mono:'JetBrains Mono',ui-monospace,monospace;--serif:'Instrument Serif',Georgia,serif;
--snap:cubic-bezier(.16,1,.3,1);--t:150ms var(--snap)}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased;
  min-height:100vh;display:flex;flex-direction:column}
img{max-width:100%;display:block}a{color:inherit}
::selection{background:var(--accent);color:#fff}
.wrap{width:100%;max-width:520px;margin:0 auto;padding:0 20px;flex:1;display:flex;flex-direction:column}

.qtop{display:flex;align-items:center;gap:10px;height:52px;border-bottom:1px solid var(--hair);margin-bottom:0}
.qtop .bk{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
  text-decoration:none;transition:color var(--t)}
.qtop .bk:hover{color:var(--accent)}
.qtop .sp{margin-left:auto;display:flex;gap:6px}
.lang{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint);
  background:none;border:1px solid var(--hair);border-radius:2px;padding:4px 8px;cursor:pointer;transition:all var(--t)}
.lang:hover{border-color:var(--ink);color:var(--ink)}

.bar{height:2px;background:var(--hair);margin-top:0}
.bar i{display:block;height:100%;width:0;background:var(--accent);transition:width 280ms var(--snap)}

.scr{flex:1;display:flex;flex-direction:column;justify-content:center;padding:36px 0 56px;gap:0}
.scr.top{justify-content:flex-start;padding-top:30px}

.hero{width:150px;height:150px;border-radius:14px;object-fit:cover;margin:0 auto 26px;
  border:1px solid var(--hair)}
h1{font-size:clamp(30px,8vw,44px);font-weight:600;letter-spacing:-.04em;line-height:1.05;text-align:center}
.sub{font-size:17.5px;line-height:1.5;color:var(--muted);text-align:center;margin-top:16px;max-width:34ch;
  margin-left:auto;margin-right:auto}
.fine{font-family:var(--mono);font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--faint);
  text-align:center;margin-top:20px}
.big{display:block;width:100%;margin-top:26px;height:52px;border:0;border-radius:3px;background:var(--ink);color:#fff;
  font-family:var(--sans);font-size:16px;font-weight:600;cursor:pointer;transition:background var(--t)}
.big:hover{background:var(--accent)}

.qnum{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
.qtx{font-size:22px;font-weight:600;letter-spacing:-.03em;line-height:1.25;margin-top:12px}
@media(min-width:640px){.qtx{font-size:25px}}
.svar{display:flex;flex-direction:column;gap:9px;margin-top:26px}
.svar button{display:flex;align-items:flex-start;gap:11px;width:100%;padding:14px 15px;border:1px solid var(--hair);
  border-radius:3px;background:var(--surface);color:var(--body);font-family:var(--sans);font-size:16px;
  line-height:1.4;text-align:left;cursor:pointer;transition:all var(--t)}
.svar button:hover{border-color:var(--ink);color:var(--ink);transform:translateX(2px)}
.svar .id{font-family:var(--mono);font-size:11px;color:var(--faint);padding-top:3px;flex:none}
.svar button:hover .id{color:var(--accent)}
.tillbaka{align-self:flex-start;margin-top:20px;background:none;border:0;padding:0;cursor:pointer;
  font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}
.tillbaka:hover{color:var(--accent)}

.rem{font-size:44px;line-height:1;text-align:center}
.rnamn{font-size:clamp(28px,7.4vw,40px);font-weight:600;letter-spacing:-.04em;line-height:1.06;text-align:center;margin-top:14px}
.rhead{font-family:var(--serif);font-size:23px;line-height:1.3;text-align:center;color:var(--accent);margin-top:14px}
@media(min-width:640px){.rhead{font-size:26px}}
.rbild{width:100%;border-radius:4px;margin-top:24px;border:1px solid var(--hair)}
.rbody{font-size:17px;line-height:1.62;color:var(--body);margin-top:24px}
.recept{margin-top:22px;padding:17px;border:1px solid var(--hair);border-left:2px solid var(--accent);
  border-radius:2px;background:#fdfcfa}
.recept .l{font-family:var(--mono);font-size:9.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin-bottom:8px}
.recept p{font-size:16.5px;line-height:1.55;color:var(--ink)}

.sekt{margin-top:34px}
.sekt .sl{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint);
  padding-bottom:9px;border-bottom:1px solid var(--hair)}
.spegel{font-size:15.5px;line-height:1.55;color:var(--body);padding:13px 0;border-bottom:1px solid var(--hair)}
.spegel:last-child{border-bottom:0}
.kombo{font-size:15px;line-height:1.55;color:var(--body);padding:13px 0 13px 13px;border-left:2px solid var(--accent);
  margin-top:11px;background:#fdfcfa}

.dela{display:flex;gap:8px;margin-top:26px;flex-wrap:wrap}
.dela a,.dela button{display:inline-flex;align-items:center;justify-content:center;gap:7px;height:40px;padding:0 14px;
  border:1px solid var(--hair);border-radius:3px;background:var(--surface);color:var(--ink);font-family:var(--sans);
  font-size:14px;font-weight:600;text-decoration:none;cursor:pointer;transition:all var(--t)}
.dela a:hover,.dela button:hover{border-color:var(--ink)}
.dbtn{display:inline-flex;align-items:center;justify-content:center;gap:8px;width:100%;height:48px;margin-top:26px;
  border-radius:3px;background:var(--discord);color:#fff;font-size:15.5px;font-weight:600;text-decoration:none;
  transition:background var(--t)}
.dbtn:hover{background:#4752c4}
.dbtn svg{width:18px;height:18px;fill:currentColor}
.dsub{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;color:var(--faint);text-align:center;margin-top:9px}
.omstart{display:block;margin:22px auto 0;background:none;border:0;padding:0;cursor:pointer;
  font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}
.omstart:hover{color:var(--accent)}

.qfoot{border-top:1px solid var(--hair);padding:13px 0;display:flex;justify-content:space-between;gap:10px;
  font-family:var(--mono);font-size:10px;letter-spacing:.05em;color:var(--faint)}
.qfoot a{text-decoration:none;color:var(--faint);transition:color var(--t)}
.qfoot a:hover{color:var(--accent)}
.gomd{display:none}
"""

DISCORD_SVG = (
    '<svg viewBox="0 0 127 96"><path d="M107.7 8.07A105.15 105.15 0 0 0 81.47 0a72.06 '
    "72.06 0 0 0-3.36 6.83 97.68 97.68 0 0 0-29.11 0A72.37 72.37 0 0 0 45.64 0a105.89 "
    "105.89 0 0 0-26.25 8.09C2.79 32.65-1.71 56.6.54 80.21a105.73 105.73 0 0 0 32.17 "
    "16.15 77.7 77.7 0 0 0 6.89-11.11 68.42 68.42 0 0 1-10.85-5.18c.91-.66 1.8-1.34 "
    "2.66-2a75.57 75.57 0 0 0 64.32 0c.87.71 1.76 1.39 2.66 2a68.68 68.68 0 0 "
    "1-10.87 5.19 77 77 0 0 0 6.89 11.1 105.25 105.25 0 0 0 "
    "32.19-16.14c2.64-27.38-4.51-51.11-18.9-72.15ZM42.45 65.69C36.18 65.69 31 60 31 "
    "53s5-12.74 11.43-12.74S54 46 53.89 53s-5.05 12.69-11.44 12.69Zm42.24 0C78.41 "
    "65.69 73.25 60 73.25 53s5-12.74 11.44-12.74S96.23 46 96.12 53s-5.04 12.69-11.43 "
    '12.69Z"/></svg>'
)


def head(sokvag, titel, beskrivning, og_bild, extra_ld=None):
    url = BASE + sokvag
    b = html.escape(beskrivning, quote=True)
    t = html.escape(titel, quote=True)
    ld = json.dumps(extra_ld, ensure_ascii=False, indent=2) if extra_ld else None
    ld_tagg = (
        f'<script type="application/ld+json">\n{ld}\n</script>\n' if ld else ""
    )
    return f"""<!doctype html><html lang="sv"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{t}</title>
<meta name="description" content="{b}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="theme-color" content="#fbfaf7">
<meta name="author" content="opensverige">
<meta property="og:type" content="website">
<meta property="og:site_name" content="opensverige">
<meta property="og:locale" content="sv_SE">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{b}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}{og_bild}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{b}">
<meta name="twitter:image" content="{BASE}{og_bild}">
<link rel="icon" href="/favicon/favicon.ico" sizes="32x32">
<link rel="icon" type="image/png" href="/favicon/favicon-96x96.png" sizes="96x96">
<link rel="apple-touch-icon" href="/favicon/apple-touch-icon.png">
<link rel="manifest" href="/favicon/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:ital,wght@0,400..700;1,400..700&family=JetBrains+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<style>{CSS}</style>
{ld_tagg}</head><body>"""


def fot(hoger='<a href="/">opensverige →</a>'):
    return f"""
<div class="wrap">
  <div class="qfoot"><span>gollum-testet v1.0</span>{hoger}</div>
</div>
</body></html>
"""


# ------------------------------------------------------------------ quizen

def bygg_quiz():
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Quiz",
                "@id": f"{BASE}/gollum#quiz",
                "name": "Gollum-testet",
                "description": "Tio frågor som avgör om du faktiskt bygger och shippar, eller sitter fast i AI:ns dopaminloop och hoardar din kod.",
                "url": f"{BASE}/gollum",
                "inLanguage": ["sv-SE", "en"],
                "educationalLevel": "beginner",
                "numberOfQuestions": len(DATA["QUESTIONS"]),
                "about": {"@id": f"{BASE}/#organization"},
                "publisher": {"@id": f"{BASE}/#organization"},
                "timeRequired": "PT90S",
                "isAccessibleForFree": True,
            },
            {
                "@type": "WebPage",
                "@id": f"{BASE}/gollum#webpage",
                "url": f"{BASE}/gollum",
                "name": "Gollum-testet — Är du Gollum?",
                "inLanguage": "sv-SE",
                "isPartOf": {"@id": f"{BASE}/#website"},
                "primaryImageOfPage": {
                    "@type": "ImageObject",
                    "url": f"{BASE}/assets/og-gollum.jpg",
                    "width": 1200,
                    "height": 630,
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{BASE}/gollum#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Start", "item": f"{BASE}/"},
                    {"@type": "ListItem", "position": 2, "name": "Gollum-testet", "item": f"{BASE}/gollum"},
                ],
            },
        ],
    }

    # Kombinationerna behåller sin ursprungliga check-logik
    kombos = ",\n".join(
        "  {id:%s, bonusShip:%d, bonusAiDep:%d, callout:%s, check:%s}"
        % (
            json.dumps(k["id"]),
            k["bonusShip"],
            k["bonusAiDep"],
            json.dumps(k["callout"], ensure_ascii=False),
            k["check"],
        )
        for k in DATA["COMBOS"]
    )

    data_js = f"""
const QUESTIONS = {json.dumps(DATA["QUESTIONS"], ensure_ascii=False)};
const RESULTS = {json.dumps(DATA["RESULTS"], ensure_ascii=False)};
const MIRROR_MAP = {json.dumps(DATA["MIRROR_MAP"], ensure_ascii=False)};
const PRIORITY_ORDER = {json.dumps(DATA["PRIORITY_ORDER"], ensure_ascii=False)};
const COMBOS = [
{kombos}
];
const BILD = {{gollum:'/assets/gollum-gollum.webp',dreambuilder:'/assets/gollum-dreambuilder.webp',
  speedrunner:'/assets/gollum-speedrunner.webp',shipper:'/assets/gollum-shipper.webp'}};
"""

    logik_js = """
const COPY = {
  heading:{sv:'Är du Gollum?',en:'Are you Gollum?'},
  sub:{sv:'Tio frågor. Brutalt ärliga svar. Ta reda på om du bygger — eller bara hoardar.',
       en:"Ten questions. Brutally honest answers. Find out if you're building — or just hoarding."},
  cta:{sv:'Starta testet',en:'Take the test'},
  fine:{sv:'Tar 90 sekunder. Inga email. Ingen bullshit.',en:'Takes 90 seconds. No email. No bullshit.'},
  back:{sv:'← Tillbaka',en:'← Back'},
  spegel:{sv:'Spegeln',en:'The mirror'},
  kombo:{sv:'Mönster vi såg',en:'Patterns we saw'},
  recept:{sv:'Receptet',en:'The fix'},
  dela:{sv:'Dela',en:'Share'},
  kopiera:{sv:'Kopiera länk',en:'Copy link'},
  kopierad:{sv:'Kopierad',en:'Copied'},
  discord:{sv:'Gå med i Discord',en:'Join the Discord'},
  discordSub:{sv:'600+ builders som faktiskt shippar & failar',en:'600+ builders who actually ship & fail'},
  omstart:{sv:'Gör om testet',en:'Retake the test'},
  fraga:{sv:'Fråga',en:'Question'}
};

let lang = 'sv';
let answers = [];
const app = document.getElementById('app');
const bar = document.getElementById('bar');
const langBtn = document.getElementById('langBtn');

function t(o){ return o ? (o[lang] || o.sv) : ''; }
function esc(s){ const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

function classify(ship, aiDep){
  if (ship >= 0 && aiDep >= 2) return 'gollum';
  if (ship >= 0 && aiDep < 2)  return 'dreambuilder';
  if (ship < 0  && aiDep >= 2) return 'speedrunner';
  return 'shipper';
}

function calculateScores(a){
  let ship = 0, aiDep = 0;
  for (const x of a){ ship += x.shipDelta; aiDep += x.aiDepDelta; }
  const triggered = [];
  for (const c of COMBOS){
    if (c.check(a)){ ship += c.bonusShip; aiDep += c.bonusAiDep; triggered.push(c); }
  }
  const archetype = classify(ship, aiDep);
  const mirrors = [];
  for (const qId of PRIORITY_ORDER[archetype]){
    const sv = a[qId-1];
    if (sv && mirrors.length < 3){
      const m = MIRROR_MAP[qId] && MIRROR_MAP[qId][sv.id];
      if (m) mirrors.push(m);
    }
  }
  return { ship, aiDep, archetype, triggered, mirrors };
}

function setProgress(p){ bar.style.width = p + '%'; }

function visaLanding(){
  setProgress(0);
  app.className = 'scr';
  app.innerHTML =
    '<img class="hero" src="/assets/gollum-precious.webp" alt="Gollum-testet" width="150" height="150">' +
    '<h1>' + esc(t(COPY.heading)) + '</h1>' +
    '<p class="sub">' + esc(t(COPY.sub)) + '</p>' +
    '<button class="big" id="start">' + esc(t(COPY.cta)) + '</button>' +
    '<p class="fine">' + esc(t(COPY.fine)) + '</p>';
  document.getElementById('start').onclick = () => { answers = []; visaFraga(0); };
}

function visaFraga(i){
  const q = QUESTIONS[i];
  setProgress(Math.round((i / QUESTIONS.length) * 100));
  app.className = 'scr top';
  app.innerHTML =
    '<div class="qnum">' + esc(t(COPY.fraga)) + ' ' + (i+1) + ' / ' + QUESTIONS.length + '</div>' +
    '<h1 class="qtx">' + esc(t(q.text)) + '</h1>' +
    '<div class="svar">' + q.answers.map((a, n) =>
      '<button data-n="' + n + '"><span class="id">' + a.id + '</span><span>' + esc(t(a.text)) + '</span></button>'
    ).join('') + '</div>' +
    '<button class="tillbaka" id="bak">' + esc(t(COPY.back)) + '</button>';

  app.querySelectorAll('.svar button').forEach(b => {
    b.onclick = () => {
      answers = answers.slice(0, i);
      answers.push(q.answers[+b.dataset.n]);
      if (i < QUESTIONS.length - 1) visaFraga(i + 1);
      else visaResultat(calculateScores(answers));
    };
  });
  document.getElementById('bak').onclick = () => {
    if (i === 0){ answers = []; visaLanding(); } else visaFraga(i - 1);
  };
}

function visaResultat(res){
  const r = RESULTS[res.archetype];
  const delUrl = 'https://opensverige.se/gollum/' + res.archetype;
  setProgress(100);
  app.className = 'scr top';

  let h =
    '<div class="rem">' + r.emoji + '</div>' +
    '<h1 class="rnamn">' + esc(t(r.name)) + '</h1>' +
    '<p class="rhead">' + esc(t(r.headline)) + '</p>' +
    '<img class="rbild" src="' + BILD[res.archetype] + '" alt="' + esc(t(r.name)) + '" loading="lazy">' +
    '<p class="rbody">' + esc(t(r.body)) + '</p>' +
    '<div class="recept"><div class="l">' + esc(t(COPY.recept)) + '</div><p>' + esc(t(r.recipe)) + '</p></div>';

  if (res.mirrors.length){
    h += '<div class="sekt"><div class="sl">' + esc(t(COPY.spegel)) + '</div>' +
         res.mirrors.map(m => '<div class="spegel">' + esc(t(m)) + '</div>').join('') + '</div>';
  }
  if (res.triggered.length){
    h += '<div class="sekt"><div class="sl">' + esc(t(COPY.kombo)) + '</div>' +
         res.triggered.map(c => '<div class="kombo">' + esc(t(c.callout)) + '</div>').join('') + '</div>';
  }

  const delText = t(r.name) + ' ' + t(r.headline);
  h += '<div class="dela">' +
    '<a href="https://twitter.com/intent/tweet?text=' + encodeURIComponent(delText) +
      '&url=' + encodeURIComponent(delUrl) + '" rel="noopener" target="_blank">X</a>' +
    '<a href="https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(delUrl) +
      '" rel="noopener" target="_blank">LinkedIn</a>' +
    '<button id="kopiera">' + esc(t(COPY.kopiera)) + '</button>' +
    '</div>' +
    '<a class="dbtn" href="' + DISCORD_URL + '" rel="noopener">' + DISCORD_SVG + esc(t(COPY.discord)) + '</a>' +
    '<p class="dsub">' + esc(t(COPY.discordSub)) + '</p>' +
    '<button class="omstart" id="omstart">' + esc(t(COPY.omstart)) + '</button>';

  app.innerHTML = h;

  document.getElementById('kopiera').onclick = (e) => {
    navigator.clipboard.writeText(delUrl).then(() => {
      e.target.textContent = t(COPY.kopierad);
      setTimeout(() => { e.target.textContent = t(COPY.kopiera); }, 1600);
    }).catch(() => {});
  };
  document.getElementById('omstart').onclick = () => { answers = []; visaLanding(); };
}

langBtn.onclick = () => {
  lang = lang === 'sv' ? 'en' : 'sv';
  langBtn.textContent = lang === 'sv' ? 'EN' : 'SV';
  document.documentElement.lang = lang === 'sv' ? 'sv' : 'en';
  if (answers.length === QUESTIONS.length) visaResultat(calculateScores(answers));
  else if (answers.length) visaFraga(answers.length);
  else visaLanding();
};

// Bakåtkompatibelt: gamla delade länkar använde ?r=<slug>
const delad = new URLSearchParams(location.search).get('r');
if (delad && RESULTS[delad]) {
  visaResultat({ archetype: delad, mirrors: [], triggered: [], ship: 0, aiDep: 0 });
} else {
  visaLanding();
}
"""

    return (
        head(
            "/gollum",
            "Gollum-testet — Är du Gollum?",
            "Är du Gollum? Tio brutalt ärliga frågor avslöjar om du faktiskt bygger eller är fast i AI-dopaminloopen. 90 sekunder, inga email.",
            "/assets/og-gollum.jpg",
            ld,
        )
        + f"""
<div class="wrap">
  <header class="qtop">
    <a class="bk" href="/">← opensverige</a>
    <span class="sp"><button class="lang" id="langBtn" aria-label="Byt språk">EN</button></span>
  </header>
  <div class="bar"><i id="bar"></i></div>
  <main class="scr" id="app">
    <h1>Är du Gollum?</h1>
    <p class="sub">Tio frågor. Brutalt ärliga svar. Ta reda på om du bygger — eller bara hoardar.</p>
    <noscript><p class="fine">Testet kräver JavaScript. Läs om arketyperna:
      <a href="/gollum/gollum">Gollum</a>, <a href="/gollum/dreambuilder">Drömbyggaren</a>,
      <a href="/gollum/speedrunner">Speedrunnern</a>, <a href="/gollum/shipper">Shipparen</a>.</p></noscript>
  </main>
</div>
<script>
const DISCORD_URL = {json.dumps(DISCORD)};
const DISCORD_SVG = {json.dumps(DISCORD_SVG)};
{data_js}
{logik_js}
</script>
"""
        + fot()
    )


# ------------------------------------------------------ resultatsidorna

NAMN_SV = {
    "gollum": "Gollum",
    "dreambuilder": "Drömbyggaren",
    "speedrunner": "Speedrunnern",
    "shipper": "Shipparen",
}


def bygg_resultat(slug):
    r = DATA["RESULTS"][slug]
    meta = RESULTAT_META[slug]
    andra = [s for s in ARKETYPER if s != slug]

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{BASE}/gollum/{slug}#webpage",
                "url": f"{BASE}/gollum/{slug}",
                "name": meta["titel"],
                "description": meta["beskrivning"],
                "inLanguage": "sv-SE",
                "isPartOf": {"@id": f"{BASE}/#website"},
                "about": {"@id": f"{BASE}/gollum#quiz"},
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{BASE}/gollum/{slug}#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Start", "item": f"{BASE}/"},
                    {"@type": "ListItem", "position": 2, "name": "Gollum-testet", "item": f"{BASE}/gollum"},
                    {"@type": "ListItem", "position": 3, "name": NAMN_SV[slug]},
                ],
            },
        ],
    }

    lankar = " · ".join(
        f'<a href="/gollum/{s}">{NAMN_SV[s]}</a>' for s in andra
    )

    return (
        head("/gollum/" + slug, meta["titel"], meta["beskrivning"], "/assets/og-gollum.jpg", ld)
        + f"""
<div class="wrap">
  <header class="qtop">
    <a class="bk" href="/gollum">← Gollum-testet</a>
  </header>
  <div class="bar"><i style="width:100%"></i></div>
  <main class="scr top">
    <div class="rem">{r["emoji"]}</div>
    <h1 class="rnamn">{html.escape(r["name"]["sv"])}</h1>
    <p class="rhead">{html.escape(r["headline"]["sv"])}</p>
    <img class="rbild" src="/assets/gollum-{slug}.webp" alt="{html.escape(r["name"]["sv"])}" loading="lazy">
    <p class="rbody">{html.escape(r["body"]["sv"])}</p>
    <div class="recept"><div class="l">Receptet</div><p>{html.escape(r["recipe"]["sv"])}</p></div>

    <a class="dbtn" href="{DISCORD}" rel="noopener">{DISCORD_SVG}Gå med i Discord</a>
    <p class="dsub">600+ builders som faktiskt shippar &amp; failar</p>

    <div class="sekt">
      <div class="sl">Är du inte den här?</div>
      <div class="spegel">Ta testet själv — tio frågor, 90 sekunder. <a href="/gollum">Starta testet →</a></div>
      <div class="spegel">Andra arketyper: {lankar}</div>
    </div>
  </main>
</div>
"""
        + fot('<a href="/gollum">gör testet →</a>')
    )


def main():
    (SITE / "gollum").mkdir(parents=True, exist_ok=True)
    filer = {SITE / "gollum" / "index.html": bygg_quiz()}
    for slug in ARKETYPER:
        filer[SITE / "gollum" / f"{slug}.html"] = bygg_resultat(slug)
    for p, innehall in filer.items():
        p.write_text(innehall, encoding="utf-8")
        print(f"  {p.relative_to(SITE)}  {len(innehall):,} tecken")


if __name__ == "__main__":
    main()
