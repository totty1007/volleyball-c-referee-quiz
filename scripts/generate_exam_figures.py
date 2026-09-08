# -*- coding: utf-8 -*-
"""
exam_figures.json ジェネレーター(ビルド時のみ使用する補助スクリプト)。

MODE 06「模擬審査会」で使う図をSVGで自作する。

 ・court    … 6人制コートの各部の名称・寸法を答えさせる図(問1用)。
               ライン名(Ａ〜Ｄ)・寸法(あ〜く)・ゾーン名(ａ〜f)の空欄が入る。
 ・rotation … ラインアップシートと5つの選手配置図(問5用)。サービスヒット時に
               ポジションの反則が起きている配置を選ばせる。

実物の審査会練習問題(資料\提供資料\)は相模原バレーボール協会・神奈川県
バレーボール協会が作成した第三者の著作物なので、**図を複製してはいけない**。
このスクリプトは「出題形式(どこに何の空欄があるか)」だけを踏襲し、図そのものは
競技規則の寸法から独自に座標を計算して描いている(signals.json と同じ方針)。

再生成:
    PYTHONIOENCODING=utf-8 python3 scripts/generate_exam_figures.py
"""
import json
from pathlib import Path

INK = "#0F1F33"      # ライン・文字
COURT = "#EDE8DA"    # コート面
FREE = "#F7F5EE"     # フリーゾーン
NETC = "#6B7C8F"     # ネット・補助線
BLANK = "#D1495B"    # 空欄の記号(赤)。答えを書き込む場所だと分かるように
DIM = "#3E7CB1"      # 寸法線(青)
HALO = "#FFFFFF"

M = 24               # 1m = 24px


def _t(x, y, s, size=13, anchor="middle", fill=INK, weight="400"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-family="sans-serif" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}">{s}</text>')


def _blank(x, y, label, size=14, anchor="middle"):
    """答えを書き込む空欄「( あ )」。赤にして本文の説明文と区別する。"""
    return _t(x, y, f'( {label} )', size=size, anchor=anchor, fill=BLANK, weight="700")


def _arrow_defs():
    return ('<defs>'
            f'<marker id="ed" markerUnits="userSpaceOnUse" markerWidth="14" markerHeight="14" '
            f'refX="12" refY="7" orient="auto"><path d="M0,1 L13,7 L0,13 Z" fill="{DIM}"/></marker>'
            f'<marker id="es" markerUnits="userSpaceOnUse" markerWidth="14" markerHeight="14" '
            f'refX="12" refY="7" orient="auto"><path d="M0,1 L13,7 L0,13 Z" fill="{INK}"/></marker>'
            '</defs>')


def _blank_with(x, y, label, suffix="", size=14):
    """空欄と語尾を1行に並べる(「( f )ゾーン」)。空欄を右寄せ・語尾を左寄せに
    して x を境に並べるので、全体がだいたい x を中心に収まる。
    空欄と語尾を別の行に置くと必ず重なるので、この形に統一する。"""
    if not suffix:
        return _blank(x, y, label, size=size)
    return (_t(x + 2, y, f'( {label} )', size=size, anchor="end", fill=BLANK, weight="700")
            + _t(x + 4, y, suffix, size=size - 2, anchor="start"))


def _dim_h(x1, x2, y, label, above=True, suffix="", dy=None):
    """水平の寸法線(両矢印)＋空欄ラベル。dy でラベルの上下位置を微調整する。"""
    off = dy if dy is not None else (-8 if above else 18)
    return (f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{DIM}" stroke-width="1.6" '
            f'marker-end="url(#ed)"/>'
            f'<line x1="{x2}" y1="{y}" x2="{x1}" y2="{y}" stroke="{DIM}" stroke-width="1.6" '
            f'marker-end="url(#ed)"/>'
            + _blank_with((x1 + x2) / 2, y + off, label, suffix))


def _dim_v(y1, y2, x, label, dx=30):
    """垂直の寸法線(両矢印)＋空欄ラベル。dx でラベルの左右位置を微調整する
    (図の部品とぶつかるので呼び出し側で指定する)。"""
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{DIM}" stroke-width="1.6" '
            f'marker-end="url(#ed)"/>'
            f'<line x1="{x}" y1="{y2}" x2="{x}" y2="{y1}" stroke="{DIM}" stroke-width="1.6" '
            f'marker-end="url(#ed)"/>'
            + _blank(x + dx, (y1 + y2) / 2 + 5, label))


def _callout(x1, y, x2, label):
    """細かい寸法用の引き出し線＋空欄。拡大図の中の数ピクセルの寸法は両矢印では
    点に見えてしまうので、その位置から横に線を引いて離れた所にラベルを置く。"""
    lx = x2 + (26 if x2 > x1 else -26)
    return (f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{DIM}" stroke-width="1.4"/>'
            f'<circle cx="{x1}" cy="{y}" r="2.6" fill="{DIM}"/>'
            + _blank(lx, y + 5, label))


def _leader(x1, y1, x2, y2):
    """引き出し線(ラベルから図の部位へ)。"""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK}" '
            f'stroke-width="1.4" marker-end="url(#es)"/>')


# ---------------------------------------------------------------------------
# 問1用: 6人制のコート
# ---------------------------------------------------------------------------

def court_figure():
    """6人制コート図。空欄は18か所(ライン名Ａ〜Ｄ・寸法あ〜く・ゾーン名ａ〜f)。
    ラベルが18個も入るので、置き場所は次のルールで固定してある:
      ・ライン名 → 図の上と左下に置き、引き出し線で該当のラインを指す
      ・ゾーン名 → コートの中(ｃ・ａ)、コートの外の該当位置(ｂ)、下の寸法線(ｄ・ｅ)、上の寸法線(f)
      ・寸法 → コートの中(あ・い・う)と下の拡大図の中(え〜く)
    どれか1つを動かすと隣とぶつかるので、動かすときは必ず全体を目視確認する。"""
    x0, y0 = 210, 190
    w, h = 18 * M, 9 * M              # 432 x 216
    x1, y1 = x0 + w, y0 + h
    cx = x0 + 9 * M                   # センターライン 426
    al_l, al_r = cx - 3 * M, cx + 3 * M   # アタックライン 354 / 498
    fz = 3 * M
    fx0, fy0, fx1, fy1 = x0 - fz, y0 - fz, x1 + fz, y1 + fz

    p = [_arrow_defs()]
    p.append(f'<rect x="{fx0}" y="{fy0}" width="{fx1 - fx0}" height="{fy1 - fy0}" '
             f'fill="{FREE}" stroke="{NETC}" stroke-width="1.4" stroke-dasharray="7 6"/>')
    p.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="{COURT}" '
             f'stroke="{INK}" stroke-width="3"/>')
    p.append(f'<line x1="{cx}" y1="{y0}" x2="{cx}" y2="{y1}" stroke="{INK}" stroke-width="3.4"/>')
    for ax in (al_l, al_r):
        p.append(f'<line x1="{ax}" y1="{y0}" x2="{ax}" y2="{y1}" stroke="{INK}" stroke-width="2.2"/>')
        for side, sgn in ((y0, -1), (y1, 1)):
            for k in range(5):
                s0 = side + sgn * (7 + k * 13)
                p.append(f'<line x1="{ax}" y1="{s0}" x2="{ax}" y2="{s0 + sgn * 6}" '
                         f'stroke="{INK}" stroke-width="2.4"/>')
    for ex, sgn in ((x0, -1), (x1, 1)):
        for sy, dy in ((y0, 5), (y1, -5)):
            p.append(f'<line x1="{ex + sgn * 5}" y1="{sy}" x2="{ex + sgn * 5}" y2="{sy + dy}" '
                     f'stroke="{INK}" stroke-width="2.4"/>')

    # ---- 上段: フリーゾーンの寸法とライン名3つ ----
    p.append(_dim_h(fx0, fx1, 108, 'f', suffix='ゾーン'))
    for lab, tx, lead_from, lead_to in (
            ('Ｄ', 320, (350, 162), (al_l, y0 - 4)),
            ('Ｃ', 470, (444, 162), (cx, y0 - 4)),
            ('Ａ', 600, (600, 162), (578, y0 - 4))):
        p.append(_blank(tx, 156, lab, anchor="start") + _t(tx + 54, 156, 'ライン', anchor="start"))
        p.append(_leader(*lead_from, *lead_to))

    # ---- 左下: エンドライン ----
    p.append(_blank(150, 452, 'Ｂ', anchor="start") + _t(204, 452, 'ライン', anchor="start"))
    p.append(_leader(196, 446, x0 - 3, y1 - 24))

    # ---- コートの中: ゾーン名と寸法 ----
    p.append(_blank_with((x0 + al_l) / 2, 252, 'ｃ', 'ゾーン', size=13))
    p.append(_blank((al_l + cx) / 2, 246, 'ａ', size=13) +
             _t((al_l + cx) / 2, 262, 'ゾーン', size=11.5))
    p.append(_blank(fx0 + 36, 296, 'ｂ', size=13) + _t(fx0 + 36, 312, 'ゾーン', size=11.5))
    p.append(_dim_h(x0, x1, 340, 'あ', dy=-14))
    p.append(_dim_v(y0, y1, 596, 'い', dx=26))
    p.append(_dim_h(al_l, cx, 384, 'う', above=False))

    # ---- 下段: 選手交代ゾーンとリベロリプレイスメントゾーン ----
    p.append(_dim_h(al_l, al_r, 502, 'ｄ', above=False, suffix='ゾーン'))
    p.append(_dim_h(al_r, x1, 502, 'ｅ', above=False, suffix='ゾーン'))

    # ---- 拡大図1: アタックラインの破線延長(サイドラインの外) ----
    bx, by, bw, bh = 150, 556, 300, 104
    p.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{HALO}" '
             f'stroke="{NETC}" stroke-width="1.4"/>')
    p.append(_t(bx + 10, by + 19, '〈拡大1〉アタックラインの延長', size=12, anchor="start", fill=NETC))
    sl = by + 36
    p.append(f'<line x1="{bx + 24}" y1="{sl}" x2="{bx + 132}" y2="{sl}" stroke="{INK}" stroke-width="3.4"/>')
    p.append(_t(bx + 86, sl - 7, 'サイドライン', size=10.5, anchor="start", fill=NETC))
    for k in range(5):
        yy = sl + 8 + k * 12
        p.append(f'<line x1="{bx + 66}" y1="{yy}" x2="{bx + 66}" y2="{yy + 7}" '
                 f'stroke="{INK}" stroke-width="3.4"/>')
    p.append(_dim_v(sl + 8, sl + 63, bx + 40, 'え', dx=-28))
    p.append(_callout(bx + 66, sl + 18, bx + 150, 'お'))
    p.append(_callout(bx + 66, sl + 36, bx + 150, 'か'))

    # ---- 拡大図2: サービスゾーンを示す短い線 ----
    bx2 = 470
    p.append(f'<rect x="{bx2}" y="{by}" width="{bw}" height="{bh}" fill="{HALO}" '
             f'stroke="{NETC}" stroke-width="1.4"/>')
    p.append(_t(bx2 + 10, by + 19, '〈拡大2〉サービスゾーンを示す線', size=12, anchor="start", fill=NETC))
    el = bx2 + 176
    p.append(f'<line x1="{el}" y1="{by + 30}" x2="{el}" y2="{by + 98}" stroke="{INK}" stroke-width="3.4"/>')
    p.append(_t(el + 8, by + 40, 'エンドライン', size=10.5, anchor="start", fill=NETC))
    p.append(f'<line x1="{el - 52}" y1="{by + 70}" x2="{el - 20}" y2="{by + 70}" '
             f'stroke="{INK}" stroke-width="3.4"/>')
    p.append(_dim_h(el - 52, el - 20, by + 60, 'き', dy=-12))
    p.append(_callout(el - 10, by + 90, el - 80, 'く'))

    return (f'<svg viewBox="0 0 900 680" xmlns="http://www.w3.org/2000/svg">'
            + "".join(p) + '</svg>')


# ---------------------------------------------------------------------------
# 問5用: ラインアップシートと5つの選手配置図
# ---------------------------------------------------------------------------

# ラインアップシート: ポジションと背番号
LINEUP = {"Ⅰ": 1, "Ⅱ": 2, "Ⅲ": 3, "Ⅳ": 4, "Ⅴ": 5, "Ⅵ": 6}

# 次のサーバーが3番 → 3番は現在ポジションⅡにいる。そこから逆算した現在の配置:
#   Ⅰ=2 Ⅱ=3 Ⅲ=4 Ⅳ=5 Ⅴ=6 Ⅵ=1
#   前衛(左→右) Ⅳ=5, Ⅲ=4, Ⅱ=3 ／ 後衛(左→右) Ⅴ=6, Ⅵ=1, Ⅰ=2
# サービスヒット時に必要な位置関係:
#   6は5より後ろ / 1は4より後ろ / 2は3より後ろ
#   前衛の左右順 5-4-3 / 後衛の左右順 6-1-2
# 下の5配置のうち、反則が起きているのは 2 と 4(答え)。
ARRANGEMENTS = [
    # (番号, [(背番号, x比, y比), ...], 反則か)
    (1, [(5, .20, .26), (4, .50, .22), (3, .80, .28),
         (6, .18, .68), (1, .48, .72), (2, .80, .65)], False),
    (2, [(5, .20, .30), (4, .50, .62), (3, .80, .26),
         (6, .18, .72), (1, .46, .44), (2, .80, .68)], True),
    (3, [(5, .22, .34), (4, .44, .24), (3, .76, .30),
         (6, .14, .60), (1, .52, .80), (2, .84, .56)], False),
    (4, [(5, .20, .28), (4, .50, .24), (3, .80, .30),
         (6, .16, .66), (2, .46, .70), (1, .80, .62)], True),
    (5, [(5, .24, .30), (4, .52, .36), (3, .78, .32),
         (6, .20, .78), (1, .50, .66), (2, .82, .72)], False),
]


def _player(x, y, num):
    """選手のマーカー(足形の楕円＋背番号)。実物は足形のアイコンだが、
    ここでは楕円で描いた自作の記号。前後関係が読めることが要件なので、
    楕円の中心が立ち位置になるようにしてある。"""
    return (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="11" ry="8.5" fill="{INK}"/>'
            + _t(x, y + 4, str(num), size=11.5, fill="#FFFFFF", weight="700"))


def _half_court(ox, oy, bw, bh, players, label):
    """自コートの半面(上辺=ネット、内側の横線=アタックライン)。"""
    p = [f'<rect x="{ox}" y="{oy}" width="{bw}" height="{bh}" fill="{COURT}" '
         f'stroke="{INK}" stroke-width="2"/>']
    p.append(f'<line x1="{ox}" y1="{oy}" x2="{ox + bw}" y2="{oy}" stroke="{INK}" stroke-width="4"/>')
    al = oy + bh * 0.42
    p.append(f'<line x1="{ox}" y1="{al:.1f}" x2="{ox + bw}" y2="{al:.1f}" '
             f'stroke="{INK}" stroke-width="1.8"/>')
    p.append(_t(ox + bw / 2, oy - 8, 'ネット', size=11, fill=NETC))
    for num, rx, ry in players:
        p.append(_player(ox + bw * rx, oy + bh * ry, num))
    p.append(f'<rect x="{ox - 2}" y="{oy - 30}" width="26" height="20" rx="4" fill="{INK}"/>')
    p.append(_t(ox + 11, oy - 15, label, size=13, fill="#FFFFFF", weight="700"))
    return "".join(p)


def rotation_figure():
    p = [_arrow_defs()]
    # ---- ラインアップシート ----
    lx, ly, cw, ch = 26, 40, 62, 46
    p.append(_t(lx, ly - 14, '〔ラインアップシート〕', size=13, anchor="start", weight="700"))
    p.append(f'<rect x="{lx}" y="{ly}" width="{cw * 3}" height="{ch * 2}" fill="{HALO}" '
             f'stroke="{INK}" stroke-width="2"/>')
    for c, pos in enumerate(("Ⅳ", "Ⅲ", "Ⅱ")):
        p.append(_t(lx + cw * c + cw / 2, ly + 14, pos, size=12, fill=NETC))
        p.append(f'<circle cx="{lx + cw * c + cw / 2}" cy="{ly + 30}" r="13" fill="none" '
                 f'stroke="{INK}" stroke-width="1.6"/>')
        p.append(_t(lx + cw * c + cw / 2, ly + 35, str(LINEUP[pos]), size=15, weight="700"))
    for c, pos in enumerate(("Ⅴ", "Ⅵ", "Ⅰ")):
        p.append(_t(lx + cw * c + cw / 2, ly + ch + 14, pos, size=12, fill=NETC))
        p.append(f'<circle cx="{lx + cw * c + cw / 2}" cy="{ly + ch + 30}" r="13" fill="none" '
                 f'stroke="{INK}" stroke-width="1.6"/>')
        p.append(_t(lx + cw * c + cw / 2, ly + ch + 35, str(LINEUP[pos]), size=15, weight="700"))
    p.append(f'<line x1="{lx}" y1="{ly + ch}" x2="{lx + cw * 3}" y2="{ly + ch}" '
             f'stroke="{INK}" stroke-width="1.4"/>')
    p.append(_t(lx, ly + ch * 2 + 22, 'ネット側 → 上の行(Ⅳ Ⅲ Ⅱ)が前衛',
                size=11.5, anchor="start", fill=NETC))

    # ---- 5つの配置図 ----
    bw, bh = 196, 128
    slots = [(238, 40), (452, 40), (24, 236), (238, 236), (452, 236)]
    for (num, players, _bad), (ox, oy) in zip(ARRANGEMENTS, slots):
        p.append(_half_court(ox, oy, bw, bh, players, str(num)))

    return (f'<svg viewBox="0 0 668 392" xmlns="http://www.w3.org/2000/svg">'
            + "".join(p) + '</svg>')


FIGURES = {
    "court": court_figure(),
    "rotation": rotation_figure(),
}

# 問5の正解(反則が起きている配置の番号)。exam.json 側と食い違わないよう
# ここから生成できるようにしておく。
ROTATION_FAULTS = [n for n, _pl, bad in ARRANGEMENTS if bad]

out = Path(__file__).resolve().parent.parent / "exam_figures.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump({"figures": FIGURES, "rotationFaults": ROTATION_FAULTS},
              f, ensure_ascii=False, indent=2)
    f.write("\n")

print("generated", len(FIGURES), "figures / rotation faults =", ROTATION_FAULTS, "->", out)
