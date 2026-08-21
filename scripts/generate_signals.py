# -*- coding: utf-8 -*-
"""
signals.json ジェネレーター(ビルド時のみ使用する補助スクリプト。アプリ本体は
生成済みの signals.json を静的データとして読み込むだけで、実行時にこの
スクリプトは一切関与しない)。

公式ハンドシグナルの「腕・手の動き」の文章記述(6人制バレーボール競技規則
2026年度版で確認済み)をもとに、オリジナルの棒人間ピクトグラムをSVGで
自作する。JVA公式イラストの複製ではなく、動きの説明文から独自に描き起こした
簡易図であることに注意。
"""
import json
from pathlib import Path

INK = "#0F1F33"
ACCENT = "#3E7CB1"   # 手・指など「動きの主役」を強調するための差し色(--volley-blue)
YELLOW = "#F2B705"
RED = "#D1495B"
WOOD = "#C98A4B"

def body(role_label):
    """共通の人型本体(頭・肩・胴・脚)と役職ラベルを返す。
    棒人間ではなく、肩幅のある台形の胴体(シャツのシルエット)にすることで、
    「人がジェスチャーをしている」ことが一目で伝わるようにしている。"""
    label = f'<text x="100" y="256" text-anchor="middle" font-family="sans-serif" font-size="15" font-weight="700" fill="{INK}">{role_label}</text>' if role_label else ""
    return f'''<circle cx="100" cy="36" r="24" fill="{INK}"/>
<path d="M64,84 L136,84 L124,152 L76,152 Z" fill="{INK}"/>
<line x1="100" y1="150" x2="78" y2="230" stroke="{INK}" stroke-width="14" stroke-linecap="round"/>
<line x1="100" y1="150" x2="122" y2="230" stroke="{INK}" stroke-width="14" stroke-linecap="round"/>
{label}'''

def arm(x1, y1, x2, y2, bend=20):
    """肩(x1,y1)から手(x2,y2)への腕。直線ではなく、体の外側方向にわずかに
    肘を張り出させた2本のセグメントで描くことで、実際の腕の動きに近い
    自然なポーズに見えるようにしている(棒人間の"まっすぐな線"問題への対応)。"""
    import math
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1
    px, py = -dy / length, dx / length
    sign = 1 if (x1 - 100) >= 0 else -1
    if px * sign < 0:
        px, py = -px, -py
    mx, my = (x1 + x2) / 2 + px * bend, (y1 + y2) / 2 + py * bend
    return (f'<line x1="{x1}" y1="{y1}" x2="{mx:.1f}" y2="{my:.1f}" stroke="{INK}" stroke-width="14" stroke-linecap="round"/>'
            f'<line x1="{mx:.1f}" y1="{my:.1f}" x2="{x2}" y2="{y2}" stroke="{INK}" stroke-width="14" stroke-linecap="round"/>')

def hand_circle(x, y, r=13, fill=ACCENT):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>'

def hand_bar(x, y, w=30, h=11, angle=0, fill=ACCENT):
    return f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" rx="4" fill="{fill}" transform="rotate({angle} {x} {y})"/>'

def fingers(x, y, count, spread=11, length=24, angle=-90):
    import math
    parts = []
    start = x - spread * (count - 1) / 2
    for i in range(count):
        fx = start + i * spread
        rad = math.radians(angle)
        fx2 = fx + length * math.cos(rad)
        fy2 = y + length * math.sin(rad)
        parts.append(f'<line x1="{fx}" y1="{y}" x2="{fx2}" y2="{fy2}" stroke="{ACCENT}" stroke-width="6" stroke-linecap="round"/>')
    parts.append(hand_circle(x, y, 10))
    return "".join(parts)

def card(x, y, color, w=20, h=28, angle=0):
    return f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" rx="2" fill="{color}" stroke="{INK}" stroke-width="1.5" transform="rotate({angle} {x} {y})"/>'

def curved_arrow(cx, cy, r, start_deg, end_deg, color=INK):
    import math
    s = math.radians(start_deg); e = math.radians(end_deg)
    x1, y1 = cx + r*math.cos(s), cy + r*math.sin(s)
    x2, y2 = cx + r*math.cos(e), cy + r*math.sin(e)
    large = 1 if abs(end_deg - start_deg) > 180 else 0
    return (f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="4" marker-end="url(#arrowhead)"/>')

ARROWHEAD_DEF = ('<defs><marker id="arrowhead" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">'
                  f'<path d="M0,0 L8,4 L0,8 Z" fill="{INK}"/></marker></defs>')

def net_line(x=170):
    ticks = "".join(f'<line x1="{x-6}" y1="{y}" x2="{x+6}" y2="{y}" stroke="{INK}" stroke-width="2"/>' for y in range(20, 241, 20))
    return f'<line x1="{x}" y1="15" x2="{x}" y2="245" stroke="{INK}" stroke-width="3"/>{ticks}'

def net_top(y=60, x1=125, x2=195):
    ticks = "".join(f'<line x1="{x}" y1="{y-6}" x2="{x}" y2="{y+6}" stroke="{INK}" stroke-width="2"/>' for x in range(x1, x2+1, 15))
    return f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{INK}" stroke-width="3"/>{ticks}'

def floor_line(y=250, x1=55, x2=145):
    return f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{INK}" stroke-width="3" stroke-dasharray="6 4"/>'

def flag(x, y, angle=0, color=WOOD):
    return (f'<g transform="rotate({angle} {x} {y})">'
            f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y-40}" stroke="{INK}" stroke-width="4"/>'
            f'<path d="M{x},{y-40} L{x+26},{y-32} L{x},{y-24} Z" fill="{color}" stroke="{INK}" stroke-width="1.5"/></g>')

def wave_lines(x, y):
    return "".join(f'<path d="M{x-10},{y-8+i*10} q10,-8 20,0" fill="none" stroke="{INK}" stroke-width="3"/>' for i in range(3))

def anim_g(content, cls, origin_x, origin_y):
    """動きそのものが意味を持つ一部のシグナルだけ、CSSアニメーション用の
    グループでラップする(対応する @keyframes は style.css 側で定義)。
    transform-origin をSVGのユーザー単位で指定するため、対応するクラス名は
    style.css の transform-origin ともセットで管理すること。"""
    return f'<g class="{cls}" style="transform-origin:{origin_x}px {origin_y}px">{content}</g>'

def svg_wrap(inner, role_label):
    return (f'<svg viewBox="0 0 220 265" xmlns="http://www.w3.org/2000/svg">{ARROWHEAD_DEF}'
            f'{body(role_label)}{inner}</svg>')

SIGNALS = []

def add(id_, name, role_label, inner, hint=""):
    SIGNALS.append({"id": id_, "name": name, "hint": hint, "svg": svg_wrap(inner, role_label)})

# ---- ファーストレフェリー/セカンドレフェリーの公式ハンドシグナル ----

add("sig01", "サービス許可", "審判",
    arm(122, 95, 185, 70) + hand_circle(185, 70) +
    f'<line x1="185" y1="70" x2="205" y2="60" stroke="{INK}" stroke-width="3"/>' +
    f'<path d="M200,55 L208,58 L203,65 Z" fill="{INK}"/>',
    "サービスの方向を手で示す")

add("sig02", "サービスを行うチーム", "審判",
    arm(122, 95, 190, 95) + hand_circle(190, 95),
    "サービスをする側の腕を横に上げる")

add("sig03", "コートチェンジ", "審判",
    anim_g(arm(78, 95, 42, 95) + hand_circle(42, 95), "anim-swing-l", 78, 95) +
    anim_g(arm(122, 95, 158, 95) + hand_circle(158, 95), "anim-swing-r", 122, 95),
    "左腕は前から後ろへ、右腕は後ろから前へ弧を描く(アニメーションで動きを再現)")

add("sig04", "タイムアウト", "審判",
    arm(78, 95, 58, 45) + hand_bar(58, 30, 34, 10),
    "片方の手を垂直に立て、その上に反対側の手のひらをのせてT字を作る")

add("sig05", "選手交代(サブスティチューション)", "審判",
    anim_g(
        f'<line x1="90" y1="95" x2="110" y2="130" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>' +
        f'<line x1="110" y1="95" x2="90" y2="130" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>' +
        curved_arrow(100, 112, 28, -30, 300),
        "anim-spin", 100, 112),
    "両腕の前腕部を、互いに回転させる(アニメーションで動きを再現)")

add("sig06", "軽度の不法な行為への警告(イエローカード)", "審判",
    arm(122, 95, 122, 20) + card(122, 10, YELLOW),
    "ステージ2の警告としてイエローカードを示す")

add("sig07", "ペナルティ", "審判",
    arm(122, 95, 122, 20) + card(122, 10, RED),
    "ペナルティとしてレッドカードを示す")

add("sig08", "退場", "審判",
    arm(122, 95, 122, 20) + card(112, 10, YELLOW) + card(132, 10, RED),
    "退場としてイエローカードとレッドカードを一緒に示す")

add("sig09", "失格", "審判",
    arm(78, 95, 78, 20) + card(78, 10, YELLOW) + arm(122, 95, 140, 20) + card(140, 10, RED),
    "失格としてイエローカードとレッドカードを別々に示す")

add("sig10", "セット(ゲーム)の終了", "審判",
    f'<line x1="68" y1="90" x2="132" y2="132" stroke="{ACCENT}" stroke-width="13" stroke-linecap="round"/>' +
    f'<line x1="132" y1="90" x2="68" y2="132" stroke="{ACCENT}" stroke-width="13" stroke-linecap="round"/>',
    "両腕を胸の前で交差する")

add("sig11", "サービスでボールをヒットしなかった、またはトスをしないで打った反則", "審判",
    arm(122, 100, 175, 145) + hand_bar(180, 150, 26, 8, -35),
    "腕を前方に伸ばしたまま、手のひらを上に向けて上げる")

add("sig12", "ディレイインサービス(サービス時8秒ルールの反則)", "審判",
    arm(78, 95, 45, 35) + fingers(38, 25, 4, angle=-110) +
    arm(122, 95, 155, 35) + fingers(162, 25, 4, angle=-70),
    "指を8本、広げて上げる")

add("sig13", "ブロックの反則またはスクリーン", "審判",
    arm(78, 95, 65, 15) + hand_bar(60, 8, 24, 8, 20) +
    arm(122, 95, 135, 15) + hand_bar(140, 8, 24, 8, -20),
    "両方の手のひらを前方に向け、真上に上げる")

add("sig14", "ポジションまたはローテーションの反則", "審判",
    arm(122, 95, 160, 95) + anim_g(curved_arrow(160, 95, 16, 0, 340), "anim-spin", 160, 95),
    "人差し指で円を描く(アニメーションで動きを再現)")

add("sig15", "ボール『イン』", "審判",
    arm(122, 100, 150, 235) + floor_line(245, 120, 180),
    "フロアーを指す")

add("sig16", "ボール『アウト』", "審判",
    f'<line x1="78" y1="95" x2="94" y2="95" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>' +
    f'<line x1="94" y1="95" x2="90" y2="20" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>' +
    hand_circle(90, 14) +
    f'<line x1="122" y1="95" x2="106" y2="95" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>' +
    f'<line x1="106" y1="95" x2="110" y2="20" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>' +
    hand_circle(110, 14),
    "両手のひらを自分の方に向け、前腕を垂直に上げる")

add("sig17", "キャッチ(ボールの保持)", "審判",
    arm(78, 100, 45, 130) + hand_bar(38, 138, 26, 8, -60) +
    anim_g(f'<path d="M45,110 L45,95" stroke="{INK}" stroke-width="3" fill="none"/><path d="M40,100 L45,90 L50,100 Z" fill="{INK}"/>',
           "anim-lift", 45, 100),
    "片方の手のひらを上に向け、前腕をゆっくり持ち上げる(アニメーションで動きを再現)")

add("sig18", "ダブルコンタクト", "審判",
    arm(122, 95, 162, 40) + fingers(168, 28, 2, spread=16, angle=-70),
    "指を2本伸ばし、その手を上げる")

add("sig19", "フォアヒット", "審判",
    arm(122, 95, 165, 40) + fingers(172, 28, 4, angle=-70),
    "指を4本伸ばし、その手を上げる")

add("sig20", "選手のタッチネット", "審判",
    arm(122, 95, 158, 95) + hand_circle(158, 95) + net_line(178),
    "反則をしたチーム側のネットを示す")

add("sig21", "オーバーネット", "審判",
    arm(122, 90, 165, 62) + hand_bar(178, 60, 26, 8, 10) + net_top(60, 130, 195),
    "手のひらを下に向け、ネット上方にかざす")

add("sig22", "アタックヒットの反則", "審判",
    anim_g(arm(122, 90, 150, 30) + hand_bar(155, 22, 26, 8, -30), "anim-chop", 122, 90) +
    curved_arrow(140, 60, 30, -40, 60),
    "手のひらを広げて上方に伸ばし、前腕を振り下ろす(アニメーションで動きを再現)")

add("sig23", "ペネトレーションフォルト", "審判",
    arm(70, 95, 20, 190) + hand_circle(20, 190) + floor_line(205, 2, 58),
    "センターラインまたは該当するラインを指す")

add("sig24", "ダブルフォルトおよびリプレイ", "審判",
    arm(78, 95, 52, 30) + hand_circle(52, 30) + f'<rect x="45" y="8" width="12" height="22" rx="5" fill="{ACCENT}"/>' +
    arm(122, 95, 148, 30) + hand_circle(148, 30) + f'<rect x="151" y="8" width="12" height="22" rx="5" fill="{ACCENT}"/>',
    "両方の親指を立て、両腕を上げる")

add("sig25", "ボールコンタクト(ワンタッチ)", "審判",
    arm(78, 100, 95, 130) + fingers(95, 122, 3, spread=8, length=16, angle=-90) +
    arm(122, 100, 105, 135) + hand_bar(108, 140, 20, 6, 35),
    "垂直に立てた手の指先を、他方の手でブラシをかけるようにする")

add("sig26", "ディレイウォーニングまたはディレイペナルティ", "審判",
    arm(122, 130, 90, 150) + card(85, 155, YELLOW, w=16, h=22, angle=20),
    "イエローカード(またはレッドカード)を他方の手首にあてる")

# ---- ラインジャッジ(線審)の公式フラッグシグナル ----

add("sig27", "ボール『イン』(ラインジャッジ)", "線審",
    arm(122, 95, 130, 195) + flag(130, 195, angle=170),
    "フラッグを下げる")

add("sig28", "ボール『アウト』(ラインジャッジ)", "線審",
    arm(122, 95, 122, 40) + flag(122, 40),
    "フラッグを真上に上げる")

add("sig29", "ボールコンタクト(ラインジャッジ)", "線審",
    arm(122, 95, 122, 40) + flag(122, 40) +
    arm(78, 100, 100, 60) + hand_circle(100, 55, 9),
    "フラッグを立て、他方の手のひらをフラッグの先端にのせる")

add("sig30", "ボールのアンテナ外通過・フットフォルト等(ラインジャッジ)", "線審",
    arm(122, 95, 122, 40) + anim_g(flag(122, 40), "anim-wave", 122, 40) + wave_lines(150, 40),
    "アンテナまたはラインを指し示し、フラッグを頭上で左右に振る(アニメーションで動きを再現)")

add("sig31", "判定不能(ラインジャッジ)", "線審",
    f'<line x1="68" y1="90" x2="132" y2="132" stroke="{ACCENT}" stroke-width="13" stroke-linecap="round"/>' +
    f'<line x1="132" y1="90" x2="68" y2="132" stroke="{ACCENT}" stroke-width="13" stroke-linecap="round"/>',
    "両腕を胸の前で交差する")

out_path = Path(__file__).resolve().parent.parent / "signals.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"signals": SIGNALS}, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("generated", len(SIGNALS), "signals ->", out_path)
