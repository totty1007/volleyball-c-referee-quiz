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


# v2の arm()(肩と手から肘を自動計算する腕)は、腕を体の前へ回すポーズで
# 人体としてあり得ない肘の曲がり方になったため v3 で削除した。
# 腕は必ず arm3()(肘を明示する)で描く。


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


# v2の hand_bar()(平たい棒の手)は、手のひらの向き(前方/自分/上/下)を
# 描き分けられず「全部天井向きに見える」原因だったため v3 で削除した。
# 手は必ず hand() で描く。


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


def motion_arc(cx, cy, r, start_deg, end_deg, color=BLUE, w=5.5, sweep=1):
    """動きの軌跡を弧＋矢印で示す。CSSアニメーションが効かない場面
    (一覧のサムネイル・印刷・prefers-reduced-motion)でも動きが伝わるように、
    動作系のシグナルには必ずこれを重ねる。
    破線にすると一覧のサムネイルサイズで点が飛んで消えてしまうため、
    実線＋白フチにして小さくても矢印として読めるようにしている。
    sweep は回す向き。1=時計回り、0=反時計回り。v3で追加した引数で、
    アタックヒットの反則やキャッチのように「体の前を通って上下する」動きを
    描くのに必要(既定の時計回りだけだと腕が体の外側を回ってしまう)。"""
    s, e = math.radians(start_deg), math.radians(end_deg)
    x1, y1 = cx + r * math.cos(s), cy + r * math.sin(s)
    x2, y2 = cx + r * math.cos(e), cy + r * math.sin(e)
    span = (end_deg - start_deg) % 360 if sweep else (start_deg - end_deg) % 360
    large = 1 if span > 180 else 0
    marker = "ahA" if color == ACCENT else "ah"
    d = f'M{x1:.1f},{y1:.1f} A{r},{r} 0 {large} {sweep} {x2:.1f},{y2:.1f}'
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


# ---------------------------------------------------------------------------
# v3(2026-08-28)で追加したプリミティブ
#
# v2は「図がまだ分かりづらい」という指摘を受けた。今度は絵の構造ではなく
# 人体としての正しさが原因で、指摘は具体的に次の3点に集約された:
#
#  (A) 腕を挙げているのか下げているのかが読めない。しかも arm() が肩と手の
#      座標から肘を自動で外側へ張り出させていたため、腕を体の前へ回すポーズ
#      (キャッチ・タッチネット)で「その角度に肘は曲がらない」形になっていた。
#      → arm3() で肘の位置を必ず明示し、人体としてあり得る曲げ方だけを描く。
#
#  (B) 手のひらの向きがシグナルの意味そのものなのに(前方に向ける/自分に
#      向ける/上に向ける/下に向ける)、hand_bar() の平たい棒では全部同じに
#      見えていた。
#      → hand() の4種類のグリフに統一。どの向きでも共通のルールで、
#        ・手のひら側 = 明るい面(PALM_FACE)＋手相の線
#        ・手の甲側   = 関節の点＋指先の爪
#        を描くので、サムネイルサイズでも向きが1目で分かる。
#
#  (C) 動作系のシグナルは終了姿勢だけを描いていたため、「どこから どこへ」の
#      動きが伝わらなかった(公式図は開始姿勢を破線で描いている)。
#      → ghost() で開始姿勢を薄い破線で重ね、step_chip() で ①→② の順序を示す。
# ---------------------------------------------------------------------------

UPPER_W = 15         # 上腕(肩→肘)。前腕より太くして肩の位置を読ませる
FORE_W = 12          # 前腕(肘→手)
PALM_FACE = JERSEY   # 手のひらの面。手の甲側には描かない(向きの識別に使う)


def arm3(sx, sy, ex, ey, hx, hy, joint=True):
    """肩(sx,sy)→肘(ex,ey)→手(hx,hy)。肘の位置を呼び出し側が必ず指定する腕。
    白フチは肩から手までを1本の折れ線として先に敷く(上腕と前腕で別々に敷くと
    互いの白フチが肘を削って関節が千切れて見える)。"""
    d = f"M{sx:.1f},{sy:.1f} L{ex:.1f},{ey:.1f} L{hx:.1f},{hy:.1f}"
    out = (f'<path d="{d}" fill="none" stroke="{HALO}" stroke-width="{UPPER_W + HALO_EXTRA}" '
           f'stroke-linecap="round" stroke-linejoin="round"/>')
    out += limb([(sx, sy), (ex, ey)], w=UPPER_W, halo=False)
    out += limb([(ex, ey), (hx, hy)], w=FORE_W, halo=False)
    if joint:
        out += (f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{UPPER_W * 0.34:.1f}" fill="{JERSEY}" '
                f'stroke="{INK}" stroke-width="1.6"/>')
    return out


def _hand_face(back, palm_w=27, palm_h=18, fin_len=16, fin_w=5.6):
    """正面から見た開いた手。原点=手首、-Y方向(上)へ指先が伸びる。
    back=False → 手のひらがこちらを向いている(=手のひらを前方に向けた手)
    back=True  → 手の甲がこちらを向いている(=手のひらを自分に向けた手)
    親指を出す側も左右で描き分け、鏡像として「表か裏か」が分かるようにする。"""
    xs = [-palm_w / 2 + palm_w * (i + 0.5) / 4 for i in range(4)]
    top = -palm_h
    halo = [f'<rect x="{-palm_w / 2 - 3:.1f}" y="{top - 3:.1f}" width="{palm_w + 6:.1f}" '
            f'height="{palm_h + 9:.1f}" rx="8" fill="{HALO}"/>']
    main = [f'<rect x="{-palm_w / 2:.1f}" y="{top:.1f}" width="{palm_w:.1f}" '
            f'height="{palm_h + 3:.1f}" rx="6" fill="{ACCENT}"/>']
    for fx in xs:
        halo.append(f'<line x1="{fx:.1f}" y1="{top + 2}" x2="{fx:.1f}" y2="{top - fin_len:.1f}" '
                    f'stroke="{HALO}" stroke-width="{fin_w + 5:.1f}" stroke-linecap="round"/>')
        main.append(f'<line x1="{fx:.1f}" y1="{top + 2}" x2="{fx:.1f}" y2="{top - fin_len:.1f}" '
                    f'stroke="{ACCENT}" stroke-width="{fin_w:.1f}" stroke-linecap="round"/>')
    tsx = (palm_w / 2 - 2) if back else (-palm_w / 2 + 2)
    tex = tsx + (14 if back else -14)
    halo.append(f'<line x1="{tsx:.1f}" y1="-1" x2="{tex:.1f}" y2="{top - 2:.1f}" '
                f'stroke="{HALO}" stroke-width="{fin_w + 7:.1f}" stroke-linecap="round"/>')
    main.append(f'<line x1="{tsx:.1f}" y1="-1" x2="{tex:.1f}" y2="{top - 2:.1f}" '
                f'stroke="{ACCENT}" stroke-width="{fin_w + 1.8:.1f}" stroke-linecap="round"/>')
    out = "".join(halo) + "".join(main)
    if back:
        out += "".join(f'<circle cx="{fx:.1f}" cy="{top + 4:.1f}" r="2.3" fill="{INK}" '
                       f'opacity="0.8"/>' for fx in xs)
        out += "".join(f'<line x1="{fx:.1f}" y1="{top - fin_len + 2.5:.1f}" x2="{fx:.1f}" '
                       f'y2="{top - fin_len + 5.5:.1f}" stroke="{HALO}" '
                       f'stroke-width="{fin_w - 1.6:.1f}" stroke-linecap="round"/>' for fx in xs)
    else:
        out += (f'<rect x="{-palm_w / 2 + 4:.1f}" y="{top + 4:.1f}" width="{palm_w - 8:.1f}" '
                f'height="{palm_h - 3:.1f}" rx="5" fill="{PALM_FACE}"/>')
        out += (f'<path d="M{-palm_w / 2 + 6.5:.1f},{top + 8:.1f} Q0,{top + 13.5:.1f} '
                f'{palm_w / 2 - 6.5:.1f},{top + 9:.1f}" fill="none" stroke="{ACCENT}" '
                f'stroke-width="1.8" opacity="0.85"/>')
    return out


def _hand_side(face_up, length=34, thick=15):
    """側面から見た平らな手(公式図⑪のウェッジ形)。原点=手首、+X方向へ指先。
    手のひら側に明るい面と『受け皿』の弧を入れて、上向き/下向きを描き分ける。"""
    s = -1 if face_up else 1      # SVGは下が+Y。上向きの手のひら面は -Y 側
    h = thick / 2
    # 指先はとがらせず、短い縦の辺で切る。先を1点に絞ると、サムネイルでは
    # 手ではなく「矢印の先端」に見えてしまい、隣に置いた動きの矢印と混ざる。
    shape = (f'M0,{-h:.1f} L{length * 0.68:.1f},{-h * 0.92:.1f} L{length:.1f},{-h * 0.42:.1f} '
             f'L{length:.1f},{h * 0.42:.1f} L{length * 0.68:.1f},{h * 0.92:.1f} L0,{h:.1f} Z')
    out = (f'<path d="M0,{-h - 3.5:.1f} L{length * 0.68:.1f},{-h - 3:.1f} '
           f'L{length + 3.5:.1f},{-h * 0.42 - 3:.1f} L{length + 3.5:.1f},{h * 0.42 + 3:.1f} '
           f'L{length * 0.68:.1f},{h + 3:.1f} L0,{h + 3.5:.1f} Z" fill="{HALO}"/>')
    out += f'<path d="{shape}" fill="{ACCENT}"/>'
    out += (f'<path d="M2.5,{s * h * 0.66:.1f} L{length * 0.68:.1f},{s * h * 0.5:.1f}" fill="none" '
            f'stroke="{PALM_FACE}" stroke-width="5.4" stroke-linecap="round"/>')
    out += (f'<path d="M3,{s * (h + 8):.1f} Q{length * 0.44:.1f},{s * (h + 1.5):.1f} '
            f'{length * 0.84:.1f},{s * (h + 7):.1f}" fill="none" stroke="{INK}" '
            f'stroke-width="3" stroke-linecap="round" opacity="0.8"/>')
    return out


def hand(kind, x, y, rot=0, mirror=False):
    """手のひらの向きが必ず読める手のグリフ。向きはシグナルの意味そのもの
    なので、v3では手を必ずこの関数で描く(hand_bar() は使わない)。
      "front" = 手のひらを前方(=見ている側)に向ける
      "self"  = 手のひらを自分に向ける(=手の甲がこちら)
      "up"    = 手のひらを上に向ける
      "down"  = 手のひらを下に向ける
    rot は front/self では指先の向き、up/down では手の伸びる向きの回転角。
    mirror=True で左右反転する。両手を使うシグナルは、反転しないと片方の
    親指が体の外側、もう片方が内側に出てしまい人の手に見えない。"""
    if kind in ("front", "self"):
        inner = _hand_face(kind == "self")
    else:
        # 側面から見た手は、指先が左を向く角度(|rot|>90)まで回すと上下が
        # 裏返り、「手のひらを上に向ける」が下向きになってしまう。
        # 回転後に世界座標でどちらを向くかで、描く側を先に反転しておく。
        flipped = abs(((rot + 180) % 360) - 180) > 90
        inner = _hand_side((kind == "up") != flipped)
    flip = " scale(-1 1)" if mirror else ""
    return f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot}){flip}">{inner}</g>'


def point_hand(x, y, angle=0, fin_len=27):
    """人差し指1本を伸ばした手。原点=手首、angle=指す方向(0で右向き)。
    v2は「握りの丸＋指の線」だけだったため、杖やフラッグを持っているように
    見えていた(2026-08-28指摘)。握りを角丸の四角、親指をその上のこぶとして
    描き、そこから指が1本出ている形にして『指さし』に見えるようにする。"""
    fx, fy = 13, -4.5
    tx, ty = fx + fin_len, fy
    inner = (
        f'<rect x="-8" y="-13" width="25" height="26" rx="10" fill="{HALO}"/>'
        f'<rect x="{fx - 2}" y="{fy - 6.5:.1f}" width="{fin_len + 4}" height="13" rx="6.5" fill="{HALO}"/>'
        f'<rect x="-5" y="-10" width="19" height="20" rx="8" fill="{ACCENT}"/>'
        f'<rect x="-1" y="-16" width="13" height="11" rx="5.5" fill="{HALO}"/>'
        f'<rect x="1" y="-14" width="9" height="8" rx="4" fill="{ACCENT}"/>'
        f'<line x1="{fx}" y1="{fy}" x2="{tx}" y2="{ty}" stroke="{ACCENT}" stroke-width="8" '
        f'stroke-linecap="round"/>'
    )
    return f'<g transform="translate({x:.1f} {y:.1f}) rotate({angle})">{inner}</g>'


def ghost(content):
    """開始姿勢(公式図が破線で描いているもの)。動作系のシグナルは終了姿勢
    だけでは「腕を挙げたのか下げたのか」が読めないため、開始姿勢を薄い
    破線で重ねる。塗り(手のグリフ)も一緒に薄くなるので、終了姿勢との
    見分けは付く。"""
    return f'<g opacity="0.3" stroke-dasharray="7 5">{content}</g>'


def step_chip(x, y, n="1"):
    """動作の順序(①→②)。開始姿勢と終了姿勢のどちらが先かを明示する。
    num_badge() の青丸(指の本数)と混ざらないよう、白地＋青枠にしている。"""
    return (f'<circle cx="{x}" cy="{y}" r="12.5" fill="{HALO}"/>'
            f'<circle cx="{x}" cy="{y}" r="10.5" fill="#FFFFFF" stroke="{BLUE}" stroke-width="2.6"/>'
            f'<text x="{x}" y="{y + 4.6:.1f}" text-anchor="middle" font-family="sans-serif" '
            f'font-size="14" font-weight="700" fill="{BLUE}">{n}</text>')


def contact_mark(x, y, r=13, color=BLUE):
    """「ここに触れている」ことを示す接触マーク。タッチネットのように
    ネットのどこに触れるかで意味が決まるシグナル用。"""
    parts = [f'<circle cx="{x}" cy="{y}" r="{r + 2.5}" fill="{HALO}" opacity="0.9"/>']
    for deg in (-58, -18, 22, 62):
        a = math.radians(deg)
        parts.append(f'<line x1="{x + r * 0.55 * math.cos(a):.1f}" y1="{y + r * 0.55 * math.sin(a):.1f}" '
                     f'x2="{x + r * 1.25 * math.cos(a):.1f}" y2="{y + r * 1.25 * math.sin(a):.1f}" '
                     f'stroke="{color}" stroke-width="3.2" stroke-linecap="round"/>')
    return "".join(parts)


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
#
# v3(2026-08-28)では全ポーズを arm3()(肘を明示した腕)と hand()(手のひらの
# 向きが読めるグリフ)で描き直した。座標を触るときの原則:
#   ・肩は左(76,92)/右(124,92)。頭は中心(100,36)半径24、胴は y=84〜152。
#   ・上腕と前腕の長さはできるだけ揃える(片方が2倍近くなると骨折して見える)。
#   ・肘は「その向きに人体が曲がるか」を必ず確認する。肘は体の後ろには
#     曲がらないし、前腕は上腕の内側へ180度は畳めない。
#   ・手のひらの向きは規則の文言そのままを hand() の種類で表す
#     ("front"=前方 / "self"=自分 / "up"=上 / "down"=下)。
#   ・動作系は ghost() で開始姿勢を描き、step_chip() で ①→② を振る。

add("sig01", "サービス許可", "審判",
    arm3(124, 92, 152, 80, 180, 68) + hand("front", 184, 64, 67, mirror=True) +
    motion_arc(124, 92, 74, 56, 14, sweep=0),
    "サービスを行う方向へ、手のひらを開いたまま腕を振り出す")

add("sig02", "サービスを行うチーム", "審判",
    arm3(124, 92, 154, 93, 184, 94) + hand("front", 188, 94, 92),
    "サービス権を得たチーム側の腕を、水平に横へ上げる(振らずに止める)")

# コートチェンジは「左右の腕が逆方向に動く=入れ替え」が要点。回転の弧だと
# sig05(選手交代)の回す動きと紛れるので、上下逆向きの直線矢印で表す。
add("sig03", "コートチェンジ", "審判",
    anim_g(arm3(76, 94, 58, 114, 36, 128) + hand("self", 32, 130, 244), "anim-swing-l", 76, 94) +
    anim_g(arm3(124, 94, 146, 80, 168, 62) + hand("self", 172, 58, 116), "anim-swing-r", 124, 94) +
    motion_line(11, 158, 11, 104) +
    motion_line(205, 38, 205, 92),
    "左腕は前から後ろへ、右腕は後ろから前へ弧を描く(前後に入れ替える動き)")

# タイムアウトは「T字」が読めることが命。縦棒は「指を上に立てた手」、横棒は
# 「手のひらを下に向けた手」で描き分ける。横棒を持つ腕は縦棒の指先の上を
# 通す角度にして、縦棒が腕に隠れないようにしてある(ここを外すと「⌐」と棒に
# 見えてTに読めない)。
add("sig04", "タイムアウト", "審判",
    arm3(76, 104, 56, 138, 44, 112) + hand("front", 44, 112, 0) +
    arm3(124, 98, 112, 74, 70, 70) + hand("down", 66, 72, 180),
    "片方の手を指先を上にして垂直に立て、その指先の上に反対の手のひらを"
    "下向きにのせて『T』の字を作る")

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
    arm3(124, 94, 146, 74, 140, 46) + card(140, 28, YELLOW),
    "肘を曲げて前腕を立て、イエローカードを頭の高さに掲げる")

add("sig07", "ペナルティ", "審判",
    arm3(124, 94, 146, 74, 140, 46) + card(140, 28, RED),
    "肘を曲げて前腕を立て、レッドカードを頭の高さに掲げる")

add("sig08", "退場", "審判",
    arm3(124, 94, 146, 74, 142, 48) + card(131, 30, YELLOW) + card(155, 30, RED),
    "イエローカードとレッドカードを、片手で一緒に掲げる")

add("sig09", "失格", "審判",
    arm3(76, 94, 54, 74, 58, 48) + card(56, 30, YELLOW) +
    arm3(124, 94, 146, 74, 142, 48) + card(144, 30, RED),
    "イエローカードとレッドカードを、左右の手に分けて別々に掲げる")

# セット終了は「腕の交差する高さ」が要点。v2は両手を腰の高さまで下げて
# しまっていたが、公式図は肘を体の横に落として前腕を斜め上へ交差させ、
# 手は反対側の肩の高さまで来る(2026-08-28指摘)。手の甲がこちらを向く。
add("sig10", "セット(ゲーム)の終了", "審判",
    arm3(76, 94, 66, 128, 108, 96) +
    arm3(124, 94, 134, 128, 92, 96) +
    hand("self", 92, 96, -40) + hand("self", 108, 96, 40),
    "肘を体の横に下げ、両方の前腕を胸の前で斜め上に交差させる"
    "(手は開いて反対側の肩の高さ・手の甲が相手側)")

# 公式図は「腕を下げた状態(破線)→前方水平まで上げる」の2姿勢で描かれている。
# v2は終了姿勢を斜め下に描いていたため、腕を上げる動作に見えなかった。
add("sig11", "サービスでボールをヒットしなかった、またはトスをしないで打った反則", "審判",
    ghost(arm3(124, 94, 138, 126, 148, 158) + hand("up", 150, 160, 68)) +
    arm3(124, 96, 154, 102, 186, 106) + hand("up", 188, 106, 6) +
    motion_arc(124, 96, 76, 60, 22, sweep=0) +
    step_chip(176, 184) + step_chip(178, 68, "2"),
    "腕を前方にまっすぐ伸ばし、手のひらを上に向けたまま、"
    "下げた位置から水平まで上げる")

# 8本指。指を描き分けても数えられないので数字バッジを併記する。
# 肘は体の横に落とし、前腕を立てて手を顔の高さに置く(公式図の形)。
add("sig12", "ディレイインサービス(サービス時8秒ルールの反則)", "審判",
    arm3(76, 94, 56, 114, 50, 78) + fingers(48, 68, 4, spread=13, length=24, angle=-100) +
    arm3(124, 94, 144, 114, 150, 78) + fingers(152, 68, 4, spread=13, length=24, angle=-80) +
    num_badge(200, 42, "8"),
    "肘を下げて前腕を立て、両手で指を合計8本、広げて顔の高さに上げる")

# 「手のひらを前方に向ける」が意味なので、天井向きの平手ではなく
# こちらを向いた手のひら(明るい面＋手相の線)で描く(2026-08-28指摘)。
add("sig13", "ブロックの反則またはスクリーン", "審判",
    arm3(76, 92, 70, 66, 64, 44) + hand("front", 64, 44, -8) +
    arm3(124, 92, 130, 66, 136, 44) + hand("front", 136, 44, 8, mirror=True),
    "両腕を真上に伸ばし、両方の手のひらを前方(相手コート側)に向ける"
    "。天井に向けるのではない")

add("sig14", "ポジションまたはローテーションの反則", "審判",
    arm3(124, 96, 150, 100, 172, 96) + hand_circle(172, 96, 11) +
    f'<line x1="172" y1="96" x2="194" y2="89" stroke="{HALO}" stroke-width="11" stroke-linecap="round"/>'
    f'<line x1="172" y1="96" x2="194" y2="89" stroke="{ACCENT}" stroke-width="6" stroke-linecap="round"/>' +
    anim_g(motion_arc(196, 100, 21, -70, 250, color=ACCENT, w=4.5), "anim-spin", 196, 100),
    "握った手から人差し指だけを伸ばし、その指先で円を描く")

# v2は肩から床近くまで1本の腕を伸ばしていて「旗を持っているのか」に
# 見えていた(2026-08-28指摘)。肘を明示して腕の長さを人体の比率に戻し、
# 指し示しているのは伸ばした人差し指であることを分かるようにする。
add("sig15", "ボール『イン』", "審判",
    floor(246, 34, 214) +
    arm3(124, 96, 148, 124, 166, 152) + point_hand(166, 152, 58) +
    motion_line(186, 184, 195, 224),
    "腕と指をフロアー(コートの内側)へ向けて斜め下に伸ばし、指先で床を指す")

# 「手のひらを自分に向ける」が意味。平手だと天井向きに見えてしまうので、
# 手の甲(関節の点＋指先の爪)をこちらに向けた手で描く(2026-08-28指摘)。
add("sig16", "ボール『アウト』", "審判",
    arm3(76, 92, 52, 96, 50, 62) + hand("self", 50, 62, 0) +
    arm3(124, 92, 148, 96, 150, 62) + hand("self", 150, 62, 0, mirror=True),
    "上腕を体の横に張り、肘を直角に曲げて両方の前腕を垂直に立て、"
    "手のひらを自分の方に向ける(こちらから見えるのは手の甲)")

# v2は肘を自動計算していたため「その角度に肘は曲がらない」形になっていた
# (2026-08-28指摘)。肘を体の横に固定し、前腕だけを持ち上げる動きにする。
add("sig17", "キャッチ(ボールの保持)", "審判",
    ghost(arm3(76, 96, 66, 126, 56, 150) + hand("up", 56, 150, 120)) +
    anim_g(arm3(76, 96, 66, 126, 44, 116) + hand("up", 44, 116, 184), "anim-lift", 66, 126) +
    motion_arc(66, 126, 40, 118, 176, sweep=1) +
    step_chip(70, 178) + step_chip(20, 94, "2"),
    "肘を体の横に付けたまま手のひらを上に向け、前腕だけをゆっくり持ち上げる")

add("sig18", "ダブルコンタクト", "審判",
    arm3(124, 94, 148, 74, 158, 48) + fingers(158, 46, 2, spread=18, length=26, angle=-74) +
    num_badge(198, 96, "2"),
    "肘を曲げて前腕を立て、指を2本伸ばして上げる")

add("sig19", "フォアヒット", "審判",
    arm3(124, 94, 148, 74, 158, 48) + fingers(158, 46, 4, spread=12, length=26, angle=-74) +
    num_badge(198, 96, "4"),
    "肘を曲げて前腕を立て、指を4本伸ばして上げる")

# v2はネットの真ん中あたりを平手で指していて「どこを指すのか」「手のひらは
# どちら向きか」が伝わらなかった(2026-08-28指摘)。示すのはネットの上端
# (白帯)なので、その帯を青枠で囲み、手のひらを下に向けて帯の上に置く。
add("sig20", "選手のタッチネット", "審判",
    net_panel_v(188, 44, 228) +
    f'<rect x="158" y="35" width="60" height="29" rx="8" fill="none" stroke="{BLUE}" '
    f'stroke-width="3"/>' +
    arm3(124, 92, 150, 76, 164, 48) + hand("down", 164, 48, 6),
    "反則をしたチーム側のネットの上端(白帯)に、手のひらを下に向けて触れる")

add("sig21", "オーバーネット", "審判",
    net_panel_h(70, 128, 214, 74) +
    arm3(124, 92, 148, 74, 172, 60) + hand("down", 176, 58, 6),
    "肘を曲げて腕を前に出し、手のひらを下に向けてネットの上方にかざす")

# 公式は「前腕を垂直に上げ、そこから振り下ろす」動作。v2は終了姿勢だけを
# 斜め上に描いていたので、上げたのか下ろしたのかが読めなかった
# (2026-08-28指摘)。①上げた姿勢を破線、②顔の前まで振り下ろした姿勢を実線で
# 描き、体の前を通る反時計回りの弧でつなぐ。
add("sig22", "アタックヒットの反則", "審判",
    ghost(arm3(124, 92, 148, 72, 156, 38) + hand("front", 156, 38, 12, mirror=True)) +
    anim_g(arm3(124, 92, 148, 72, 116, 80) + hand("down", 112, 80, 174), "anim-chop", 148, 72) +
    motion_arc(148, 72, 34, -77, 166, color=ACCENT, sweep=0) +
    step_chip(194, 42) + step_chip(94, 110, "2"),
    "手のひらを開いて前腕を垂直に上げ、そこから前腕を顔の前へ振り下ろす"
    "(振り下ろした手のひらは下向き)")

add("sig23", "ペネトレーションフォルト", "審判",
    center_line(228, 8, 100) +
    arm3(76, 98, 66, 132, 56, 170) + point_hand(56, 170, 118) +
    motion_line(40, 196, 30, 220),
    "センターライン(または該当するライン)を、伸ばした指で指し示す")

add("sig24", "ダブルフォルトおよびリプレイ", "審判",
    arm3(76, 94, 56, 78, 54, 50) + thumb_up(52, 38) +
    arm3(124, 94, 144, 78, 146, 50) + thumb_up(148, 38),
    "肘を曲げて両方の前腕を立て、両手の親指を立てて上げる")

# ワンタッチは v1 では両手が胴体に完全に埋もれていた。v3では「指を立てた手」
# を hand("front") の縦向き、「なでる手」を hand("down") の横向きにして、
# 2つの手の役割の違い(立てる/なでる)が形で分かるようにしてある。
add("sig25", "ボールコンタクト(ワンタッチ)", "審判",
    arm3(76, 104, 58, 140, 44, 164) + hand("front", 44, 164, 0) +
    arm3(124, 100, 102, 116, 74, 128) + hand("down", 70, 130, 180) +
    motion_line(64, 112, 26, 116, w=5),
    "片方の手を指先を上にして垂直に立て、その指先を他方の手のひらで"
    "ブラシをかけるようになでる")

# 「手首にカードをあてる」= 前腕とカードが接している事が読めれば成立する。
# 前腕を体の前に水平に出し、そこへ反対の手でカードを添える形にする。
add("sig26", "ディレイウォーニングまたはディレイペナルティ", "審判",
    arm3(76, 106, 120, 114, 162, 122) + hand_circle(166, 123, 11) +
    arm3(124, 96, 140, 100, 150, 110) +
    card(153, 114, YELLOW, w=19, h=26, angle=16),
    "片腕を前に水平に伸ばし、その手首にイエローカード(またはレッドカード)をあてる")

# ---- ラインジャッジ(線審)の公式フラッグシグナル ----

add("sig27", "ボール『イン』(ラインジャッジ)", "線審",
    floor(246, 34, 214) +
    arm3(124, 98, 146, 134, 152, 172) + flag(152, 182, angle=182),
    "腕を下ろし、フラッグを下に向けて下げる")

add("sig28", "ボール『アウト』(ラインジャッジ)", "線審",
    arm3(124, 94, 142, 74, 146, 52) + flag(146, 52),
    "肘を曲げて前腕を立て、フラッグを真上に上げる")

# もう一方の手を旗の先端にのせる動作。旗を右に立てると届かせる腕が
# 頭を貫いてしまうので、旗を左に立てて腕を顔の前で交差させる。
# 描画順は「渡す腕 → 旗を持つ腕と旗 → 先端にのせる手のひら」。旗を腕より
# 後に描かないと、旗が腕の白フチに潰されて三角が消える。
add("sig29", "ボールコンタクト(ラインジャッジ)", "線審",
    arm3(124, 104, 94, 84, 72, 50) +
    arm3(76, 104, 52, 116, 38, 96) + flag(38, 96) +
    hand("down", 68, 48, 184),
    "フラッグを立て、他方の手のひらを下に向けてフラッグの先端にのせる")

add("sig30", "ボールのアンテナ外通過・フットフォルト等(ラインジャッジ)", "線審",
    antenna(200, 20, 140) +
    arm3(124, 94, 142, 74, 148, 50) +
    anim_g(flag(148, 50), "anim-wave", 148, 50) +
    motion_arc(148, 26, 32, 208, 332, color=ACCENT, w=4.5),
    "アンテナまたはラインを指し示し、フラッグを頭上で左右に振る")

# sig10(セット終了)と同じ所作。役職チップの「審判」/「線審」で区別する。
add("sig31", "判定不能(ラインジャッジ)", "線審",
    arm3(76, 94, 66, 128, 108, 96) +
    arm3(124, 94, 134, 128, 92, 96) +
    hand("self", 92, 96, -40) + hand("self", 108, 96, 40),
    "肘を体の横に下げ、両方の前腕を胸の前で斜め上に交差させ、"
    "判定できなかったことを示す")

# ---------------------------------------------------------------------------
# 図の読み方(凡例)
# v3で手のひらの向きと開始姿勢の表し方を決めたので、その表し方自体を学習画面
# の冒頭で説明する。凡例が無いと「明るい面は何?」「薄い腕は何?」が分からず、
# せっかく描き分けた向きが伝わらない。app.js の renderSignalList() が
# signals.json の legend を読んで並べる。凡例を増やすときは、免責表示
# (app.js の notice-banner)の文言も合わせて見直すこと。
# ---------------------------------------------------------------------------

LEGEND = []


def add_legend(label, inner, w=96, h=72):
    LEGEND.append({
        "label": label,
        "svg": (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
                f'{ARROWHEAD_DEF}{inner}</svg>'),
    })


add_legend("手のひらを前に向けた手。明るい面と手相の線が見える側が手のひら",
           hand("front", 48, 56, 0))
add_legend("手のひらを自分に向けた手。関節の点と爪が見える側が手の甲",
           hand("self", 48, 56, 0))
add_legend("手のひらを上に向けた手。明るい面が上側に付く",
           hand("up", 30, 38, 0))
add_legend("手のひらを下に向けた手。明るい面が下側に付く",
           hand("down", 30, 34, 0))
add_legend("薄い破線は動き出す前の姿勢。濃い方が動き終わった姿勢",
           ghost(arm3(22, 18, 32, 42, 42, 64)) + arm3(22, 18, 50, 28, 80, 36))
add_legend("①→②は動作の順番。青い矢印はその間の動き",
           step_chip(22, 40) + motion_line(40, 40, 60, 40) + step_chip(78, 40, "2"))


out_path = Path(__file__).resolve().parent.parent / "signals.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"signals": SIGNALS, "legend": LEGEND}, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("generated", len(SIGNALS), "signals /", len(LEGEND), "legend ->", out_path)
