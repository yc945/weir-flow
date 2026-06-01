#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
溢流堰堰顶不规则断面过流能力计算
Irregular Cross-Section Weir Overflow Capacity Calculator

参照规范:
  SL 253-2018    溢洪道设计规范
  SL 265-2016    水闸设计规范
  GB 50286-2013  堤防工程设计规范
  水力计算手册（第二版）武汉水利电力学院

计算方法（控制点梯形积分法）:
  将堰顶横断面由 N 个控制点描述，相邻控制点之间为一个计算区间。

  对第 i 个控制点:
    h_i  = H - Z_i              堰顶水头（H 为上游水位高程）
    H0_i = 1.5 × h_i           计入行近流速的总水头
    q_i  = m × √(2g) × H0_i^1.5  单宽流量 (m²/s)

  对第 i 个区间（控制点 i 至 i+1，宽度 B_i）:
    Q_i = (q_i + q_{i+1}) / 2 × B_i   （梯形积分）

  总过流量:
    Q总 = Σ Q_i

  流量系数 m 参考（水力计算手册 第8章）:
    宽顶堰（折线、弧形顶）  m = 0.32 ~ 0.385
    实用堰（WES 曲线型）    m = 0.44 ~ 0.502
    折线型实用堰            m = 0.38 ~ 0.42
    薄壁矩形堰              m = 0.42 ~ 0.50
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import math
from datetime import datetime
import csv

# ── 常量 ──────────────────────────────────────────────────────────────────────
G = 9.81
SQRT2G = math.sqrt(2 * G)   # ≈ 4.4294

FONT_TITLE = ('微软雅黑', 13, 'bold')
FONT_HEAD  = ('微软雅黑', 10, 'bold')
FONT_NORM  = ('微软雅黑', 9)
FONT_MONO  = ('Consolas', 10)
COLOR_BLUE  = '#1a5c8a'
COLOR_GREEN = '#1a7a3c'
COLOR_RED   = '#c0392b'
COLOR_GRAY  = '#555555'
COLOR_AMBER = '#b8860b'

M_REFS = {
    '宽顶堰（折线/弧形顶）': (0.320, 0.385, 0.385),
    '实用堰（WES 曲线型）':  (0.440, 0.502, 0.480),
    '折线型实用堰':          (0.380, 0.420, 0.400),
    '薄壁矩形堰':            (0.420, 0.500, 0.450),
    '梯形薄壁堰':            (0.420, 0.480, 0.450),
    '驼峰堰':                (0.380, 0.420, 0.400),
}


# ══════════════════════════════════════════════════════════════════════════════
# 水力计算核心
# ══════════════════════════════════════════════════════════════════════════════

def unit_discharge(H, Z, m):
    """
    计算单个控制点的堰顶水头和单宽流量。
    返回 (h, H0, q)；H <= Z 时均返回 0。
    """
    h = H - Z
    if h <= 0:
        return 0.0, 0.0, 0.0
    H0 = 1.5 * h
    q  = m * SQRT2G * H0 ** 1.5
    return h, H0, q


def calc_weir(H, points, m):
    """
    梯形积分法计算不规则断面总过流量。

    points: list of {'name':str, 'Z':float, 'B':float}
      其中 B 为该控制点到【上一个】控制点的水平距离（第一个点 B=0）。

    返回:
      cp_results  : 各控制点结果列表 [{'name','Z','h','H0','q'}, ...]
      seg_results : 各区间结果列表   [{'seg','B','q_avg','Q'}, ...]
      Q_total     : 总过流量 m³/s
    """
    cp_results  = []
    seg_results = []

    for pt in points:
        h, H0, q = unit_discharge(H, pt['Z'], m)
        cp_results.append(dict(name=pt['name'], Z=pt['Z'], h=h, H0=H0, q=q))

    Q_total = 0.0
    for i in range(1, len(points)):
        B     = points[i]['B']
        q_avg = (cp_results[i - 1]['q'] + cp_results[i]['q']) / 2.0
        Q_seg = q_avg * B
        Q_total += Q_seg
        seg_results.append(dict(
            seg   = f'{cp_results[i-1]["name"]}→{cp_results[i]["name"]}',
            B     = B,
            q_avg = q_avg,
            Q     = Q_seg,
        ))

    return cp_results, seg_results, Q_total


# ══════════════════════════════════════════════════════════════════════════════
# 控制点输入表格
# ══════════════════════════════════════════════════════════════════════════════

class PointTable(ttk.Frame):
    """
    可动态增删的控制点表格。
    列: 编号 | 堰顶高程 Z (m) | 距前点 B (m) | 备注
    第1行的 B 必须为 0 或留空（左边界控制点，无区间在其左侧）。
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self._rows = []
        self._build_header()
        self._build_scroll()
        self._build_btns()
        # 默认示例（来自 Excel"不规则断面起算水深（4600）.xlsx"）
        defaults = [
            ('1', '98.00', '0',     '左边界'),
            ('2', '95.85', '1.80',  ''),
            ('3', '95.15', '9.17',  ''),
            ('4', '96.72', '22.73', ''),
            ('5', '96.34', '14.70', ''),
            ('6', '95.08', '24.88', ''),
            ('7', '93.30', '23.30', ''),
            ('8', '97.56', '2.90',  ''),
            ('9', '98.00', '18.12', '右边界'),
        ]
        for d in defaults:
            self._add_row(*d)

    # ── 构建界面 ──────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ttk.Frame(self)
        hdr.pack(fill='x', padx=2)
        specs = [('编 号', 6), ('堰顶高程 Z (m)', 14), ('距前点 B (m)', 14), ('备 注', 10)]
        for text, w in specs:
            ttk.Label(hdr, text=text, font=FONT_HEAD, foreground=COLOR_BLUE,
                      width=w, anchor='center', relief='groove',
                      padding=(2, 3)).pack(side='left', fill='x',
                                           expand=(w > 8))

    def _build_scroll(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill='both', expand=True)

        self._canvas = tk.Canvas(wrap, highlightthickness=0, bg='#f0f4f8')
        sb = ttk.Scrollbar(wrap, orient='vertical', command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self._canvas.pack(side='left', fill='both', expand=True)

        self._body = ttk.Frame(self._canvas)
        self._win_id = self._canvas.create_window((0, 0), window=self._body, anchor='nw')

        self._body.bind('<Configure>',
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox('all')))
        self._canvas.bind('<Configure>',
            lambda e: self._canvas.itemconfig(self._win_id, width=e.width))
        self._canvas.bind_all('<MouseWheel>',
            lambda e: self._canvas.yview_scroll(-1 * (e.delta // 120), 'units'))

    def _build_btns(self):
        bar = ttk.Frame(self)
        bar.pack(fill='x', pady=(4, 0))
        ttk.Button(bar, text='＋ 增加控制点', command=self._add_empty).pack(side='left', padx=3)
        ttk.Button(bar, text='－ 删除末行',   command=self._del_last).pack(side='left', padx=3)
        ttk.Button(bar, text='清 空',         command=self._clear_all).pack(side='left', padx=3)
        ttk.Button(bar, text='导入 CSV',      command=self._import_csv).pack(side='right', padx=3)
        ttk.Button(bar, text='导出 CSV',      command=self._export_csv).pack(side='right', padx=3)

    # ── 行操作 ────────────────────────────────────────────────────────────────
    def _add_row(self, name='', Z='', B='', note=''):
        if not name:
            name = str(len(self._rows) + 1)
        frm = ttk.Frame(self._body)
        frm.pack(fill='x', pady=1, padx=2)

        name_v = tk.StringVar(value=name)
        Z_v    = tk.StringVar(value=Z)
        B_v    = tk.StringVar(value=B)
        note_v = tk.StringVar(value=note)

        ttk.Entry(frm, textvariable=name_v, width=6,  justify='center').pack(side='left', padx=1)
        ttk.Entry(frm, textvariable=Z_v,    width=14, justify='center').pack(side='left', padx=1, fill='x', expand=True)
        ttk.Entry(frm, textvariable=B_v,    width=14, justify='center').pack(side='left', padx=1, fill='x', expand=True)
        ttk.Entry(frm, textvariable=note_v, width=10, justify='center').pack(side='left', padx=1)

        self._rows.append(dict(name=name_v, Z=Z_v, B=B_v, note=note_v, frame=frm))

    def _add_empty(self):
        self._add_row()

    def _del_last(self):
        if self._rows:
            self._rows.pop()['frame'].destroy()

    def _clear_all(self):
        for r in self._rows:
            r['frame'].destroy()
        self._rows.clear()

    # ── CSV I/O ───────────────────────────────────────────────────────────────
    def _import_csv(self):
        path = filedialog.askopenfilename(
            title='导入控制点数据',
            filetypes=[('CSV 文件', '*.csv'), ('所有文件', '*.*')])
        if not path:
            return
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                self._clear_all()
                for row in csv.DictReader(f):
                    self._add_row(row.get('编号', ''), row.get('Z', ''),
                                  row.get('B', ''), row.get('备注', ''))
        except Exception as e:
            messagebox.showerror('导入错误', str(e))

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            title='导出控制点数据', defaultextension='.csv',
            filetypes=[('CSV 文件', '*.csv')])
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                w.writerow(['编号', 'Z', 'B', '备注'])
                for r in self._rows:
                    w.writerow([r['name'].get(), r['Z'].get(),
                                 r['B'].get(), r['note'].get()])
            messagebox.showinfo('导出成功', f'已保存:\n{path}')
        except Exception as e:
            messagebox.showerror('导出错误', str(e))

    # ── 读取数据 ──────────────────────────────────────────────────────────────
    def get_points(self):
        """解析并返回控制点列表，出错时抛出 ValueError。"""
        if not self._rows:
            raise ValueError('请至少输入 2 个控制点')
        points = []
        for i, r in enumerate(self._rows, 1):
            name = r['name'].get().strip() or str(i)
            Zs   = r['Z'].get().strip()
            Bs   = r['B'].get().strip()
            if not Zs:
                raise ValueError(f'第 {i} 行堰顶高程 Z 为空')
            try:
                Z = float(Zs)
            except ValueError:
                raise ValueError(f'第 {i} 行 Z="{Zs}" 不是有效数字')
            # 第1行 B 可为空或0
            if i == 1:
                B = 0.0
            else:
                if not Bs:
                    raise ValueError(f'第 {i} 行距前点 B 为空（第1行以外必须填写）')
                try:
                    B = float(Bs)
                except ValueError:
                    raise ValueError(f'第 {i} 行 B="{Bs}" 不是有效数字')
                if B <= 0:
                    raise ValueError(f'第 {i} 行 B={B} ≤ 0，宽度必须为正数')
            points.append(dict(name=name, Z=Z, B=B))
        if len(points) < 2:
            raise ValueError('至少需要 2 个控制点才能计算')
        return points


# ══════════════════════════════════════════════════════════════════════════════
# 主应用
# ══════════════════════════════════════════════════════════════════════════════

class WeirApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title('溢流堰堰顶不规则断面过流能力计算  v1.1')
        root.geometry('1120x740')
        root.minsize(920, 600)
        self._build_style()
        self._build_header()
        self._build_body()
        self._last_report = ''

    def _build_style(self):
        s = ttk.Style()
        s.theme_use('clam')
        s.configure('.', font=FONT_NORM)
        s.configure('TNotebook', background='#eaf0f6')
        s.configure('TNotebook.Tab', font=('微软雅黑', 10), padding=[10, 4])
        s.configure('TLabelframe.Label', font=FONT_HEAD, foreground=COLOR_BLUE)
        s.configure('Calc.TButton', font=('微软雅黑', 11, 'bold'),
                    foreground='white', background=COLOR_BLUE)
        s.map('Calc.TButton', background=[('active', '#144f7a')])

    def _build_header(self):
        bar = tk.Frame(self.root, bg=COLOR_BLUE, height=50)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text='溢流堰堰顶不规则断面过流能力计算',
                 bg=COLOR_BLUE, fg='white',
                 font=('微软雅黑', 15, 'bold')).pack(side='left', padx=18, pady=8)
        tk.Label(bar,
                 text='SL 253-2018 | SL 265-2016 | 水力计算手册（第二版）',
                 bg=COLOR_BLUE, fg='#b8d8f0',
                 font=('微软雅黑', 8)).pack(side='right', padx=18)

    def _build_body(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill='both', expand=True, padx=6, pady=6)

        t1, t2, t3 = ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb)
        nb.add(t1, text='  ▷ 过流能力计算  ')
        nb.add(t2, text='  ◎ 流量系数参考  ')
        nb.add(t3, text='  ？ 计算说明      ')
        self._build_calc_tab(t1)
        self._build_mref_tab(t2)
        self._build_help_tab(t3)

    # ── Tab1 ──────────────────────────────────────────────────────────────────
    def _build_calc_tab(self, tab):
        # ── 左侧 ──
        left = ttk.Frame(tab)
        left.pack(side='left', fill='both', padx=(8, 4), pady=8)

        # 全局参数
        pf = ttk.LabelFrame(left, text='全局计算参数', padding=8)
        pf.pack(fill='x', pady=(0, 6))

        def row(parent, r, label, var_default, hint=''):
            ttk.Label(parent, text=label).grid(row=r, column=0, sticky='e',
                                               padx=(4, 6), pady=4)
            v = tk.StringVar(value=var_default)
            ttk.Entry(parent, textvariable=v, width=13).grid(row=r, column=1,
                                                              sticky='w', pady=4)
            if hint:
                ttk.Label(parent, text=hint, foreground=COLOR_GRAY).grid(
                    row=r, column=2, sticky='w', padx=6)
            return v

        self.v_H  = row(pf, 0, '上游水位 H (m):',  '98.5',
                        '实测或设计水位高程')
        self.v_Ht = row(pf, 1, '下游水位 Ht (m):', '',
                        '可选，用于淹没判断')

        ttk.Label(pf, text='堰型选择:').grid(row=2, column=0, sticky='e',
                                              padx=(4, 6), pady=4)
        self.v_wtype = tk.StringVar(value=list(M_REFS.keys())[0])
        cb = ttk.Combobox(pf, textvariable=self.v_wtype,
                          values=list(M_REFS.keys()), state='readonly', width=20)
        cb.grid(row=2, column=1, columnspan=2, sticky='w', pady=4)
        cb.bind('<<ComboboxSelected>>', self._on_wtype)

        ttk.Label(pf, text='流量系数 m:').grid(row=3, column=0, sticky='e',
                                               padx=(4, 6), pady=4)
        self.v_m = tk.StringVar(value='0.385')
        ttk.Entry(pf, textvariable=self.v_m, width=13).grid(row=3, column=1,
                                                              sticky='w', pady=4)
        self.lbl_mrange = ttk.Label(pf, text='参考: 0.320 ~ 0.385',
                                     foreground=COLOR_AMBER)
        self.lbl_mrange.grid(row=3, column=2, sticky='w', padx=6)

        # 控制点表格
        tf = ttk.LabelFrame(
            left,
            text='堰顶断面控制点定义\n'
                 '（自左向右逐点输入；B = 本点与上一控制点的水平距离，第1点填0）',
            padding=6)
        tf.pack(fill='both', expand=True, pady=(0, 6))
        self.pt_table = PointTable(tf)
        self.pt_table.pack(fill='both', expand=True)

        # 计算按钮
        ttk.Button(left, text='开  始  计  算', style='Calc.TButton',
                   command=self._calc).pack(fill='x', ipady=5)

        # ── 右侧结果 ──
        right = ttk.Frame(tab)
        right.pack(side='right', fill='both', expand=True, padx=(0, 8), pady=8)

        ttk.Label(right, text='计算结果', font=FONT_HEAD,
                  foreground=COLOR_BLUE).pack(anchor='w', pady=(0, 4))
        btn_row = ttk.Frame(right)
        btn_row.pack(fill='x', pady=(0, 4))
        ttk.Button(btn_row, text='清除',
                   command=lambda: self._clear(self.out)).pack(side='left', padx=4)
        ttk.Button(btn_row, text='导出报告 TXT',
                   command=self._export_txt).pack(side='right', padx=4)

        self.out = scrolledtext.ScrolledText(
            right, font=FONT_MONO, state='disabled',
            wrap='none', bg='#f8fbff', relief='sunken')
        self.out.pack(fill='both', expand=True)

    def _on_wtype(self, *_):
        lo, hi, default = M_REFS.get(self.v_wtype.get(), (0.32, 0.50, 0.385))
        self.v_m.set(f'{default:.3f}')
        self.lbl_mrange.config(text=f'参考: {lo:.3f} ~ {hi:.3f}')

    # ── Tab2 ──────────────────────────────────────────────────────────────────
    def _build_mref_tab(self, tab):
        ttk.Label(tab,
                  text='流量系数 m 参考值  （水力计算手册第8章 / SL 253-2018 附录）',
                  font=FONT_TITLE, foreground=COLOR_BLUE).pack(pady=(10, 6), padx=10, anchor='w')

        cols = ('堰型', 'm 下限', 'm 上限', '常用取值', '适用条件')
        tree = ttk.Treeview(tab, columns=cols, show='headings', height=10)
        for col, w in zip(cols, (200, 80, 80, 90, 350)):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor='center' if w < 200 else 'w')

        data = [
            ('宽顶堰（折线/弧形顶）', '0.320', '0.385', '0.385',
             '堰顶宽 δ/H₀ = 0.67~5.0，常见于溢流坝'),
            ('实用堰（WES 曲线型）',  '0.440', '0.502', '0.480',
             '低溢流坝，P/H₀ ≥ 1.33，按设计水头设计'),
            ('折线型实用堰',          '0.380', '0.420', '0.400',
             '堰面折线近似曲线，低坝或护坦末端'),
            ('薄壁矩形堰',            '0.420', '0.500', '0.450',
             '堰厚 δ/H < 0.1，量水堰常用'),
            ('梯形薄壁堰',            '0.420', '0.480', '0.450',
             '侧收缩明显时需乘侧收缩系数 ε'),
            ('驼峰堰',                '0.380', '0.420', '0.400',
             '堰面圆弧，低水头大流量工程'),
        ]
        for d in data:
            tree.insert('', 'end', values=d)
        tree.pack(fill='both', expand=True, padx=10, pady=(0, 6))

        nf = ttk.LabelFrame(tab, text='淹没出流判断（SL 265-2016 附录 D）', padding=8)
        nf.pack(fill='x', padx=10, pady=(0, 8))
        ttk.Label(nf, justify='left', foreground='#333', text=(
            '当下游水深 ht（= 下游水位 − 堰顶高程）> 0 时，可能发生淹没出流，需乘淹没系数 σs < 1.0。\n'
            '  宽顶堰淹没临界：ht / H₀ ≤ 0.75   （ht/H₀ > 0.75 为淹没）\n'
            '  实用堰淹没临界：ht / H₀ ≤ 0.85   （ht/H₀ > 0.85 为淹没）\n'
            '  σs 值按 SL 253-2018 附录 B 或水力计算手册表8-12 查取。\n'
            '  本程序仅给出淹没状态警告，不自动修正 m；如有淹没，请手动调整 m 后重算。'
        )).pack(anchor='w')

    # ── Tab3 ──────────────────────────────────────────────────────────────────
    def _build_help_tab(self, tab):
        st = scrolledtext.ScrolledText(tab, font=('微软雅黑', 9),
                                        wrap='word', state='normal', bg='#fafcff')
        st.pack(fill='both', expand=True, padx=10, pady=10)
        st.insert('1.0', HELP_TEXT)
        st.config(state='disabled')

    # ── 计算 ──────────────────────────────────────────────────────────────────
    def _calc(self):
        try:
            H = float(self.v_H.get())
            m = float(self.v_m.get())
        except ValueError:
            messagebox.showerror('输入错误', '上游水位 H 或流量系数 m 不是有效数字')
            return
        if not (0.1 <= m <= 0.8):
            messagebox.showwarning('参数警告',
                                   f'流量系数 m={m:.3f} 超出常用范围（0.1~0.8），请核查！')

        Ht = None
        ht_s = self.v_Ht.get().strip()
        if ht_s:
            try:
                Ht = float(ht_s)
            except ValueError:
                messagebox.showerror('输入错误', '下游水位 Ht 不是有效数字'); return

        try:
            points = self.pt_table.get_points()
        except ValueError as e:
            messagebox.showerror('控制点数据错误', str(e)); return

        cp_res, seg_res, Q_total = calc_weir(H, points, m)

        if Q_total == 0.0:
            messagebox.showwarning('无过流', '上游水位低于所有控制点堰顶高程，无过流。')

        report = self._build_report(H, m, Ht, points, cp_res, seg_res, Q_total)
        self._last_report = report
        self._show(self.out, report)

    def _build_report(self, H, m, Ht, points, cp_res, seg_res, Q_total) -> str:
        wtype = self.v_wtype.get()
        now   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        S1 = '═' * 72
        S2 = '─' * 72

        lines = [
            S1,
            '        溢流堰堰顶不规则断面过流能力计算报告',
            S1,
            f'  计算时间   : {now}',
            f'  堰  型     : {wtype}',
            f'  上游水位 H : {H:.3f} m',
            f'  流量系数 m : {m:.4f}',
            f'  √(2g)      : {SQRT2G:.4f}',
        ]
        if Ht is not None:
            lines.append(f'  下游水位Ht : {Ht:.3f} m')
        lines += ['', S2,
                  '  【控制点计算结果】',
                  f'  {"点号":^6} {"高程Z(m)":^10} {"水头h(m)":^10} '
                  f'{"总水头H0(m)":^12} {"单宽流量q(m²/s)":^16}']
        lines.append('  ' + '-' * 60)

        for cp in cp_res:
            sub = ''
            if Ht is not None and cp['H0'] > 0:
                ht_i = Ht - cp['Z']
                ratio = ht_i / cp['H0'] if cp['H0'] > 0 else 0
                if ht_i > 0 and ratio > 0.75:
                    sub = '  ⚠淹没'
            flag = '(未过水)' if cp['h'] <= 0 else sub
            lines.append(
                f'  {cp["name"]:^6} {cp["Z"]:^10.3f} {cp["h"]:^10.3f} '
                f'{cp["H0"]:^12.3f} {cp["q"]:^16.4f}{flag}'
            )

        lines += ['', S2,
                  '  【区间过流量（梯形积分法）】',
                  f'  {"区间":^12} {"宽度B(m)":^10} {"平均q(m²/s)":^14} '
                  f'{"区间Q(m³/s)":^14}']
        lines.append('  ' + '-' * 55)

        for sg in seg_res:
            lines.append(
                f'  {sg["seg"]:^12} {sg["B"]:^10.3f} {sg["q_avg"]:^14.4f} '
                f'{sg["Q"]:^14.4f}'
            )

        B_total  = sum(pt['B'] for pt in points[1:])
        B_effect = sum(sg['B'] for sg in seg_res if sg['q_avg'] > 0)
        q_avg    = Q_total / B_effect if B_effect > 0 else 0.0

        lines += [
            '  ' + '-' * 55,
            f'  总堰顶宽度（Σ各区间）= {B_total:.3f} m',
            f'  有效过水宽度         = {B_effect:.3f} m',
            f'  平均单宽流量 q̄       = {q_avg:.4f} m²/s',
            '',
            S1,
            f'  ★  总过流量  Q总 = {Q_total:.4f}  m³/s   =  {Q_total:.2f}  m³/s',
            S1,
        ]

        # 淹没汇总警告
        if Ht is not None:
            warns = []
            for cp in cp_res:
                if cp['H0'] > 0:
                    ht_i = Ht - cp['Z']
                    if ht_i > 0 and ht_i / cp['H0'] > 0.75:
                        warns.append(
                            f'    控制点 {cp["name"]}: ht/H₀ = {ht_i/cp["H0"]:.3f} > 0.75 → 淹没出流')
            if warns:
                lines += ['', '  ⚠ 淹没出流警告（以下控制点需查淹没系数 σs 修正 m）:']
                lines.extend(warns)
                lines.append('    → 请参照"流量系数参考"标签中淹没系数说明进行修正后重新计算。')

        return '\n'.join(lines)

    # ── 工具 ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _show(w, text):
        w.config(state='normal')
        w.delete('1.0', 'end')
        w.insert('1.0', text)
        w.config(state='disabled')

    @staticmethod
    def _clear(w):
        w.config(state='normal')
        w.delete('1.0', 'end')
        w.config(state='disabled')

    def _export_txt(self):
        if not self._last_report:
            messagebox.showwarning('无内容', '请先完成计算'); return
        path = filedialog.asksaveasfilename(
            title='导出计算报告', defaultextension='.txt',
            filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')],
            initialfile=f'堰顶过流_{datetime.now():%Y%m%d_%H%M%S}.txt')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8-sig') as f:
                f.write(self._last_report)
            messagebox.showinfo('导出成功', f'报告已保存:\n{path}')
        except Exception as e:
            messagebox.showerror('导出失败', str(e))


# ── 使用说明 ──────────────────────────────────────────────────────────────────
HELP_TEXT = """
溢流堰堰顶不规则断面过流能力计算  ─  使用说明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【适用范围】
  适用于堰顶高程沿宽度方向不均一（"不规则断面"）的溢流堰/溢洪道/
  河道天然溢流段，采用控制点梯形积分法计算总过流量。

  典型场景：
  ① 老旧溢洪道底板高程不规则；
  ② 改扩建工程新旧堰面高差明显；
  ③ 山洪沟过路涵前天然溢流段；
  ④ 河道堤防溃口分析（堤顶高程不均一）。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【计算原理】

  1. 控制点定义
     从左到右沿堰轴线布设 N 个控制点，测量/读取各点堰顶高程 Z_i。
     相邻控制点之间的水平距离为 B_i（第 i 个区间的宽度）。

  2. 各控制点单宽流量（宽顶堰公式）
       h_i  = H  - Z_i          （堰顶水头）
       H0_i = 1.5 × h_i         （总水头，含行近流速水头）
       q_i  = m × √(2g) × H0_i^1.5

     说明: H0 = 1.5h 来自临界水深关系（hc = 2/3·H0），
           近似条件：行近流速 v₀ < 0.5 m/s。

  3. 区间流量（梯形积分）
       Q_区间i = (q_i + q_{i+1}) / 2 × B_i

  4. 总过流量
       Q总 = Σ Q_区间i

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【操作步骤】
  1. 实测上游水位 H（高程，m）；
  2. 从左到右沿堰轴线量取各控制点高程 Z_i 及区间宽度 B_i；
  3. 在"控制点表"中按顺序输入（第1点 B 填0或留空）；
  4. 选择堰型→自动填入默认 m，也可手动修改；
  5. 下游水位 Ht 可选填，仅用于淹没判断；
  6. 点击"开始计算"；
  7. 如有淹没警告，按淹没系数 σs 修正 m 后重算。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【控制点划分建议】
  ① 堰面高程突变处（如台阶、折坡）必须布设控制点；
  ② 均匀段控制点间距建议 ≤ 5 m；
  ③ H - Z_i ≤ 0 的控制点自动标注"未过水"，但仍参与梯形积分，
     相邻区间 q 取为 0，过渡自然；
  ④ 两端边界建议各设一个控制点（可取 Z ≈ H 使 h=0）。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【CSV 导入格式】
  表头（必须）: 编号,Z,B,备注
  第1行 B 可为 0 或留空。示例：
    编号,Z,B,备注
    1,98.00,0,左边界
    2,95.85,1.80,
    3,95.15,9.17,
    ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【参考规程规范】
  SL 253-2018   溢洪道设计规范
  SL 265-2016   水闸设计规范
  GB 50286-2013 堤防工程设计规范
  水力计算手册（第二版），武汉水利电力学院，水利电力出版社

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ── 入口 ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    WeirApp(root)
    root.mainloop()
