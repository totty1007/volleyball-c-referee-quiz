# -*- coding: utf-8 -*-
"""
signals.json ジェネレーター(ビルド時のみ使用する補助スクリプト。アプリ本体は
生成済みの signals.json を静的データとして読み込むだけで、実行時にこの
スクリプトは一切関与しない)。

公式ハンドシグナルの「腕・手の動き」の文章記述(6人制バレーボール競技規則
2026年度版で確認済み)をもとに、オリジナルの棒人間ピクトグラムをSVGで
自作する。JVA公式イラストの複製ではなく、動きの説明文から独自に描き起こした
簡易図であることに注意。

---------------------------------------------------------------------------
2026-08-22 改訂(v2)。「図が何のポーズか読み取れない」という指摘を受けた
全面リデザイン。原因は絵の巧拙ではなく構造的な4点だったので、それぞれに
対応する描画プリミティブを用意している:

 (1) 胴体が濃紺ベタ塗りで、腕が体の前を通ると完全に埋もれていた
     → 胴体を「明るいジャージ色の塗り + 濃紺の輪郭」に変更(JERSEY)。
        濃紺の腕を胴体の上に重ねても必ず見える。さらに全ての手足は
        limb() で白フチ(HALO)を下敷きにしてから描くので、腕と腕、
        腕とネットが重なっても互いに分離して見える。

 (2) 指の本数が読めなかった(2本/4本/8本が全部同じギザギザに見えた)
     → fingers() は指を1本ずつ「白フチ→本体」の順に描くため、隣の指の
        白フチが手前の指を削って必ず隙間ができる(=数えられる)。
        加えて num_badge() で本数を数字として明示する。試験で最も問われる
        箇所なので、公式図には無い学習用の補助表示として意図的に足している。

 (3) 「どこを指しているか」で意味が決まるのに、指す対象が無かった
     → net_panel_v()/net_panel_h()/floor()/center_line()/antenna() で
        ネット・フロアー・センターライン・アンテナを実体として描く。

 (4) 動作が抽象記号に置き換わって人の所作に見えなかった
     → 動きのあるシグナルは必ず「腕そのもの」を描き、その上に
        motion_arc() で静止画でも伝わる動きの矢印を重ねる。CSSアニメーション
        (anim_g)は補助であって、静止画だけでも意味が取れる状態にする。

図に載せる文字は「審判/線審」の役職チップと指の本数の数字バッジだけに
限っている(答えを明かす反則名は載せない)。学習画面と出題画面の差は図の
表示サイズとHTML側の説明文で付ける。詳しくは add() のコメントを参照。
---------------------------------------------------------------------------
"""
import json
import math
from pathlib import Path

INK = "#0F1F33"      # 頭・腕・脚・輪郭
JERSEY = "#EDE8DA"   # 胴体(ユニフォーム)の塗り。腕を重ねても見えるよう明るい色にする
ACCENT = "#E8722C"   # 手・指など「動きの主役」を強調するための差し色。
                     # UIの他の場所(ボタン等)で使っている青と被らないよう、
                     # カード色(黄・赤)とも区別しやすいオレンジを採用。
BLUE = "#3E7CB1"     # 数字バッジ・動きの矢印(手のオレンジ、体の紺と区別する)
YELLOW = "#F2B705"
RED = "#D1495B"
WOOD = "#C98A4B"
NETC = "#6B7C8F"     # ネットの網目
HALO = "#FFFFFF"     # 重なりを分離するための白フチ

LIMB_W = 13          # 腕・脚の太さ
HALO_EXTRA = 6       # 白フチの太さ(本体+この値)。大きすぎると腕が交差する
                     # ポーズで互いを削り合って団子になるため、分離が見える
                     # 最小限に抑えている。

VIEW_W, VIEW_H = 230, 264


# ---------------------------------------------------------------------------
# 基本プリミティブ
# ---------------------------------------------------------------------------

def limb(points, color=INK, w=LIMB_W, halo=True):
    """折れ線で手足を描く。halo=Trueのとき、まず白フチを敷いてから本体を描く。
    これにより腕と腕・腕とネットが重なっても互いに分離して見える。
    重なり順は呼び出し順(後に描いたものが手前)になる。"""
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    out = ""
    if halo:
        out += (f'<path d="{d}" fill="none" stroke="{HALO}" stroke-width="{w + HALO_EXTRA}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
    out += (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')
    return out


def arm(x1, y1, x2, y2, bend=20, w=LIMB_W, joint=True):
    """肩(x1,y1)から手(x2,y2)への腕。直線ではなく、体の外側方向にわずかに
    肘を張り出させた2セグメントで描く。肘には明るい関節マーカーを打ち、
    腕がどこで曲がっているか(=どんなポーズか)が読めるようにする。"""
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1
    px, py = -dy / length, dx / length
    sign = 1 if (x1 - 100) >= 0 else -1
    if px * sign < 0:
        px, py = -px, -py
    mx, my = (x1 + x2) / 2 + px * bend, (y1 + y2) / 2 + py * bend
    out = limb([(x1, y1), (mx, my), (x2, y2)], w=w)
    if joint:
        out += f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{w * 0.32:.1f}" fill="{JERSEY}"/>'
    return out


def body(role_label):
    """共通の人型本体(脚→胴→首→頭の順)と役職チップを返す。
    胴体を明るいジャージ色にしてあるため、この後に描く腕が胴体の前を
    通っても埋もれない(v1の最大の欠点だった点)。"""
    chip = ""
    if role_label:
        # 左上の隅にぴったり寄せる。少しでも内側に置くと、上げた手・カードと
        # 重なるシグナル(sig09/sig12/sig13など)が出てくる。
        chip = (f'<rect x="3" y="3" width="42" height="19" rx="6" fill="{INK}"/>'
                f'<text x="24" y="17" text-anchor="middle" font-family="sans-serif" '
                f'font-size="12" font-weight="700" fill="#FFFFFF">{role_label}</text>')
    return (
        limb([(100, 148), (78, 230)]) +
        limb([(100, 148), (122, 230)]) +
        limb([(100, 58), (100, 90)], w=16) +
        f'<path d="M64,84 L136,84 L124,152 L76,152 Z" fill="{JERSEY}" stroke="{INK}" '
        f'stroke-width="5" stroke-linejoin="round"/>' +
        f'<circle cx="100" cy="36" r="24" fill="{INK}"/>' +
        chip
    )


def hand_circle(x, y, r=13, fill=ACCENT):
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 3}" fill="{HALO}"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>')


def hand_bar(x, y, w=30, h=11, angle=0, fill=ACCENT):
    """手のひら(平らな面)。角度をつけて向きを表す。"""
    return (f'<g transform="rotate({angle} {x:.1f} {y:.1f})">'
            f'<rect x="{x - w / 2 - 3:.1f}" y="{y - h / 2 - 3:.1f}" width="{w + 6}" height="{h + 6}" '
            f'rx="6" fill="{HALO}"/>'
            f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w}" height="{h}" rx="4" fill="{fill}"/></g>')


def fingers(x, y, count, spread=14, length=27, angle=-90, w=5):
    """立てた指を count 本描く。指は「白フチ→本体」を1本ずつ順に描くので、
    隣の指の白フチが手前の指を削って必ず隙間ができ、本数が数えられる。
    手のひらは最後に重ねて指の根元をまとめる。"""
    parts = []
    start = x - spread * (count - 1) / 2
    rad = math.radians(angle)
    for i in range(count):
        fx = start + i * spread
        fx2 = fx + length * math.cos(rad)
        fy2 = y + length * math.sin(rad)
        parts.append(f'<line x1="{fx:.1f}" y1="{y:.1f}" x2="{fx2:.1f}" y2="{fy2:.1f}" '
                     f'stroke="{HALO}" stroke-width="{w + 5}" stroke-linecap="round"/>')
        parts.append(f'<line x1="{fx:.1f}" y1="{y:.1f}" x2="{fx2:.1f}" y2="{fy2:.1f}" '
                     f'stroke="{ACCENT}" stroke-width="{w}" stroke-linecap="round"/>')
    parts.append(hand_circle(x, y, 11))
    return "".join(parts)


def thumb_up(x, y, angle=0):
    """親指を立てた手(ダブルフォルト用)。丸い手だと「棒付きの飴」に見えてしまう
    ので、握りこぶしを角丸の四角、親指をその肩口から伸びる細い角丸で描き分ける。"""
    return (f'<g transform="rotate({angle} {x} {y})">'
            f'<rect x="{x - 15}" y="{y - 13}" width="30" height="26" rx="10" fill="{HALO}"/>'
            f'<rect x="{x - 12}" y="{y - 10}" width="24" height="20" rx="8" fill="{ACCENT}"/>'
            f'<rect x="{x - 15}" y="{y - 35}" width="17" height="27" rx="8.5" fill="{HALO}"/>'
            f'<rect x="{x - 12.5}" y="{y - 32}" width="12" height="23" rx="6" fill="{ACCENT}"/></g>')


def card(x, y, color, w=21, h=29, angle=0):
    return (f'<g transform="rotate({angle} {x} {y})">'
            f'<rect x="{x - w / 2 - 2.5:.1f}" y="{y - h / 2 - 2.5:.1f}" width="{w + 5}" height="{h + 5}" '
            f'rx="4" fill="{HALO}"/>'
            f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w}" height="{h}" rx="2.5" '
            f'fill="{color}" stroke="{INK}" stroke-width="1.5"/></g>')


def num_badge(x, y, text, r=17):
    """指の本数を数字で明示する学習用バッジ。指を丁寧に描いても
    サムネイルでは 2/4/8 を見分けられないため、数字を併記する。
    公式ハンドシグナルには無い補助表示であることに注意(免責表示で言及済み)。"""
    return (f'<circle cx="{x}" cy="{y}" r="{r + 3}" fill="{HALO}"/>'
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{BLUE}"/>'
            f'<text x="{x}" y="{y + r * 0.38:.1f}" text-anchor="middle" font-family="sans-serif" '
            f'font-size="{r * 1.35:.0f}" font-weight="700" fill="#FFFFFF">{text}</text>')


# 矢印の先端は markerUnits="userSpaceOnUse" で固定サイズにする。既定の
# strokeWidth 基準だと線の太さに引きずられて先端が小さくなり、一覧の
# サムネイルでは「ただの棒」に見えてしまう。
ARROWHEAD_DEF = (
    '<defs>'
    f'<marker id="ah" markerUnits="userSpaceOnUse" markerWidth="20" markerHeight="20" '
    f'refX="9" refY="10" orient="auto"><path d="M0,1 L19,10 L0,19 Z" fill="{BLUE}"/></marker>'
    f'<marker id="ahA" markerUnits="userSpaceOnUse" markerWidth="20" markerHeight="20" '
    f'refX="9" refY="10" orient="auto"><path d="M0,1 L19,10 L0,19 Z" fill="{ACCENT}"/></marker>'
    '</defs>'
)


def motion_arc(cx, cy, r, start_deg, end_deg, color=BLUE, w=5.5):
    """動きの軌跡を弧＋矢印で示す。CSSアニメーションが効かない場面
    (一覧のサムネイル・印刷・prefers-reduced-motion)でも動きが伝わるように、
    動作系のシグナルには必ずこれを重ねる。
    破線にすると一覧のサムネイルサイズで点が飛んで消えてしまうため、
    実線＋白フチにして小さくても矢印として読めるようにしている。"""
    s, e = math.radians(start_deg), math.radians(end_deg)
    x1, y1 = cx + r * math.cos(s), cy + r * math.sin(s)
    x2, y2 = cx + r * math.cos(e), cy + r * math.sin(e)
    large = 1 if abs(end_deg - start_deg) > 180 else 0
    marker = "ahA" if color == ACCENT else "ah"
    d = f'M{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f}'
    return (f'<path d="{d}" fill="none" stroke="{HALO}" stroke-width="{w + 5}" stroke-linecap="round"/>'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" '
            f'marker-end="url(#{marker})"/>')


def motion_line(x1, y1, x2, y2, color=BLUE, w=5.5):
    """動きの向きを示す直線矢印(実線＋白フチ。理由は motion_arc と同じ)。"""
    marker = "ahA" if color == ACCENT else "ah"
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{HALO}" '
            f'stroke-width="{w + 5}" stroke-linecap="round"/>'
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" '
            f'stroke-linecap="round" marker-end="url(#{marker})"/>')


# ---------------------------------------------------------------------------
# 文脈オブジェクト(ネット・フロアー・ライン・アンテナ)
# 「審判がどこを指しているか」で意味が決まるシグナルは、指す対象が画面に
# 無いと成立しない。v1で最も抜けていた部分。
# ---------------------------------------------------------------------------

def net_panel_v(x=188, y1=44, y2=228, w=34):
    """審判の横(右手側)に立っているネットを、縦帯＋網目で表す。
    タッチネットなど「ネットを示す」シグナル用。
    細長すぎると物差しに見えてしまうので、網目の升目が分かる幅を確保する。"""
    half = w / 2
    parts = [f'<rect x="{x - half}" y="{y1}" width="{w}" height="{y2 - y1}" fill="{HALO}" '
             f'stroke="{INK}" stroke-width="2.5"/>']
    for yy in range(y1 + 14, y2, 16):
        parts.append(f'<line x1="{x - half}" y1="{yy}" x2="{x + half}" y2="{yy}" '
                     f'stroke="{NETC}" stroke-width="1.5"/>')
    for xx in (x - half / 3, x + half / 3):
        parts.append(f'<line x1="{xx:.1f}" y1="{y1 + 10}" x2="{xx:.1f}" y2="{y2}" '
                     f'stroke="{NETC}" stroke-width="1.5"/>')
    parts.append(f'<rect x="{x - half}" y="{y1}" width="{w}" height="10" fill="{INK}"/>')
    return "".join(parts)


def net_panel_h(y=66, x1=126, x2=214, depth=76):
    """ネットを横から見た面(上端の白帯＋下に垂れる網)。
    オーバーネットなど「ネットの上方」を扱うシグナル用。"""
    parts = [f'<rect x="{x1}" y="{y}" width="{x2 - x1}" height="{depth}" fill="{HALO}" '
             f'stroke="{INK}" stroke-width="2.5"/>']
    for xx in range(x1 + 12, x2, 14):
        parts.append(f'<line x1="{xx}" y1="{y}" x2="{xx}" y2="{y + depth}" stroke="{NETC}" stroke-width="1.5"/>')
    for yy in range(y + 14, y + depth, 14):
        parts.append(f'<line x1="{x1}" y1="{yy}" x2="{x2}" y2="{yy}" stroke="{NETC}" stroke-width="1.5"/>')
    parts.append(f'<rect x="{x1}" y="{y}" width="{x2 - x1}" height="9" fill="{INK}"/>')
    return "".join(parts)


def floor(y=246, x1=34, x2=214):
    """コートのフロアー面。イン/アウトなど床を指すシグナル用。"""
    hatch = "".join(f'<line x1="{xx}" y1="{y}" x2="{xx - 8}" y2="{y + 9}" stroke="{NETC}" stroke-width="1.6"/>'
                    for xx in range(x1 + 10, x2 + 1, 15))
    return f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{INK}" stroke-width="4"/>{hatch}'


def center_line(y=228, x1=8, x2=104):
    """センターライン。ペネトレーションフォルト用に、床の上の1本の線として描く。"""
    return (f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{HALO}" stroke-width="11"/>'
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{INK}" stroke-width="6"/>')


def antenna(x=196, y1=20, y2=132):
    """アンテナ(紅白のポール)。線審のアンテナ外通過シグナル用。"""
    parts = [f'<rect x="{x - 5}" y="{y1}" width="10" height="{y2 - y1}" fill="{HALO}" '
             f'stroke="{INK}" stroke-width="2"/>']
    n = 0
    yy = y1
    while yy < y2:
        seg = min(14, y2 - yy)
        if n % 2 == 0:
            parts.append(f'<rect x="{x - 4}" y="{yy + 1}" width="8" height="{seg - 1}" fill="{RED}"/>')
        yy += seg
        n += 1
    return "".join(parts)


def flag(x, y, angle=0, color=WOOD):
    return (f'<g transform="rotate({angle} {x} {y})">'
            f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y - 44}" stroke="{HALO}" stroke-width="9"/>'
            f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y - 44}" stroke="{INK}" stroke-width="4.5"/>'
            f'<path d="M{x},{y - 44} L{x + 30},{y - 35} L{x},{y - 25} Z" fill="{color}" '
            f'stroke="{INK}" stroke-width="1.5"/></g>')



def anim_g(content, cls, origin_x, origin_y):
    """動きそのものが意味を持つ一部のシグナルだけ、CSSアニメーション用の
    グループでラップする(対応する @keyframes は style.css 側で定義)。
    transform-origin をSVGのユーザー単位で指定するため、対応するクラス名は
    style.css の transform-origin ともセットで管理すること。
    なお動きは motion_arc() で静止画にも描いてあるので、アニメーションが
    効かなくても意味は取れる。"""
    return f'<g class="{cls}" style="transform-origin:{origin_x}px {origin_y}px">{content}</g>'


def svg_wrap(inner, role_label):
    return (f'<svg viewBox="0 0 {VIEW_W} {VIEW_H}" xmlns="http://www.w3.org/2000/svg">'
            f'{ARROWHEAD_DEF}{body(role_label)}{inner}</svg>')


SIGNALS = []


def add(id_, name, role_label, inner, hint=""):
    """1シグナル = 1つのSVG。
    当初は学習用(補助ラベル付き)と出題用の2枚を出し分ける設計にしたが、
     ・図の中に日本語ラベルを焼き込むと脚や頭に文字が重なる
     ・その説明文は学習画面のHTML側(名称＋hint)と内容が二重になる
    という2点で割に合わなかったため、SVGは1枚に統一した。
    学習画面と出題画面の差は「図の表示サイズ」と「HTML側に添える説明文」で
    付ける(app.js / style.css 側の責務)。
    数字バッジ・文脈オブジェクト・動きの矢印は"どのシグナルかを識別するための
    情報"なので、出題時にも必要。よって両方の画面で同じ図を使う。"""
    SIGNALS.append({
        "id": id_,
        "name": name,
        "hint": hint,
        "svg": svg_wrap(inner, role_label),
    })


# ---- ファーストレフェリー/セカンドレフェリーの公式ハンドシグナル ----

add("sig01", "サービス許可", "審判",
    arm(122, 95, 172, 78) + hand_bar(186, 74, 30, 11, -18) +
    motion_line(174, 104, 220, 90),
    "サービスを行う方向へ、手のひらを開いて腕を振り出す")

add("sig02", "サービスを行うチーム", "審判",
    arm(122, 95, 184, 95) + hand_bar(198, 95, 28, 11, 0),
    "サービス権を得たチーム側の腕を、水平に横へ上げる")

# コートチェンジは「左右の腕が逆方向に動く=入れ替え」が要点。回転の弧だと
# sig05(選手交代)の回す動きと紛れるので、上下逆向きの直線矢印で表す。
add("sig03", "コートチェンジ", "審判",
    anim_g(arm(78, 95, 38, 126) + hand_circle(38, 126), "anim-swing-l", 78, 95) +
    anim_g(arm(122, 95, 162, 64) + hand_circle(162, 64), "anim-swing-r", 122, 95) +
    motion_line(20, 150, 20, 96) +
    motion_line(182, 46, 182, 100),
    "左腕は前から後ろへ、右腕は後ろから前へ弧を描く(前後に入れ替える動き)")

# タイムアウトは「T字」が読めることが命。頭に重ならない胸の高さの左側に
# T字を置き、両腕は曲げずに直線で描く。横棒を持つ腕はT字の縦棒の上を
# 通過する角度にして、縦棒が腕に隠れないようにしてある(ここを外すと
# 「⌐」と棒に見えてTに読めない)。
add("sig04", "タイムアウト", "審判",
    limb([(78, 108), (46, 114)]) +
    limb([(122, 104), (68, 64)]) +
    f'<rect x="36.5" y="67.5" width="15" height="48" rx="6" fill="{HALO}"/>'
    f'<rect x="39" y="70" width="10" height="43" rx="5" fill="{ACCENT}"/>' +
    hand_bar(44, 62, 38, 11, 0),
    "片方の手を垂直に立て、その上に反対側の手のひらをのせて『T』の字を作る")

# 選手交代は v1 ではオレンジの円だけで、人の動作に全く見えなかった。
# 胸の前で上下に並べた2本の前腕を描き、回転の矢印は前腕と重ならないよう
# 体の左右の外側だけに置く。
add("sig05", "選手交代(サブスティチューション)", "審判",
    limb([(72, 108), (126, 108)]) + hand_circle(128, 108, 11) +
    limb([(128, 130), (74, 130)]) + hand_circle(72, 130, 11) +
    anim_g(motion_arc(100, 119, 50, 128, 232, color=ACCENT, w=5) +
           motion_arc(100, 119, 50, -52, 52, color=ACCENT, w=5),
           "anim-spin", 100, 119),
    "胸の前で両腕の前腕部を、互いに回転させる")

add("sig06", "軽度の不法な行為への警告(イエローカード)", "審判",
    arm(122, 95, 138, 34) + card(138, 18, YELLOW),
    "ステージ2の警告として、イエローカードを掲げる")

add("sig07", "ペナルティ", "審判",
    arm(122, 95, 138, 34) + card(138, 18, RED),
    "ペナルティとして、レッドカードを掲げる")

add("sig08", "退場", "審判",
    arm(122, 95, 140, 40) + card(130, 20, YELLOW) + card(154, 20, RED),
    "退場として、イエローカードとレッドカードを片手で一緒に掲げる")

add("sig09", "失格", "審判",
    arm(78, 95, 64, 42) + card(62, 22, YELLOW) +
    arm(122, 95, 136, 42) + card(138, 22, RED),
    "失格として、イエローカードとレッドカードを左右の手に分けて掲げる")

# 胴体が明るくなったので、腕が胸の前で交差する様子をそのまま描ける
# (v1は抽象的な×印だった)。肘は曲げず直線で1回だけ交差させるのが最も読める。
add("sig10", "セット(ゲーム)の終了", "審判",
    limb([(76, 92), (130, 132)]) + hand_circle(132, 134, 11) +
    limb([(124, 92), (70, 132)]) + hand_circle(68, 134, 11),
    "両腕を胸の前で交差させる")

add("sig11", "サービスでボールをヒットしなかった、またはトスをしないで打った反則", "審判",
    arm(122, 102, 176, 130) + hand_bar(192, 134, 32, 11, -12) +
    motion_line(196, 114, 196, 74),
    "腕を前方に伸ばしたまま、手のひらを上に向けて上げる")

# 8本指。指を描き分けても数えられないので数字バッジを併記する。
# バッジは頭・役職チップと重ならない右上の空きに置く。
add("sig12", "ディレイインサービス(サービス時8秒ルールの反則)", "審判",
    arm(78, 96, 50, 58) + fingers(44, 48, 4, spread=12, length=24, angle=-108) +
    arm(122, 96, 150, 58) + fingers(156, 48, 4, spread=12, length=24, angle=-72) +
    num_badge(202, 40, "8"),
    "両手で指を合計8本、広げて上げる(サービスの8秒超過)")

add("sig13", "ブロックの反則またはスクリーン", "審判",
    arm(78, 95, 66, 34) + hand_bar(64, 18, 26, 11, 6) +
    arm(122, 95, 134, 34) + hand_bar(136, 18, 26, 11, -6),
    "両方の手のひらを前方に向け、両腕を真上に上げる")

add("sig14", "ポジションまたはローテーションの反則", "審判",
    arm(122, 98, 166, 92) +
    f'<line x1="166" y1="92" x2="186" y2="86" stroke="{HALO}" stroke-width="10" stroke-linecap="round"/>'
    f'<line x1="166" y1="92" x2="186" y2="86" stroke="{ACCENT}" stroke-width="6" stroke-linecap="round"/>' +
    anim_g(motion_arc(186, 96, 20, -70, 250, color=ACCENT, w=4.5), "anim-spin", 186, 96),
    "人差し指を伸ばし、その指で円を描く")

add("sig15", "ボール『イン』", "審判",
    floor(246, 34, 214) +
    arm(122, 102, 156, 226) + hand_bar(160, 236, 26, 10, -70),
    "腕を伸ばし、手でフロアー(コートの内側)を指す")

# 前腕を胴体の中央に立てるとサスペンダーのように見えてしまうので、
# 肩の真上に左右対称で立てる。
add("sig16", "ボール『アウト』", "審判",
    limb([(76, 96), (72, 40)]) + hand_bar(72, 26, 26, 11, 0) +
    limb([(124, 96), (128, 40)]) + hand_bar(128, 26, 26, 11, 0),
    "両方の前腕を垂直に立て、手のひらを自分の方に向ける")

add("sig17", "キャッチ(ボールの保持)", "審判",
    arm(78, 102, 46, 134) + hand_bar(36, 142, 32, 11, -22) +
    anim_g(motion_line(34, 122, 34, 78), "anim-lift", 34, 122),
    "片方の手のひらを上に向け、前腕をゆっくり持ち上げる")

add("sig18", "ダブルコンタクト", "審判",
    arm(122, 95, 158, 48) + fingers(166, 36, 2, spread=18, length=27, angle=-72) +
    num_badge(196, 96, "2"),
    "指を2本伸ばし、その手を上げる")

add("sig19", "フォアヒット", "審判",
    arm(122, 95, 158, 48) + fingers(166, 36, 4, spread=12, length=27, angle=-72) +
    num_badge(196, 96, "4"),
    "指を4本伸ばし、その手を上げる")

add("sig20", "選手のタッチネット", "審判",
    net_panel_v(188, 44, 228) +
    arm(122, 95, 162, 104) + hand_bar(174, 107, 24, 10, 10),
    "反則をしたチーム側のネット(の面)を手で示す")

add("sig21", "オーバーネット", "審判",
    net_panel_h(70, 128, 214, 74) +
    arm(122, 92, 158, 58) + hand_bar(178, 56, 30, 11, 4),
    "手のひらを下に向け、ネットの上方にかざす")

add("sig22", "アタックヒットの反則", "審判",
    anim_g(arm(122, 92, 152, 34) + hand_bar(158, 22, 28, 11, -26), "anim-chop", 122, 92) +
    motion_arc(136, 66, 42, -58, 44, color=ACCENT),
    "手のひらを広げて上方に伸ばし、そこから前腕を振り下ろす")

add("sig23", "ペネトレーションフォルト", "審判",
    center_line(228, 8, 100) +
    arm(78, 100, 40, 206) + hand_bar(34, 216, 26, 10, 68),
    "センターライン(または該当するライン)を手で指し示す")

add("sig24", "ダブルフォルトおよびリプレイ", "審判",
    arm(78, 95, 56, 52) + thumb_up(52, 40) +
    arm(122, 95, 144, 52) + thumb_up(148, 40),
    "両方の親指を立て、両腕を上げる")

# ワンタッチは v1 では両手が胴体に完全に埋もれていた。胸の前に重ねると
# 団子になるので、体の左脇の空きに縦に間隔をとって並べる。
# 下=指を立てた手、その指先の少し上=なでる手のひら、さらに上=なでる方向の矢印。
add("sig25", "ボールコンタクト(ワンタッチ)", "審判",
    limb([(78, 112), (48, 142)]) +
    fingers(44, 138, 3, spread=11, length=24, angle=-90) +
    limb([(122, 108), (66, 98)]) + hand_bar(50, 96, 30, 10, 8) +
    motion_line(80, 78, 32, 84, color=ACCENT, w=5),
    "垂直に立てた手の指先を、他方の手でブラシをかけるようになでる")

# 「手首にカードをあてる」= 前腕とカードが接している事が読めれば成立する。
# 前腕を体の右前に水平に出し、そこへカードを添える形にする。
add("sig26", "ディレイウォーニングまたはディレイペナルティ", "審判",
    limb([(80, 108), (168, 122)]) + hand_circle(174, 123, 11) +
    limb([(124, 100), (146, 92)]) +
    card(148, 108, YELLOW, w=19, h=26, angle=14),
    "イエローカード(またはレッドカード)を、他方の手首にあてる")

# ---- ラインジャッジ(線審)の公式フラッグシグナル ----

add("sig27", "ボール『イン』(ラインジャッジ)", "線審",
    floor(246, 34, 214) +
    arm(122, 98, 148, 200) + flag(150, 210, angle=182),
    "フラッグを下げて、ボールがインであることを示す")

add("sig28", "ボール『アウト』(ラインジャッジ)", "線審",
    arm(122, 95, 136, 56) + flag(136, 50),
    "フラッグを真上に上げて、ボールがアウトであることを示す")

# もう一方の手を旗の先端にのせる動作。旗を右に立てると、届かせる腕が
# 頭を貫いてしまうので、旗を左に立てて腕を頭の下で交差させる。
# 描画順は「渡す腕 → 旗を持つ腕と旗 → 先端にのせる手のひら」。旗を腕より
# 後に描かないと、旗が腕の白フチに潰されて三角が消える。
add("sig29", "ボールコンタクト(ラインジャッジ)", "線審",
    limb([(122, 106), (66, 26)]) +
    arm(78, 96, 56, 72) + flag(56, 72) +
    hand_bar(56, 16, 28, 10, 8),
    "フラッグを立て、他方の手のひらをフラッグの先端にのせる")

add("sig30", "ボールのアンテナ外通過・フットフォルト等(ラインジャッジ)", "線審",
    antenna(200, 20, 140) +
    arm(122, 95, 140, 52) +
    anim_g(flag(140, 46), "anim-wave", 140, 46) +
    motion_arc(140, 34, 30, 200, 340, color=ACCENT, w=4.5),
    "アンテナまたはラインを指し示し、フラッグを頭上で左右に振る")

# sig10(セット終了)と同じ所作。役職チップの「審判」/「線審」で区別する。
add("sig31", "判定不能(ラインジャッジ)", "線審",
    limb([(76, 92), (130, 132)]) + hand_circle(132, 134, 11) +
    limb([(124, 92), (70, 132)]) + hand_circle(68, 134, 11),
    "両腕を胸の前で交差させ、判定できなかったことを示す")

out_path = Path(__file__).resolve().parent.parent / "signals.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"signals": SIGNALS}, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("generated", len(SIGNALS), "signals ->", out_path)
