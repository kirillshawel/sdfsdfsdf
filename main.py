# -*- coding: utf-8 -*-
"""mishabetmen Android (Kivy) — master key + encrypted vault + sync import."""
from __future__ import annotations
import json
import os
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.utils import platform

# storage dir
if platform == "android":
    from android.storage import app_storage_path  # type: ignore
    DATA = Path(app_storage_path()) / "data"
else:
    DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(parents=True, exist_ok=True)

# reuse desktop crypto if present, else minimal vault in JSON gated by key hash (android build bundles security.py)
try:
    from security import (
        vault_exists, create_vault, unlock_vault, save_vault,
        import_sync_blob,
    )
    HAS_SEC = True
except Exception:
    HAS_SEC = False

KV = """
#:import dp kivy.metrics.dp

<GateScreen>:
    canvas.before:
        Color:
            rgba: 0.043, 0.055, 0.078, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: "vertical"
        padding: dp(28)
        spacing: dp(12)
        Label:
            text: "mishabetmen"
            color: 0.357, 0.553, 0.937, 1
            font_size: "24sp"
            size_hint_y: None
            height: dp(40)
        Label:
            text: "Введите мастер-ключ"
            color: 0.42, 0.48, 0.56, 1
            font_size: "14sp"
            size_hint_y: None
            height: dp(24)
        TextInput:
            id: key
            password: True
            multiline: False
            size_hint_y: None
            height: dp(48)
            background_color: 0.08, 0.10, 0.13, 1
            foreground_color: 0.91, 0.93, 0.97, 1
            cursor_color: 0.357, 0.553, 0.937, 1
            padding: [dp(14), dp(14)]
        Label:
            id: msg
            text: ""
            color: 0.95, 0.33, 0.35, 1
            font_size: "13sp"
            size_hint_y: None
            height: dp(22)
        Button:
            text: "Войти"
            size_hint_y: None
            height: dp(48)
            background_normal: ""
            background_color: 0.357, 0.553, 0.937, 1
            on_release: root.do_unlock()
        Label:
            text: "Ключ выдаёт только админ"
            color: 0.42, 0.48, 0.56, 1
            font_size: "12sp"
            size_hint_y: None
            height: dp(24)

<MainScreen>:
    canvas.before:
        Color:
            rgba: 0.043, 0.055, 0.078, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(8)
        Label:
            text: "mishabetmen"
            color: 0.357, 0.553, 0.937, 1
            font_size: "20sp"
            size_hint_y: None
            height: dp(36)
            halign: "left"
            text_size: self.size
        ScrollView:
            GridLayout:
                id: acc_box
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
                row_default_height: dp(64)
                row_force_default: True
        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)
            Button:
                text: "Import sync"
                background_normal: ""
                background_color: 0.357, 0.553, 0.937, 1
                on_release: root.import_sync()
            Button:
                text: "Обновить"
                background_normal: ""
                background_color: 0.10, 0.13, 0.18, 1
                on_release: root.refresh()

<DetailScreen>:
    phone: ""
    canvas.before:
        Color:
            rgba: 0.043, 0.055, 0.078, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(10)
        Label:
            id: title
            text: root.phone
            color: 0.91, 0.93, 0.97, 1
            font_size: "18sp"
            size_hint_y: None
            height: dp(32)
        Label:
            text: "LOGIN CODE"
            color: 0.42, 0.48, 0.56, 1
            font_size: "11sp"
            size_hint_y: None
            height: dp(18)
        Label:
            id: code
            text: "—"
            color: 0.357, 0.553, 0.937, 1
            font_size: "28sp"
            size_hint_y: None
            height: dp(40)
        Label:
            text: "2FA PASSWORD"
            color: 0.42, 0.48, 0.56, 1
            font_size: "11sp"
            size_hint_y: None
            height: dp(18)
        Label:
            id: pwd
            text: "••••••"
            color: 0.24, 0.84, 0.55, 1
            font_size: "16sp"
            size_hint_y: None
            height: dp(28)
        Label:
            id: raw
            text: ""
            color: 0.72, 0.77, 0.85, 1
            font_size: "13sp"
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1] + dp(8)
        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)
            Button:
                text: "Copy code"
                background_normal: ""
                background_color: 0.10, 0.13, 0.18, 1
                on_release: root.copy_code()
            Button:
                text: "Copy pwd"
                background_normal: ""
                background_color: 0.10, 0.13, 0.18, 1
                on_release: root.copy_pwd()
            Button:
                text: "Назад"
                background_normal: ""
                background_color: 0.357, 0.553, 0.937, 1
                on_release: root.go_back()
"""


class GateScreen(Screen):
    def do_unlock(self):
        key = self.ids.key.text.strip()
        if not key:
            self.ids.msg.text = "Введи ключ"
            return
        try:
            from license_keys import verify_license
            if not verify_license(key):
                self.ids.msg.color = (0.95, 0.33, 0.35, 1)
                self.ids.msg.text = "Неверный ключ"
                return
        except Exception:
            self.ids.msg.text = "license module error"
            return
        app = App.get_running_app()
        try:
            if HAS_SEC:
                import security
                security.DATA_DIR = DATA
                security.VAULT_FILE = DATA / "vault.enc"
                security.META_FILE = DATA / "vault.meta.json"
                DATA.mkdir(parents=True, exist_ok=True)
                if not security.vault_exists():
                    security.create_vault(key, {"accounts": {}})
                try:
                    data = security.unlock_vault(key)
                except Exception:
                    security.create_vault(key, {"accounts": {}})
                    data = security.unlock_vault(key)
            else:
                data = {"accounts": {}}
            app.master_key = key
            app.vault = data
            self.manager.get_screen("main").refresh()
            self.manager.current = "main"
        except Exception:
            self.ids.msg.color = (0.95, 0.33, 0.35, 1)
            self.ids.msg.text = "Ошибка входа"


class MainScreen(Screen):
    def refresh(self):
        box = self.ids.acc_box
        box.clear_widgets()
        app = App.get_running_app()
        accounts = (app.vault or {}).get("accounts", {})
        if not accounts:
            box.add_widget(Label(text="Нет аккаунтов — Import sync", color=(0.42, 0.48, 0.56, 1)))
            return
        for ph in sorted(accounts.keys()):
            info = accounts[ph]
            name = info.get("name") or ""
            code = info.get("last_code") or ""
            txt = f"{ph}\n{name}" + (f"  ·  {code}" if code else "")
            btn = Button(
                text=txt,
                halign="left",
                background_normal="",
                background_color=(0.08, 0.10, 0.13, 1),
                size_hint_y=None,
                height=dp(64),
            )
            btn.bind(on_release=lambda _b, p=ph: self.open_detail(p))
            box.add_widget(btn)

    def open_detail(self, phone):
        app = App.get_running_app()
        info = (app.vault or {}).get("accounts", {}).get(phone, {})
        d = self.manager.get_screen("detail")
        d.phone = phone
        d.ids.title.text = phone
        d.ids.code.text = info.get("last_code") or "—"
        d.ids.pwd.text = "••••••"
        d._pwd = info.get("password") or ""
        d.ids.raw.text = info.get("last_raw") or ""
        self.manager.current = "detail"

    def import_sync(self):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        ti = TextInput(hint_text="Вставь sync blob или JSON", multiline=True)
        content.add_widget(ti)
        bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        pop = Popup(title="Import sync", content=content, size_hint=(0.92, 0.6))

        def do(_):
            raw = ti.text.strip()
            try:
                if raw.startswith("{"):
                    j = json.loads(raw)
                    acc = j.get("accounts", j)
                else:
                    if not HAS_SEC:
                        raise RuntimeError("no security")
                    import security
                    security.DATA_DIR = DATA
                    j = security.import_sync_blob(app.master_key, raw)
                    acc = j.get("accounts", {})
                app.vault.setdefault("accounts", {}).update(acc)
                if HAS_SEC:
                    import security
                    security.DATA_DIR = DATA
                    security.VAULT_FILE = DATA / "vault.enc"
                    security.META_FILE = DATA / "vault.meta.json"
                    security.save_vault(app.master_key, app.vault)
                pop.dismiss()
                self.refresh()
            except Exception as e:
                ti.text = f"Ошибка: {e}"

        ok = Button(text="Import", background_normal="", background_color=(0.357, 0.553, 0.937, 1))
        ok.bind(on_release=do)
        bar.add_widget(ok)
        content.add_widget(bar)
        pop.open()


class DetailScreen(Screen):
    phone = StringProperty("")
    _pwd = ""

    def copy_code(self):
        t = self.ids.code.text
        if t and t != "—":
            Clipboard.copy(t)

    def copy_pwd(self):
        if self._pwd:
            Clipboard.copy(self._pwd)
            self.ids.pwd.text = self._pwd

    def go_back(self):
        self.manager.current = "main"


class MishaApp(App):
    master_key = None
    vault = None

    def build(self):
        Window.clearcolor = (0.043, 0.055, 0.078, 1)
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(GateScreen(name="gate"))
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(DetailScreen(name="detail"))
        return sm


if __name__ == "__main__":
    MishaApp().run()
