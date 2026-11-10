"""Visual da tela de login: fundo azul com gráficos e cartão branco central."""
from __future__ import annotations

import base64

_PONTOS = [(0, 700), (120, 655), (240, 685), (360, 595), (480, 625), (600, 535), (720, 565),
           (840, 465), (960, 495), (1080, 395), (1200, 425), (1320, 325), (1440, 290)]
_PONTOS2 = [(0, 780), (160, 760), (320, 770), (480, 720), (640, 735), (800, 680), (960, 690),
            (1120, 630), (1280, 640), (1440, 580)]
_BARRAS = [(905, 150), (965, 230), (1025, 190), (1085, 300), (1145, 260), (1205, 370), (1265, 330), (1325, 450)]


def _fundo_svg() -> str:
    linha = " ".join(f"{x},{y}" for x, y in _PONTOS)
    linha2 = " ".join(f"{x},{y}" for x, y in _PONTOS2)
    grade = "".join(f'<line x1="0" y1="{y}" x2="1440" y2="{y}"/>' for y in range(90, 900, 90))
    grade += "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="900"/>' for x in range(120, 1440, 120))
    barras = "".join(f'<rect x="{x}" y="{900 - h}" width="34" height="{h}" rx="5"/>' for x, h in _BARRAS)
    nos = "".join(f'<circle cx="{x}" cy="{y}" r="5"/>' for x, y in _PONTOS[1:-1])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#071a4a"/><stop offset=".55" stop-color="#0f3fa6"/><stop offset="1" stop-color="#2f80ed"/>
  </linearGradient>
  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="luz" cx=".5" cy=".42" r=".5">
    <stop offset="0" stop-color="#7fb4ff" stop-opacity=".35"/><stop offset="1" stop-color="#7fb4ff" stop-opacity="0"/>
  </radialGradient>
</defs>
<rect width="1440" height="900" fill="url(#bg)"/>
<rect width="1440" height="900" fill="url(#luz)"/>
<g stroke="#fff" stroke-opacity=".06" stroke-width="1">{grade}</g>
<g fill="#fff" fill-opacity=".09">{barras}</g>
<polyline points="{linha2}" fill="none" stroke="#9cc5ff" stroke-opacity=".35" stroke-width="2" stroke-dasharray="6 8"/>
<polygon points="{linha} 1440,900 0,900" fill="url(#area)"/>
<polyline points="{linha}" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="3" stroke-linejoin="round"/>
<g fill="#fff" fill-opacity=".85">{nos}</g>
<g fill="none" stroke-width="26" transform="translate(210 210) rotate(-90)">
  <circle r="84" stroke="#fff" stroke-opacity=".10"/>
  <circle r="84" stroke="#8fc0ff" stroke-opacity=".55" stroke-dasharray="190 528" stroke-linecap="round"/>
  <circle r="84" stroke="#fff" stroke-opacity=".30" stroke-dasharray="110 528" stroke-dashoffset="-215" stroke-linecap="round"/>
</g>
<g fill="none" stroke-width="14" transform="translate(1230 170) rotate(-90)">
  <circle r="46" stroke="#fff" stroke-opacity=".10"/>
  <circle r="46" stroke="#fff" stroke-opacity=".40" stroke-dasharray="200 289" stroke-linecap="round"/>
</g>
</svg>'''


def css() -> str:
    fundo = base64.b64encode(_fundo_svg().encode()).decode()
    return f"""<style>
.stApp {{ background: #0f3fa6 url("data:image/svg+xml;base64,{fundo}") center / cover no-repeat fixed; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stToolbar"] {{ display: none; }}
[data-testid="stMainBlockContainer"] {{ max-width: 440px; padding: 11vh 16px 40px; }}
.st-key-login_card {{
  background: rgba(255,255,255,.97); border-radius: 20px; padding: 36px 32px 26px;
  box-shadow: 0 24px 60px rgba(4,16,52,.45), 0 0 0 1px rgba(255,255,255,.4);
}}
.st-key-login_card, .st-key-login_card p, .st-key-login_card label {{ color: #0b1f44; }}
.login-topo {{ text-align: center; margin-bottom: 6px; }}
.login-logo {{
  width: 60px; height: 60px; border-radius: 16px; margin: 0 auto 14px; display: grid; place-items: center;
  background: linear-gradient(135deg, #0f3fa6, #2f80ed); box-shadow: 0 8px 20px rgba(47,128,237,.45);
}}
.login-titulo {{ font-size: 1.55rem; font-weight: 700; color: #0b1f44; margin: 0; padding: 0; letter-spacing: -.01em; }}
.login-topo p {{ color: #5a6b8c; font-size: .93rem; margin: 6px 0 0; }}
.st-key-login_card [data-testid="stForm"] {{ border: 0; padding: 0; }}
.st-key-login_card [data-testid="stTextInputRootElement"] {{
  background: #f1f5fc; border: 1px solid #d5e0f3; border-radius: 10px; transition: border-color .12s, box-shadow .12s;
}}
.st-key-login_card [data-testid="stTextInputRootElement"] * {{ background: transparent; border-color: transparent; }}
.st-key-login_card [data-testid="stTextInputRootElement"]:focus-within {{
  border-color: #2f80ed; box-shadow: 0 0 0 3px rgba(47,128,237,.18);
}}
.st-key-login_card input {{ color: #0b1f44; caret-color: #1d5fd0; }}
.st-key-login_card input::placeholder {{ color: #8a98b4; }}
.st-key-login_card [data-testid="stTextInputRootElement"] button {{ color: #5a6b8c; }}
.st-key-login_card [data-testid="InputInstructions"] {{ display: none; }}
.st-key-login_card [data-testid="stFormSubmitButton"] button {{
  width: 100%; border: 0; border-radius: 10px; padding: .62rem 1rem; color: #fff; font-weight: 600;
  background: linear-gradient(135deg, #0f3fa6, #2f80ed); box-shadow: 0 6px 16px rgba(47,128,237,.4);
  transition: transform .12s, box-shadow .12s;
}}
.st-key-login_card [data-testid="stFormSubmitButton"] button:hover {{ transform: translateY(-1px); box-shadow: 0 10px 22px rgba(47,128,237,.5); color: #fff; }}
.st-key-login_card [data-testid="stFormSubmitButton"] button p {{ color: #fff; }}
.login-rodape {{ text-align: center; color: #7a89a6; font-size: .78rem; margin-top: 4px; }}
.login-rodape svg {{ vertical-align: -2px; margin-right: 4px; }}
@media (max-width: 480px) {{
  [data-testid="stMainBlockContainer"] {{ padding-top: 7vh; }}
  .st-key-login_card {{ padding: 28px 22px 20px; }}
}}
</style>"""


TOPO = """<div class="login-topo">
  <div class="login-logo">
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
      <path d="M5 27V17M13 27V11M21 27v-8M29 27V5"/><path d="M4 9l8-5 8 6 9-7" stroke-opacity=".55" stroke-width="2"/>
    </svg>
  </div>
  <div class="login-titulo">Meu BI Financeiro</div>
  <p>Seus gastos, limites e faturas em um só lugar</p>
</div>"""

RODAPE = """<div class="login-rodape">
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>
  Acesso protegido · seus dados ficam só neste painel
</div>"""
