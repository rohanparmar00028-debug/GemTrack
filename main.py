import sqlite3
import calendar
import os
import urllib.request
from datetime import datetime, date
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.uix.popup import Popup
from kivy.core.window import Window

# --- DIRECTORY FIX FOR APK ---
# This ensures the app looks for fonts and DB in the right place after install
APP_PATH = os.path.dirname(__file__)
DB_PATH = os.path.join(APP_PATH, 'hira_diary.db')

def get_font_path(font_name):
    return os.path.join(APP_PATH, font_name)

# --- AUTO FONT DOWNLOADER ---
def ensure_fonts_exist():
    gu_font, hi_font = 'NotoSansGujarati-Regular.ttf', 'NotoSansDevanagari-Regular.ttf'
    gu_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansGujarati/NotoSansGujarati-Regular.ttf"
    hi_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"
    
    for f_name, url in [(gu_font, gu_url), (hi_font, hi_url)]:
        p = get_font_path(f_name)
        if not os.path.exists(p):
            try:
                print(f"Downloading {f_name}...")
                urllib.request.urlretrieve(url, p)
            except: pass

ensure_fonts_exist()

FONTS = {
    'EN': 'Roboto',  
    'GU': get_font_path('NotoSansGujarati-Regular.ttf'), 
    'HI': get_font_path('NotoSansDevanagari-Regular.ttf')
}

# --- UI COLORS ---
BG_DEEP_SPACE = (0.04, 0.05, 0.08, 1)    
NEON_CYAN = (0.0, 0.9, 1.0, 1)           
TEXT_WHITE = (0.95, 0.95, 0.95, 1)       
CARD_BG = (0.08, 0.11, 0.16, 0.9)        
DIAMOND_TYPES = ['A', 'B', 'C', 'D']

TEXTS = {
    'EN': {'title': 'HIRA NEXUS', 'btn_add': 'ADD RECORD', 'btn_view': 'VIEW HISTORY', 'btn_rates': 'SET RATES', 'save': 'SAVE', 'footer_qty': 'TOTAL 💎 : ', 'footer_rs': 'NET ₹ : ', 'delete': 'Delete', 'okay': 'Okay'},
    'GU': {'title': 'હીરા નેક્સસ', 'btn_add': 'નવી એન્ટ્રી લખો', 'btn_view': 'રેકોર્ડ જોવો', 'btn_rates': 'ભાવ સેટિંગ', 'save': 'સેવ', 'footer_qty': 'કુલ 💎 : ', 'footer_rs': 'કુલ ₹ : '},
    'HI': {'title': 'हीरा नेक्सस', 'btn_add': 'नई एंट्री', 'btn_view': 'रिकॉर्ड देखें', 'btn_rates': 'रेट सेटिंग', 'save': 'सेव', 'footer_qty': 'कुल 💎 : ', 'footer_rs': 'कुल ₹ : '}
}

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, type TEXT, quantity INTEGER, rate REAL, total REAL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS rates (type TEXT PRIMARY KEY, rate REAL)')
    cursor.execute("SELECT COUNT(*) FROM rates")
    if cursor.fetchone()[0] == 0:
        for t in DIAMOND_TYPES: cursor.execute("INSERT INTO rates (type, rate) VALUES (?, 0.0)", (t,))
    conn.commit(); conn.close()

# --- REUSABLE COMPONENTS ---
class NeonButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''; self.background_color = (0, 0, 0, 0); self.color = NEON_CYAN
        with self.canvas.before:
            Color(*CARD_BG); self.bg = RoundedRectangle(radius=[dp(10)])
            Color(*NEON_CYAN); self.outline = Line(width=dp(1.1))
        self.bind(pos=self.update_graphics, size=self.update_graphics)
    def update_graphics(self, *args):
        self.bg.pos, self.bg.size = self.pos, self.size
        self.outline.rounded_rectangle = [self.x, self.y, self.width, self.height, dp(10)]

class CyberInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''; self.background_color = (0.1, 0.1, 0.15, 1); self.foreground_color = (1, 1, 1, 1)
        self.cursor_color = NEON_CYAN; self.halign = 'center'; self.multiline = False

class CyberCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'; self.size_hint_y = None; self.height = dp(65); self.padding = [dp(15), dp(5)]
        with self.canvas.before:
            Color(*CARD_BG); self.bg = RoundedRectangle(radius=[dp(10)])
            Color(0.0, 0.9, 1.0, 0.2); self.outline = Line(width=dp(1))
        self.bind(pos=self.update_graphics, size=self.update_graphics)
    def update_graphics(self, *args):
        self.bg.pos, self.bg.size = self.pos, self.size
        self.outline.rounded_rectangle = [self.x, self.y, self.width, self.height, dp(10)]

# --- POPUPS ---
class CalendarPopup(Popup):
    def __init__(self, callback, font, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select Date"; self.size_hint = (0.9, 0.7); self.callback = callback
        self.year, self.month = date.today().year, date.today().month
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))
        header = BoxLayout(size_hint_y=None, height=dp(50))
        header.add_widget(Button(text="<", on_press=self.prev_m))
        self.month_lbl = Label(text="", bold=True, font_name=font); header.add_widget(self.month_lbl)
        header.add_widget(Button(text=">", on_press=self.next_m))
        layout.add_widget(header)
        self.grid = GridLayout(cols=7, spacing=dp(2)); layout.add_widget(self.grid)
        self.content = layout; self.update_cal()
    def prev_m(self, *a):
        self.month -= 1
        if self.month < 1: self.month = 12; self.year -= 1
        self.update_cal()
    def next_m(self, *a):
        self.month += 1
        if self.month > 12: self.month = 1; self.year += 1
        self.update_cal()
    def update_cal(self):
        self.grid.clear_widgets(); self.month_lbl.text = f"{calendar.month_name[self.month]} {self.year}"
        cal = calendar.monthcalendar(self.year, self.month)
        for week in cal:
            for day in week:
                if day == 0: self.grid.add_widget(Label())
                else:
                    btn = Button(text=str(day), on_press=lambda x, d=day: self.pick(d))
                    self.grid.add_widget(btn)
    def pick(self, d):
        self.callback(f"{d:02d}/{self.month:02d}/{self.year}"); self.dismiss()

class FuturisticHeader(BoxLayout):
    def __init__(self, screen_obj, **kwargs):
        super().__init__(**kwargs)
        self.screen_obj = screen_obj; self.orientation = 'horizontal'; self.size_hint_y = None; self.height = dp(50)
        with self.canvas.before:
            Color(*BG_DEEP_SPACE); self.bg = Rectangle()
            Color(*NEON_CYAN); self.line = Line(width=dp(1))
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        self.back_btn = Button(text="<", bold=True, size_hint_x=None, width=dp(50), background_color=(0,0,0,0), color=NEON_CYAN)
        self.back_btn.bind(on_press=self.go_back)
        self.title_label = Label(text="", bold=True, color=TEXT_WHITE, font_size=sp(16))
        self.add_widget(self.back_btn); self.add_widget(self.title_label); self.add_widget(Label(size_hint_x=None, width=dp(50)))
    def update_graphics(self, *args):
        self.bg.pos, self.bg.size = self.pos, self.size
        self.line.points = [self.x, self.y, self.right, self.y]
    def go_back(self, instance):
        self.screen_obj.manager.transition = SlideTransition(direction='right'); self.screen_obj.manager.current = 'home'

# --- SCREENS ---
class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before: Color(*BG_DEEP_SPACE); self.bg = Rectangle()
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        top = AnchorLayout(anchor_x='right', size_hint_y=None, height=dp(40))
        self.lang_btn = NeonButton(size_hint=(None, None), size=(dp(100), dp(40)))
        self.lang_btn.bind(on_press=self.toggle_lang); top.add_widget(self.lang_btn); layout.add_widget(top)
        self.lbl_title = Label(color=NEON_CYAN, font_size=sp(28), bold=True, size_hint_y=0.3); layout.add_widget(self.lbl_title)
        for s in ['add', 'view', 'rates']:
            btn = NeonButton(size_hint_y=None, height=dp(55))
            btn.bind(on_press=lambda x, target=s: self.go(target))
            setattr(self, f'btn_{s}', btn); layout.add_widget(btn)
        self.add_widget(layout)
    def update_bg(self, *args): self.bg.pos, self.bg.size = self.pos, self.size
    def toggle_lang(self, i):
        a = App.get_running_app(); l = ['EN', 'GU', 'HI']
        a.lang = l[(l.index(a.lang)+1)%3]; a.update_all_screens()
    def go(self, s):
        self.manager.transition = SlideTransition(direction='left'); self.manager.current = s
        if hasattr(self.manager.get_screen(s), 'load_data'): self.manager.get_screen(s).load_data()
    def update_ui(self, l, f):
        t = TEXTS[l]; self.lang_btn.text = f"LANG: {l}"; self.lbl_title.text = t['title']
        self.btn_add.text = t['btn_add']; self.btn_view.text = t['btn_view']; self.btn_rates.text = t['btn_rates']
        for obj in [self.lbl_title, self.lang_btn, self.btn_add, self.btn_view, self.btn_rates]: obj.font_name = f

class ViewRecordsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before: Color(*BG_DEEP_SPACE); self.bg = Rectangle()
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical')
        self.header = FuturisticHeader(self); layout.add_widget(self.header)
        self.scroll = ScrollView(); self.list = BoxLayout(orientation='vertical', size_hint_y=None, padding=dp(8), spacing=dp(8))
        self.list.bind(minimum_height=self.list.setter('height')); self.scroll.add_widget(self.list)
        layout.add_widget(self.scroll)
        self.footer = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(10))
        with self.footer.canvas.before: Color(*CARD_BG); self.fbg = Rectangle()
        self.footer.bind(pos=self.update_fbg, size=self.update_fbg)
        self.f_qty = Label(bold=True, font_size=sp(13)); self.f_rs = Label(bold=True, color=NEON_CYAN, font_size=sp(13))
        self.footer.add_widget(self.f_qty); self.footer.add_widget(self.f_rs); layout.add_widget(self.footer); self.add_widget(layout)
    def update_bg(self, *args): self.bg.pos, self.bg.size = self.pos, self.size
    def update_fbg(self, *args): self.fbg.pos, self.fbg.size = self.footer.pos, self.footer.size
    def update_ui(self, l, f):
        t = TEXTS[l]; self.header.title_label.text = t['btn_view']; self.header.title_label.font_name = f
        self.f_qty.font_name = f; self.f_rs.font_name = f; self.load_data()
    def load_data(self):
        self.list.clear_widgets()
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT date, SUM(total) FROM entries GROUP BY date ORDER BY date DESC")
        data = cur.fetchall(); l = App.get_running_app().lang; f = FONTS[l]
        for d_str, tot_rs in data:
            card = CyberCard(); row = BoxLayout()
            row.add_widget(Label(text=f"// {d_str}", bold=True, color=NEON_CYAN, font_name=f, halign='left', size_hint_x=0.5))
            row.add_widget(Label(text=f"₹ {tot_rs:.2f}", bold=True, font_name=f, halign='right', size_hint_x=0.4))
            i_btn = Button(text="(i)", size_hint_x=None, width=dp(35), background_color=(0,0,0,0), color=NEON_CYAN, bold=True)
            i_btn.bind(on_press=lambda x, dt=d_str: self.show_detail(dt))
            row.add_widget(i_btn); card.add_widget(row); self.list.add_widget(card)
        cur.execute("SELECT SUM(quantity), SUM(total) FROM entries")
        res = cur.fetchone(); self.f_qty.text = f"{TEXTS[l]['footer_qty']}{res[0] if res[0] else 0}"
        self.f_rs.text = f"{TEXTS[l]['footer_rs']}{res[1] if res[1] else 0:.2f}"; conn.close()
    def show_detail(self, date_str):
        l = App.get_running_app().lang; f, t = FONTS[l], TEXTS[l]
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT type, quantity, rate, total FROM entries WHERE date=?", (date_str,))
        rows = cur.fetchall(); conn.close()
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(8))
        content.add_widget(Label(text=f"DATE: {date_str}", bold=True, font_name=f, font_size=sp(18)))
        grand_tot = 0
        for r in rows:
            line = f"{r[0]} : {r[1]} * {r[2]} = {r[3]:.2f}"; content.add_widget(Label(text=line, font_name=f, font_size=sp(14)))
            grand_tot += r[3]
        content.add_widget(Label(text=f"TOTAL = {grand_tot:.2f}", bold=True, color=NEON_CYAN, font_name=f, font_size=sp(16)))
        btns = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        d_btn = Button(text=t['delete'], background_color=(1, 0.2, 0.2, 1)); d_btn.bind(on_press=lambda x: self.confirm_delete(date_str, p))
        o_btn = Button(text=t['okay'], background_color=(0, 0.8, 0.6, 1)); o_btn.bind(on_press=lambda x: p.dismiss())
        btns.add_widget(d_btn); btns.add_widget(o_btn); content.add_widget(btns)
        p = Popup(title="", content=content, size_hint=(0.8, 0.6), background_color=(0.05, 0.05, 0.05, 1)); p.open()
    def confirm_delete(self, date_str, popup):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("DELETE FROM entries WHERE date=?", (date_str,)); conn.commit(); conn.close()
        popup.dismiss(); self.load_data()

class AddEntryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before: Color(*BG_DEEP_SPACE); self.bg = Rectangle()
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical'); layout.add_widget(FuturisticHeader(self))
        self.date_btn = Button(text=date.today().strftime("%d/%m/%Y"), size_hint_y=None, height=dp(45), background_color=CARD_BG)
        self.date_btn.bind(on_press=self.open_cal); layout.add_widget(self.date_btn); self.rows = {}
        grid = GridLayout(cols=3, padding=dp(10), spacing=dp(8), row_default_height=dp(38), row_force_default=True)
        for t in DIAMOND_TYPES:
            grid.add_widget(Label(text=f"[{t}]", bold=True, color=NEON_CYAN))
            qty = CyberInput(input_filter='int'); grid.add_widget(qty)
            rate = Label(text="0.0"); grid.add_widget(rate); self.rows[t] = (qty, rate)
        layout.add_widget(grid); self.save_btn = NeonButton(size_hint_y=None, height=dp(55))
        self.save_btn.bind(on_press=self.save_entry); layout.add_widget(self.save_btn); self.add_widget(layout)
    def update_bg(self, *args): self.bg.pos, self.bg.size = self.pos, self.size
    def open_cal(self, *a): CalendarPopup(callback=self.set_dt, font=FONTS[App.get_running_app().lang]).open()
    def set_dt(self, dt): self.date_btn.text = dt
    def load_data(self):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor(); cur.execute("SELECT type, rate FROM rates")
        for r in cur.fetchall():
            if r[0] in self.rows: self.rows[r[0]][1].text = str(r[1])
        conn.close()
    def save_entry(self, i):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor(); dt = self.date_btn.text
        for t, (qty_in, rate_lbl) in self.rows.items():
            q = int(qty_in.text or 0); r = float(rate_lbl.text)
            if q > 0: cur.execute("INSERT INTO entries (date, type, quantity, rate, total) VALUES (?,?,?,?,?)", (dt, t, q, r, q*r))
        conn.commit(); conn.close()
        for q_in, r_l in self.rows.values(): q_in.text = ""
        self.manager.current = 'home'
    def update_ui(self, l, f): self.save_btn.text = TEXTS[l]['save']; self.save_btn.font_name = f

class RatesScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before: Color(*BG_DEEP_SPACE); self.bg = Rectangle()
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical'); layout.add_widget(FuturisticHeader(self))
        self.inputs = {}
        grid = GridLayout(cols=2, padding=dp(20), spacing=dp(10), row_default_height=dp(40), row_force_default=True)
        for t in DIAMOND_TYPES:
            grid.add_widget(Label(text=f"[{t}]", color=NEON_CYAN, bold=True))
            inp = TextInput(input_filter='float', multiline=False, halign='center'); self.inputs[t] = inp; grid.add_widget(inp)
        layout.add_widget(grid); self.save_btn = NeonButton(size_hint_y=None, height=dp(50))
        self.save_btn.bind(on_press=self.save_rates); layout.add_widget(self.save_btn); self.add_widget(layout)
    def update_bg(self, *args): self.bg.pos, self.bg.size = self.pos, self.size
    def update_ui(self, l, f): self.save_btn.text = TEXTS[l]['save']; self.save_btn.font_name = f
    def load_data(self):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor(); cur.execute("SELECT type, rate FROM rates")
        for r in cur.fetchall():
            if r[0] in self.inputs: self.inputs[r[0]].text = str(r[1])
        conn.close()
    def save_rates(self, i):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        for t, inp in self.inputs.items(): cur.execute("UPDATE rates SET rate=? WHERE type=?", (float(inp.text or 0), t))
        conn.commit(); conn.close(); self.manager.current = 'home'

# --- APP ---
class MainApp(App):
    def __init__(self, **kwargs): super().__init__(**kwargs); self.lang = 'EN'
    def build(self):
        setup_database(); self.sm = ScreenManager()
        self.sm.add_widget(HomeScreen(name='home'))
        self.sm.add_widget(RatesScreen(name='rates'))
        self.sm.add_widget(AddEntryScreen(name='add'))
        self.sm.add_widget(ViewRecordsScreen(name='view'))
        self.update_all_screens(); return self.sm
    def update_all_screens(self):
        f = FONTS[self.lang]
        for s in self.sm.screens:
            if hasattr(s, 'update_ui'): s.update_ui(self.lang, f)

if __name__ == '__main__': MainApp().run()
