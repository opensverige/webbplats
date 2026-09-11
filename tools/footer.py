#!/usr/bin/env python3
"""Lägger föreningsfootern på varje sida i site/.

Footern definieras här och bara här. Skriptet körs efter generatorerna i
BYGGSTEG, eftersom bygg-sidor.py och bygg-gollum.py skriver om sin HTML vid
varje bygge och annars skulle radera den.

Idempotent: blocken märks med sentinels och ersätts vid omkörning i stället
för att dubbleras.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

ORGNR = "802557-3422"
BILDAD = "23 april 2026"
EPOST = "opensverige@gmail.com"
DISCORD = "https://discord.gg/ZbV4qB34um"

CSS_START, CSS_SLUT = "/* footer:start */", "/* footer:slut */"
HTML_START, HTML_SLUT = "<!-- footer:start -->", "<!-- footer:slut -->"

# Egen padding i stället för var(--gut): gollum-sidorna definierar inte den
# variabeln, och footern ska se likadan ut överallt.
CSS = f"""{CSS_START}
.sfoot{{border-top:1px solid var(--hair);margin-top:96px;padding:56px 0 44px}}
.sfin{{max-width:1360px;margin:0 auto;padding:0 20px}}
.scols{{display:grid;gap:36px 28px;grid-template-columns:1fr}}
.swm{{font-family:var(--serif,'Instrument Serif',Georgia,serif);font-size:40px;line-height:.95;
  letter-spacing:-.015em;color:var(--ink)}}
.sdesc{{color:var(--muted);font-size:14px;line-height:1.55;margin:12px 0 0;max-width:32ch}}
/* Etiketten bär hierarkin i mörkt, länkarna ligger tillbaka i grått.
   --faint ger bara 3,2:1 mot bakgrunden och klarar inte AA för brödtext. */
.scl{{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--ink);margin-bottom:13px}}
.scol a{{display:block;width:max-content;font-size:14.5px;color:var(--muted);padding:5px 0;
  transition:color 150ms cubic-bezier(.4,0,.2,1)}}
.scol a:hover{{color:var(--accent)}}
.scol a i{{font-style:normal;font-size:10px;margin-left:5px;vertical-align:1px;opacity:.45}}
.sbot{{display:flex;flex-wrap:wrap;gap:10px 24px;justify-content:space-between;align-items:baseline;
  margin-top:48px;padding-top:22px;border-top:1px solid var(--hair)}}
.sorg{{margin:0;font-family:var(--mono);font-size:12px;color:var(--muted);letter-spacing:.01em}}
.sorg b{{color:var(--ink);font-weight:500}}
.ssrc{{font-family:var(--mono);font-size:12px;color:var(--muted);transition:color 150ms cubic-bezier(.4,0,.2,1)}}
.ssrc:hover{{color:var(--accent)}}
.vh{{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;
  clip:rect(0 0 0 0);white-space:nowrap;border:0}}
@media(min-width:640px){{.scols{{grid-template-columns:repeat(2,1fr)}}}}
@media(min-width:960px){{.scols{{grid-template-columns:1.5fr repeat(4,1fr);gap:28px}}}}
@media(min-width:1080px){{.sfin{{padding:0 46px}}}}
{CSS_SLUT}"""


def lank_ut(url: str, text: str) -> str:
    """Extern länk: ny flik, och det sägs även för den som lyssnar."""
    return (
        f'<a href="{url}" target="_blank" rel="noopener">{text}'
        f'<i aria-hidden="true">↗</i><span class="vh">, öppnas i ny flik</span></a>'
    )


HTML = f"""{HTML_START}
<footer class="sfoot">
  <div class="sfin">
    <div class="scols">
      <div>
        <div class="swm">opensverige</div>
        <p class="sdesc">Sveriges öppna community för builders som bygger AI-agenter,
          MCP-servrar och vibecoding-projekt.</p>
      </div>

      <nav class="scol" aria-labelledby="f-sajt">
        <div class="scl" id="f-sajt">Sajten</div>
        <a href="/bli-medlem">Bli medlem</a>
        <a href="/showcase">Showcase</a>
        <a href="/blogg">Blogg</a>
        <a href="/varfor">Varför opensverige</a>
      </nav>

      <nav class="scol" aria-labelledby="f-foreningen">
        <div class="scl" id="f-foreningen">Föreningen</div>
        <a href="/stadgar">Stadgar</a>
        <a href="/regler">Regler</a>
        <a href="/integritet">Integritet</a>
        <a href="mailto:{EPOST}">Kontakt</a>
      </nav>

      <nav class="scol" aria-labelledby="f-community">
        <div class="scl" id="f-community">Community</div>
        {lank_ut(DISCORD, "Discord")}
        {lank_ut("https://github.com/orgs/opensverige", "GitHub")}
        {lank_ut("https://www.linkedin.com/groups/9544657/", "LinkedIn")}
      </nav>

      <nav class="scol" aria-labelledby="f-maskiner">
        <div class="scl" id="f-maskiner">För maskiner</div>
        <a href="/llms.txt">llms.txt</a>
        <a href="/api/community.json">API</a>
        <a href="/sitemap.xml">Sitemap</a>
      </nav>
    </div>

    <div class="sbot">
      <p class="sorg">Ideell förening · Org.nr <b>{ORGNR}</b> · Bildad {BILDAD}</p>
      {lank_ut("https://github.com/opensverige/webbplats", "Sajtens källkod").replace('<a ', '<a class="ssrc" ')}
    </div>
  </div>
</footer>
{HTML_SLUT}"""


def ersatt_eller_satt_in(text: str, start: str, slut: str, block: str, fore: str) -> str:
    """Byt ut ett tidigare injicerat block, annars sätt in det före `fore`."""
    if start in text:
        return re.sub(
            re.escape(start) + r".*?" + re.escape(slut), lambda _: block, text, flags=re.S
        )
    # Sista förekomsten, så våra regler hamnar sist i kaskaden.
    brytpunkt = text.rfind(fore)
    if brytpunkt == -1:
        raise ValueError(f"hittade inte {fore!r}")
    return text[:brytpunkt] + block + "\n" + text[brytpunkt:]


def main() -> None:
    sidor = sorted(SITE.rglob("*.html"))
    for p in sidor:
        t = p.read_text(encoding="utf-8")
        t = ersatt_eller_satt_in(t, CSS_START, CSS_SLUT, CSS, "</style>")
        t = ersatt_eller_satt_in(t, HTML_START, HTML_SLUT, HTML, "</body>")
        p.write_text(t, encoding="utf-8")
    print(f"Footer på {len(sidor)} sidor · org.nr {ORGNR} · bildad {BILDAD}")


if __name__ == "__main__":
    main()
