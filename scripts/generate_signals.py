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
     → 指を1本ずつ「白フチ→本体」の順に描くため、隣の指の白フチが手前の
        指を削って必ず隙間ができる(=数えられる)。加えて num_badge() で
        本数を数字として明示する。試験で最も問われる箇所なので、公式図には
        無い学習用の補助表示として意図的に足している。
        (v3.2でこの描画は hand(..., n=本数, fan=, thumb="fold") に統合した。
         手のひらの向きも同時に読めるようになり、親指を折るので本数が
         1本増えて見えることもなくなった。)

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


def body_side(role_label, cx=78):
    """横から見た人型(右を向く)。ネットの「手前か奥か」「上を越えているか」で
    意味が決まるシグナル(⑳タッチネット・㉑オーバーネット)は、正面向きの図では
    奥行きが描けないため横から見た図を使う(公式図もそうしている)。
    横向きなので見える腕は1本だけ。rest_arm() は付けない(反対の腕は体の
    後ろに隠れる)。ネットは体の右側に net_persp() で描く。"""
    chip = ""
    if role_label:
        chip = (f'<rect x="3" y="3" width="42" height="19" rx="6" fill="{INK}"/>'
                f'<text x="24" y="17" text-anchor="middle" font-family="sans-serif" '
                f'font-size="12" font-weight="700" fill="#FFFFFF">{role_label}</text>')
    return (
        limb([(cx - 1, 150), (cx - 5, 230)]) +
        limb([(cx - 1, 150), (cx + 9, 228)]) +
        limb([(cx, 58), (cx, 88)], w=16) +
        f'<path d="M{cx - 18},84 L{cx + 18},84 L{cx + 14},152 L{cx - 14},152 Z" '
        f'fill="{JERSEY}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>' +
        f'<circle cx="{cx}" cy="36" r="23" fill="{INK}"/>' +
        # 鼻の出っ張りで向いている方向を示す(横向きだと分からなくなる)
        f'<path d="M{cx + 19},33 L{cx + 27},38 L{cx + 19},43 Z" fill="{INK}"/>' +
        chip
    )


def net_persp(nx1=106, ny1=100, nx2=220, ny2=82, d1=58, d2=40, band=9):
    """遠近法で描いた横から見たネット。手前(nx1,ny1)から奥(nx2,ny2)へ
    上端(白帯)が上がっていく。d1/d2 は手前・奥での網の垂れ下がり。
    「手前の白帯」と「奥の白帯」が別の高さになるので、審判が奥のネットに
    手を触れているのか、ネットの上方に手をかざしているのかが描き分けられる。"""
    parts = [f'<path d="M{nx1},{ny1} L{nx2},{ny2} L{nx2},{ny2 + d2} L{nx1},{ny1 + d1} Z" '
             f'fill="{HALO}" stroke="{INK}" stroke-width="2.5"/>']
    for i in range(1, 8):
        t = i / 8
        x = nx1 + (nx2 - nx1) * t
        yt = ny1 + (ny2 - ny1) * t
        yb = yt + d1 + (d2 - d1) * t
        parts.append(f'<line x1="{x:.1f}" y1="{yt:.1f}" x2="{x:.1f}" y2="{yb:.1f}" '
                     f'stroke="{NETC}" stroke-width="1.4"/>')
    for j in range(1, 5):
        u = j / 5
        parts.append(f'<line x1="{nx1}" y1="{ny1 + d1 * u:.1f}" x2="{nx2}" '
                     f'y2="{ny2 + d2 * u:.1f}" stroke="{NETC}" stroke-width="1.4"/>')
    parts.append(f'<line x1="{nx1}" y1="{ny1}" x2="{nx2}" y2="{ny2}" stroke="{INK}" '
                 f'stroke-width="{band}" stroke-linecap="square"/>')
    return "".join(parts)


def hand_circle(x, y, r=13, fill=ACCENT):
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 3}" fill="{HALO}"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>')


# v2の hand_bar()(平たい棒の手)は、手のひらの向き(前方/自分/上/下)を
# 描き分けられず「全部天井向きに見える」原因だったため v3 で削除した。
# 手は必ず hand() で描く。


# v2の fingers()(指を線で count 本並べる)は、手のひらの向きが描けず
# 「どちら向きの手で何本立てているのか」が読めなかったため v3.2 で削除した。
# 指の本数を示す手は hand(..., n=本数, fan=広げる角度, thumb="fold") で描く。


def thumb_up(x, y, angle=0, mirror=False):
    """親指を立てた手(ダブルフォルト用)。丸い手だと「棒付きの飴」に見えてしまう
    ので、握りこぶしを角丸の四角、親指をその肩口から伸びる細い角丸で描き分ける。
    親指は既定で左側(-X)に出る。両手を立てるシグナルは片方を mirror=True にして
    左右とも親指が体の外側に来るようにする(公式図がそう描いている)。"""
    flip = " scale(-1 1)" if mirror else ""
    return (f'<g transform="translate({x} {y}) rotate({angle}){flip}">'
            f'<rect x="-15" y="-13" width="30" height="26" rx="10" fill="{HALO}"/>'
            f'<rect x="-12" y="-10" width="24" height="20" rx="8" fill="{ACCENT}"/>'
            f'<rect x="-15" y="-35" width="17" height="27" rx="8.5" fill="{HALO}"/>'
            f'<rect x="-12.5" y="-32" width="12" height="23" rx="6" fill="{ACCENT}"/></g>')


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


def net_plane(x=190, y_top=36, y_band=74):
    """ネットの垂直面。公式図(第11図㉑オーバーネット)が赤い破線で描き添えて
    いるもので、手がこの線を越えていれば「ネットの上方=相手コート側の空間に
    手をかざしている」ことが読める。
    v3.3までは灰色の実線で描いていたが、それでは網目やアンテナと同じ「物」に
    見えてしまい、"面"を表す補助線だと分からなかった。公式図どおり赤い破線に
    して、実在するネット(白帯・網目)と補助線をはっきり描き分ける。"""
    return (f'<line x1="{x}" y1="{y_top}" x2="{x}" y2="{y_band}" stroke="{HALO}" '
            f'stroke-width="8"/>'
            f'<line x1="{x}" y1="{y_top}" x2="{x}" y2="{y_band}" stroke="{RED}" '
            f'stroke-width="3" stroke-dasharray="10 7"/>')


def gap_arrow(x, y1, y2, color=BLUE, w=4.5):
    """2点の間が「離れている」ことを示す両矢印。
    ㉑オーバーネットで手が白帯から離れて上にあることを示す。⑳タッチネットは
    contact_mark()(接触の印)を使うので、両者が一目で見分けられる。"""
    marker = "ahA" if color == ACCENT else "ah"
    mid = (y1 + y2) / 2
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{HALO}" '
            f'stroke-width="{w + 6}" stroke-linecap="round"/>'
            f'<line x1="{x}" y1="{mid:.1f}" x2="{x}" y2="{y1}" stroke="{color}" '
            f'stroke-width="{w}" marker-end="url(#{marker})"/>'
            f'<line x1="{x}" y1="{mid:.1f}" x2="{x}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{w}" marker-end="url(#{marker})"/>')


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


def _hand_face(back, palm_w=27, palm_h=18, fin_len=16, fin_w=5.6,
               n=4, fan=0, thumb="open"):
    """正面から見た開いた手。原点=手首、-Y方向(上)へ指先が伸びる。
    back=False → 手のひらがこちらを向いている(=手のひらを前方に向けた手)
    back=True  → 手の甲がこちらを向いている(=手のひらを自分に向けた手)

    n    = 伸ばしている指の本数(1〜4)。残りは手のひらの上端の「折り曲げた
           こぶ」として描く。本数が意味を持つシグナル(ダブルコンタクト2本・
           フォアヒット4本・ディレイインサービス片手4本)で使う。
    fan  = 伸ばした指を扇状に開く角度。公式図のディレイインサービスや
           ダブルコンタクトは指を広げているので、その再現に使う。
    thumb= "open" 通常の開いた手(親指も伸ばす) /
           "fold" 親指を手のひらへ折りたたむ。**指の本数を示すシグナルは
           必ず "fold"**。親指を伸ばすと本数が1本増えて見えてしまう
           (公式図も指の本数を示すときは親指を折っている)。

    親指をどちら側に出すかは mirror(hand()の引数)で決める。向きはシグナル
    ごとに公式図で確認すること(§4-A-1の表)。"""
    n = max(1, min(4, n))
    xs = [-palm_w / 2 + palm_w * (i + 0.5) / 4 for i in range(4)]
    top = -palm_h
    halo = [f'<rect x="{-palm_w / 2 - 3:.1f}" y="{top - 3:.1f}" width="{palm_w + 6:.1f}" '
            f'height="{palm_h + 9:.1f}" rx="8" fill="{HALO}"/>']
    main = [f'<rect x="{-palm_w / 2:.1f}" y="{top:.1f}" width="{palm_w:.1f}" '
            f'height="{palm_h + 3:.1f}" rx="6" fill="{ACCENT}"/>']
    tips = []
    for i in range(n):
        fx = xs[i]
        a = math.radians((i - (n - 1) / 2) * fan)
        ex = fx + fin_len * math.sin(a)
        ey = top - fin_len * math.cos(a)
        tips.append((ex, ey))
        halo.append(f'<line x1="{fx:.1f}" y1="{top + 2}" x2="{ex:.1f}" y2="{ey:.1f}" '
                    f'stroke="{HALO}" stroke-width="{fin_w + 5:.1f}" stroke-linecap="round"/>')
        main.append(f'<line x1="{fx:.1f}" y1="{top + 2}" x2="{ex:.1f}" y2="{ey:.1f}" '
                    f'stroke="{ACCENT}" stroke-width="{fin_w:.1f}" stroke-linecap="round"/>')
    # 折り曲げた指は手のひらの上端のこぶで表す(伸ばした指との差がはっきり出る)
    for i in range(n, 4):
        halo.append(f'<circle cx="{xs[i]:.1f}" cy="{top + 1:.1f}" r="{fin_w / 2 + 3.5:.1f}" '
                    f'fill="{HALO}"/>')
        main.append(f'<circle cx="{xs[i]:.1f}" cy="{top + 1:.1f}" r="{fin_w / 2 + 1.2:.1f}" '
                    f'fill="{ACCENT}"/>')
    if thumb == "open":
        tsx = (palm_w / 2 - 2) if back else (-palm_w / 2 + 2)
        tex = tsx + (14 if back else -14)
        halo.append(f'<line x1="{tsx:.1f}" y1="-1" x2="{tex:.1f}" y2="{top - 2:.1f}" '
                    f'stroke="{HALO}" stroke-width="{fin_w + 7:.1f}" stroke-linecap="round"/>')
        main.append(f'<line x1="{tsx:.1f}" y1="-1" x2="{tex:.1f}" y2="{top - 2:.1f}" '
                    f'stroke="{ACCENT}" stroke-width="{fin_w + 1.8:.1f}" stroke-linecap="round"/>')
    out = "".join(halo) + "".join(main)
    if thumb == "fold":
        # 手のひらを横切る短い折りたたんだ親指。輪郭を濃紺で描いて
        # 「伸ばした指ではない」ことが分かるようにする。
        tsx = (palm_w / 2 - 3) if back else (-palm_w / 2 + 3)
        tex = tsx + (-13 if back else 13)
        out += (f'<line x1="{tsx:.1f}" y1="{-1}" x2="{tex:.1f}" y2="{top + 6:.1f}" '
                f'stroke="{INK}" stroke-width="{fin_w + 3.4:.1f}" stroke-linecap="round" '
                f'opacity="0.55"/>')
        out += (f'<line x1="{tsx:.1f}" y1="{-1}" x2="{tex:.1f}" y2="{top + 6:.1f}" '
                f'stroke="{ACCENT}" stroke-width="{fin_w + 0.6:.1f}" stroke-linecap="round"/>')
    if back:
        for i in range(n):
            out += (f'<circle cx="{xs[i]:.1f}" cy="{top + 4:.1f}" r="2.3" fill="{INK}" '
                    f'opacity="0.8"/>')
        for ex, ey in tips:
            out += (f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{fin_w / 2 - 0.6:.1f}" '
                    f'fill="{HALO}"/>')
    else:
        out += (f'<rect x="{-palm_w / 2 + 4:.1f}" y="{top + 4:.1f}" width="{palm_w - 8:.1f}" '
                f'height="{palm_h - 3:.1f}" rx="5" fill="{PALM_FACE}"/>')
        out += (f'<path d="M{-palm_w / 2 + 6.5:.1f},{top + 8:.1f} Q0,{top + 13.5:.1f} '
                f'{palm_w / 2 - 6.5:.1f},{top + 9:.1f}" fill="none" stroke="{ACCENT}" '
                f'stroke-width="1.8" opacity="0.85"/>')
    return out


def _hand_side(face_up, length=34, thick=15, grooves=False):
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
    if grooves:
        # 指先側に区切りを入れて「板」ではなく「指のある手」に見せる
        for t in (0.60, 0.72, 0.84):
            gx = length * t
            out += (f'<line x1="{gx:.1f}" y1="{-h * 0.78:.1f}" x2="{gx:.1f}" y2="{h * 0.78:.1f}" '
                    f'stroke="{HALO}" stroke-width="1.8" opacity="0.9"/>')
    return out


def hand(kind, x, y, rot=0, mirror=False, n=4, fan=0, thumb="open"):
    """手のひらの向きが必ず読める手のグリフ。向きはシグナルの意味そのもの
    なので、v3では手を必ずこの関数で描く(hand_bar() は使わない)。
      "front" = 手のひらを前方(=見ている側)に向ける
      "self"  = 手のひらを自分に向ける(=手の甲がこちら)
      "up"    = 手のひらを上に向ける
      "down"  = 手のひらを下に向ける
    rot は front/self では指先の向き、up/down では手の伸びる向きの回転角。
    mirror=True で左右反転する。**親指をどちら側に出すかはシグナルごとに
    公式図で決まっている**(ブロックの反則は内向き、ボールアウトは外向き。
    §4-A-1の表を見ること)。両手を使うシグナルで反転を忘れると、片方の親指が
    体の外側、もう片方が内側に出て人の手に見えない。
    n / fan / thumb は front/self のときだけ効く(_hand_face を参照)。"""
    if kind in ("front", "self"):
        inner = _hand_face(kind == "self", n=n, fan=fan, thumb=thumb)
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


def rest_arm(side):
    """シグナルに使っていない側の腕(体の横に下ろした腕)。
    公式図は必ず反対側の腕を下ろした状態で描いている。片腕のシグナルで
    これを描かないと「腕が1本しかない人」に見えるため、v3.1で追加した。
    シグナルの腕より先に描くこと(後に描くと手前に来て邪魔になる)。"""
    if side == "left":
        return arm3(76, 94, 66, 124, 70, 154) + f'<circle cx="70" cy="156" r="8.5" fill="{INK}"/>'
    return arm3(124, 94, 134, 124, 130, 154) + f'<circle cx="130" cy="156" r="8.5" fill="{INK}"/>'


def motion_ellipse(cx, cy, rx, ry, color=BLUE, w=5):
    """体の周りを水平に一周する動き(コートチェンジ)。縦向きの円で描くと
    sig05(選手交代)の前腕の回転と紛れるため、横長の楕円＋手前を通る向きの
    矢印で「体の周りを回る」ことを表す。"""
    d = (f'M{cx - rx:.1f},{cy:.1f} A{rx},{ry} 0 0 1 {cx + rx:.1f},{cy:.1f} '
         f'A{rx},{ry} 0 0 1 {cx - rx:.1f},{cy:.1f}')
    out = (f'<path d="{d}" fill="none" stroke="{HALO}" stroke-width="{w + 5}"/>'
           f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"/>')
    out += motion_line(cx - rx * 0.30, cy + ry, cx + rx * 0.42, cy + ry * 0.93,
                       color=color, w=w)
    return out


def hand_edge(x, y, palm="right", length=34):
    """横から見た薄い手を垂直に立てた形(指先は上)。原点=手首。
    タイムアウトのT字の縦棒・ワンタッチの立てた手・ディレイウォーニングの
    立てた手は、公式図ではどれも**横から見た薄い手**で描かれている。
    正面向きの手のひら(hand("front"))で描くと幅が広すぎてT字の縦棒に
    見えず、さらに「手のひらをこちらに向けている」という誤った情報になる
    (2026-08-28指摘)。
    palm = "right"/"left" で手のひらが画面のどちら側を向くか。
    (指先を上に向けた手の手のひらは体の左右どちらかを向く。正面でも背面でもない)"""
    # rot=-90 で局所の -Y が画面左、+Y が画面右に来る。
    inner = _hand_side(palm == "left", length=length, grooves=True)
    return f'<g transform="translate({x:.1f} {y:.1f}) rotate(-90)">{inner}</g>'


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


def svg_wrap(inner, role_label, side=False):
    """side=True で横から見た人型(body_side)を使う。ネットの手前/奥や
    前腕を前方へ持ち上げる動きは、正面向きでは奥行き方向になって読めない。"""
    figure = body_side(role_label) if side else body(role_label)
    return (f'<svg viewBox="0 0 {VIEW_W} {VIEW_H}" xmlns="http://www.w3.org/2000/svg">'
            f'{ARROWHEAD_DEF}{figure}{inner}</svg>')


def svg_wrap_two(left, right, left_label="横から見た図", right_label="正面から見た図"):
    """2面図。ネットの垂直面を越えているかどうかで意味が決まるシグナル
    (㉑オーバーネット)は1方向からの図では説明しきれないので、公式図と同じく
    横から見た図と正面から見た図を並べる。
    left/right はそれぞれ人型を含んだ 230x264 の描画内容をそのまま渡す
    (役職チップは左だけに入れる)。視点のラベルは反則名ではないので、
    出題で答えが割れることはない。"""
    return (f'<svg viewBox="0 0 484 300" xmlns="http://www.w3.org/2000/svg">'
            f'{ARROWHEAD_DEF}'
            f'<g>{left}</g>'
            f'<line x1="242" y1="12" x2="242" y2="266" stroke="#DDD5C2" stroke-width="2"/>'
            f'<g transform="translate(254 0)">{right}</g>'
            f'<text x="115" y="290" text-anchor="middle" font-family="sans-serif" '
            f'font-size="16" font-weight="700" fill="{INK}">{left_label}</text>'
            f'<text x="369" y="290" text-anchor="middle" font-family="sans-serif" '
            f'font-size="16" font-weight="700" fill="{INK}">{right_label}</text>'
            f'</svg>')


SIGNALS = []


def add_raw(id_, name, svg, hint="", wide=False):
    """SVGを丸ごと差し替えて登録する。2面図のように svg_wrap() の
    1体1面という前提に収まらないシグナル用。
    wide=True は横長の図(2面図)の印。app.js/style.css がこの印を見て
    図の枠を広くする(横長の図を他と同じ幅に押し込むと小さすぎて読めない)。"""
    item = {"id": id_, "name": name, "hint": hint, "svg": svg}
    if wide:
        item["wide"] = True
    SIGNALS.append(item)


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
# 2026-08-28、規則書「第11図 ファーストレフェリーとセカンドレフェリーの公式
# ハンドシグナル」(p.128〜135)と「第12図 ラインジャッジの公式フラッグシグナル」
# の全ページ写真(資料\ハンドシグナル\IMG_1719〜1728.JPG)を入手したので、
# 26種＋線審5種すべてを公式図と1件ずつ突き合わせて直した(v3.1)。
# 公式の説明文はそのまま hint に入れてある。
#
# 座標を触るときの原則:
#   ・肩は左(76,92)/右(124,92)。頭は中心(100,36)半径24、胴は y=84〜152。
#   ・上腕と前腕の長さはできるだけ揃える(片方が2倍近くなると骨折して見える)。
#   ・肘は「その向きに人体が曲がるか」を必ず確認する。肘は体の後ろには
#     曲がらないし、前腕は上腕の内側へ180度は畳めない。
#   ・手のひらの向きは規則の文言そのままを hand() の種類で表す
#     ("front"=前方 / "self"=自分 / "up"=上 / "down"=下)。
#   ・片腕のシグナルは rest_arm() で反対の腕を下ろす(公式図がそう描いている)。
#   ・動作系は ghost() で開始姿勢を描き、step_chip() で ①→② を振る。

add("sig01", "サービス許可", "審判",
    rest_arm("left") +
    arm3(124, 92, 152, 84, 182, 78) + hand("down", 184, 78, -6) +
    motion_arc(124, 92, 70, 60, 20, sweep=0),
    "サービスの方向を手で示す(腕を前方へ振り出し、手のひらは平らにする)")

add("sig02", "サービスを行うチーム", "審判",
    rest_arm("left") +
    arm3(124, 92, 154, 92, 186, 92) + hand("down", 188, 92, 0),
    "サービスをする側の腕を横に上げる(振らずに水平で止める)")

# 公式図は「左腕は前から後ろへ、右腕は後ろから前へ」で、前腕を体の前に
# 水平に構えたまま体の周りを水平に回す動き。v3は腕を上下に振っていたが、
# 公式は上下ではなく水平の回転(2026-08-28に公式図で確認)。
add("sig03", "コートチェンジ", "審判",
    anim_g(arm3(76, 96, 58, 118, 102, 128) + hand_circle(106, 128, 10),
           "anim-swing-l", 76, 96) +
    anim_g(arm3(124, 96, 142, 112, 98, 104) + hand_circle(94, 104, 10),
           "anim-swing-r", 124, 96) +
    motion_ellipse(100, 116, 66, 21),
    "前腕を体の前に構え、左腕は前から後ろへ、右腕は後ろから前へ"
    "(体の周りを水平に回す)")

# 公式は「片方の手を垂直に立て、その上に反対側の手のひらをのせてT字を形作る。
# そして、要求したチームを示す」。T字は体の前(胸の高さ)で作る。v3は体の
# 外側に置いていた(2026-08-28に公式図で確認)。
add("sig04", "タイムアウト", "審判",
    arm3(76, 100, 60, 128, 84, 118) + hand_edge(84, 118, palm="right") +
    arm3(124, 92, 140, 66, 104, 76) + hand("down", 100, 78, 180),
    "胸の前で片方の手を指先を上にして垂直に立て、その指先の上に反対の"
    "手のひらを下向きにのせて『T』を作る。そのあと要求したチームを腕で示す")

# 選手交代は v1 ではオレンジの円だけで、人の動作に全く見えなかった。
# 胸の前で上下に並べた2本の前腕を描き、回転の矢印は前腕と重ならないよう
# 体の左右の外側だけに置く。
add("sig05", "選手交代(サブスティチューション)", "審判",
    limb([(72, 108), (126, 108)]) + hand_circle(128, 108, 11) +
    limb([(128, 130), (74, 130)]) + hand_circle(72, 130, 11) +
    anim_g(motion_arc(100, 119, 50, 128, 232, color=ACCENT, w=5) +
           motion_arc(100, 119, 50, -52, 52, color=ACCENT, w=5),
           "anim-spin", 100, 119),
    "両腕の前腕部を、互いに回転させる")

# 公式図はカードを頭より高く掲げている(肘を曲げて前腕を立て、手は頭の
# 上あたり)。v3はカードが頭の横で止まっていた。
add("sig06", "軽度の不法な行為への警告(イエローカード)", "審判",
    rest_arm("left") +
    arm3(124, 92, 148, 68, 142, 38) + card(142, 20, YELLOW),
    "ウォーニングとして、イエローカードを頭より高く掲げて示す")

add("sig07", "ペナルティ", "審判",
    rest_arm("left") +
    arm3(124, 92, 148, 68, 142, 38) + card(142, 20, RED),
    "ペナルティとして、レッドカードを頭より高く掲げて示す")

add("sig08", "退場", "審判",
    rest_arm("left") +
    arm3(124, 92, 148, 68, 144, 40) + card(133, 22, YELLOW) + card(157, 22, RED),
    "退場として、イエローカードとレッドカードを片手で一緒に示す")

add("sig09", "失格", "審判",
    arm3(76, 92, 52, 68, 58, 40) + card(56, 22, YELLOW) +
    arm3(124, 92, 148, 68, 142, 40) + card(144, 22, RED),
    "失格として、イエローカードとレッドカードの両方を別々に示す")

# 公式図は肘を体の横に落として前腕を斜め上へ交差させ、手は反対側の肩の
# 高さまで来る。手の甲がこちらを向く。
add("sig10", "セット(ゲーム)の終了", "審判",
    arm3(76, 94, 66, 128, 108, 96) +
    arm3(124, 94, 134, 128, 92, 96) +
    hand("self", 92, 96, -40) + hand("self", 108, 96, 40, mirror=True),
    "両腕を胸の前で交差する(肘は体の横に下げ、手は開いて反対側の肩の高さ・"
    "手の甲が相手側)")

# 公式図は「腕を下げた状態(破線)→前方水平まで上げる」の2姿勢で描かれている。
add("sig11", "サービスでボールをヒットしなかった、またはトスをしないで打った反則", "審判",
    ghost(arm3(124, 94, 138, 126, 148, 158) + hand("up", 150, 160, 68)) +
    arm3(124, 96, 154, 102, 186, 106) + hand("up", 188, 106, 6) +
    motion_arc(124, 96, 76, 60, 22, sweep=0) +
    step_chip(176, 184) + step_chip(178, 68, "2"),
    "腕を前方に伸ばしたまま、手のひらを上に向けて上げる"
    "(下げた位置から水平まで)")

# 8本指。指を描き分けても数えられないので数字バッジを併記する。
# 肘は体の横に落とし、前腕を立てて手を顔の高さに置く(公式図の形)。
add("sig12", "ディレイインサービス(サービス時8秒ルールの反則)", "審判",
    arm3(76, 94, 54, 112, 48, 78) +
    hand("front", 48, 78, -12, mirror=True, n=4, fan=15, thumb="fold") +
    arm3(124, 94, 146, 112, 152, 78) +
    hand("front", 152, 78, 12, n=4, fan=15, thumb="fold") +
    num_badge(200, 42, "8"),
    "指を8本、広げて上げる(肘を下げて前腕を立て、手は顔の高さ)")

# 「手のひらを前方に向ける」が意味なので、天井向きの平手ではなく
# こちらを向いた手のひら(明るい面＋手相の線)で描く。
add("sig13", "ブロックの反則またはスクリーン", "審判",
    arm3(76, 92, 70, 66, 64, 44) + hand("front", 64, 44, -8, mirror=True) +
    arm3(124, 92, 130, 66, 136, 44) + hand("front", 136, 44, 8),
    "両方の手のひらを前方に向け、真上に上げる(天井に向けるのではない)")

# 公式図は腕を体の前に下ろし、人差し指を下に向けて腰のあたりで円を描く。
# v3は腕を前方水平に伸ばしていた(2026-08-28に公式図で確認)。
add("sig14", "ポジションまたはローテーションの反則", "審判",
    rest_arm("left") +
    arm3(124, 96, 146, 120, 138, 150) + point_hand(138, 152, 84) +
    anim_g(motion_arc(144, 190, 18, -70, 250, color=ACCENT, w=4.5), "anim-spin", 144, 190),
    "人差し指で円を描く(腕を体の前に下ろし、指先を下に向けて回す)")

# 公式図は腕をほぼまっすぐ斜め下へ伸ばし、指先で床を指す。
add("sig15", "ボール『イン』", "審判",
    floor(246, 34, 214) +
    rest_arm("left") +
    arm3(124, 96, 142, 128, 152, 164) + point_hand(152, 166, 76) +
    motion_line(168, 204, 176, 230),
    "フロアーを指す(腕と指をフロアーへ向けて斜め下に伸ばす)")

# 公式図は「前腕を横に下ろした状態(破線)→垂直に上げる」の2姿勢。
# 手のひらを自分に向けるので、こちらから見えるのは手の甲。
add("sig16", "ボール『アウト』", "審判",
    ghost(arm3(76, 94, 66, 132, 44, 156) + hand("self", 44, 158, 225, mirror=True) +
          arm3(124, 94, 134, 132, 156, 156) + hand("self", 156, 158, 135)) +
    arm3(76, 94, 66, 132, 56, 92) + hand("self", 56, 92, 0, mirror=True) +
    arm3(124, 94, 134, 132, 144, 92) + hand("self", 144, 92, 0) +
    motion_line(26, 150, 26, 106) + motion_line(174, 150, 174, 106),
    "両手のひらを自分の方に向け、前腕を垂直に上げる"
    "(こちらから見えるのは手の甲)")

# 公式図は肘を体の横に付けたまま、前腕を体の前で上へ持ち上げる(手のひらは
# 上向き)。v3は前腕を体の外側へ水平に出していた(2026-08-28に公式図で確認)。
add_raw("sig17", "キャッチ(ボールの保持)",
    svg_wrap(
        ghost(arm3(94, 92, 100, 124, 106, 160) + hand("up", 108, 162, 62)) +
        anim_g(arm3(94, 92, 100, 124, 136, 120) + hand("up", 138, 120, -4),
               "anim-lift", 100, 124) +
        motion_line(162, 158, 168, 126) +
        step_chip(100, 198) + step_chip(196, 96, "2"),
        "審判", side=True),
    "片方の手のひらを上に向け、前腕をゆっくり持ち上げる"
    "(肘は体の横に付けたまま、体の前で上げる)")

add("sig18", "ダブルコンタクト", "審判",
    rest_arm("left") +
    arm3(124, 94, 148, 74, 158, 50) +
    hand("front", 158, 50, 10, n=2, fan=22, thumb="fold") +
    num_badge(198, 96, "2"),
    "指を2本伸ばし、その手を上げる")

add("sig19", "フォアヒット", "審判",
    rest_arm("left") +
    arm3(124, 94, 148, 74, 158, 50) +
    hand("front", 158, 50, 10, n=4, fan=13, thumb="fold") +
    num_badge(198, 96, "4"),
    "指を4本伸ばし、その手を上げる")

# 公式図はネットの上端(白帯)が審判の肩の高さにあり、腕を水平に伸ばして
# 手のひらを下向きに白帯へ触れている。v3は腕を上へ伸ばしていた
# (2026-08-28に公式図で確認)。示す位置が意味なので白帯を青枠で囲む。
add_raw("sig20", "選手のタッチネット(サービスボールがネットの垂直面を越えないときも同じ)",
    svg_wrap(
        net_persp(120, 112, 226, 88, 64, 46) +
        # ㉑オーバーネットと同じ赤い破線(ネットの垂直面)を描き添える。
        # ㉑は手がこの線をまたぐのに対し、⑳は手が白帯に触れたまま線より上に
        # 出ない。同じ表現で並べることで、2つの違いが線1本で読み比べられる。
        net_plane(196, 36, 94) +
        contact_mark(192, 97, 10) +
        arm3(94, 92, 126, 96, 156, 92) +
        hand("self", 156, 92, 100, mirror=True, n=4, fan=12),
        "審判", side=True),
    "反則をしたチーム側(奥)のネットを示す。腕を水平に伸ばし、手のひらを"
    "下に向けてネットの上端＝白帯に触れる"
    "(赤い破線＝ネットの垂直面。手はこの線より上には出ない)")

# 公式図もこのシグナルだけは横から見た図と正面から見た図の2面で描いている。
# 「ネットの上を越えている」ことは1方向からでは説明しきれないため。
add_raw("sig21", "オーバーネット",
    svg_wrap_two(
        # 横から: 奥のネットの白帯より「上」に手をかざす(⑳との違いがここ)
        body_side("審判") +
        net_persp(120, 112, 226, 88, 64, 46) + net_plane(166, 24, 102) +
        arm3(94, 84, 126, 78, 158, 64) + hand("down", 158, 64, -6) +
        gap_arrow(184, 71, 96),
        # 正面から: 公式図(いただいた第11図㉑の写真)と同じ姿勢にする。
        #  ・反対の肩から体の前を横切るように腕を出し、前腕は水平
        #  ・手のひらは下向き
        #  ・ネットの垂直面(赤い破線)を手がまたいで相手コート側へ出ている
        # v3.3は腕を斜め上へ伸ばしていたため「ネットの上方にかざす」ではなく
        # 「上を指す」に見えていた。破線は手の下をくぐらせて描く(手が線の
        # 手前と向こうの両側に出ていることが、またいでいる証拠になる)。
        body("") + rest_arm("right") +
        # ネットは幅を広く・丈を短くする。細長い帯だと網目が見えず、
        # サムネイルでは物差しや柱に見えてしまう。
        net_panel_v(169, 116, 212, w=46) + net_plane(169, 26, 116) +
        arm3(76, 92, 106, 76, 144, 76) + hand("down", 146, 76, -3) +
        gap_arrow(206, 88, 116, w=5.5)),
    "手のひらを下に向け、ネットの上方(相手コート側の空間)にかざす"
    "(赤い破線＝ネットの垂直面。白帯に触れるタッチネットと違い、"
    "手は白帯より上に出て垂直面を越える)",
    wide=True)

# 公式図は「手のひらを広げて上方に伸ばし、前腕を振り下ろす」。振り下ろす
# 先は顔の前。①上げた姿勢を破線、②振り下ろした姿勢を実線で描く。
add("sig22", "アタックヒットの反則", "審判",
    rest_arm("left") +
    ghost(arm3(124, 92, 148, 72, 156, 40) + hand_edge(156, 40, palm="right")) +
    anim_g(arm3(124, 92, 148, 72, 116, 80) + hand("down", 112, 80, 174), "anim-chop", 148, 72) +
    motion_arc(148, 72, 34, -77, 166, color=ACCENT, sweep=0) +
    step_chip(194, 42) + step_chip(94, 110, "2"),
    "手のひらを広げて上方に伸ばし、前腕を振り下ろす"
    "(振り下ろした先は顔の前・手のひらは下向き)")

add("sig23", "ペネトレーションフォルト(ボールがネット下を通過・サーバーのフットフォルト等)", "審判",
    center_line(228, 8, 100) +
    rest_arm("right") +
    arm3(76, 98, 66, 132, 56, 170) + point_hand(56, 170, 118) +
    motion_line(40, 196, 30, 220),
    "センターラインまたは該当するラインを指す")

add("sig24", "ダブルフォルトおよびリプレイ", "審判",
    arm3(76, 94, 58, 78, 60, 50) + thumb_up(62, 38) +
    arm3(124, 94, 144, 78, 146, 50) + thumb_up(148, 38, mirror=True),
    "両方の親指を立て、両腕を上げる")

# 公式図は両手を顔の高さで使う。垂直に立てた手は顎の前あたり、なでる手は
# その指先の上を横切る。v3は腰の高さに置いていた(2026-08-28に公式図で確認)。
add("sig25", "ボールコンタクト(ワンタッチ)", "審判",
    arm3(76, 104, 54, 130, 50, 96) + hand_edge(50, 96, palm="right") +
    arm3(124, 98, 112, 64, 82, 56) + hand("down", 82, 56, 180) +
    motion_line(56, 38, 22, 44, w=5),
    "垂直に立てた手の指先を、他方の手でブラシをかけるようにする"
    "(両手とも顔の高さで行う)")

# 公式図は片方の前腕を垂直に立て、その手首に反対の手でカードをあてる。
# v3は腕を前方へ水平に伸ばしていた(2026-08-28に公式図で確認)。
add("sig26", "ディレイウォーニングまたはディレイペナルティ", "審判",
    arm3(76, 98, 54, 76, 56, 46) + hand_edge(56, 46, palm="right") +
    arm3(124, 100, 104, 82, 76, 64) + hand_circle(74, 62, 10) +
    card(58, 52, YELLOW, w=16, h=21, angle=-10),
    "ディレイウォーニングの場合はイエローカードを、ディレイペナルティの場合は"
    "レッドカードを他方の手首にあてる(手首は前腕を立てた側)")

# ---- ラインジャッジ(線審)の公式フラッグシグナル ----

add("sig27", "ボール『イン』(ラインジャッジ)", "線審",
    floor(246, 34, 214) +
    rest_arm("left") +
    arm3(124, 98, 146, 134, 152, 172) + flag(152, 182, angle=182),
    "フラッグを下げる")

add("sig28", "ボール『アウト』(ラインジャッジ)", "線審",
    rest_arm("left") +
    arm3(124, 94, 142, 74, 146, 52) + flag(146, 52),
    "フラッグを真上に上げる")

# もう一方の手を旗の先端にのせる動作。旗を右に立てると届かせる腕が
# 頭を貫いてしまうので、旗を左に立てて腕を胸の前で交差させる。
# 描画順は「渡す腕 → 旗を持つ腕と旗 → 先端にのせる手のひら」。旗を腕より
# 後に描かないと、旗が腕の白フチに潰されて三角が消える。
add("sig29", "ボールコンタクト(ラインジャッジ)", "線審",
    arm3(124, 104, 94, 84, 72, 50) +
    arm3(76, 104, 52, 116, 38, 96) + flag(38, 96) +
    hand("down", 68, 48, 184),
    "フラッグを立て、他方の手のひらをフラッグの先端にのせる")

# 公式図は両腕を使う。片方の腕でアンテナ(またはライン)を指し示し、
# もう片方の腕でフラッグを頭上で左右に振る。v3は指し示す腕が無かった
# (2026-08-28に公式図で確認)。
add("sig30", "ボールのアンテナ外通過・アンテナ等への接触・フットフォルト(ラインジャッジ)", "線審",
    antenna(204, 36, 150) +
    arm3(76, 96, 58, 80, 58, 56) +
    anim_g(flag(58, 56), "anim-wave", 58, 56) +
    motion_arc(66, 44, 22, 214, 326, color=ACCENT, w=4.5) +
    arm3(124, 96, 152, 98, 178, 100) + point_hand(178, 100, 4),
    "アンテナまたはラインを指し示し、フラッグを頭上で左右に振る")

# sig10(セット終了)と同じ所作だが、線審はフラッグを持ったまま交差させる。
# 役職チップの「審判」/「線審」とフラッグの有無で区別する。
add("sig31", "判定不能(ラインジャッジ)", "線審",
    arm3(76, 94, 66, 128, 108, 96) +
    arm3(124, 94, 134, 128, 92, 96) +
    flag(112, 92, angle=46) +
    hand("self", 92, 96, -40) + hand("self", 108, 96, 40, mirror=True),
    "両腕を胸の前で交差する(フラッグは持ったまま)")

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
add_legend("指の本数を示す手。親指は折りたたみ、伸ばした指だけを数える",
           hand("front", 48, 58, 0, n=2, fan=22, thumb="fold"))
add_legend("薄い破線は動き出す前の姿勢。濃い方が動き終わった姿勢",
           ghost(arm3(22, 18, 32, 42, 42, 64)) + arm3(22, 18, 50, 28, 80, 36))
add_legend("①→②は動作の順番。青い矢印はその間の動き",
           step_chip(22, 40) + motion_line(40, 40, 60, 40) + step_chip(78, 40, "2"))
add_legend("赤い破線はネットの垂直面(実物ではなく面を示す補助線)。"
           "手がこの線を越えていればネットの上方にかざした手",
           net_plane(48, 6, 66) + hand("down", 30, 36, 0))


out_path = Path(__file__).resolve().parent.parent / "signals.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"signals": SIGNALS, "legend": LEGEND}, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("generated", len(SIGNALS), "signals /", len(LEGEND), "legend ->", out_path)
