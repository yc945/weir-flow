#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
溢流堰堰顶不规则断面过流能力计算  Android/Kivy 版
参照: SL 253-2018 | SL 265-2016 | 水力计算手册（第二版）

计算方法：控制点梯形积分法
  h_i  = H - Z_i
  H0_i = 1.5 × h_i          （临界水深关系）
  q_i  = m × √(2g) × H0_i^1.5
  Q_i  = (q_{i-1} + q_i) / 2 × B_i   （梯形积分，B 为距前点距离）
  Q总  = Σ Q_i
"""

from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'system')
Config.set('graphics', 'resizable', '1')

import os, sys, math
from datetime import datetime

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.clock import Clock
import kivy

Window.clearcolor = (0.96, 0.96, 0.97, 1)
Window.softinput_mode = 'below_target'

G = 9.81
SQRT2G = math.sqrt(2 * G)

# ── 流量系数参考 ──────────────────────────────────────────────────────────────
M_OPTIONS = ['0.385', '0.400', '0.420', '0.450', '0.480', '自定义']
WTYPE_M = {
    '宽顶堰':     '0.385',
    '折线实用堰': '0.400',
    'WES实用堰':  '0.480',
    '薄壁堰':     '0.450',
    '驼峰堰':     '0.400',
}
WTYPE_LIST = list(WTYPE_M.keys())

# ── CJK 字体 ─────────────────────────────────────────────────────────────────
def _find_cjk_font():
    _here = os.path.dirname(os.path.abspath(__file__))
    _wf = (os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'Fonts') + os.sep
           if sys.platform == 'win32' else '/mnt/c/Windows/Fonts/')
    candidates = [
        os.path.join(_here, 'fonts', 'CJK.ttf'),
        os.path.join(_here, 'fonts', 'simhei.ttf'),
        _wf + 'simhei.ttf', _wf + 'simkai.ttf',
        _wf + 'STFANGSO.TTF', _wf + 'msyh.ttc',
        # AOSP / Pixel
        '/system/fonts/NotoSansCJK-Regular.ttc',
        '/system/fonts/NotoSansCJKsc-Regular.otf',
        '/system/fonts/DroidSansChinese.ttf',
        '/system/fonts/DroidSansFallback.ttf',
        # MIUI (小米)
        '/system/fonts/MiSans-Regular.ttf',
        '/system/fonts/MiSans-Normal.ttf',
        # HarmonyOS (华为)
        '/system/fonts/HarmonyOS_Sans_SC_Regular.ttf',
        '/system/fonts/HMOS_Sans_SC.ttf',
        # ColorOS (OPPO/一加)
        '/system/fonts/OPPOSans-R.ttf',
        # OriginOS / Funtouch (vivo)
        '/system/fonts/vivoSans-Regular.ttf',
        # Samsung
        '/system/fonts/SamsungSans-Regular.ttf',
        # Linux (CI / desktop)
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    ]
    for fp in candidates:
        if os.path.exists(fp):
            return fp
    return os.path.join(kivy.kivy_data_dir, 'fonts', 'Roboto-Regular.ttf')

try:
    LabelBase.register('CJK', fn_regular=_find_cjk_font())
except Exception:
    LabelBase.register('CJK', fn_regular=os.path.join(
        kivy.kivy_data_dir, 'fonts', 'Roboto-Regular.ttf'))


# ══════════════════════════════════════════════════════════════════════════════
# 水力计算核心
# ══════════════════════════════════════════════════════════════════════════════

def unit_q(H, Z, m):
    h = H - Z
    if h <= 0:
        return 0.0, 0.0, 0.0
    H0 = 1.5 * h
    return h, H0, m * SQRT2G * H0 ** 1.5

def calc_weir(H, points, m):
    cp = []
    for pt in points:
        h, H0, q = unit_q(H, pt['Z'], m)
        cp.append({'name': pt['name'], 'Z': pt['Z'], 'h': h, 'H0': H0, 'q': q})

    segs = []
    Q_total = 0.0
    for i in range(1, len(cp)):
        B     = points[i]['B']
        q_avg = (cp[i-1]['q'] + cp[i]['q']) / 2.0
        Q_seg = q_avg * B
        Q_total += Q_seg
        segs.append({'seg': f'{cp[i-1]["name"]}→{cp[i]["name"]}',
                     'B': B, 'q_avg': q_avg, 'Q': Q_seg})
    return cp, segs, Q_total

def build_report(H, m, wtype, cp, segs, Q_total):
    S = '─' * 36
    lines = [
        '═' * 36,
        '  溢流堰不规则断面过流计算',
        '═' * 36,
        f'  堰型: {wtype}',
        f'  上游水位 H = {H:.3f} m',
        f'  流量系数 m = {m:.4f}',
        f'  计算时间: {datetime.now():%Y-%m-%d %H:%M}',
        '',
        S,
        f'  {"点号":^4} {"Z(m)":^8} {"h(m)":^7} {"H0(m)":^7} {"q(m²/s)":^10}',
        S,
    ]
    for c in cp:
        flag = ' -' if c['h'] <= 0 else ''
        lines.append(
            f'  {c["name"]:^4} {c["Z"]:^8.3f} {c["h"]:^7.3f} '
            f'{c["H0"]:^7.3f} {c["q"]:^10.4f}{flag}')
    lines += ['', S,
              f'  {"区间":^10} {"B(m)":^6} {"q均":^9} {"Q(m³/s)":^10}', S]
    for sg in segs:
        lines.append(
            f'  {sg["seg"]:^10} {sg["B"]:^6.2f} '
            f'{sg["q_avg"]:^9.4f} {sg["Q"]:^10.4f}')
    B_eff = sum(sg['B'] for sg in segs if sg['q_avg'] > 0)
    q_bar = Q_total / B_eff if B_eff > 0 else 0.0
    lines += [
        S,
        f'  有效过水宽 = {B_eff:.2f} m',
        f'  平均单宽流量 q̄ = {q_bar:.4f} m²/s',
        '',
        '═' * 36,
        f'  Q总 = {Q_total:.4f} m³/s',
        f'      = {Q_total:.2f} m³/s',
        '═' * 36,
    ]
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# KV 布局（静态部分）
# ══════════════════════════════════════════════════════════════════════════════
KV = '''
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<Label>:   font_name: 'CJK'
<Button>:  font_name: 'CJK'
<TextInput>: font_name: 'CJK'
<Spinner>: font_name: 'CJK'
<SpinnerOption>: font_name: 'CJK'

# ── 通用模板 ──
<SH@Label>:
    size_hint_y: None
    height: dp(30)
    font_size: sp(13)
    bold: True
    color: 1, 1, 1, 1
    halign: 'left'
    valign: 'middle'
    text_size: self.size
    padding: dp(8), 0
    canvas.before:
        Color:
            rgba: 0.18, 0.50, 0.72, 1
        Rectangle:
            pos: self.pos
            size: self.size

<FR@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(50)
    spacing: dp(4)
    padding: dp(8), dp(3)

<ML@Label>:
    size_hint_x: 0.44
    font_size: sp(13)
    halign: 'right'
    valign: 'middle'
    text_size: self.size
    color: 0.15, 0.15, 0.2, 1
    padding: dp(4), 0

<MI@TextInput>:
    size_hint_x: 0.56
    font_size: sp(14)
    multiline: False
    background_color: 0.93, 0.96, 1, 1
    foreground_color: 0, 0, 0, 1
    padding: dp(6), dp(8)

<MS@Spinner>:
    size_hint_x: 0.56
    font_size: sp(13)
    background_color: 0.12, 0.46, 0.70, 1
    background_normal: ''
    color: 1, 1, 1, 1
    option_cls: 'MSO'

<MSO@SpinnerOption>:
    font_size: sp(13)
    font_name: 'CJK'
    height: dp(44)

<CB@Button>:
    size_hint_y: None
    height: dp(54)
    font_size: sp(16)
    bold: True
    background_color: 0.09, 0.64, 0.35, 1
    background_normal: ''
    color: 1, 1, 1, 1

<NB@Button>:
    font_name: 'CJK'
    background_normal: ''
    background_color: 0.1, 0.36, 0.54, 1
    color: 1, 1, 1, 1
    font_size: sp(12)
    bold: True

# ── 根布局 ────────────────────────────────────────────────────────────────────
<RootBox>:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: 0.96, 0.96, 0.97, 1
        Rectangle:
            pos: self.pos
            size: self.size

    # 顶部标题栏
    BoxLayout:
        size_hint_y: None
        height: dp(48)
        canvas.before:
            Color:
                rgba: 0.1, 0.36, 0.54, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: '溢流堰过流能力计算'
            font_size: sp(16)
            bold: True
            color: 1, 1, 1, 1

    ScreenManager:
        id: sm

    # 底部导航
    BoxLayout:
        size_hint_y: None
        height: dp(50)
        spacing: dp(1)
        padding: dp(1)
        canvas.before:
            Color:
                rgba: 0.08, 0.28, 0.42, 1
            Rectangle:
                pos: self.pos
                size: self.size
        NB:
            text: '≋ 过流计算'
            on_press: app.go('weir')
        NB:
            text: '◎ 参数说明'
            on_press: app.go('help')

# ── 计算界面 ──────────────────────────────────────────────────────────────────
<WeirScreen>:
    canvas.before:
        Color:
            rgba: 0.96, 0.96, 0.97, 1
        Rectangle:
            pos: self.pos
            size: self.size

    ScrollView:
        do_scroll_x: False
        BoxLayout:
            id: main_box
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: dp(2)
            padding: 0, 0, 0, dp(20)

            # ── 全局参数 ──
            SH:
                text: '  全局参数'
            FR:
                ML:
                    text: '上游水位 H(m):'
                MI:
                    id: inp_H
                    text: '98.5'
                    input_filter: 'float'
            FR:
                ML:
                    text: '堰型:'
                MS:
                    id: sp_wtype
                    text: '宽顶堰'
                    values: ['宽顶堰','折线实用堰','WES实用堰','薄壁堰','驼峰堰']
                    on_text: root.on_wtype(self.text)
            FR:
                ML:
                    text: '流量系数 m:'
                MI:
                    id: inp_m
                    text: '0.385'
                    input_filter: 'float'

            # ── 控制点表头 ──
            SH:
                text: '  控制点（自左向右，B=距前点距离）'
            BoxLayout:
                size_hint_y: None
                height: dp(32)
                padding: dp(4), dp(2)
                spacing: dp(2)
                canvas.before:
                    Color:
                        rgba: 0.82, 0.89, 0.96, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                Label:
                    text: '编号'
                    font_size: sp(12)
                    bold: True
                    color: 0.1, 0.2, 0.4, 1
                    size_hint_x: 0.16
                Label:
                    text: '堰顶高程 Z(m)'
                    font_size: sp(12)
                    bold: True
                    color: 0.1, 0.2, 0.4, 1
                    size_hint_x: 0.38
                Label:
                    text: '距前点 B(m)'
                    font_size: sp(12)
                    bold: True
                    color: 0.1, 0.35, 0.1, 1
                    size_hint_x: 0.34
                Label:
                    text: '删'
                    font_size: sp(12)
                    bold: True
                    color: 0.5, 0.1, 0.1, 1
                    size_hint_x: 0.12

            # ── 控制点动态行容器 ──
            BoxLayout:
                id: rows_box
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height

            # ── 增加/删除按钮 ──
            BoxLayout:
                size_hint_y: None
                height: dp(52)
                spacing: dp(6)
                padding: dp(8), dp(4)
                Button:
                    text: '＋ 增加控制点'
                    font_name: 'CJK'
                    font_size: sp(14)
                    bold: True
                    background_color: 0.12, 0.55, 0.30, 1
                    background_normal: ''
                    color: 1, 1, 1, 1
                    on_press: root.add_point()
                Button:
                    text: '－ 删除末行'
                    font_name: 'CJK'
                    font_size: sp(14)
                    background_color: 0.65, 0.18, 0.18, 1
                    background_normal: ''
                    color: 1, 1, 1, 1
                    on_press: root.del_last()

            # ── 计算按钮 ──
            BoxLayout:
                size_hint_y: None
                height: dp(62)
                padding: dp(8), dp(4)
                CB:
                    text: '开  始  计  算'
                    on_press: root.calc()

            # ── 结果 ──
            SH:
                text: '  计算结果'
            Label:
                id: lbl_result
                text: '填写参数后点击"开始计算"'
                font_size: sp(12)
                halign: 'left'
                valign: 'top'
                text_size: self.width, None
                size_hint_y: None
                height: max(self.texture_size[1] + dp(20), dp(80))
                padding: dp(8), dp(6)
                color: 0.08, 0.08, 0.15, 1

# ── 说明界面 ──────────────────────────────────────────────────────────────────
<HelpScreen>:
    canvas.before:
        Color:
            rgba: 0.96, 0.96, 0.97, 1
        Rectangle:
            pos: self.pos
            size: self.size

    ScrollView:
        do_scroll_x: False
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: 0, 0, 0, dp(16)

            SH:
                text: '  流量系数 m 参考'
            BoxLayout:
                size_hint_y: None
                height: dp(28)
                padding: dp(4), dp(2)
                canvas.before:
                    Color:
                        rgba: 0.82, 0.89, 0.96, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                Label:
                    text: '堰型'
                    font_size: sp(12)
                    bold: True
                    color: 0.1, 0.2, 0.4, 1
                    size_hint_x: 0.42
                Label:
                    text: 'm 范围'
                    font_size: sp(12)
                    bold: True
                    color: 0.1, 0.2, 0.4, 1
                    size_hint_x: 0.3
                Label:
                    text: '常用值'
                    font_size: sp(12)
                    bold: True
                    color: 0.1, 0.35, 0.1, 1
                    size_hint_x: 0.28

            Label:
                id: lbl_mref
                text: ''
                font_size: sp(12)
                halign: 'left'
                valign: 'top'
                text_size: self.width, None
                size_hint_y: None
                height: max(self.texture_size[1] + dp(10), dp(200))
                padding: dp(4), dp(4)
                color: 0.08, 0.08, 0.15, 1

            SH:
                text: '  计算公式说明'
            Label:
                id: lbl_help
                text: ''
                font_size: sp(12)
                halign: 'left'
                valign: 'top'
                text_size: self.width, None
                size_hint_y: None
                height: max(self.texture_size[1] + dp(10), dp(400))
                padding: dp(8), dp(6)
                color: 0.08, 0.08, 0.15, 1
'''


# ══════════════════════════════════════════════════════════════════════════════
# 控制点行组件（纯 Python 创建，方便动态增删）
# ══════════════════════════════════════════════════════════════════════════════

def make_point_row(screen, idx, name='', Z='', B=''):
    """返回一个控制点输入行 BoxLayout"""
    row = BoxLayout(
        orientation='horizontal',
        size_hint_y=None,
        height=dp(50),
        spacing=dp(2),
        padding=(dp(4), dp(3)),
    )
    bg = (0.95, 0.97, 1, 1) if idx % 2 == 0 else (0.88, 0.93, 0.97, 1)

    # 编号标签
    name_lbl = Label(
        text=name or str(idx),
        font_name='CJK',
        font_size=sp(13),
        size_hint_x=0.16,
        color=(0.15, 0.15, 0.3, 1),
    )

    # Z 输入
    Z_inp = TextInput(
        text=Z,
        hint_text='高程',
        font_name='CJK',
        font_size=sp(14),
        size_hint_x=0.38,
        multiline=False,
        input_filter='float',
        background_color=bg,
        foreground_color=(0, 0, 0, 1),
        padding=(dp(4), dp(8)),
    )

    # B 输入（第1点灰显不可编辑）
    B_inp = TextInput(
        text='0' if (idx == 1 and not B) else B,
        hint_text='间距',
        font_name='CJK',
        font_size=sp(14),
        size_hint_x=0.34,
        multiline=False,
        input_filter='float',
        readonly=(idx == 1),
        background_color=(0.88, 0.88, 0.88, 1) if idx == 1 else bg,
        foreground_color=(0.4, 0.4, 0.4, 1) if idx == 1 else (0, 0, 0, 1),
        padding=(dp(4), dp(8)),
    )

    # 删除按钮
    del_btn = Button(
        text='✕',
        font_name='CJK',
        font_size=sp(13),
        size_hint_x=0.12,
        background_color=(0.75, 0.2, 0.2, 1),
        background_normal='',
        color=(1, 1, 1, 1),
    )
    del_btn.bind(on_press=lambda btn, r=row: screen.del_row(r))

    row.add_widget(name_lbl)
    row.add_widget(Z_inp)
    row.add_widget(B_inp)
    row.add_widget(del_btn)

    # 附加数据引用
    row._name_lbl = name_lbl
    row._Z_inp    = Z_inp
    row._B_inp    = B_inp

    return row


# ══════════════════════════════════════════════════════════════════════════════
# Screen 类
# ══════════════════════════════════════════════════════════════════════════════

class RootBox(BoxLayout):
    pass


class WeirScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._rows = []   # list of row BoxLayout
        Clock.schedule_once(self._init_rows, 0.1)

    def _init_rows(self, *_):
        # 载入示例数据（来自 Excel 参考文件）
        defaults = [
            ('1', '98.00', '0'),
            ('2', '95.85', '1.80'),
            ('3', '95.15', '9.17'),
            ('4', '96.72', '22.73'),
            ('5', '96.34', '14.70'),
            ('6', '95.08', '24.88'),
            ('7', '93.30', '23.30'),
            ('8', '97.56', '2.90'),
            ('9', '98.00', '18.12'),
        ]
        for name, Z, B in defaults:
            self._add_row_data(name=name, Z=Z, B=B)

    def _add_row_data(self, name='', Z='', B=''):
        idx = len(self._rows) + 1
        row = make_point_row(self, idx, name=name, Z=Z, B=B)
        self._rows.append(row)
        self.ids.rows_box.add_widget(row)

    def add_point(self):
        self._add_row_data()

    def del_last(self):
        if len(self._rows) > 1:
            row = self._rows.pop()
            self.ids.rows_box.remove_widget(row)

    def del_row(self, row):
        if row in self._rows and len(self._rows) > 1:
            self._rows.remove(row)
            self.ids.rows_box.remove_widget(row)
            self._renumber()

    def _renumber(self):
        for i, row in enumerate(self._rows, 1):
            row._name_lbl.text = str(i)
            if i == 1:
                row._B_inp.readonly = True
                row._B_inp.text = '0'
                row._B_inp.background_color = (0.88, 0.88, 0.88, 1)
            else:
                row._B_inp.readonly = False
                row._B_inp.background_color = (0.93, 0.96, 1, 1)

    def on_wtype(self, wtype):
        m = WTYPE_M.get(wtype, '0.385')
        self.ids.inp_m.text = m

    def calc(self):
        try:
            H = float(self.ids.inp_H.text)
            m = float(self.ids.inp_m.text)
        except ValueError:
            self.ids.lbl_result.text = '错误: 上游水位 H 或流量系数 m 无效'
            return

        points = []
        for i, row in enumerate(self._rows, 1):
            Zs = row._Z_inp.text.strip()
            Bs = row._B_inp.text.strip()
            if not Zs:
                self.ids.lbl_result.text = f'错误: 第{i}行 Z 为空'
                return
            try:
                Z = float(Zs)
                B = float(Bs) if Bs else 0.0
            except ValueError:
                self.ids.lbl_result.text = f'错误: 第{i}行数据非数字'
                return
            if i > 1 and B <= 0:
                self.ids.lbl_result.text = f'错误: 第{i}行 B={Bs} 必须 > 0'
                return
            points.append({'name': str(i), 'Z': Z, 'B': B})

        if len(points) < 2:
            self.ids.lbl_result.text = '错误: 至少需要2个控制点'
            return

        wtype = self.ids.sp_wtype.text
        cp, segs, Q_total = calc_weir(H, points, m)
        report = build_report(H, m, wtype, cp, segs, Q_total)
        self.ids.lbl_result.text = report


class HelpScreen(Screen):
    def on_enter(self, *_):
        Clock.schedule_once(self._fill, 0.05)

    def _fill(self, *_):
        mref_lines = [
            '  宽顶堰（折/弧顶）  0.32~0.385  0.385',
            '  WES 实用堰         0.44~0.502  0.480',
            '  折线型实用堰       0.38~0.42   0.400',
            '  薄壁矩形堰         0.42~0.50   0.450',
            '  驼峰堰             0.38~0.42   0.400',
        ]
        self.ids.lbl_mref.text = '\n'.join(mref_lines)

        self.ids.lbl_help.text = (
            '【计算原理 — 控制点梯形积分法】\n\n'
            '  将堰顶横断面由 N 个控制点描述，\n'
            '  相邻控制点之间为一个计算区间。\n\n'
            '  各控制点单宽流量：\n'
            '    h_i  = H − Z_i\n'
            '    H0_i = 1.5 × h_i（临界水深关系）\n'
            '    q_i  = m × √(2g) × H0_i^1.5\n\n'
            '  区间流量（梯形积分）：\n'
            '    Q_i = (q_{i-1} + q_i) / 2 × B_i\n\n'
            '  总过流量：\n'
            '    Q总 = Σ Q_i\n\n'
            '【输入说明】\n\n'
            '  H   上游水位高程（m）\n'
            '  m   流量系数（按堰型选取）\n'
            '  Z_i 各控制点堰顶高程（m）\n'
            '  B_i 本控制点到上一控制点的\n'
            '      水平距离（m），第1点填0\n\n'
            '【淹没出流】\n\n'
            '  当 ht/H0 > 0.75（宽顶堰）时\n'
            '  发生淹没，需乘淹没系数 σs < 1\n'
            '  查 SL 253-2018 附录B。\n\n'
            '【参考规范】\n'
            '  SL 253-2018  溢洪道设计规范\n'
            '  SL 265-2016  水闸设计规范\n'
            '  水力计算手册（第二版）\n'
            '  武汉水利电力学院'
        )


# ══════════════════════════════════════════════════════════════════════════════
# App
# ══════════════════════════════════════════════════════════════════════════════

class WeirCalcApp(App):
    def build(self):
        Builder.load_string(KV)
        root = RootBox()
        sm = root.ids.sm
        sm.transition = FadeTransition(duration=0.15)
        sm.add_widget(WeirScreen(name='weir'))
        sm.add_widget(HelpScreen(name='help'))
        return root

    def go(self, name):
        self.root.ids.sm.current = name


if __name__ == '__main__':
    WeirCalcApp().run()
