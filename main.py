# -*- coding: utf-8 -*-
"""
СИСТЕМА УПРАВЛЕНИЯ ДОГОВОРАМИ
ООО "ФАСТЛЭНД" | Москва, 2025
"""

import os
import re
import sqlite3
import hashlib
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from typing import Optional
import subprocess
import platform

import tkinter.font as tkfont


# noinspection PyBroadException
class TextShortcutsMixin:
    """Миксин для добавления горячих клавиш работы с текстом"""

    def __init__(self, *args, **kwargs):
        # Вызываем конструктор следующего класса в MRO
        super().__init__(*args, **kwargs)
        # История изменений для Entry виджетов
        self.entry_history = {}
        self.entry_history_index = {}

    def setup_text_shortcuts(self, widget):
        """Настройка горячих клавиш для текстового виджета"""
        widget_id = str(widget)

        if isinstance(widget, tk.Text):
            # Для Text виджета включаем поддержку отмены/повтора
            widget.configure(undo=True, autoseparators=True, maxundo=-1)

        elif isinstance(widget, (ttk.Entry, tk.Entry)):
            # Для Entry виджетов инициализируем историю изменений
            self.entry_history[widget_id] = []
            self.entry_history_index[widget_id] = -1

            # Сохраняем начальное состояние
            initial_text = widget.get()
            self._save_entry_state(widget, initial_text)

            # Привязываем обработчики изменений
            widget.bind('<KeyPress>', lambda e: self._on_entry_key_press(e))
            widget.bind('<FocusOut>', lambda e: self._save_entry_state(e.widget, e.widget.get()))

        # Общие горячие клавиши для всех виджетов
        # Ctrl+A - выделить все
        widget.bind('<Control-Key-a>', self.select_all)
        widget.bind('<Control-Key-A>', self.select_all)

        # Ctrl+C - копировать
        widget.bind('<Control-Key-c>', self.copy_text)
        widget.bind('<Control-Key-C>', self.copy_text)

        # Ctrl+X - вырезать
        widget.bind('<Control-Key-x>', self.cut_text)
        widget.bind('<Control-Key-X>', self.cut_text)

        # Ctrl+V - вставить
        widget.bind('<Control-Key-v>', self.paste_text)
        widget.bind('<Control-Key-V>', self.paste_text)

        # Ctrl+Z - отменить
        widget.bind('<Control-Key-z>', self.undo_text)
        widget.bind('<Control-Key-Z>', self.undo_text)

        # Ctrl+Y - повторить
        widget.bind('<Control-Key-y>', self.redo_text)
        widget.bind('<Control-Key-Y>', self.redo_text)

    def _on_entry_key_press(self, event):
        """Обработчик нажатия клавиш для Entry виджетов"""
        # Игнорируем служебные клавиши
        if event.keysym in ['Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Shift_L', 'Shift_R']:
            return

        # Игнорируем сочетания клавиш, которые обрабатываются отдельно
        if event.state & 0x4:  # Control key
            return

        # Сохраняем состояние после короткой задержки (чтобы изменение уже произошло)
        widget = event.widget
        widget.after(10, lambda: self._save_entry_state(widget, widget.get()))

    def _save_entry_state(self, widget, text):
        """Сохраняет состояние Entry виджета в историю"""
        widget_id = str(widget)

        if widget_id not in self.entry_history:
            return

        history = self.entry_history[widget_id]
        current_index = self.entry_history_index[widget_id]

        # Если текущий текст совпадает с последним сохраненным, не сохраняем
        if history and history[current_index] == text:
            return

        # Удаляем все состояния после текущего индекса
        if current_index < len(history) - 1:
            del history[current_index + 1:]

        # Добавляем новое состояние
        history.append(text)

        # Ограничиваем размер истории
        if len(history) > 50:  # Максимум 50 состояний
            history.pop(0)

        # Обновляем индекс
        self.entry_history_index[widget_id] = len(history) - 1

    @staticmethod
    def select_all(event):
        """Выделить весь текст"""
        widget = event.widget
        if isinstance(widget, tk.Text):
            # Для Text виджета используем tag_add
            widget.tag_add('sel', '1.0', 'end')
            widget.mark_set('insert', '1.0')
        elif isinstance(widget, (ttk.Entry, tk.Entry)):
            # Для Entry виджета используем select_range
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
        return "break"

    @staticmethod
    def copy_text(event):
        """Копировать текст"""
        widget = event.widget
        try:
            if isinstance(widget, tk.Text):
                selected_text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                widget.clipboard_clear()
                widget.clipboard_append(selected_text)
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                selected_text = widget.selection_get()
                widget.clipboard_clear()
                widget.clipboard_append(selected_text)
        except tk.TclError:
            # Если ничего не выделено, копируем весь текст
            if isinstance(widget, tk.Text):
                all_text = widget.get(1.0, tk.END)
                widget.clipboard_clear()
                widget.clipboard_append(all_text)
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                all_text = widget.get()
                widget.clipboard_clear()
                widget.clipboard_append(all_text)
        return "break"

    def cut_text(self, event):
        """Вырезать текст"""
        widget = event.widget
        try:
            if isinstance(widget, tk.Text):
                selected_text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                widget.clipboard_clear()
                widget.clipboard_append(selected_text)
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                selected_text = widget.selection_get()
                widget.clipboard_clear()
                widget.clipboard_append(selected_text)
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                # Сохраняем новое состояние после вырезания
                self._save_entry_state(widget, widget.get())
        except tk.TclError:
            pass
        return "break"

    def paste_text(self, event):
        """Вставить текст"""
        widget = event.widget
        try:
            clipboard_text = widget.clipboard_get()
            if isinstance(widget, tk.Text):
                try:
                    # Удаляем выделенный текст если есть
                    widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass
                widget.insert(tk.INSERT, clipboard_text)
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                try:
                    # Удаляем выделенный текст если есть
                    widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass
                widget.insert(tk.INSERT, clipboard_text)
                # Сохраняем новое состояние после вставки
                self._save_entry_state(widget, widget.get())
        except tk.TclError:
            pass
        return "break"

    def undo_text(self, event):
        """Отменить последнее действие"""
        widget = event.widget

        if isinstance(widget, tk.Text):
            # Для Text виджета используем встроенную систему отмены
            try:
                if widget.edit_undo():
                    widget.edit_separator()
            except tk.TclError:
                pass

        elif isinstance(widget, (ttk.Entry, tk.Entry)):
            # Для Entry виджета используем модифицированную систему отмены
            widget_id = str(widget)
            if widget_id in self.entry_history and widget_id in self.entry_history_index:
                history = self.entry_history[widget_id]
                current_index = self.entry_history_index[widget_id]

                if current_index > 0:
                    # Переходим к предыдущему состоянию
                    new_index = current_index - 1
                    previous_text = history[new_index]

                    # Сохраняем текущую позицию курсора
                    cursor_pos = widget.index(tk.INSERT)

                    # Восстанавливаем текст
                    widget.delete(0, tk.END)
                    widget.insert(0, previous_text)

                    # Восстанавливаем позицию курсора (если возможно)
                    try:
                        widget.icursor(min(cursor_pos, len(previous_text)))
                    except:
                        widget.icursor(tk.END)

                    # Обновляем индекс
                    self.entry_history_index[widget_id] = new_index

        return "break"

    def redo_text(self, event):
        """Повторить последнее действие"""
        widget = event.widget

        if isinstance(widget, tk.Text):
            # Для Text виджета используем встроенную систему повтора
            try:
                if widget.edit_redo():
                    widget.edit_separator()
            except tk.TclError:
                pass

        elif isinstance(widget, (ttk.Entry, tk.Entry)):
            # Для Entry виджета используем модифицированную систему повтора
            widget_id = str(widget)
            if widget_id in self.entry_history and widget_id in self.entry_history_index:
                history = self.entry_history[widget_id]
                current_index = self.entry_history_index[widget_id]

                if current_index < len(history) - 1:
                    # Переходим к следующему состоянию
                    new_index = current_index + 1
                    next_text = history[new_index]

                    # Сохраняем текущую позицию курсора
                    cursor_pos = widget.index(tk.INSERT)

                    # Восстанавливаем текст
                    widget.delete(0, tk.END)
                    widget.insert(0, next_text)

                    # Восстанавливаем позицию курсора (если возможно)
                    try:
                        widget.icursor(min(cursor_pos, len(next_text)))
                    except:
                        widget.icursor(tk.END)

                    # Обновляем индекс
                    self.entry_history_index[widget_id] = new_index

        return "break"


class HoverTooltip:
    """Toplevel tooltip with delay."""

    def __init__(self, parent, wraplength=700, delay=500):
        self.parent = parent
        self.wraplength = wraplength
        self.delay = delay
        self._after_id = None
        self._tw = None

    def schedule(self, text, x, y):
        self.cancel()
        self._after_id = self.parent.after(self.delay, lambda: self._show_now(text, x, y))

    def cancel(self):
        if self._after_id:
            try:
                self.parent.after_cancel(self._after_id)
            except tk.TclError:
                pass
        self._after_id = None
        self.hide()

    def _show_now(self, text, x, y):
        self.hide()
        try:
            tw = tk.Toplevel(self.parent)
            tw.wm_overrideredirect(True)
            try:
                tw.attributes("-topmost", True)
            except tk.TclError:
                pass
            lbl = tk.Label(tw, text=text, justify="left", anchor="w", relief="solid", borderwidth=1, padx=6, pady=4, wraplength=self.wraplength)
            lbl.pack()
            tw.update_idletasks()
            sw = tw.winfo_screenwidth()
            sh = tw.winfo_screenheight()
            w = tw.winfo_width()
            h = tw.winfo_height()
            x0 = x + 16
            y0 = y + 16
            if x0 + w > sw:
                x0 = max(sw - w - 10, 10)
            if y0 + h > sh:
                y0 = max(sh - h - 10, 10)
            tw.wm_geometry(f"+{x0}+{y0}")
            self._tw = tw
        except tk.TclError:
            self._tw = None

    def hide(self):
        if self._tw:
            try:
                self._tw.destroy()
            except tk.TclError:
                pass
        self._tw = None


# ======================= КОНФИГУРАЦИЯ =======================
DB_FILE = "contracts.db"
LOG_FILE = "app_log.txt"
BACKUP_DIR = "backups"


# ======================= УТИЛИТАРНЫЕ ФУНКЦИИ =======================
def validate_inn(inn: str, org_type: str = 'legal') -> bool:
    """Проверка валидности ИНН с учетом типа организации"""
    if not inn.isdigit():
        return False

    if org_type == 'legal':
        if len(inn) == 10:
            # Проверка контрольной суммы для 10-значного ИНН Юр. Лица
            coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
            checksum = sum(int(inn[i]) * coefficients[i] for i in range(9)) % 11
            if checksum > 9:
                checksum %= 10
            return checksum == int(inn[9])
        elif len(inn) == 12:
            # Проверка контрольных сумм для 12-значного ИНН
            coefficients1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
            checksum1 = sum(int(inn[i]) * coefficients1[i] for i in range(10)) % 11
            if checksum1 > 9:
                checksum1 %= 10

            coefficients2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
            checksum2 = sum(int(inn[i]) * coefficients2[i] for i in range(11)) % 11
            if checksum2 > 9:
                checksum2 %= 10

            return checksum1 == int(inn[10]) and checksum2 == int(inn[11])
    else:  # individual (ИП)
        if len(inn) == 12:
            # Проверка контрольных сумм для ИП (12 цифр)
            coefficients1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0]
            checksum1 = sum(int(inn[i]) * coefficients1[i] for i in range(11)) % 11
            if checksum1 > 9:
                checksum1 %= 10

            coefficients2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0]
            checksum2 = sum(int(inn[i]) * coefficients2[i] for i in range(12)) % 11
            if checksum2 > 9:
                checksum2 %= 10

            return checksum1 == int(inn[10]) and checksum2 == int(inn[11])

    return False


def validate_kpp(kpp: str) -> bool:
    """Проверка валидности КПП"""
    if len(kpp) != 9:
        return False
    # КПП должен состоять из 9 цифр
    return kpp.isdigit()


def validate_ogrn(ogrn: str, org_type: str = 'legal') -> bool:
    """Проверка валидности ОГРН с учетом типа организации"""
    if not ogrn.isdigit():
        return False

    if org_type == 'legal':
        # ОГРН Юр. Лица (13 цифр)
        if len(ogrn) == 13:
            checksum = int(ogrn[:-1]) % 11
            if checksum > 9:
                checksum %= 10
            return checksum == int(ogrn[-1])
    else:  # individual (ИП)
        # ОГРНИП (15 цифр)
        if len(ogrn) == 15:
            checksum = int(ogrn[:-1]) % 13
            if checksum > 9:
                checksum %= 10
            return checksum == int(ogrn[-1])

    return False


def validate_phone(phone: str) -> bool:
    """Проверка валидности телефона по шаблону +7 (xxx) xxx-xxxx"""
    pattern = r'^\+7 \(\d{3}\) \d{3}-\d{4}$'
    return bool(re.match(pattern, phone))


def validate_email(email: str) -> bool:
    """Проверка валидности email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def format_phone(phone: str) -> str:
    """Форматирование телефона в формат +7 (xxx) xxx-xxxx"""
    if not phone:
        return ""

    # Удаляем все нецифровые символы
    digits = ''.join(filter(lambda x: x.isdigit(), phone))

    if digits.startswith('7') and len(digits) == 11:
        digits = digits[1:]  # Убираем первую 7
    elif digits.startswith('8') and len(digits) == 11:
        digits = digits[1:]  # Убираем первую 8
    elif len(digits) == 10:
        pass  # Оставляем как есть
    else:
        return phone  # Возвращаем исходное значение если формат не распознан

    if len(digits) == 10:
        return f"+7 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    return phone


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def format_amount(amount) -> str:
    try:
        if amount is None:
            return "0,00"
        return f"{float(amount):,.2f}".replace(",", " ").replace(".", ",")
    except (ValueError, TypeError):
        return "0,00"


def parse_amount(text: str) -> float:
    try:
        return float(text.replace(" ", "").replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def center_window(win):
    """Центрирует окно на экране без фиксированного размера"""
    win.update_idletasks()
    width = win.winfo_reqwidth()
    height = win.winfo_reqheight()
    x = (win.winfo_screenwidth() // 2) - (width // 2)
    y = (win.winfo_screenheight() // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")


def center_window_with_size(win, width, height):
    """Центрирует окно с указанным размером"""
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (width // 2)
    y = (win.winfo_screenheight() // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")


def log_message(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    print(log_entry)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except OSError:
        pass


def open_file(file_path: str):
    """Открывает файл с помощью системного приложения по умолчанию"""
    try:
        if os.path.exists(file_path):
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", file_path], check=False)
            else:
                subprocess.run(["xdg-open", file_path], check=False)
            return True
        else:
            messagebox.showerror("Ошибка", f"Файл не найден:\n{file_path}")
            return False
    except (OSError, subprocess.SubprocessError) as e:
        messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{str(e)}")
        return False


class AmountEntry(ttk.Entry):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.bind('<KeyRelease>', self._format)
        self.bind('<FocusOut>', self._format)

    def _format(self, event=None):
        if event and event.keysym == 'Escape':
            return
        value = self.get()
        cleaned = re.sub(r'[^\d,.]', '', value).replace('.', ',')
        parts = cleaned.split(',')
        if len(parts) > 2:
            cleaned = parts[0] + ',' + ''.join(parts[1:])
        if ',' in cleaned:
            integer, decimal = cleaned.split(',', 1)
            decimal = decimal[:2]
            integer = integer.lstrip('0') or '0'
            if integer != '0':
                integer = f"{int(integer):,}".replace(',', ' ')
            formatted = f"{integer},{decimal}"
        else:
            integer = cleaned.lstrip('0') or '0'
            if integer != '0':
                integer = f"{int(integer):,}".replace(',', ' ')
            formatted = integer
        if formatted != value:
            pos = self.index(tk.INSERT)
            self.delete(0, tk.END)
            self.insert(0, formatted)
            self.icursor(min(pos, len(formatted)))


class PhoneEntry(ttk.Entry):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.bind('<KeyRelease>', self._format)
        self.bind('<FocusIn>', lambda e: self._on_focus_in())
        self.bind('<FocusOut>', lambda e: self._on_focus_out())
        self._has_initial_format = False

    def _on_focus_in(self):
        """Обработчик получения фокуса"""
        if not self._has_initial_format and not self.get().strip():
            # Если поле пустое, устанавливаем +7
            self.delete(0, tk.END)
            self.insert(0, "+7 (")
            self._has_initial_format = True
            self.icursor(4)

    def _on_focus_out(self):
        """Обработчик потери фокуса"""
        value = self.get().strip()
        if value in ["+7 (", ""]:
            # Если только +7 или пусто, очищаем поле
            self.delete(0, tk.END)
            self._has_initial_format = False

    def _format(self, event=None):
        """Форматирование номера телефона"""
        # Игнорируем служебные клавиши (стрелки, удаление и т.д.)
        if event and event.keysym in ['Left', 'Right', 'Up', 'Down', 'BackSpace', 'Delete', 'Tab', 'Return', 'Escape']:
            return

        value = self.get()

        # Сохраняем позицию курсора
        cursor_pos = self.index(tk.INSERT)

        # Удаляем все нецифровые символы, кроме +
        digits = ''.join(filter(lambda x: x.isdigit() or x == '+', value))

        # Если начинается с +7, убираем его для обработки
        if digits.startswith('+7'):
            digits = digits[2:]
        elif digits.startswith('7'):
            digits = digits[1:]
        elif digits.startswith('8'):
            digits = digits[1:]

        # Ограничиваем длину (10 цифр без кода страны)
        if len(digits) > 10:
            digits = digits[:10]

        # Форматируем по шаблону
        if len(digits) >= 10:
            formatted = f"+7 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) >= 6:
            formatted = f"+7 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) >= 3:
            formatted = f"+7 ({digits[:3]}) {digits[3:]}"
        elif digits:
            formatted = f"+7 ({digits}"
        else:
            formatted = "+7 ("
            self._has_initial_format = True

        if formatted != value:
            # Сохраняем позицию относительно цифр
            if cursor_pos > 0:
                # Подсчитываем количество цифр до позиции курсора
                digits_before = ''.join([x for x in value[:cursor_pos] if x.isdigit() or x == '+'])
                new_cursor_pos = self._find_cursor_position(formatted, len(digits_before))
            else:
                new_cursor_pos = len(formatted)

            self.delete(0, tk.END)
            self.insert(0, formatted)
            self.icursor(new_cursor_pos)

    @staticmethod
    def _find_cursor_position(formatted_phone, digits_count):
        """Находит позицию курсора в отформатированном номере на основе количества цифр"""
        if digits_count == 0:
            return 4

        digit_positions = []
        digit_index = 0

        for i, char in enumerate(formatted_phone):
            if char.isdigit():
                digit_positions.append(i)
                digit_index += 1
                if digit_index >= digits_count:
                    return i + 1  # Позиция после текущей цифры

        return len(formatted_phone)  # Если что-то пошло не так, ставим в конец

    def get_clean_phone(self):
        """Возвращает очищенный номер телефона (только цифры)"""
        value = self.get()
        digits = ''.join([x for x in value if x.isdigit()])
        if digits.startswith('7') and len(digits) == 11:
            return digits
        elif len(digits) == 10:
            return '7' + digits
        return digits

    def set_phone(self, phone_number):
        """Устанавливает номер телефона с форматированием"""
        if phone_number:
            formatted = format_phone(phone_number)
            self.delete(0, tk.END)
            self.insert(0, formatted)
            self._has_initial_format = True


# ======================= СЕРВИС АВТОМАТИЧЕСКОГО НАЗНАЧЕНИЯ =======================
class AutoAssignService:
    def __init__(self):
        self.user_assignments = {}
        log_message("Сервис автоматического назначения инициализирован")

    def get_next_user_by_round_robin(self, role_name: str) -> Optional[int]:
        """Получить следующего пользователя по принципу round-robin"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute('''
                SELECT u.id FROM users u
                JOIN user_roles ur ON u.id = ur.user_id
                JOIN roles r ON ur.role_id = r.id
                WHERE r.name = ? AND u.is_active = 1
                ORDER BY u.id
            ''', (role_name,))
            users = [row[0] for row in cur.fetchall()]

            if not users:
                return None

            if role_name not in self.user_assignments:
                self.user_assignments[role_name] = 0

            user_id = users[self.user_assignments[role_name] % len(users)]
            self.user_assignments[role_name] += 1

            return user_id
        except sqlite3.Error as e:
            log_message(f"Ошибка в round-robin назначении: {e}")
            return None


# ======================= ИНИЦИАЛИЗАЦИЯ БД =======================
def init_database():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Создание таблиц
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            organization_type TEXT DEFAULT 'legal',  -- 'legal' или 'individual'
            inn TEXT, kpp TEXT, ogrn TEXT,
            legal_address TEXT, phone TEXT, email TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password TEXT NOT NULL,
            department TEXT,
            position TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER,
            role_id INTEGER,
            PRIMARY KEY(user_id, role_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(role_id) REFERENCES roles(id)
        );

        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_number TEXT UNIQUE,
            title TEXT NOT NULL,
            counterparty TEXT,
            amount REAL DEFAULT 0,
            status TEXT DEFAULT 'Черновик',
            owner_id INTEGER,
            department TEXT,
            file_path TEXT,
            priority TEXT DEFAULT 'standard',
            deadline_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS approval_flows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            department TEXT,
            steps TEXT  -- JSON: [{"step":1, "role":"Юрист", "deadline_days":2}, ...]
        );

        CREATE TABLE IF NOT EXISTS approval_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER,
            flow_id INTEGER,
            status TEXT DEFAULT 'running',
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT,
            FOREIGN KEY(contract_id) REFERENCES contracts(id),
            FOREIGN KEY(flow_id) REFERENCES approval_flows(id)
        );

        CREATE TABLE IF NOT EXISTS approval_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id INTEGER,
            step_order INTEGER,
            role_name TEXT,
            assigned_user_id INTEGER,
            status TEXT DEFAULT 'pending',
            assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            comment TEXT,
            deadline_at TEXT,
            deadline_notified INTEGER DEFAULT 0,
            FOREIGN KEY(instance_id) REFERENCES approval_instances(id),
            FOREIGN KEY(assigned_user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    ''')

    # Добавление тестовых данных
    try:
        # Организация
        if cur.execute("SELECT COUNT(*) FROM organizations").fetchone()[0] == 0:
            # Основная организация
            cur.execute(
                "INSERT INTO organizations (name, organization_type, inn, kpp, ogrn, legal_address, phone, email) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("ООО 'ФАСТЛЭНД'", "legal", "7703234453", "770301001", "1027739292448",
                 "123242, Г.МОСКВА, ВН.ТЕР.Г. МУНИЦИПАЛЬНЫЙ ОКРУГ ПРЕСНЕНСКИЙ, УЛ БОЛЬШАЯ ГРУЗИНСКАЯ, Д. 20, ПОМЕЩ. 3/П",
                 "+7 (495) 785-81-11", "fastland@cafemumu.ru")
            )

            # 20 тестовых организаций
            test_organizations = [
                ("ООО 'Поставщик+'", "legal", "3328450239", "772501001", "1073328002846",
                 "115470, Г.МОСКВА, УЛ. СУДОСТРОИТЕЛЬНАЯ, Д.25, К.2",
                 "+7 (495) 123-45-67", "info@postavchik.ru"),
                ("ТК 'Ашан'", "legal", "7703270067", "502901001", "1027739329408",
                 "141031, МОСКОВСКАЯ ОБЛАСТЬ, Г.О. МЫТИЩИ, Г МЫТИЩИ, Ш ОСТАШКОВСКОЕ, Д. 1",
                 "+7 (495) 234-56-78", "contracts@auchan.ru"),
                ("ООО 'СервисПро'", "legal", "772708432703", "772701001", "1237700891119",
                 "117461, Г.МОСКВА, ВН.ТЕР.Г. МУНИЦИПАЛЬНЫЙ ОКРУГ ЗЮЗИНО, УЛ ХЕРСОНСКАЯ, Д. 5, К. 2, ПОМЕЩ. 1Н",
                 "+7 (495) 345-67-89", "office@servicepro.ru"),
                ("ИП Иванова И.В.", "individual", "500300703103", "", "323774600494380",
                 "125373, г.Москва, Походный проезд, домовладение 3, стр.2",
                 "+7 (495) 456-78-90", "ivanov@mail.ru"),
                ("ООО 'МеталлТрейд'", "legal", "7708123456", "770801001", "1157746123456",
                 "109428, г.Москва, Рязанский проспект, д.8А, стр.1",
                 "+7 (495) 567-89-01", "metal@metalltrade.ru"),
                ("АО 'СтройМатериалы'", "legal", "7711223344", "771101001", "1167745678901",
                 "127015, г.Москва, ул.Бутырская, д.86, офис 305",
                 "+7 (495) 678-90-12", "info@stroymat.ru"),
                ("ООО 'ТехноПрофи'", "legal", "7733445566", "773301001", "1177756789012",
                 "115201, г.Москва, Каширское шоссе, д.31, корп.1А",
                 "+7 (495) 789-01-23", "order@technoprofi.ru"),
                ("ЗАО 'Пищепром'", "legal", "7744556677", "774401001", "1187767890123",
                 "115114, г.Москва, ул.Летниковская, д.10, стр.4",
                 "+7 (495) 890-12-34", "sales@foodprom.ru"),
                ("ООО 'ЛогистикГрупп'", "legal", "7755667788", "775501001", "1197778901234",
                 "125040, г.Москва, ул.Правды, д.15, офис 210",
                 "+7 (495) 901-23-45", "logist@logisticgroup.ru"),
                ("ИП Петров С.М.", "individual", "500400803204", "", "320774600567891",
                 "119361, г.Москва, ул.Озерная, д.42, кв.15",
                 "+7 (495) 012-34-56", "petrov@mail.ru"),
                ("ООО 'ЭкоПродукт'", "legal", "7766778899", "776601001", "1207789012345",
                 "121096, г.Москва, ул.Барклая, д.8, стр.3",
                 "+7 (495) 123-45-67", "eco@ecoproduct.ru"),
                ("АО 'ТрансАвто'", "legal", "7777889900", "777701001", "1217790123456",
                 "109316, г.Москва, Волгоградский проспект, д.47",
                 "+7 (495) 234-56-78", "trans@transauto.ru"),
                ("ООО 'ИТСервис'", "legal", "7788990011", "778801001", "1227801234567",
                 "123557, г.Москва, ул.Краснопресненская, д.12",
                 "+7 (495) 345-67-89", "support@itservice.ru"),
                ("ИП Сидорова А.К.", "individual", "500500903305", "", "321774600678902",
                 "127273, г.Москва, ул.Яблочкова, д.21, кв.8",
                 "+7 (495) 456-78-90", "sidorova@mail.ru"),
                ("ООО 'МедТехника'", "legal", "7799001122", "779901001", "1237812345678",
                 "117218, г.Москва, ул.Кржижановского, д.15, корп.2",
                 "+7 (495) 567-89-01", "med@medtech.ru"),
                ("ЗАО 'СтройИнвест'", "legal", "7800112233", "780001001", "1247823456789",
                 "125190, г.Москва, ул.Космонавта Волкова, д.10",
                 "+7 (495) 678-90-12", "invest@stroinvest.ru"),
                ("ООО 'АгроПродукт'", "legal", "7811223344", "781101001", "1257834567890",
                 "115533, г.Москва, проспект Андропова, д.18",
                 "+7 (495) 789-01-23", "agro@agroproduct.ru"),
                ("ИП Козлов В.П.", "individual", "500600100406", "", "322774600789013",
                 "119634, г.Москва, ул.Авиаторов, д.7, кв.23",
                 "+7 (495) 890-12-34", "kozlov@mail.ru"),
                ("ООО 'Безопасность+'", "legal", "7822334455", "782201001", "1267845678901",
                 "127006, г.Москва, ул.Долгоруковская, д.6",
                 "+7 (495) 901-23-45", "security@securityplus.ru"),
                ("АО 'ФинансКонсалт'", "legal", "7833445566", "783301001", "1277856789012",
                 "125009, г.Москва, ул.Тверская, д.22А",
                 "+7 (495) 012-34-56", "finance@finconsult.ru")
            ]

            # ИСПРАВЛЕННЫЙ ЗАПРОС - добавлен organization_type
            cur.executemany(
                "INSERT INTO organizations (name, organization_type, inn, kpp, ogrn, legal_address, phone, email) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                test_organizations
            )

        # Роли
        if cur.execute("SELECT COUNT(*) FROM roles").fetchone()[0] == 0:
            roles = [
                ("Генеральный директор", "Руководитель организации"),
                ("Финансовый директор", "Руководитель финансового отдела"),
                ("Юрист", "Юридическая экспертиза"),
                ("Начальник отдела закупок", "Руководитель отдела закупок"),
                ("Начальник отдела продаж", "Руководитель отдела продаж"),
                ("Коммерческий директор", "Руководитель коммерческой деятельности"),
                ("Администратор", "Администратор системы"),
                ("Служба безопасности", "Проверка контрагентов"),
                ("Отдел логистики", "Логистическая экспертиза")
            ]
            cur.executemany("INSERT INTO roles (name, description) VALUES (?, ?)", roles)

        # Пользователи
        if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            users_data = [
                ("admin", "Администратор Системы", hash_password("admin"), "ИТ", "Администратор", 1),
                ("gen_dir", "Иванов Иван Иванович", hash_password("123"), "Руководство", "Генеральный директор", 1),
                ("finance", "Петров Петр Петрович", hash_password("123"), "Финансы", "Финансовый директор", 1),
                ("lawyer", "Сидорова Мария Ивановна", hash_password("123"), "Юридический", "Юрист", 1),
                ("sales", "Козлов Алексей Владимирович", hash_password("123"), "Продажи", "Начальник отдела продаж", 1),
                ("purchase", "Николаев Дмитрий Сергеевич", hash_password("123"), "Закупки", "Начальник отдела закупок",
                 1),
                ("commercial", "Федорова Ольга Петровна", hash_password("123"), "Коммерция", "Коммерческий директор",
                 1),
                ("security", "Алексеев Сергей Викторович", hash_password("123"), "Безопасность", "Начальник СБ", 1),
                ("logistics", "Орлов Михаил Петрович", hash_password("123"), "Логистика", "Начальник отдела логистики",
                 1)
            ]

            for user in users_data:
                cur.execute(
                    "INSERT INTO users (username, full_name, password, department, position, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                    user
                )
                user_id = cur.lastrowid

                # Назначение ролей
                username = user[0]
                role_map = {
                    "admin": "Администратор",
                    "gen_dir": "Генеральный директор",
                    "finance": "Финансовый директор",
                    "lawyer": "Юрист",
                    "sales": "Начальник отдела продаж",
                    "purchase": "Начальник отдела закупок",
                    "commercial": "Коммерческий директор",
                    "security": "Служба безопасности",
                    "logistics": "Отдел логистики"
                }

                if username in role_map:
                    role_name = role_map[username]
                    cur.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
                    role_result = cur.fetchone()
                    if role_result:
                        cur.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                                    (user_id, role_result[0]))

        # Маршруты согласования - обновлены согласно бизнес-процессу
        if cur.execute("SELECT COUNT(*) FROM approval_flows").fetchone()[0] == 0:
            flows = [
                ("Закупки", "Маршрут для договоров закупок", "Закупки",
                 '[{"step": 1, "role": "Юрист", "deadline_days": 2}, '
                 '{"step": 1, "role": "Финансовый директор", "deadline_days": 2}, '
                 '{"step": 1, "role": "Служба безопасности", "deadline_days": 2}, '
                 '{"step": 1, "role": "Отдел логистики", "deadline_days": 2}, '
                 '{"step": 2, "role": "Коммерческий директор", "deadline_days": 2}, '
                 '{"step": 3, "role": "Генеральный директор", "deadline_days": 3}]'),

                ("Продажи", "Маршрут для договоров продаж", "Продажи",
                 '[{"step": 1, "role": "Начальник отдела продаж", "deadline_days": 3}, '
                 '{"step": 2, "role": "Юрист", "deadline_days": 2}, '
                 '{"step": 2, "role": "Финансовый директор", "deadline_days": 2}, '
                 '{"step": 2, "role": "Служба безопасности", "deadline_days": 2}, '
                 '{"step": 2, "role": "Отдел логистики", "deadline_days": 2}, '
                 '{"step": 3, "role": "Коммерческий директор", "deadline_days": 2}, '
                 '{"step": 4, "role": "Генеральный директор", "deadline_days": 3}]'),

                ("Общий", "Общий маршрут согласования", "Общий",
                 '[{"step": 1, "role": "Юрист", "deadline_days": 2}, '
                 '{"step": 1, "role": "Финансовый директор", "deadline_days": 2}, '
                 '{"step": 1, "role": "Служба безопасности", "deadline_days": 2}, '
                 '{"step": 1, "role": "Отдел логистики", "deadline_days": 2}, '
                 '{"step": 2, "role": "Коммерческий директор", "deadline_days": 2}, '
                 '{"step": 3, "role": "Генеральный директор", "deadline_days": 3}]')
            ]

            cur.executemany(
                "INSERT INTO approval_flows (name, description, department, steps) VALUES (?, ?, ?, ?)",
                flows
            )

        # 50 тестовых договоров
        if cur.execute("SELECT COUNT(*) FROM contracts").fetchone()[0] == 0:
            # Создаем словарь для сопоставления названий организаций с их ID
            org_name_to_id = {}
            cur.execute("SELECT id, name FROM organizations")
            for org_id, org_name in cur.fetchall():
                org_name_to_id[org_name] = org_id

            # Получаем ID пользователей
            user_ids = {}
            cur.execute("SELECT id, username FROM users")
            for user_id, username in cur.fetchall():
                user_ids[username] = user_id

            test_contracts = [
                # Договоры закупок (20 шт.)
                ("Д-2025-001", "Поставка сырья для производства", org_name_to_id.get("ООО 'Поставщик+'"), 1500000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-002", "Закупка оборудования для цеха", org_name_to_id.get("ООО 'МеталлТрейд'"), 2500000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "urgent", None),
                ("Д-2025-003", "Поставка упаковочных материалов", org_name_to_id.get("ООО 'СервисПро'"), 500000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-004", "Закупка спецодежды для сотрудников", org_name_to_id.get("ИП Иванова И.В."), 250000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-005", "Поставка электронных компонентов", org_name_to_id.get("ООО 'ТехноПрофи'"), 1800000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "urgent", None),
                ("Д-2025-006", "Закупка продуктов питания", org_name_to_id.get("ЗАО 'Пищепром'"), 1200000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-007", "Поставка логистических услуг", org_name_to_id.get("ООО 'ЛогистикГрупп'"), 800000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-008", "Закупка экологичной продукции", org_name_to_id.get("ООО 'ЭкоПродукт'"), 950000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "custom", None),
                ("Д-2025-009", "Поставка автотранспорта", org_name_to_id.get("АО 'ТрансАвто'"), 3500000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "urgent", None),
                ("Д-2025-010", "Закупка IT оборудования", org_name_to_id.get("ООО 'ИТСервис'"), 1200000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-011", "Поставка медицинского оборудования", org_name_to_id.get("ООО 'МедТехника'"), 2800000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "urgent", None),
                ("Д-2025-012", "Закупка строительных материалов", org_name_to_id.get("ЗАО 'СтройИнвест'"), 3200000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-013", "Поставка сельхозпродукции", org_name_to_id.get("ООО 'АгроПродукт'"), 750000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-014", "Закупка систем безопасности", org_name_to_id.get("ООО 'Безопасность+'"), 1600000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "custom", None),
                ("Д-2025-015", "Поставка финансовых услуг", org_name_to_id.get("АО 'ФинансКонсалт'"), 600000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-016", "Закупка канцелярских товаров", org_name_to_id.get("ИП Петров С.М."), 180000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-017", "Поставка химических реактивов", org_name_to_id.get("ООО 'Поставщик+'"), 890000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "urgent", None),
                ("Д-2025-018", "Закупка мебели для офиса", org_name_to_id.get("АО 'СтройМатериалы'"), 1450000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),
                ("Д-2025-019", "Поставка промышленного оборудования", org_name_to_id.get("ООО 'ТехноПрофи'"), 4200000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "urgent", None),
                ("Д-2025-020", "Закупка программного обеспечения", org_name_to_id.get("ООО 'ИТСервис'"), 950000.0,
                 user_ids.get("purchase"), "Закупки", "Черновик", "standard", None),

                # Договоры продаж (20 шт.)
                ("Д-2025-021", "Реализация готовой продукции", org_name_to_id.get("ТК 'Ашан'"), 2500000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-022", "Продажа полуфабрикатов оптом", org_name_to_id.get("ООО 'Поставщик+'"), 1800000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "urgent", None),
                ("Д-2025-023", "Экспорт продукции в ЕС", org_name_to_id.get("ЗАО 'Пищепром'"), 4800000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "custom", None),
                ("Д-2025-024", "Реализация замороженных продуктов", org_name_to_id.get("ИП Козлов В.П."), 920000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-025", "Продажа кондитерских изделий", org_name_to_id.get("ТК 'Ашан'"), 1650000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "urgent", None),
                ("Д-2025-026", "Реализация мясной продукции", org_name_to_id.get("ООО 'ЭкоПродукт'"), 2100000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-027", "Продажа молочной продукции", org_name_to_id.get("ИП Сидорова А.К."), 1350000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-028", "Реализация хлебобулочных изделий", org_name_to_id.get("ООО 'АгроПродукт'"), 980000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "custom", None),
                ("Д-2025-029", "Продажа напитков и соков", org_name_to_id.get("ТК 'Ашан'"), 1250000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-030", "Реализация детского питания", org_name_to_id.get("ООО 'Поставщик+'"), 1850000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "urgent", None),
                ("Д-2025-031", "Продажа диетических продуктов", org_name_to_id.get("ООО 'ЭкоПродукт'"), 760000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-032", "Реализация бакалейных товаров", org_name_to_id.get("ИП Петров С.М."), 540000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-033", "Продажа замороженных полуфабрикатов", org_name_to_id.get("ЗАО 'Пищепром'"), 1980000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "urgent", None),
                ("Д-2025-034", "Реализация консервированной продукции", org_name_to_id.get("ТК 'Ашан'"), 1120000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-035", "Продажа специй и приправ", org_name_to_id.get("ИП Иванова И.В."), 320000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "custom", None),
                ("Д-2025-036", "Реализация кофе и чая", org_name_to_id.get("ООО 'АгроПродукт'"), 870000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-037", "Продажа алкогольной продукции", org_name_to_id.get("ТК 'Ашан'"), 2450000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "urgent", None),
                ("Д-2025-038", "Реализация табачных изделий", org_name_to_id.get("ООО 'Поставщик+'"), 1890000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-039", "Продажа кормов для животных", org_name_to_id.get("ООО 'ЭкоПродукт'"), 680000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "standard", None),
                ("Д-2025-040", "Реализация бытовой химии", org_name_to_id.get("ИП Козлов В.П."), 450000.0,
                 user_ids.get("sales"), "Продажи", "Черновик", "custom", None),

                # Общие договоры (10 шт.)
                ("Д-2025-041", "Обслуживание оборудования", org_name_to_id.get("ООО 'СервисПро'"), 500000.0,
                 user_ids.get("commercial"), "Общий", "Черновик", "custom", None),
                ("Д-2025-042", "Аренда складских помещений", org_name_to_id.get("ЗАО 'СтройИнвест'"), 1200000.0,
                 user_ids.get("commercial"), "Общий", "Черновик", "standard", None),
                ("Д-2025-043", "Услуги охраны объекта", org_name_to_id.get("ООО 'Безопасность+'"), 680000.0,
                 user_ids.get("commercial"), "Общий", "Черновик", "standard", None),
                ("Д-2025-044", "IT аутсорсинг", org_name_to_id.get("ООО 'ИТСервис'"), 950000.0,
                 user_ids.get("commercial"), "Общий", "Черновик", "urgent", None),
                ("Д-2025-045", "Юридическое сопровождение", org_name_to_id.get("АО 'ФинансКонсалт'"), 420000.0,
                 user_ids.get("commercial"), "Общий", "Черновик", "standard", None),
                ("Д-2025-046", "Транспортные услуги", org_name_to_id.get("АО 'ТрансАвто'"), 780000.0,
                 user_ids.get("commercial"), "Общий", "Черновик", "custom", None),
                ("Д-2025-047", "Маркетинговые услуги", org_name_to_id.get("ООО 'ТехноПрофи'"), 560000.0,
                 user_ids.get("commercial"), "Общий", "Черновик", "standard", None),
                ("Д-2025-048", "Консалтинговые услуги", org_name_to_id.get("АО 'ФинансКонсалт'"), 320000.0,
                 user_ids.get("commercial"), "Общий", "Черновик", "urgent", None),
                ("Д-2025-049", "Ремонт офисных помещений", org_name_to_id.get("АО 'СтройМатериалы'"), 890000.0,
                 user_ids.get("commercial"), "Общий", "Черновик", "standard", None),
                ("Д-2025-050", "Уборка производственных помещений", org_name_to_id.get("ИП Сидорова А.К."), 280000.0,
                 user_ids.get("commercial"), "Общий", "Черновик", "custom", None)
            ]

            # Фильтруем договоры, для которых нашли организации
            valid_contracts = [contract for contract in test_contracts if contract[2] is not None]

            if valid_contracts:
                cur.executemany(
                    "INSERT INTO contracts (contract_number, title, counterparty, amount, owner_id, department, status, priority, deadline_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    valid_contracts
                )
                log_message(f"Создано {len(valid_contracts)} тестовых договоров")
            else:
                log_message("Не удалось создать тестовые договоры - организации не найдены")

        conn.commit()
        log_message("База данных успешно инициализирована с тестовыми данными")

    except sqlite3.Error as e:
        conn.rollback()
        log_message(f"Ошибка при инициализации БД: {e}")
        raise
    finally:
        conn.close()


# ======================= АВТОРИЗАЦИЯ =======================
def get_active_users_with_roles():
    """Получить список активных пользователей с ролями"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('''
            SELECT u.id, u.full_name, u.username, u.is_active, u.department,
                   GROUP_CONCAT(r.name, ', ') as roles
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.is_active = 1
            GROUP BY u.id
            ORDER BY u.full_name
        ''')
        users = cur.fetchall()
        conn.close()
        return users
    except sqlite3.Error as e:
        log_message(f"Ошибка получения пользователей: {e}")
        return []


def get_user_roles(user_id):
    """Получить роли пользователя"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT r.name FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = ?",
                    (user_id,))
        roles = [row[0] for row in cur.fetchall()]
        conn.close()
        return roles
    except sqlite3.Error as e:
        log_message(f"Ошибка получения ролей: {e}")
        return []


# ======================= ФУНКЦИИ ДЛЯ РАБОТЫ С ОРГАНИЗАЦИЯМИ =======================
def get_all_organizations():
    """Получить все организации для выпадающего списка"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('''
            SELECT id, name, inn FROM organizations 
            ORDER BY name
        ''')
        organizations = cur.fetchall()
        conn.close()
        return organizations
    except sqlite3.Error as e:
        log_message(f"Ошибка получения организаций: {e}")
        return []


# ======================= ДИАЛОГ УПРАВЛЕНИЯ ОРГАНИЗАЦИЯМИ =======================
class OrganizationManagementDialog(TextShortcutsMixin):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.win = tk.Toplevel(parent)
        self.win.title("Управление организациями")
        self.win.geometry("1000x600")
        self.win.transient(parent)
        self.win.grab_set()

        self.organizations_tree = None

        self.create_widgets()
        self.load_organizations()
        center_window(self.win)

    def create_widgets(self):
        main_frame = ttk.Frame(self.win, padding=15)
        main_frame.pack(fill="both", expand=True)

        # Панель инструментов
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(toolbar, text="➕ Добавить организацию", command=lambda: self.add_organization()).pack(side="left", padx=2)
        ttk.Button(toolbar, text="✏️ Редактировать", command=lambda: self.add_organization()).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🗑️ Удалить", command=lambda: self.add_organization()).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🔄 Обновить", command=lambda: self.add_organization()).pack(side="left", padx=2)

        # Таблица организаций
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True)

        # ИСПРАВЛЕНО: Правильный порядок колонок
        columns = ("id", "name", "type", "inn", "kpp", "ogrn", "legal_address", "phone", "email")
        self.organizations_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)

        # ИСПРАВЛЕНО: Правильные заголовки с email
        headers = ["ID", "Название", "Тип", "ИНН", "КПП", "ОГРН", "Юридический адрес", "Телефон", "Email"]
        widths = [50, 200, 80, 100, 100, 120, 250, 120, 150]

        for col, header, width in zip(columns, headers, widths):
            self.organizations_tree.heading(col, text=header)
            self.organizations_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.organizations_tree.yview)
        self.organizations_tree.configure(yscrollcommand=scrollbar.set)

        self.organizations_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Привязываем подсказки для длинных текстов
        self.attach_tooltips_to_tree(self.organizations_tree, delay=450)

    def attach_tooltips_to_tree(self, tree: ttk.Treeview, delay: int = 450):
        """Attach hover tooltips to a Treeview."""
        tooltip = HoverTooltip(self.win, wraplength=700, delay=delay)
        last = {"row": None, "col": None}
        try:
            tree_font = tkfont.nametofont(tree.cget("font"))
        except tk.TclError:
            tree_font = tkfont.Font(family="TkDefaultFont", size=10)

        def motion(event):
            try:
                x, y = event.x, event.y
                region = tree.identify_region(x, y)
                if region != "cell":
                    last["row"], last["col"] = None, None
                    tooltip.cancel()
                    return
                rowid = tree.identify_row(y)
                col = tree.identify_column(x)
                if not rowid or not col:
                    last["row"], last["col"] = None, None
                    tooltip.cancel()
                    return
                if rowid == last["row"] and col == last["col"]:
                    return
                last["row"], last["col"] = rowid, col
                col_index = int(col.replace("#", "")) - 1
                values = tree.item(rowid, "values") or ()
                cell_text = ""
                if 0 <= col_index < len(values):
                    cell_text = str(values[col_index] or "")
                if not cell_text:
                    tooltip.cancel()
                    return
                col_id = tree["columns"][col_index] if col_index < len(tree["columns"]) else None
                try:
                    col_width = tree.column(col_id, option="width") if col_id else None
                except tk.TclError:
                    col_width = None
                try:
                    text_px = tree_font.measure(cell_text)
                except tk.TclError:
                    text_px = len(cell_text) * 7
                if col_width and text_px <= col_width + 8:
                    tooltip.cancel()
                    return
                abs_x = tree.winfo_rootx() + event.x
                abs_y = tree.winfo_rooty() + event.y
                tooltip.schedule(cell_text, abs_x, abs_y)
            except tk.TclError:
                tooltip.cancel()

        def leave(_event=None):
            tooltip.cancel()

        def anyhide(_event=None):
            tooltip.cancel()

        tree.bind("<Motion>", motion, add="+")
        tree.bind("<Leave>", leave, add="+")
        tree.bind("<ButtonPress>", anyhide, add="+")
        tree.bind("<MouseWheel>", anyhide, add="+")
        tree.bind("<Button-4>", anyhide, add="+")
        tree.bind("<Button-5>", anyhide, add="+")

    def load_organizations(self):
        for item in self.organizations_tree.get_children():
            self.organizations_tree.delete(item)

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute('''
                SELECT id, name, organization_type, inn, kpp, ogrn, legal_address, phone, email
                FROM organizations 
                ORDER BY name
            ''')
            organizations = cur.fetchall()
            conn.close()

            for org in organizations:
                org_id, name, org_type, inn, kpp, ogrn, address, phone, email = org
                org_type_display = "Юрлицо" if org_type == "legal" else "ИП"

                # ИСПРАВЛЕНО: Правильный порядок вставки данных
                self.organizations_tree.insert("", "end", values=(
                    org_id,
                    name,
                    org_type_display,
                    inn or "",
                    kpp or "",
                    ogrn or "",
                    address or "",
                    phone or "",
                    email or ""  # Теперь email будет в правильном столбце
                ))

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить организации: {e}")

    def add_organization(self):
        self._show_organization_dialog()

    def edit_organization(self):
        selection = self.organizations_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите организацию для редактирования")
            return

        item = self.organizations_tree.item(selection[0])
        org_id = item['values'][0]

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT * FROM organizations WHERE id = ?", (org_id,))
            organization = cur.fetchone()
            conn.close()

            self._show_organization_dialog(organization)

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные организации: {e}")

    def delete_organization(self):
        selection = self.organizations_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите организацию для удаления")
            return

        item = self.organizations_tree.item(selection[0])
        org_id, name, inn = item['values'][0:3]

        # Проверяем, используется ли организация в договорах
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM contracts WHERE counterparty = ?", (org_id,))
            contract_count = cur.fetchone()[0]
            conn.close()

            if contract_count > 0:
                messagebox.showwarning("Внимание",
                                       f"Организация '{name}' используется в {contract_count} договоре(ах).\n" "Удаление невозможно.")
                return

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Ошибка проверки использования организации: {e}")
            return

        if messagebox.askyesno("Подтверждение",
                               f"Удалить организацию '{name}' (ИНН: {inn})?\n\n" "Внимание: Это действие нельзя отменить."):
            try:
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()
                cur.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
                conn.commit()
                conn.close()

                messagebox.showinfo("Успех", "Организация удалена")
                self.load_organizations()
                log_message(f"Удалена организация: {name} (ИНН: {inn})")

            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить организацию: {e}")

    def _show_organization_dialog(self, organization=None):
        dialog = tk.Toplevel(self.win)
        dialog.title("Редактирование организации" if organization else "Добавление организации")
        dialog.transient(self.win)
        dialog.grab_set()
        dialog.geometry("550x650")  # Увеличим высоту для новых полей

        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Переменная для типа организации
        org_type_var = tk.StringVar(value="legal")

        # Функция для обновления видимости полей
        def update_fields_visibility():
            current_org_type = org_type_var.get()  # переименовано из org_type
            if current_org_type == "legal":
                # Показываем КПП для Юр. Лиц
                kpp_label.grid()
                kpp_entry.grid()
                ogrn_label.config(text="ОГРН:*")
                inn_label.config(text="ИНН (10 или 12 цифр):*")
            else:
                # Скрываем КПП для ИП
                kpp_label.grid_remove()
                kpp_entry.grid_remove()
                ogrn_label.config(text="ОГРНИП (15 цифр):*")
                inn_label.config(text="ИНН (12 цифр):*")

        # Поля формы
        row = 0

        ttk.Label(main_frame, text="Тип организации:*").grid(row=row, column=0, sticky="w", pady=5)
        type_frame = ttk.Frame(main_frame)
        type_frame.grid(row=row, column=1, sticky="w", pady=5, padx=(10, 0))

        ttk.Radiobutton(type_frame, text="Юридическое лицо",
                        variable=org_type_var, value="legal",
                        command=update_fields_visibility).pack(side="left", padx=(0, 15))
        ttk.Radiobutton(type_frame, text="Индивидуальный предприниматель (ИП)",
                        variable=org_type_var, value="individual",
                        command=update_fields_visibility).pack(side="left")

        row += 1

        ttk.Label(main_frame, text="Название организации:*").grid(row=row, column=0, sticky="w", pady=5)
        name_entry = ttk.Entry(main_frame, width=40)
        name_entry.grid(row=row, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(name_entry)
        row += 1

        inn_label = ttk.Label(main_frame, text="ИНН (10 или 12 цифр):*")
        inn_label.grid(row=row, column=0, sticky="w", pady=5)
        inn_entry = ttk.Entry(main_frame, width=40)
        inn_entry.grid(row=row, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(inn_entry)
        row += 1

        kpp_label = ttk.Label(main_frame, text="КПП:")
        kpp_label.grid(row=row, column=0, sticky="w", pady=5)
        kpp_entry = ttk.Entry(main_frame, width=40)
        kpp_entry.grid(row=row, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(kpp_entry)
        row += 1

        ogrn_label = ttk.Label(main_frame, text="ОГРН:")
        ogrn_label.grid(row=row, column=0, sticky="w", pady=5)
        ogrn_entry = ttk.Entry(main_frame, width=40)
        ogrn_entry.grid(row=row, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(ogrn_entry)
        row += 1

        ttk.Label(main_frame, text="Юридический адрес:").grid(row=row, column=0, sticky="w", pady=5)
        address_entry = tk.Text(main_frame, width=30, height=3)
        address_entry.grid(row=row, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(address_entry)
        row += 1

        ttk.Label(main_frame, text="Телефон:").grid(row=row, column=0, sticky="w", pady=5)
        phone_entry = PhoneEntry(main_frame, width=40)
        phone_entry.grid(row=row, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(phone_entry)
        row += 1

        ttk.Label(main_frame, text="Email:").grid(row=row, column=0, sticky="w", pady=5)
        email_entry = ttk.Entry(main_frame, width=40)
        email_entry.grid(row=row, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(email_entry)
        row += 1

        # Заполняем данные если редактируем
        if organization:
            org_id, name, org_type, inn, kpp, ogrn, address, phone, email, created_at = organization
            name_entry.insert(0, name)
            inn_entry.insert(0, inn or "")
            kpp_entry.insert(0, kpp or "")
            ogrn_entry.insert(0, ogrn or "")
            address_entry.insert("1.0", address or "")

            if phone:
                phone_entry.set_phone(phone)

            email_entry.insert(0, email or "")

            # Определяем тип организации по длине ИНН/ОГРН
            if inn and len(inn) == 12:  # ИП имеют ИНН из 12 цифр
                org_type_var.set("individual")
            else:
                org_type_var.set("legal")

        # Инициализируем видимость полей
        update_fields_visibility()

        def save_organization():
            name_input = name_entry.get().strip()
            inn_input = inn_entry.get().strip()
            kpp_input = kpp_entry.get().strip()
            ogrn_input = ogrn_entry.get().strip()
            address_input = address_entry.get("1.0", "end-1c").strip()
            phone_input = phone_entry.get().strip()
            email_input = email_entry.get().strip()
            current_org_type = org_type_var.get()  # переименовано из org_type

            if not name_input or not inn_input:
                messagebox.showwarning("Внимание", "Заполните обязательные поля (Название и ИНН)")
                return

            # Проверка ИНН в зависимости от типа организации
            if not validate_inn(inn_input, current_org_type):
                if current_org_type == "legal":
                    messagebox.showwarning("Внимание",
                                           "Неверный формат ИНН для юридического лица. Должно быть 10 или 12 цифр.")
                else:
                    messagebox.showwarning("Внимание", "Неверный формат ИНН для ИП. Должно быть 12 цифр.")
                return

            # Проверка КПП (только для Юр. Лиц)
            if current_org_type == "legal" and kpp_input and not validate_kpp(kpp_input):
                messagebox.showwarning("Внимание", "КПП должен содержать 9 цифр")
                return

            # Проверка ОГРН/ОГРНИП
            if ogrn_input and not validate_ogrn(ogrn_input, current_org_type):
                if current_org_type == "legal":
                    messagebox.showwarning("Внимание", "Неверный формат ОГРН. Должно быть 13 цифр.")
                else:
                    messagebox.showwarning("Внимание", "Неверный формат ОГРНИП. Должно быть 15 цифр.")
                return

            # Проверка телефона
            if phone_input and not validate_phone(phone_input):
                messagebox.showwarning("Внимание", "Телефон должен быть в формате: +7 (xxx) xxx-xxxx")
                return

            # Проверка email
            if email_input and not validate_email(email_input):
                messagebox.showwarning("Внимание", "Неверный формат email адреса")
                return

            try:
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()

                if organization:
                    # Обновление существующей организации
                    cur.execute('''
                        UPDATE organizations 
                        SET name=?, organization_type=?, inn=?, kpp=?, ogrn=?, legal_address=?, phone=?, email=?
                        WHERE id=?
                    ''', (name_input, current_org_type, inn_input, kpp_input or None, ogrn_input or None,
                          address_input or None, phone_input or None, email_input or None,
                          organization[0]))
                    action_msg = "Организация обновлена"
                else:
                    # Создание новой организации
                    cur.execute('''
                        INSERT INTO organizations (name, organization_type, inn, kpp, ogrn, legal_address, phone, email)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (name_input, current_org_type, inn_input, kpp_input or None, ogrn_input or None,
                          address_input or None, phone_input or None, email_input or None))
                    action_msg = "Организация создана"

                conn.commit()
                conn.close()

                messagebox.showinfo("Успех", action_msg)
                self.load_organizations()
                dialog.destroy()
                log_message(
                    f"{action_msg}: {name_input} (ИНН: {inn_input}, Тип: {'Юрлицо' if current_org_type == 'legal' else 'ИП'})")

            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Организация с таким ИНН уже существует")
            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить организацию: {e}")

        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)

        save_text = "💾 Сохранить изменения" if organization else "💾 Создать организацию"
        ttk.Button(button_frame, text=save_text, command=save_organization).pack(side="left", padx=5)
        ttk.Button(button_frame, text="❌ Отмена", command=dialog.destroy).pack(side="left", padx=5)

        # Информация о форматах
        info_text = """* - обязательные поля

    Форматы данных:
    • Юрлицо: ИНН 10/12 цифр, КПП 9 цифр, ОГРН 13 цифр
    • ИП: ИНН 12 цифр, ОГРНИП 15 цифр
    • Телефон: +7 (xxx) xxx-xxxx
    • Email: example@domain.ru"""

        ttk.Label(main_frame, text=info_text, foreground="gray",
                  font=('Arial', 8), justify="left").grid(row=row + 1, column=0, columnspan=2, pady=(10, 0))

        center_window(dialog)


class LoginDialog(TextShortcutsMixin):
    def __init__(self, parent):
        super().__init__()
        self.result = None
        self.win = tk.Toplevel(parent)
        self.win.title("Вход в систему")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

        # Стилизация
        style = ttk.Style()
        style.configure('Login.TFrame', background='#f5f5f5')
        style.configure('Login.TLabel', background='#f5f5f5', font=('Arial', 10))
        style.configure('Login.TButton', font=('Arial', 10))

        main_frame = ttk.Frame(self.win, padding=30, style='Login.TFrame')
        main_frame.pack(fill="both", expand=True)

        # Заголовок
        ttk.Label(main_frame, text="СИСТЕМА УПРАВЛЕНИЯ ДОГОВОРАМИ",
                  font=("Arial", 14, "bold"), style='Login.TLabel').pack(pady=(0, 10))
        ttk.Label(main_frame, text="ООО «Фастлэнд»",
                  font=("Arial", 12), foreground="#555", style='Login.TLabel').pack(pady=(0, 30))

        # Поле выбора пользователя
        ttk.Label(main_frame, text="Пользователь:", style='Login.TLabel').pack(anchor="w", pady=(0, 5))
        self.user_var = tk.StringVar()
        self.user_combo = ttk.Combobox(main_frame, textvariable=self.user_var, state="readonly", font=('Arial', 10),
                                       width=35)
        self.user_combo.pack(pady=(0, 15))

        # Заполняем список пользователей
        users = get_active_users_with_roles()
        if users:
            self.user_combo['values'] = [f"{u[1]} ({u[2]}) - {u[4] or 'Общий'}" for u in users]
            self.user_combo.current(0)
        else:
            self.user_combo['values'] = ["Нет активных пользователей"]
            self.user_combo.current(0)

        # Поле пароля
        ttk.Label(main_frame, text="Пароль:", style='Login.TLabel').pack(anchor="w", pady=(0, 5))
        self.entry_pass = ttk.Entry(main_frame, width=38, show="●", font=('Arial', 10))
        self.entry_pass.pack(pady=(0, 20))
        self.entry_pass.focus()
        self.setup_text_shortcuts(self.entry_pass)

        # Сообщения об ошибках
        self.msg_label = ttk.Label(main_frame, text="", foreground="red", style='Login.TLabel')
        self.msg_label.pack(pady=(0, 10))

        # Кнопки
        btn_frame = ttk.Frame(main_frame, style='Login.TFrame')
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Войти", command=self.login,
                   style='Login.TButton', width=12).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Отмена", command=self.on_close,
                   style='Login.TButton', width=12).pack(side="left", padx=5)

        self.win.bind('<Return>', lambda e: self.login())

        # Центрируем окно после создания всех элементов
        center_window(self.win)

    def login(self):
        selected = self.user_var.get()
        password = self.entry_pass.get()

        if not selected or not password:
            self.msg_label.config(text="Выберите пользователя и введите пароль")
            return

        # Извлекаем логин из выбранного значения
        login = selected.split("(")[1].split(")")[0]

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute(
                "SELECT id, full_name, password, department FROM users WHERE username = ? AND is_active = 1",
                (login,)
            )
            user = cur.fetchone()
            conn.close()

            if user and hash_password(password) == user[2]:
                user_id, full_name, _, department = user
                roles = get_user_roles(user_id)

                self.result = (user_id, full_name, roles, department)
                log_message(f"Успешный вход пользователя: {full_name} ({login})")
                self.win.destroy()
            else:
                self.msg_label.config(text="Неверный пароль")
                log_message(f"Неудачная попытка входа: {login}")

        except sqlite3.Error as e:
            self.msg_label.config(text="Ошибка подключения к базе данных")
            log_message(f"Ошибка при входе: {e}")

    def on_close(self):
        self.result = None
        self.win.destroy()


# ======================= ОСНОВНОЕ ПРИЛОЖЕНИЕ =======================
def _get_contract_tag_with_deadline(status, deadline):
    """Определить тег для цветового кодирования договора с учетом дедлайна"""
    if not status:
        return ''

    # Нормализуем статус (приводим к нижнему регистру и убираем лишние пробелы)
    status_normalized = str(status).strip().lower()

    # Черновики - прозрачный цвет (без тега)
    if status_normalized == 'черновик':
        return ''

    # ОТКЛОНЕННЫЕ договоры - красный цвет (высший приоритет)
    if status_normalized in ['отклонён', 'отклонен', 'rejected']:
        return 'rejected'

    # Если договор на согласовании и есть дедлайн
    if status_normalized == 'на согласовании' and deadline:
        try:
            deadline_dt = datetime.strptime(deadline, '%Y-%m-%d %H:%M:%S')
            current_dt = datetime.now()

            if current_dt > deadline_dt:
                return 'overdue'  # Просрочен - красный
            elif (deadline_dt - current_dt).total_seconds() <= 86400:  # 24 часа
                return 'urgent'  # Срочный - оранжевый
            elif (deadline_dt - current_dt).total_seconds() <= 259200:  # 3 дня
                return 'warning'  # Предупреждение - желтый
            else:
                return 'pending'  # Стандартный цвет для согласования
        except ValueError:
            return 'pending'

    # Для договоров не на согласовании используем стандартные теги
    if status_normalized == 'согласован':
        return 'approved'

    return 'pending'


class CalendarDialog:
    """Диалог выбора даты и времени"""

    # noinspection PyTypeChecker
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        self.selected_date = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Выбор даты и времени")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        # self.dialog.geometry("400x500")

        # Временно размещаем окно за пределами экрана
        self.dialog.geometry("+10000+10000")

        # Инициализация переменных
        now = datetime.now()
        self.current_year = now.year
        self.current_month = now.month

        self.month_var = tk.IntVar(value=self.current_month)
        self.year_var = tk.IntVar(value=self.current_year)
        self.hour_var = tk.StringVar(value=now.strftime("%H"))
        self.minute_var = tk.StringVar(value=now.strftime("%M"))

        # Виджеты, создаваемые позже
        self.month_label = None
        self.days_container = None
        self.selected_label = None

        self.create_widgets()

        # Центрируем окно после создания всех виджетов
        self.dialog.after(100, self._center_dialog_direct)

    def _center_dialog_direct(self):
        """Центрирует диалоговое окно на экране"""
        self.dialog.update_idletasks()

        # Получаем реальные размеры окна после отрисовки
        width = self.dialog.winfo_reqwidth()
        height = self.dialog.winfo_reqheight()

        # Получаем размеры экрана
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()

        # Вычисляем позицию для центрирования
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        # Устанавливаем позицию
        self.dialog.geometry(f"+{x}+{y}")

    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Заголовок
        ttk.Label(main_frame, text="Выберите дату и время",
                  font=('Arial', 12, 'bold')).pack(pady=(0, 20))

        # Календарь
        calendar_frame = ttk.LabelFrame(main_frame, text="Календарь", padding=10)
        calendar_frame.pack(fill="x", pady=(0, 20))

        # Текущая дата
        now = datetime.now()
        self.current_year = now.year
        self.current_month = now.month

        # Управление месяцем/годом
        control_frame = ttk.Frame(calendar_frame)
        control_frame.pack(fill="x", pady=(0, 10))

        self.month_var = tk.IntVar(value=self.current_month)
        self.year_var = tk.IntVar(value=self.current_year)

        ttk.Button(control_frame, text="◀", width=3,
                   command=self.prev_month).pack(side="left")

        self.month_label = ttk.Label(control_frame, text="", font=('Arial', 10))
        self.month_label.pack(side="left", expand=True)

        ttk.Button(control_frame, text="▶", width=3,
                   command=self.next_month).pack(side="right")

        # Дни недели
        days_frame = ttk.Frame(calendar_frame)
        days_frame.pack(fill="x")

        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

        # Контейнер для дней
        self.days_container = ttk.Frame(calendar_frame)
        self.days_container.pack(fill="both", expand=True)

        # Настройка веса для строк (для равномерного распределения высоты)
        for i in range(7):  # 0-дни недели, 1-6 - строки с датами
            self.days_container.grid_rowconfigure(i, weight=1)
        for i in range(7):  # 7 колонок
            self.days_container.grid_columnconfigure(i, weight=1)

        # Выбор времени
        time_frame = ttk.LabelFrame(main_frame, text="Время", padding=10)
        time_frame.pack(fill="x", pady=(0, 20))

        ttk.Label(time_frame, text="Часы:").grid(row=0, column=0, sticky="w", pady=5)
        self.hour_var = tk.StringVar(value="18")
        hour_combo = ttk.Combobox(time_frame, textvariable=self.hour_var,
                                  width=5, state="readonly")
        hour_combo['values'] = [f"{i:02d}" for i in range(0, 24)]
        hour_combo.grid(row=0, column=1, sticky="w", pady=5, padx=(10, 20))

        ttk.Label(time_frame, text="Минуты:").grid(row=0, column=2, sticky="w", pady=5)
        self.minute_var = tk.StringVar(value="00")
        minute_combo = ttk.Combobox(time_frame, textvariable=self.minute_var,
                                    width=5, state="readonly")
        minute_combo['values'] = [f"{i:02d}" for i in range(0, 60, 5)]
        minute_combo.grid(row=0, column=3, sticky="w", pady=5, padx=(10, 0))

        # Выбранная дата
        selected_frame = ttk.LabelFrame(main_frame, text="Выбранная дата", padding=10)
        selected_frame.pack(fill="x", pady=(0, 20))

        self.selected_label = ttk.Label(selected_frame, text="Не выбрано",
                                        font=('Arial', 10, 'bold'))
        self.selected_label.pack()

        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="✅ Подтвердить",
                   command=self.confirm).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="❌ Отмена",
                   command=self.cancel).pack(side="left", padx=5)

        self.update_calendar()

    def prev_month(self):
        if self.month_var.get() == 1:
            self.month_var.set(12)
            self.year_var.set(self.year_var.get() - 1)
        else:
            self.month_var.set(self.month_var.get() - 1)
        self.update_calendar()

    def next_month(self):
        if self.month_var.get() == 12:
            self.month_var.set(1)
            self.year_var.set(self.year_var.get() + 1)
        else:
            self.month_var.set(self.month_var.get() + 1)
        self.update_calendar()

    def update_calendar(self):
        """Обновляет отображение календаря"""
        # Очищаем контейнер
        for widget in self.days_container.winfo_children():
            widget.destroy()

        month = self.month_var.get()
        year = self.year_var.get()

        # Обновляем заголовок
        month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        self.month_label.config(text=f"{month_names[month - 1]} {year}")

        # === ИСПРАВЛЕНИЕ: Убираем дублирование дней недели ===
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

        # Настройка одинаковой ширины для всех колонок
        for i in range(7):
            self.days_container.grid_columnconfigure(i, weight=1)

        # Размещаем дни недели только один раз в строке 0
        for i, day in enumerate(days):
            day_label = ttk.Label(self.days_container, text=day, font=('Arial', 9, 'bold'),
                                  anchor="center")
            day_label.grid(row=0, column=i, sticky="ew", padx=1, pady=2)

        # Первый день месяца
        first_day = datetime(year, month, 1)
        weekday = first_day.weekday()  # 0-понедельник, 6-воскресенье

        # Количество дней в месяце
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        days_in_month = (next_month - timedelta(days=1)).day

        # Создаем сетку дней (6 строк × 7 колонок), начиная со строки 1
        for row in range(1, 7):  # Начинаем с row=1, т.к. Row=0 занят днями недели
            for col in range(7):
                day_num = (row - 1) * 7 + col - weekday + 1
                if 1 <= day_num <= days_in_month:
                    btn = ttk.Button(self.days_container, text=str(day_num), command=lambda d=day_num: self.select_date(d))
                    btn.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

                    # Помечаем сегодняшний день
                    now = datetime.now()
                    if day_num == now.day and month == now.month and year == now.year:
                        btn.configure(style="Accent.TButton")
                else:
                    # Пустые ячейки для выравнивания
                    empty_label = ttk.Label(self.days_container, text="")
                    empty_label.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

    def select_date(self, day):
        self.selected_date = datetime(
            self.year_var.get(),
            self.month_var.get(),
            day
        )
        date_str = self.selected_date.strftime("%d.%m.%Y")
        self.selected_label.config(text=date_str)

    def confirm(self):
        if self.selected_date:
            time_str = f"{self.hour_var.get()}:{self.minute_var.get()}"
            self.result = f"{self.selected_date.strftime('%Y-%m-%d')} {time_str}:00"
            self.dialog.destroy()
        else:
            messagebox.showwarning("Внимание", "Выберите дату")

    def cancel(self):
        self.result = None
        self.dialog.destroy()


class FastlandApp(TextShortcutsMixin):
    def __init__(self, root, user_id, full_name, roles, department):
        super().__init__()
        self.root = root
        self.user_id = user_id
        self.full_name = full_name
        self.roles = roles
        self.department = department
        self.is_admin = "Администратор" in roles
        self.is_director = any(role in ["Генеральный директор", "Коммерческий директор"] for role in roles)
        self._exiting = False  # Добавляем флаг выхода

        # Инициализация атрибутов UI
        self.tab_contracts = None
        self.tab_tasks = None
        self.tab_admin = None
        self.tab_organizations = None  # Новая вкладка для организаций
        self.search_var = None
        self.search_entry = None
        self._search_placeholder = None
        self._search_has_placeholder = None
        self._contracts_tree_frame = None
        self.contracts_tree = None
        self.tasks_tree = None

        self.auto_assign_service = AutoAssignService()

        # --- для резиновой верстки таблицы договоров: веса колонок (сумма ≈ 1.0)
        self.contracts_col_weights = [0.06, 0.12, 0.34, 0.16, 0.10, 0.10, 0.06, 0.06]
        self._all_contracts = []  # кэш всех договоров (tuple rows) для фильтрации

        self.root.title(f"Система управления договорами — {full_name} ({department})")

        # Устанавливаем адаптивный размер
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1200, screen_width - 100)
        window_height = min(700, screen_height - 100)

        center_window_with_size(self.root, window_width, window_height)
        self.root.minsize(800, 500)

        # Устанавливаем обработчик закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.setup_styles()
        self.create_ui()
        self.load_contracts()
        self.load_tasks()

        # Запускаем периодическую проверку дедлайнов
        self.check_deadlines_periodically()

        log_message(f"Запущено приложение для пользователя: {full_name}")

    def check_deadlines_periodically(self):
        """Периодическая проверка дедлайнов каждые 5 минут"""
        # Проверяем, существует ли еще приложение
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.check_task_deadlines()
            self.update_contract_colors()  # ОБНОВЛЯЕМ ЦВЕТА ДОГОВОРОВ
            self.root.after(300000, self.check_deadlines_periodically)  # 5 минут

    def check_task_deadlines(self):
        """Проверка просроченных задач и отправка уведомлений"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()

            # Находим просроченные задачи
            cur.execute('''
                SELECT t.id, t.assigned_user_id, u.full_name, c.contract_number, 
                       t.role_name, t.deadline_at
                FROM approval_tasks t
                JOIN users u ON t.assigned_user_id = u.id
                JOIN approval_instances i ON t.instance_id = i.id
                JOIN contracts c ON i.contract_id = c.id
                WHERE t.status = 'pending' AND t.deadline_at < datetime('now') 
                AND t.deadline_notified = 0
            ''')  # Использовать SQL функцию вместо переменной

            overdue_tasks = cur.fetchall()

            for task in overdue_tasks:
                task_id, user_id, user_name, contract_number, role, deadline = task
                message = f"ПРОСРОЧЕНА задача по договору {contract_number}\nРоль: {role}\nДедлайн: {deadline[:16]}"

                # Помечаем задачу как уведомленную
                cur.execute('''
                    UPDATE approval_tasks SET deadline_notified = 1 WHERE id = ?
                ''', (task_id,))

                log_message(f"Уведомление о просрочке отправлено пользователю {user_name}: {message}")

            conn.commit()
            conn.close()

            # Перезагружаем задачи для обновления цветов
            self.load_tasks()

        except sqlite3.Error as e:
            log_message(f"Ошибка проверки дедлайнов: {e}")

    def update_task_colors(self):
        """Обновление цветов задач в зависимости от статуса дедлайна"""
        try:
            for item in self.tasks_tree.get_children():
                values = self.tasks_tree.item(item)['values']
                if len(values) >= 6:
                    task_id, contract_number, title, step, role, status = values[:6]

                    # Сбрасываем теги
                    self.tasks_tree.item(item, tags=())

                    # ПРИОРИТЕТ: сначала проверяем статус отклонения
                    if status == 'rejected' or status == 'Отклонён' or status == 'Отклонен':
                        self.tasks_tree.item(item, tags=('cancelled',))
                    elif status == 'cancelled':
                        self.tasks_tree.item(item, tags=('cancelled',))
                    elif status == 'pending':
                        # Логика для pending задач с дедлайнами
                        if len(values) >= 7:
                            deadline_str = values[6]
                            if deadline_str and deadline_str != "Не указан":
                                try:
                                    deadline_dt = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')
                                    current_dt = datetime.now()

                                    if current_dt > deadline_dt:
                                        self.tasks_tree.item(item, tags=('overdue',))
                                    elif (deadline_dt - current_dt).days <= 1:
                                        self.tasks_tree.item(item, tags=('urgent',))
                                except ValueError:
                                    pass

        except Exception as e:
            log_message(f"Ошибка обновления цветов задач: {e}")

    @staticmethod
    def setup_styles():
        style = ttk.Style()
        style.theme_use('clam')

        # Настройка стилей
        style.configure('Treeview', rowheight=25, font=('Arial', 9))
        style.configure('Treeview.Heading', font=('Arial', 10, 'bold'))
        style.configure('TButton', font=('Arial', 9))
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Accent.TButton', background='#e1f5fe')

    def create_ui(self):
        # Главный фрейм
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Верхняя панель с информацией о пользователе
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(top_frame, text=f"👤 {self.full_name} | Отдел: {self.department} | Роли: {', '.join(self.roles)}",
                  font=('Arial', 10)).pack(side="left")

        ttk.Button(top_frame, text="🚪 Выход", command=self.confirm_exit).pack(side="right")

        # Блокнот с вкладками
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)

        # Вкладка договоров
        self.tab_contracts = ttk.Frame(notebook)
        notebook.add(self.tab_contracts, text="📋 Договоры")

        # Вкладка задач
        self.tab_tasks = ttk.Frame(notebook)
        notebook.add(self.tab_tasks, text="📝 Задачи на согласование")

        # Вкладка организаций (только для админа и директоров)
        if self.is_admin or self.is_director:
            self.tab_organizations = ttk.Frame(notebook)
            notebook.add(self.tab_organizations, text="🏢 Организации")
            self.setup_organizations_tab()

        # Вкладка администрирования (только для админа)
        if self.is_admin:
            self.tab_admin = ttk.Frame(notebook)
            notebook.add(self.tab_admin, text="⚙️ Администрирование")
            self.setup_admin_tab()

        self.setup_contracts_tab()
        self.setup_tasks_tab()

    def setup_organizations_tab(self):
        """Настройка вкладки управления организациями"""
        content = ttk.Frame(self.tab_organizations, padding=20)
        content.pack(fill="both", expand=True)

        ttk.Label(content, text="Управление организациями", style='Title.TLabel').pack(pady=(0, 20))

        # Кнопки управления организациями
        org_buttons = [
            ("👥 Управление организациями", self.manage_organizations),
        ]

        for text, command in org_buttons:
            ttk.Button(content, text=text, command=command, width=25).pack(pady=5)

    def manage_organizations(self):
        """Открыть диалог управления организациями"""
        if not (self.is_admin or self.is_director):
            messagebox.showwarning("Доступ запрещен", "Эта функция доступна только администраторам и директорам")
            return

        OrganizationManagementDialog(self.root)

    def attach_tooltips_to_tree(self, tree: ttk.Treeview, delay: int = 450):
        """
        Attach hover tooltips to a Treeview. Shows full text when cell text overflows.
        """
        tooltip = HoverTooltip(self.root, wraplength=700, delay=delay)
        last = {"row": None, "col": None}
        try:
            tree_font = tkfont.nametofont(tree.cget("font"))
        except tk.TclError:
            tree_font = tkfont.Font(family="TkDefaultFont", size=10)

        def motion(event):
            try:
                x, y = event.x, event.y
                region = tree.identify_region(x, y)
                if region != "cell":
                    last["row"], last["col"] = None, None
                    tooltip.cancel()
                    return
                rowid = tree.identify_row(y)
                col = tree.identify_column(x)
                if not rowid or not col:
                    last["row"], last["col"] = None, None
                    tooltip.cancel()
                    return
                if rowid == last["row"] and col == last["col"]:
                    return
                last["row"], last["col"] = rowid, col
                col_index = int(col.replace("#", "")) - 1
                values = tree.item(rowid, "values") or ()
                cell_text = ""
                if 0 <= col_index < len(values):
                    cell_text = str(values[col_index] or "")
                if not cell_text:
                    tooltip.cancel()
                    return
                col_id = tree["columns"][col_index] if col_index < len(tree["columns"]) else None
                try:
                    col_width = tree.column(col_id, option="width") if col_id else None
                except tk.TclError:
                    col_width = None
                try:
                    text_px = tree_font.measure(cell_text)
                except tk.TclError:
                    text_px = len(cell_text) * 7
                if col_width and text_px <= col_width + 8:
                    tooltip.cancel()
                    return
                abs_x = tree.winfo_rootx() + event.x
                abs_y = tree.winfo_rooty() + event.y
                tooltip.schedule(cell_text, abs_x, abs_y)
            except tk.TclError:
                tooltip.cancel()

        def leave(_event=None):
            tooltip.cancel()

        def anyhide(_event=None):
            tooltip.cancel()

        tree.bind("<Motion>", motion, add="+")
        tree.bind("<Leave>", leave, add="+")
        tree.bind("<ButtonPress>", anyhide, add="+")
        tree.bind("<MouseWheel>", anyhide, add="+")
        tree.bind("<Button-4>", anyhide, add="+")
        tree.bind("<Button-5>", anyhide, add="+")

    # noinspection PyTypeChecker
    def setup_contracts_tab(self):
        # Панель инструментов
        toolbar = ttk.Frame(self.tab_contracts)
        toolbar.pack(fill="x", pady=(0, 10))

        # Левый набор кнопок
        buttons = [
            ("➕ Создать договор", self.create_contract),
            ("✏️ Редактировать", self.edit_contract),
            ("🗑️ Удалить", self.delete_contract),
            ("📂 Открыть файл", self.open_contract_file),
            ("✅ На согласование", self.send_for_approval),
            ("📊 Статус", self.show_approval_status),
            ("🔄 Обновить", self.load_contracts)
        ]

        # Добавляем кнопку изменения дедлайна только для директоров и администраторов
        if self.is_director or self.is_admin:
            buttons.insert(4, ("📅 Изменить дедлайн", self.change_contract_deadline))

        for text, command in buttons:
            ttk.Button(toolbar, text=text, command=command).pack(side="left", padx=2)

        # Правый блок для поиска (аккуратно справа от кнопок)
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side="right", padx=2)

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side="right")
        self.setup_text_shortcuts(self.search_entry)

        # placeholder implementation (серый текст подсказки)
        self._search_placeholder = "Поиск по №, названию, контрагенту, отделу..."
        self._search_has_placeholder = True

        def set_placeholder():
            if not self.search_var.get() and not self._search_has_placeholder:
                self.search_entry.delete(0, tk.END)
                self.search_entry.configure(foreground="#999999")
                self.search_entry.insert(0, self._search_placeholder)
                self._search_has_placeholder = True
                # При установке placeholder показываем ВСЕ договоры
                self.apply_contracts_filter("")

        def clear_placeholder(_event=None):
            if self._search_has_placeholder:
                self.search_entry.delete(0, tk.END)
                self.search_entry.configure(foreground="")
                self._search_has_placeholder = False

        def on_focus_out(_event=None):
            # При потере фокуса устанавливаем placeholder только если поле пустое
            if not self.search_var.get():
                set_placeholder()

        # Устанавливаем placeholder при старте
        self.search_entry.configure(foreground="#999999")
        self.search_entry.insert(0, self._search_placeholder)

        self.search_entry.bind("<FocusIn>", clear_placeholder)
        self.search_entry.bind("<FocusOut>", on_focus_out)

        # Реагируем на изменение текста поиска (trace)
        def on_search_var(*args):
            search_text = self.search_var.get()
            if self._search_has_placeholder:
                # Если есть placeholder, игнорируем изменения
                return
            self.apply_contracts_filter(search_text.strip())

        # trace variable
        self.search_var.trace_add("write", on_search_var)

        # Обработчик нажатия Enter в поле поиска
        def on_search_enter(_event=None):
            if self._search_has_placeholder:
                return
            search_text = self.search_var.get().strip()
            self.apply_contracts_filter(search_text)

        self.search_entry.bind("<Return>", on_search_enter)

        # Таблица договоров
        tree_frame = ttk.Frame(self.tab_contracts)
        tree_frame.pack(fill="both", expand=True)

        # сохраняем reference для изменения размера колонок
        self._contracts_tree_frame = tree_frame

        columns = ("id", "number", "title", "counterparty", "amount", "status", "department", "file_path", "priority",
                   "deadline")
        self.contracts_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)

        headers = ["ID", "Номер", "Наименование", "Контрагент", "Сумма", "Статус", "Отдел", "Файл", "Приоритет",
                   "Дедлайн"]
        # ширины будут устанавливаться пропорционально при изменении размера
        initial_widths = [50, 120, 250, 150, 100, 120, 100, 150, 100, 120]

        for col, header, width in zip(columns, headers, initial_widths):
            self.contracts_tree.heading(col, text=header)
            self.contracts_tree.column(col, width=width, minwidth=40)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.contracts_tree.yview)
        self.contracts_tree.configure(yscrollcommand=scrollbar.set)

        self.contracts_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        # Привязываем подсказки для длинных текстов в таблице
        self.attach_tooltips_to_tree(self.contracts_tree, delay=450)

        # Теги для цветового кодирования статусов
        self.contracts_tree.tag_configure('pending', background='#d1ecf1')
        self.contracts_tree.tag_configure('approved', background='#d4edda')
        self.contracts_tree.tag_configure('rejected', background='#f8d7da')  # Красный для отклоненных

        # Теги для цветового кодирования дедлайнов
        self.contracts_tree.tag_configure('overdue', background='#ffcccc')  # Красный для просроченных
        self.contracts_tree.tag_configure('urgent', background='#fff0cc')  # Оранжевый для срочных
        self.contracts_tree.tag_configure('warning', background='#ffffcc')  # Желтый для предупреждения

        # Двойной клик для открытия файла
        self.contracts_tree.bind('<Double-1>', self.on_contract_double_click)

        # Привязка события изменения размера фрейма таблицы - перерасчет ширин колонок
        def on_frame_configure(_event=None):
            self._adjust_contracts_columns()

        tree_frame.bind("<Configure>", on_frame_configure)

        # Привязка события изменения размера главного окна
        self.root.bind("<Configure>", lambda e: self._adjust_contracts_columns())

    def apply_contracts_filter(self, filter_text: str):
        """Применить фильтр к списку договоров (self._all_contracts)."""
        # Проверяем, существует ли дерево договоров
        if not hasattr(self, 'contracts_tree') or not self.contracts_tree.winfo_exists():
            return

        # Если placeholder виден и текст равен подсказке — считаем пустым
        if not filter_text:
            # показываем всё
            for item in self.contracts_tree.get_children():
                self.contracts_tree.delete(item)
            for contract in self._all_contracts:
                contract_id, number, title, counterparty, amount, status, dept, file_path, priority, deadline = contract
                formatted_amount = format_amount(amount)
                file_display = os.path.basename(file_path) if file_path else ""
                deadline_display = deadline[:16] if deadline else ""

                # Определяем тег для цвета с учетом дедлайна
                tag = _get_contract_tag_with_deadline(status, deadline)

                self.contracts_tree.insert("", "end", values=(
                    contract_id, number, title, counterparty or "",
                    formatted_amount, status, dept or "", file_display,
                    self._get_priority_display(priority), deadline_display
                ), tags=(tag,))
            return

        query = filter_text.lower()
        # удаляем текущие записи
        for item in self.contracts_tree.get_children():
            self.contracts_tree.delete(item)

        for contract in self._all_contracts:
            contract_id, number, title, counterparty, amount, status, dept, file_path, priority, deadline = contract
            # ищем соответствие по номеру, названию, контрагенту или отделу
            haystack = f"{number or ''} {title or ''} {counterparty or ''} {dept or ''}".lower()
            if query in haystack:
                formatted_amount = format_amount(amount)
                file_display = os.path.basename(file_path) if file_path else ""
                deadline_display = deadline[:16] if deadline else ""

                # Определяем тег для цвета с учетом дедлайна
                tag = _get_contract_tag_with_deadline(status, deadline)

                self.contracts_tree.insert("", "end", values=(
                    contract_id, number, title, counterparty or "",
                    formatted_amount, status, dept or "", file_display,
                    self._get_priority_display(priority), deadline_display
                ), tags=(tag,))

        # После применения фильтра обновляем цвета
        self.update_contract_colors()

    @staticmethod
    def _get_priority_display(priority):
        """Получить отображаемое название приоритета"""
        priority_map = {
            'standard': 'Стандартный',
            'urgent': 'Срочный',
            'custom': 'Ручной'
        }
        return priority_map.get(priority, priority)

    @staticmethod
    def _get_contract_tag(status):
        """Определить тег для цветового кодирования договора"""
        if status == 'Согласован':
            return 'approved'
        elif status == 'Отклонен':
            return 'rejected'
        elif status == 'На согласовании':
            return 'pending'
        return ''

    def update_contract_colors(self):
        """Обновление цветов договоров в зависимости от статуса дедлайна"""
        # Проверяем, существует ли дерево договоров
        if not hasattr(self, 'contracts_tree') or not self.contracts_tree.winfo_exists():
            return

        try:
            current_time = datetime.now()

            for item in self.contracts_tree.get_children():
                values = self.contracts_tree.item(item)['values']
                if len(values) >= 10:  # Проверяем, что есть все значения
                    contract_id, number, title, counterparty, amount, status, dept, file_display, priority, deadline_str = values

                    # Нормализуем статус
                    status_normalized = str(status).strip().lower() if status else ''

                    # ОТКЛОНЕННЫЕ договоры - красный цвет (высший приоритет)
                    if status_normalized in ['отклонён', 'отклонен', 'rejected']:
                        self.contracts_tree.item(item, tags=('rejected',))
                        continue

                    # Черновики - прозрачный цвет (без тега)
                    if status_normalized == 'черновик':
                        self.contracts_tree.item(item, tags=())
                        continue

                    # Если договор на согласовании и есть дедлайн
                    if status_normalized == 'на согласовании' and deadline_str and deadline_str.strip():
                        try:
                            # Преобразуем строку дедлайна в datetime
                            try:
                                deadline_dt = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                deadline_dt = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M')

                            if current_time > deadline_dt:
                                # Просроченный договор - красный цвет
                                self.contracts_tree.item(item, tags=('overdue',))
                            elif (deadline_dt - current_time).total_seconds() <= 86400:  # 24 часа
                                # Скоро дедлайн - оранжевый цвет
                                self.contracts_tree.item(item, tags=('urgent',))
                            elif (deadline_dt - current_time).total_seconds() <= 259200:  # 3 дня
                                # Приближается дедлайн - желтый цвет
                                self.contracts_tree.item(item, tags=('warning',))
                            else:
                                # Все в порядке - стандартный цвет для статуса "На согласовании"
                                self.contracts_tree.item(item, tags=('pending',))
                        except ValueError as e:
                            # Если ошибка получения даты
                            log_message(f"Ошибка получения даты для договора {number}: {e}")
                            self.contracts_tree.item(item, tags=('pending',))
                    else:
                        # Для договоров не на согласовании используем стандартные теги
                        if status_normalized == 'согласован':
                            self.contracts_tree.item(item, tags=('approved',))
                        else:
                            self.contracts_tree.item(item, tags=('pending',))

        except Exception as e:
            log_message(f"Ошибка обновления цветов договоров: {e}")

    def _adjust_contracts_columns(self):
        """Перерасчёт ширин колонок таблицы договоров на основе размеров контейнера и весов."""
        try:
            frame = getattr(self, "_contracts_tree_frame", None)
            if not frame or not frame.winfo_ismapped():
                return
            total_width = frame.winfo_width()
            if total_width <= 0:
                # попробуем взять ширину окна
                total_width = self.root.winfo_width() - 40
            # учтем небольшие отступы для прокрутки
            total_width = max(total_width - 20, 200)
            weights = getattr(self, "contracts_col_weights", None)
            if not weights or len(weights) != len(self.contracts_tree["columns"]):
                # fallback: равномерно
                n = len(self.contracts_tree["columns"])
                weights = [1.0 / n] * n

            for col, w in zip(self.contracts_tree["columns"], weights):
                new_w = max(int(total_width * w), 50)
                try:
                    self.contracts_tree.column(col, width=new_w)
                except tk.TclError:
                    pass
        except (AttributeError, tk.TclError):
            pass

    def setup_tasks_tab(self):
        # Панель инструментов
        toolbar = ttk.Frame(self.tab_tasks)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(toolbar, text="✅ Утвердить", command=self.approve_task).pack(side="left", padx=2)
        ttk.Button(toolbar, text="❌ Отклонить", command=self.reject_task).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📂 Открыть договор", command=self.open_task_contract_file).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🔄 Обновить", command=self.load_contracts).pack(side="left", padx=2)

        # Таблица задач
        tree_frame = ttk.Frame(self.tab_tasks)
        tree_frame.pack(fill="both", expand=True)

        columns = ("id", "contract_number", "title", "step", "role", "status", "deadline")
        self.tasks_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)

        headers = ["ID", "Договор", "Наименование", "Этап", "Роль", "Статус", "Дедлайн"]
        widths = [50, 100, 250, 80, 120, 100, 120]

        for col, header, width in zip(columns, headers, widths):
            self.tasks_tree.heading(col, text=header)
            self.tasks_tree.column(col, width=width)

        # Настройка цветов для задач
        self.tasks_tree.tag_configure('overdue', background='#ffcccc')  # Красный для просроченных
        self.tasks_tree.tag_configure('urgent', background='#fff0cc')  # Оранжевый для срочных
        self.tasks_tree.tag_configure('cancelled', background='#f8d7da')  # Красный для отмененных/отклоненных

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=scrollbar.set)

        self.tasks_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ДОБАВЛЯЕМ ОБРАБОТЧИК ДВОЙНОГО КЛИКА ДЛЯ ОТКРЫТИЯ ФАЙЛА
        self.tasks_tree.bind('<Double-1>', self.on_task_double_click)

    def open_task_contract_file(self):
        """Открыть файл договора для выбранной задачи"""
        selection = self.tasks_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите задачу для открытия договора")
            return

        item = self.tasks_tree.item(selection[0])
        task_id = item['values'][0]  # ID задачи

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()

            # Получаем contract_id через instance_id и затем файл договора
            cur.execute('''
                SELECT c.file_path 
                FROM contracts c
                JOIN approval_instances i ON c.id = i.contract_id
                JOIN approval_tasks t ON i.id = t.instance_id
                WHERE t.id = ?
            ''', (task_id,))

            result = cur.fetchone()
            conn.close()

            if result and result[0]:
                file_path = result[0]
                if open_file(file_path):
                    log_message(f"Открыт файл договора для задачи {task_id}: {file_path}")
            else:
                messagebox.showinfo("Информация", "Для договора в выбранной задаче файл не прикреплен")

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл договора: {e}")
            log_message(f"Ошибка открытия файла договора для задачи {task_id}: {e}")

    def on_task_double_click(self, event):
        """Обработчик двойного клика по задаче - открывает файл договора"""
        item = self.tasks_tree.identify('item', event.x, event.y)
        if item:
            self.tasks_tree.selection_set(item)
            self.open_task_contract_file()

    def setup_admin_tab(self):
        content = ttk.Frame(self.tab_admin, padding=20)
        content.pack(fill="both", expand=True)

        ttk.Label(content, text="Панель администратора", style='Title.TLabel').pack(pady=(0, 20))

        # Кнопки администратора
        admin_buttons = [
            ("👥 Управление пользователями", self.manage_users),
            ("🔄 Сбросить базу данных", self.reset_database),
            ("💾 Создать бэкап", self.create_backup),
            ("📊 Статистика системы", self.show_statistics)
        ]

        for text, command in admin_buttons:
            ttk.Button(content, text=text, command=command, width=25).pack(pady=5)

    def load_contracts(self):
        """Загружает все договора и кэширует их, сохраняя текущий фильтр поиска"""
        # Проверяем, существует ли еще дерево договоров
        if not hasattr(self, 'contracts_tree') or not self.contracts_tree.winfo_exists():
            return

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()

            # Директора видят все договоры
            if self.is_admin or self.is_director:
                cur.execute('''
                    SELECT c.id, c.contract_number, c.title, 
                           o.name as counterparty_name, 
                           c.amount, c.status, c.department, 
                           c.file_path, c.priority, c.deadline_at
                    FROM contracts c
                    LEFT JOIN organizations o ON c.counterparty = o.id
                    ORDER BY c.created_at DESC
                ''')
            else:
                cur.execute('''
                    SELECT c.id, c.contract_number, c.title, 
                           o.name as counterparty_name, 
                           c.amount, c.status, c.department, 
                           c.file_path, c.priority, c.deadline_at
                    FROM contracts c
                    LEFT JOIN organizations o ON c.counterparty = o.id
                    WHERE c.owner_id = ? OR c.department = ? OR c.status = 'На согласовании'
                    ORDER BY c.created_at DESC
                ''', (self.user_id, self.department))

            contracts = cur.fetchall()
            conn.close()

            # Сохраняем весь набор для последующей фильтрации
            self._all_contracts = contracts

            # Получаем текущий текст поиска
            search_text = ""
            if hasattr(self, 'search_var') and self.search_var and not self._search_has_placeholder:
                search_text = self.search_var.get().strip()

            # Применяем фильтр (если есть) к обновленным данным
            self.apply_contracts_filter(search_text)

            # После загрузки выставляем колонки и цвета корректно
            self._adjust_contracts_columns()
            self.update_contract_colors()

        except sqlite3.Error as e:
            # Проверяем, существует ли еще главное окно
            if hasattr(self, 'root') and self.root.winfo_exists():
                messagebox.showerror("Ошибка", f"Не удалось загрузить договоры: {e}")
            log_message(f"Ошибка загрузки договоров: {e}")

    def refresh_contracts_with_filter(self):
        """Обновить договоры с сохранением текущего фильтра"""
        self.load_contracts()  # Теперь load_contracts сам сохраняет фильтр

    def load_tasks(self):
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()

            if self.is_admin:
                cur.execute('''
                    SELECT t.id, c.contract_number, c.title, t.step_order, t.role_name, 
                           t.status, t.deadline_at, c.file_path
                    FROM approval_tasks t
                    JOIN approval_instances i ON t.instance_id = i.id
                    JOIN contracts c ON i.contract_id = c.id
                    LEFT JOIN organizations o ON c.counterparty = o.id
                    WHERE t.status = 'pending' AND c.status != 'Согласован'
                    ORDER BY t.deadline_at
                ''')
            else:
                cur.execute('''
                    SELECT t.id, c.contract_number, c.title, t.step_order, t.role_name, 
                           t.status, t.deadline_at, c.file_path  -- ДОБАВЛЯЕМ file_path
                    FROM approval_tasks t
                    JOIN approval_instances i ON t.instance_id = i.id
                    JOIN contracts c ON i.contract_id = c.id
                    WHERE t.assigned_user_id = ? AND t.status = 'pending' AND c.status != 'Согласован'
                    ORDER BY t.deadline_at
                ''', (self.user_id,))

            tasks = cur.fetchall()
            conn.close()

            for task in tasks:
                task_id, number, title_text, step_num, role, status, deadline, file_path = task
                deadline_str = deadline[:16] if deadline else "Не указан"

                # Вставляем в таблицу только необходимые для отображения данные
                self.tasks_tree.insert("", "end", values=(
                    task_id, number, title_text, step_num, role, status, deadline_str
                ))

            # Обновляем цвета после загрузки
            self.update_task_colors()

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить задачи: {e}")
            log_message(f"Ошибка загрузки задач: {e}")

    def create_contract(self):
        dialog = ContractDialog(self.root, self.user_id, self.department)
        self.root.wait_window(dialog.win)
        self.load_contracts()

    def edit_contract(self):
        selection = self.contracts_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите договор для редактирования")
            return

        item = self.contracts_tree.item(selection[0])
        contract_id = item['values'][0]

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,))
            contract = cur.fetchone()

            if contract:
                contract_status = contract[5]  # Статус договора

                # Если договор согласован, сбрасываем статус на Черновик
                if contract_status == 'Согласован':
                    if messagebox.askyesno("Подтверждение",
                                           "Договор уже согласован. Редактирование приведет к сбросу статуса в 'Черновик' и потребует нового согласования. Продолжить?"):
                        cur.execute('''
                            UPDATE contracts SET status = 'Черновик', updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (contract_id,))
                        conn.commit()
                        # Перезагружаем договор с обновленным статусом
                        cur.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,))
                        contract = cur.fetchone()
                        log_message(f"Договор {contract[1]} сброшен в статус 'Черновик' для редактирования")
                    else:
                        conn.close()
                        return

                conn.close()
                dialog = ContractDialog(self.root, self.user_id, self.department, contract)
                self.root.wait_window(dialog.win)
                self.load_contracts()

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные договора: {e}")

    def delete_contract(self):
        selection = self.contracts_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите договор для удаления")
            return

        item = self.contracts_tree.item(selection[0])
        contract_id, number, title_text = item['values'][0:3]

        if messagebox.askyesno("Подтверждение", f"Удалить договор '{number} - {title_text}'?"):
            try:
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()
                cur.execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
                conn.commit()
                conn.close()

                messagebox.showinfo("Успех", "Договор удален")
                self.load_contracts()
                log_message(f"Удален договор: {number}")

            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить договор: {e}")

    def open_contract_file(self):
        selection = self.contracts_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите договор для открытия файла")
            return

        item = self.contracts_tree.item(selection[0])
        contract_id = item['values'][0]

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT file_path FROM contracts WHERE id = ?", (contract_id,))
            result = cur.fetchone()
            conn.close()

            if result and result[0]:
                file_path = result[0]
                if open_file(file_path):
                    log_message(f"Открыт файл договора {contract_id}: {file_path}")
            else:
                messagebox.showinfo("Информация", "Для выбранного договора файл не прикреплен")

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
            log_message(f"Ошибка открытия файла договора {contract_id}: {e}")

    def on_contract_double_click(self, event):
        item = self.contracts_tree.identify('item', event.x, event.y)
        if item:
            self.contracts_tree.selection_set(item)
            self.open_contract_file()

    def change_contract_deadline(self):
        """Изменение дедлайна договора с календарем для выбора даты"""
        if not (self.is_director or self.is_admin):
            messagebox.showwarning("Доступ запрещен", "Изменение дедлайна доступно только директорам и администраторам")
            return

        selection = self.contracts_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите договор для изменения дедлайна")
            return

        item = self.contracts_tree.item(selection[0])
        contract_id, number, title_text = item['values'][0:3]

        dialog = tk.Toplevel(self.root)
        dialog.title("Изменение дедлайна договора")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("500x500")

        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text=f"Договор: {number}", font=('Arial', 10, 'bold')).pack(anchor="w")
        ttk.Label(main_frame, text=f"Наименование: {title_text}").pack(anchor="w", pady=(5, 0))

        ttk.Label(main_frame, text="Приоритет:").pack(anchor="w", pady=(15, 5))
        priority_var = tk.StringVar(value="standard")

        priority_frame = ttk.Frame(main_frame)
        priority_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(priority_frame, text="Стандартный (3 рабочих дня)", variable=priority_var, value="standard").pack(anchor="w")
        ttk.Radiobutton(priority_frame, text="Срочный (1 рабочий день)", variable=priority_var, value="urgent").pack(anchor="w")
        ttk.Radiobutton(priority_frame, text="Ручной ввод", variable=priority_var, value="custom").pack(anchor="w")

        # Фрейм для выбора даты и времени
        datetime_frame = ttk.LabelFrame(main_frame, text="Выбор даты и времени", padding=10)
        datetime_frame.pack(fill="x", pady=(15, 10))

        # Поля для отображения выбранной даты и времени
        ttk.Label(datetime_frame, text="Выбранная дата и время:").grid(row=0, column=0, sticky="w", pady=5)
        datetime_display = ttk.Entry(datetime_frame, width=20, state="readonly", font=('Arial', 10))
        datetime_display.grid(row=0, column=1, sticky="w", pady=5, padx=(10, 0))

        # Кнопка для открытия календаря
        def open_calendar():
            calendar = CalendarDialog(dialog)
            dialog.wait_window(calendar.dialog)
            if calendar.result:
                datetime_display.config(state="normal")
                datetime_display.delete(0, tk.END)
                datetime_display.insert(0, calendar.result)
                datetime_display.config(state="readonly")

        ttk.Button(datetime_frame, text="📅 Выбрать дату и время", command=open_calendar).grid(row=1, column=0, columnspan=2, pady=10)

        def update_datetime_state():
            """Обновляет состояние полей даты/времени в зависимости от выбранного приоритета"""
            if priority_var.get() == "custom":
                for widget in datetime_frame.winfo_children():
                    if isinstance(widget, ttk.Button):
                        widget.config(state="normal")
            else:
                for widget in datetime_frame.winfo_children():
                    if isinstance(widget, ttk.Button):
                        widget.config(state="disabled")
                # Автоматически устанавливаем дату для стандартных приоритетов
                if priority_var.get() == "standard":
                    days = 3
                else:  # urgent
                    days = 1

                auto_date = datetime.now() + timedelta(days=days)
                datetime_display.config(state="normal")
                datetime_display.delete(0, tk.END)
                datetime_display.insert(0, auto_date.strftime('%Y-%m-%d 18:00:00'))
                datetime_display.config(state="readonly")

        priority_var.trace_add("write", lambda name, index, mode: update_datetime_state())
        update_datetime_state()  # Инициализация состояния

        def save_deadline():
            priority = priority_var.get()
            datetime_str = datetime_display.get().strip()

            if priority == "custom" and not datetime_str:
                messagebox.showwarning("Внимание", "Для ручного ввода необходимо выбрать дату и время")
                return

            try:
                # Формируем полную дату-время
                if priority == "custom":
                    deadline_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                else:
                    days = 3 if priority == "standard" else 1
                    deadline_dt = datetime.now() + timedelta(days=days)
                    deadline_dt = deadline_dt.replace(hour=18, minute=0, second=0)

                deadline_str = deadline_dt.strftime('%Y-%m-%d %H:%M:%S')

                # Проверяем что дедлайн в будущем
                if deadline_dt <= datetime.now():
                    messagebox.showwarning("Внимание", "Дедлайн должен быть в будущем")
                    return

                # Сохраняем в базу данных
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()

                cur.execute('''
                    UPDATE contracts 
                    SET priority = ?, deadline_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (priority, deadline_str, contract_id))

                # Обновляем дедлайны всех активных задач для этого договора
                cur.execute('''
                    UPDATE approval_tasks 
                    SET deadline_at = ?, deadline_notified = 0
                    WHERE instance_id IN (
                        SELECT id FROM approval_instances 
                        WHERE contract_id = ? AND status = 'running'
                    ) AND status = 'pending'
                ''', (deadline_str, contract_id))

                conn.commit()
                conn.close()

                messagebox.showinfo("Успех", f"Дедлайн установлен на:\n{deadline_str[:16]}")
                dialog.destroy()
                self.load_contracts()
                self.load_tasks()
                log_message(f"Изменен дедлайн договора {number} на {deadline_str}")

            except ValueError as e:
                messagebox.showerror("Ошибка", f"Неверный формат даты: {e}")
            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Не удалось изменить дедлайн: {e}")

        # Кнопки сохранения/отмены
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=20)

        ttk.Button(btn_frame, text="💾 Сохранить дедлайн", command=save_deadline, style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="❌ Отмена", command=dialog.destroy).pack(side="left", padx=5)

        # Информация о формате
        info_text = """Формат даты: ГГГГ-ММ-ДД ЧЧ:ММ:СС

• Стандартный приоритет: +3 рабочих дня
• Срочный приоритет: +1 рабочий день
• Ручной ввод: выберите любую дату и время"""

        ttk.Label(main_frame, text=info_text, foreground="gray", font=('Arial', 8), justify="left").pack(pady=(10, 0))

        center_window(dialog)

    def send_for_approval(self):
        selection = self.contracts_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите договор для отправки на согласование")
            return

        item = self.contracts_tree.item(selection[0])
        values = item['values']
        contract_id = values[0]
        number = values[1]
        status = values[5]

        if status != 'Черновик':
            messagebox.showwarning("Внимание", "Только договоры в статусе 'Черновик' можно отправить на согласование")
            return

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()

            # УДАЛЯЕМ ПРЕДЫДУЩИЕ ДАННЫЕ СОГЛАСОВАНИЯ (если есть)
            cur.execute('''
                SELECT i.id FROM approval_instances i 
                WHERE i.contract_id = ? AND i.status != 'finished'
            ''', (contract_id,))
            existing_instance = cur.fetchone()

            if existing_instance:
                instance_id = existing_instance[0]
                # Удаляем задачи согласования
                cur.execute('DELETE FROM approval_tasks WHERE instance_id = ?', (instance_id,))
                # Удаляем экземпляр согласования
                cur.execute('DELETE FROM approval_instances WHERE id = ?', (instance_id,))
                log_message(f"Удален предыдущий экземпляр согласования для договора {number}")

            # Получаем отдел договора для определения маршрута
            cur.execute("SELECT department, priority, deadline_at FROM contracts WHERE id = ?", (contract_id,))
            result = cur.fetchone()
            department = result[0] if result else "Общий"
            priority = result[1] if result else "standard"
            contract_deadline = result[2] if result else None

            # Находим подходящий маршрут
            cur.execute("SELECT id, steps FROM approval_flows WHERE department = ?", (department,))
            flow = cur.fetchone()

            if not flow:
                cur.execute("SELECT id, steps FROM approval_flows WHERE department = 'Общий'")
                flow = cur.fetchone()

            if not flow:
                messagebox.showerror("Ошибка", "Не найден подходящий маршрут согласования")
                return

            flow_id, steps_json = flow
            steps = json.loads(steps_json)

            # Создаем НОВЫЙ экземпляр согласования
            cur.execute(
                "INSERT INTO approval_instances (contract_id, flow_id, status) VALUES (?, ?, 'running')",
                (contract_id, flow_id)
            )
            instance_id = cur.lastrowid

            # Создаем задачи согласования только для первого этапа
            first_step = min(step_data['step'] for step_data in steps)
            first_steps = [step_data for step_data in steps if step_data['step'] == first_step]

            # Рассчитываем дедлайн на основе приоритета
            if contract_deadline:
                deadline_str = contract_deadline
            else:
                if priority == "urgent":
                    deadline_days = 1
                elif priority == "custom":
                    deadline_days = 3  # По умолчанию для custom
                else:  # standard
                    deadline_days = 3

                deadline = (datetime.now() + timedelta(days=deadline_days)).strftime('%Y-%m-%d %H:%M:%S')
                deadline_str = deadline

            for step_data in first_steps:
                role_name = step_data['role']
                assigned_user_id = self.auto_assign_service.get_next_user_by_round_robin(role_name)

                cur.execute('''
                    INSERT INTO approval_tasks 
                    (instance_id, step_order, role_name, assigned_user_id, status, deadline_at)
                    VALUES (?, ?, ?, ?, 'pending', ?)
                ''', (instance_id, step_data['step'], role_name, assigned_user_id, deadline_str))

            # Обновляем статус договора
            cur.execute(
                "UPDATE contracts SET status = 'На согласовании', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (contract_id,)
            )

            # Записываем действия пользователя
            cur.execute(
                "INSERT INTO audit_log (user_id, action, details) VALUES (?, ?, ?)",
                (self.user_id, 'send_for_approval', f'Договор {number} отправлен на согласование')
            )

            conn.commit()
            conn.close()

            messagebox.showinfo("Успех", "Договор отправлен на согласование")
            self.load_contracts()
            self.load_tasks()
            log_message(f"Договор {number} отправлен на согласование")

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить договор на согласование: {e}")
            log_message(f"Ошибка отправки на согласование: {e}")

    def show_approval_status(self):
        selection = self.contracts_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите договор для просмотра статуса")
            return

        item = self.contracts_tree.item(selection[0])
        contract_id, number, title_text = item['values'][0:3]

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()

            # Получаем ВСЕ экземпляры согласования для этого договора
            cur.execute('''
                SELECT i.id, f.name, i.status, i.started_at, i.finished_at
                FROM approval_instances i
                JOIN approval_flows f ON i.flow_id = f.id
                WHERE i.contract_id = ?
                ORDER BY i.started_at DESC
            ''', (contract_id,))

            instances = cur.fetchall()

            if not instances:
                messagebox.showinfo("Статус", "Договор не находится на согласовании")
                return

            # Собираем все задачи согласования для всех экземпляров
            all_tasks = []
            for instance in instances:
                instance_id = instance[0]
                cur.execute('''
                    SELECT t.step_order, t.role_name, u.full_name, t.status, 
                           t.completed_at, t.comment, t.assigned_at, t.deadline_at
                    FROM approval_tasks t
                    LEFT JOIN users u ON t.assigned_user_id = u.id
                    WHERE t.instance_id = ?
                    ORDER BY t.step_order, t.assigned_at
                ''', (instance_id,))
                tasks = cur.fetchall()
                all_tasks.extend(tasks)

            conn.close()

            self.show_status_dialog(number, title_text, instances, all_tasks)

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось получить статус согласования: {e}")

    def show_status_dialog(self, number, title_text, instances, tasks):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Статус согласования - {number}")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("1000x700")

        main_frame = ttk.Frame(dialog, padding=15)
        main_frame.pack(fill="both", expand=True)

        # Информация о договоре
        info_frame = ttk.LabelFrame(main_frame, text="Информация о договоре", padding=10)
        info_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(info_frame, text=f"Договор: {number}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Наименование: {title_text}").pack(anchor="w")

        # Информация о текущем согласовании
        current_instance = instances[0]  # Последний экземпляр
        instance_id, flow_name, status, started_at, finished_at = current_instance
        ttk.Label(info_frame, text=f"Текущий маршрут: {flow_name}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Статус: {status}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Начато: {started_at[:10]}").pack(anchor="w")
        if finished_at:
            ttk.Label(info_frame, text=f"Завершено: {finished_at[:10]}").pack(anchor="w")

        # История согласований
        tasks_frame = ttk.LabelFrame(main_frame, text="История согласований", padding=10)
        tasks_frame.pack(fill="both", expand=True)

        columns = ("step", "role", "user", "status", "assigned", "completed", "comment")
        tree = ttk.Treeview(tasks_frame, columns=columns, show="headings", height=15)

        headers = ["Этап", "Роль", "Пользователь", "Статус", "Назначено", "Завершено", "Комментарий"]
        widths = [50, 120, 120, 80, 100, 100, 300]

        for col, header, width in zip(columns, headers, widths):
            tree.heading(col, text=header)
            tree.column(col, width=width)

        for task in tasks:
            step_num, role, user, status, completed, comment, assigned, deadline = task
            assigned_str = assigned[:10] if assigned else ""
            completed_str = completed[:10] if completed else ""
            user_str = user or "Не назначен"

            # Перевод статусов на русский
            status_ru = {
                'pending': 'Ожидает',
                'approved': 'Утверждено',
                'rejected': 'Отклонено',
                'cancelled': 'Отменено'
            }.get(status, status)

            tree.insert("", "end", values=(
                step_num, role, user_str, status_ru, assigned_str, completed_str, comment or ""
            ))

        scrollbar = ttk.Scrollbar(tasks_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Привязываем подсказки для длинных комментариев
        self.attach_tooltips_to_tree(tree, delay=450)

        ttk.Button(main_frame, text="Закрыть", command=dialog.destroy).pack(pady=10)

        center_window(dialog)

    def approve_task(self):
        self._process_task(True)

    def reject_task(self):
        self._process_task(False)

    def _process_task(self, approve: bool):
        selection = self.tasks_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите задачу для обработки")
            return

        item = self.tasks_tree.item(selection[0])
        task_id, contract_number, title_text, step_num, role = item['values'][0:5]

        dialog = tk.Toplevel(self.root)
        dialog.title("Утверждение задачи" if approve else "Отклонение задачи")
        dialog.transient(self.root)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=15)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text=f"Договор: {contract_number}", font=('Arial', 10, 'bold')).pack(anchor="w")
        ttk.Label(main_frame, text=f"Этап: {step_num} - {role}").pack(anchor="w", pady=(5, 0))

        ttk.Label(main_frame, text="Комментарий:").pack(anchor="w", pady=(15, 5))
        comment_text = tk.Text(main_frame, height=6, width=50)
        comment_text.pack(fill="both", expand=True)
        self.setup_text_shortcuts(comment_text)

        def process():
            comment = comment_text.get("1.0", "end-1c").strip()

            # Автоматическая подстановка комментария если поле пустое
            if not comment:
                if approve:
                    comment = "Согласовано"
                else:
                    comment = "Отклонено"

            try:
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()

                new_status = "approved" if approve else "rejected"
                completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                cur.execute('''
                    UPDATE approval_tasks 
                    SET status = ?, completed_at = ?, comment = ?
                    WHERE id = ?
                ''', (new_status, completed_at, comment, task_id))

                # Получаем информацию о задаче
                cur.execute('''
                    SELECT t.instance_id, t.step_order, i.contract_id, i.flow_id 
                    FROM approval_tasks t
                    JOIN approval_instances i ON t.instance_id = i.id
                    WHERE t.id = ?
                ''', (task_id,))
                task_info = cur.fetchone()
                instance_id, current_step, contract_id, flow_id = task_info

                if approve:
                    # Проверяем, все ли задачи текущего этапа завершены
                    cur.execute('''
                        SELECT COUNT(*) FROM approval_tasks 
                        WHERE instance_id = ? AND step_order = ? AND status = 'pending'
                    ''', (instance_id, current_step))
                    pending_count = cur.fetchone()[0]

                    if pending_count == 0:
                        # Все задачи текущего этапа завершены, проверяем следующий этап
                        cur.execute('''
                            SELECT steps FROM approval_flows WHERE id = ?
                        ''', (flow_id,))
                        flow_result = cur.fetchone()

                        if flow_result:
                            steps = json.loads(flow_result[0])
                            next_step = current_step + 1
                            next_steps = [step_data for step_data in steps if step_data['step'] == next_step]

                            if next_steps:
                                # Создаем задачи для следующего этапа
                                for step_data in next_steps:
                                    role_name = step_data['role']
                                    deadline_days = step_data.get('deadline_days', 3)
                                    deadline = (datetime.now() + timedelta(days=deadline_days)).strftime(
                                        '%Y-%m-%d %H:%M:%S')

                                    assigned_user_id = self.auto_assign_service.get_next_user_by_round_robin(role_name)

                                    cur.execute('''
                                        INSERT INTO approval_tasks 
                                        (instance_id, step_order, role_name, assigned_user_id, status, deadline_at)
                                        VALUES (?, ?, ?, ?, 'pending', ?)
                                    ''', (instance_id, next_step, role_name, assigned_user_id, deadline))
                            else:
                                # Нет следующих этапов - завершаем согласование
                                cur.execute('''
                                    UPDATE approval_instances SET status = 'finished', finished_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (instance_id,))

                                cur.execute('''
                                    UPDATE contracts SET status = 'Согласован', updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (contract_id,))
                else:
                    # Задача отклонена - ВАЖНОЕ ИСПРАВЛЕНИЕ: отменяем ВСЕ задачи для этого договора
                    cur.execute('''
                        UPDATE approval_tasks 
                        SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP, 
                            comment = CONCAT(COALESCE(comment, ''), ?)
                        WHERE instance_id = ? AND status = 'pending'
                    ''', (f" | Отменено из-за отклонения отделом {role}", instance_id))

                    cur.execute('''
                        UPDATE approval_instances SET status = 'finished', finished_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (instance_id,))

                    cur.execute('''
                        UPDATE contracts SET status = 'Отклонён', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (contract_id,))

                # Записываем действие пользователя
                action = "approve_task" if approve else "reject_task"
                cur.execute(
                    "INSERT INTO audit_log (user_id, action, details) VALUES (?, ?, ?)",
                    (self.user_id, action, f'Задача {task_id} для договора {contract_number}')
                )

                conn.commit()
                conn.close()

                messagebox.showinfo("Успех", "Задача обработана")
                dialog.destroy()
                self.load_tasks()
                self.load_contracts()
                log_message(f"Задача {task_id} {'утверждена' if approve else 'отклонена'} с комментарием: {comment}")

            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Не удалось обработать задачу: {e}")
                log_message(f"Ошибка обработки задачи: {e}")

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)

        btn_text = "✅ Утвердить" if approve else "❌ Отклонить"
        ttk.Button(btn_frame, text=btn_text, command=process).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side="left", padx=5)

        center_window(dialog)

    def manage_users(self):
        """Открыть диалог управления пользователями"""
        if not self.is_admin:
            messagebox.showwarning("Доступ запрещен", "Эта функция доступна только администраторам")
            return

        UserManagementDialog(self.root)

    def reset_database(self):
        if messagebox.askyesno("Подтверждение","ВНИМАНИЕ! Это действие удалит все данные и создает новую базу с тестовыми данными. Продолжить?"):
            try:
                if os.path.exists(DB_FILE):
                    os.remove(DB_FILE)
                init_database()
                messagebox.showinfo("Успех", "База данных сброшена")
                self.load_contracts()
                self.load_tasks()
                log_message("База данных сброшена администратором")
            except (OSError, sqlite3.Error) as e:
                messagebox.showerror("Ошибка", f"Не удалось сбросить базу данных: {e}")

    @staticmethod
    def create_backup():
        import shutil
        try:
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")

            shutil.copy2(DB_FILE, backup_file)

            messagebox.showinfo("Успех", f"Бэкап создан: {backup_file}")
            log_message(f"Создан бэкап: {backup_file}")

        except (OSError, shutil.Error) as e:
            messagebox.showerror("Ошибка", f"Не удалось создать бэкап: {e}")

    @staticmethod
    def show_statistics():
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM contracts")
            total_contracts = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM contracts WHERE status = 'На согласовании'")
            pending_contracts = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM approval_tasks WHERE status = 'pending'")
            pending_tasks = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            active_users = cur.fetchone()[0]

            conn.close()

            stats = f"""Статистика системы:

• Всего договоров: {total_contracts}
• На согласовании: {pending_contracts}
• Ожидающих задач: {pending_tasks}
• Активных пользователей: {active_users}

Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"""

            messagebox.showinfo("Статистика системы", stats)

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось получить статистику: {e}")

    def confirm_exit(self):
        """Единый метод подтверждения выхода для всех способов закрытия"""
        if self._exiting:
            return

        self._exiting = True

        # Создаем собственное диалоговое окно, чтобы гарантировать его положение поверх всех
        dialog = tk.Toplevel(self.root)
        dialog.title("Подтверждение")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Центрируем диалог относительно главного окна
        dialog.geometry("300x120")
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 60
        dialog.geometry(f"+{x}+{y}")

        # Содержимое диалога
        ttk.Label(dialog, text="Вы уверены, что хотите выйти из системы?",
                  padding=10).pack(pady=10)

        result = [False]  # Используем список для передачи по ссылке

        def on_yes():
            result[0] = True
            dialog.destroy()
            self.root.quit()  # Завершаем главный цикл приложения

        def on_no():
            result[0] = False
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Да", command=on_yes, width=10).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Нет", command=on_no, width=10).pack(side="left", padx=5)

        # Устанавливаем фокус на диалог
        dialog.focus_force()

        # Ждем закрытия диалога
        self.root.wait_window(dialog)

        if result[0]:
            self.perform_logout()
        else:
            self._exiting = False

    def perform_logout(self):
        """Выполняет фактический выход из системы"""
        log_message(f"Пользователь {self.full_name} вышел из системы")

        # Безопасно закрываем все дочерние окна
        for child in self.root.winfo_children():
            try:
                if isinstance(child, tk.Toplevel) and child.winfo_exists():
                    child.destroy()
            except tk.TclError:
                pass  # Окно уже уничтожено

        self.root.destroy()


# ======================= ДИАЛОГ РЕДАКТИРОВАНИЯ ДОГОВОРА =======================
class ContractDialog(TextShortcutsMixin):
    def __init__(self, parent, user_id, user_department, contract=None):
        super().__init__()
        self.counterparty_var = None
        self.counterparty_combo = None
        self.organizations_map = None
        self.parent = parent
        self.user_id = user_id
        self.user_department = user_department
        self.contract = contract
        self.is_edit = contract is not None

        # Инициализация атрибутов UI
        self.number_entry = None
        self.title_entry = None
        self.counterparty_entry = None
        self.amount_entry = None
        self.department_combo = None
        self.file_path = None
        self.file_entry = None
        self.priority_var = None
        self.datetime_display = None

        self.win = tk.Toplevel(parent)
        self.win.title("Редактирование договора" if self.is_edit else "Создание договора")
        self.win.transient(parent)
        self.win.grab_set()

        self.create_widgets()
        if self.is_edit:
            self.load_contract_data()

        center_window(self.win)

    def create_widgets(self):
        main_frame = ttk.Frame(self.win, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Номер договора:*").grid(row=0, column=0, sticky="w", pady=5)
        self.number_entry = ttk.Entry(main_frame, width=40)
        self.number_entry.grid(row=0, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(self.number_entry)

        ttk.Label(main_frame, text="Наименование:*").grid(row=1, column=0, sticky="w", pady=5)
        self.title_entry = ttk.Entry(main_frame, width=40)
        self.title_entry.grid(row=1, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(self.title_entry)

        ttk.Label(main_frame, text="Контрагент:*").grid(row=2, column=0, sticky="w", pady=5)

        # Заменяем текстовое поле на выпадающий список
        self.counterparty_var = tk.StringVar()
        self.counterparty_combo = ttk.Combobox(main_frame, textvariable=self.counterparty_var,
                                               width=37, state="readonly")
        self.counterparty_combo.grid(row=2, column=1, sticky="w", pady=5, padx=(10, 0))

        # Загружаем организации в combobox
        organizations = get_all_organizations()
        if organizations:
            org_display = [f"{org[1]} (ИНН: {org[2]})" for org in organizations]
            self.counterparty_combo['values'] = org_display
            self.organizations_map = {display: org[0] for display, org in zip(org_display, organizations)}
        else:
            self.counterparty_combo['values'] = ["Нет доступных организаций"]
            self.organizations_map = {}

        ttk.Label(main_frame, text="Сумма:").grid(row=3, column=0, sticky="w", pady=5)
        self.amount_entry = AmountEntry(main_frame, width=40)
        self.amount_entry.grid(row=3, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(self.amount_entry)

        ttk.Label(main_frame, text="Отдел:*").grid(row=4, column=0, sticky="w", pady=5)
        self.department_combo = ttk.Combobox(main_frame, width=37, state="readonly")
        self.department_combo['values'] = ("Закупки", "Продажи", "Производство", "Логистика", "ИТ", "Финансы",
                                           "Юридический", "Общий")
        self.department_combo.grid(row=4, column=1, sticky="w", pady=5, padx=(10, 0))
        self.department_combo.set(self.user_department)

        ttk.Label(main_frame, text="Приоритет:").grid(row=5, column=0, sticky="w", pady=5)
        priority_frame = ttk.Frame(main_frame)
        priority_frame.grid(row=5, column=1, sticky="w", pady=5, padx=(10, 0))

        self.priority_var = tk.StringVar(value="standard")
        ttk.Radiobutton(priority_frame, text="Стандартный (3 рабочих дня)", variable=self.priority_var, value="standard").pack(anchor="w")
        ttk.Radiobutton(priority_frame, text="Срочный (1 рабочий день)", variable=self.priority_var, value="urgent").pack(anchor="w")
        ttk.Radiobutton(priority_frame, text="Ручной ввод", variable=self.priority_var, value="custom").pack(anchor="w")

        ttk.Label(main_frame, text="Дата и время дедлайна (для ручного ввода):").grid(row=6, column=0, sticky="w", pady=5)

        # Фрейм для выбора даты и времени
        datetime_frame = ttk.Frame(main_frame)
        datetime_frame.grid(row=6, column=1, sticky="w", pady=5, padx=(10, 0))

        # Поле для отображения выбранной даты и времени
        self.datetime_display = ttk.Entry(datetime_frame, width=20, state="readonly", font=('Arial', 10))
        self.datetime_display.pack(side="left", padx=(0, 10))

        # Кнопка для открытия календаря
        def open_calendar():
            calendar = CalendarDialog(self.win)
            self.win.wait_window(calendar.dialog)
            if calendar.result:
                self.datetime_display.config(state="normal")
                self.datetime_display.delete(0, tk.END)
                self.datetime_display.insert(0, calendar.result)
                self.datetime_display.config(state="readonly")

        ttk.Button(datetime_frame, text="📅 Выбрать", command=open_calendar).pack(side="left")

        def update_datetime_state():
            """Обновляет состояние полей даты/времени в зависимости от выбранного приоритета"""
            if self.priority_var.get() == "custom":
                for widget in datetime_frame.winfo_children():
                    if isinstance(widget, ttk.Button):
                        widget.config(state="normal")
            else:
                for widget in datetime_frame.winfo_children():
                    if isinstance(widget, ttk.Button):
                        widget.config(state="disabled")
                # Автоматически устанавливаем дату для стандартных приоритетов
                if self.priority_var.get() == "standard":
                    days = 3
                else:  # urgent
                    days = 1

                auto_date = datetime.now() + timedelta(days=days)
                self.datetime_display.config(state="normal")
                self.datetime_display.delete(0, tk.END)
                self.datetime_display.insert(0, auto_date.strftime('%Y-%m-%d 18:00:00'))
                self.datetime_display.config(state="readonly")

        self.priority_var.trace_add("write", lambda name, index, mode: update_datetime_state())
        update_datetime_state()  # Инициализация состояния

        ttk.Label(main_frame, text="Файл договора:").grid(row=7, column=0, sticky="w", pady=5)
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=7, column=1, sticky="w", pady=5, padx=(10, 0))

        self.file_path = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path, width=30, state="readonly")
        self.file_entry.pack(side="left")

        ttk.Button(file_frame, text="Обзор", command=self.browse_file, width=8).pack(side="left", padx=(5, 0))

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, columnspan=2, pady=20)

        save_text = "💾 Сохранить изменения" if self.is_edit else "💾 Создать договор"
        ttk.Button(button_frame, text=save_text, command=self.save_contract).pack(side="left", padx=5)
        ttk.Button(button_frame, text="❌ Отмена", command=self.win.destroy).pack(side="left", padx=5)

        ttk.Label(main_frame, text="* - обязательные поля", foreground="gray", font=('Arial', 8)).grid(row=9, column=0, columnspan=2, pady=(10, 0))

    def load_contract_data(self):
        if self.contract:
            contract_id, number, title_text, counterparty, amount, status, owner_id, department, file_path, priority, deadline, created_at, updated_at = self.contract
            self.number_entry.insert(0, number)
            self.title_entry.insert(0, title_text)

            # Загружаем название контрагента вместо ID
            if counterparty:
                try:
                    conn = sqlite3.connect(DB_FILE)
                    cur = conn.cursor()
                    cur.execute("SELECT name, inn FROM organizations WHERE id = ?", (counterparty,))
                    org_data = cur.fetchone()
                    conn.close()

                    if org_data:
                        org_name, org_inn = org_data
                        display_text = f"{org_name} (ИНН: {org_inn})"
                        self.counterparty_var.set(display_text)
                except sqlite3.Error as e:
                    log_message(f"Ошибка загрузки данных контрагента: {e}")

            self.amount_entry.insert(0, format_amount(amount))
            self.department_combo.set(department)
            self.file_path.set(file_path or "")

            if priority:
                self.priority_var.set(priority)
            if deadline and priority == "custom":
                self.datetime_display.config(state="normal")
                self.datetime_display.delete(0, tk.END)
                self.datetime_display.insert(0, deadline)
                self.datetime_display.config(state="readonly")

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Выберите файл договора",
            filetypes=[("Все файлы", "*.*"), ("PDF файлы", "*.pdf"), ("Документы Word", "*.doc *.docx")]
        )
        if filename:
            self.file_path.set(filename)

    def save_contract(self):
        number = self.number_entry.get().strip()
        title_text = self.title_entry.get().strip()
        counterparty_display = self.counterparty_var.get().strip()
        amount_text = self.amount_entry.get().strip()
        department = self.department_combo.get().strip()
        file_path = self.file_path.get().strip()
        priority = self.priority_var.get()
        datetime_str = self.datetime_display.get().strip()

        if not number or not title_text or not department or not counterparty_display:
            messagebox.showwarning("Внимание", "Заполните обязательные поля (отмечены *)")
            return

        # Получаем ID выбранной организации
        if counterparty_display in self.organizations_map:
            counterparty_id = self.organizations_map[counterparty_display]
        else:
            messagebox.showwarning("Внимание", "Выберите контрагента из списка")
            return

        # Рассчитываем дедлайн на основе приоритета
        if priority == "custom":
            if not datetime_str:
                messagebox.showwarning("Внимание", "Для ручного ввода необходимо выбрать дату и время")
                return

            try:
                deadline_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                deadline_str = deadline_dt.strftime('%Y-%m-%d %H:%M:%S')

                # Проверяем что дедлайн в будущем
                if deadline_dt <= datetime.now():
                    messagebox.showwarning("Внимание", "Дедлайн должен быть в будущем")
                    return
            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат даты или времени")
                return
        else:
            # Автоматический расчет дедлайна на основе приоритета
            days = 3 if priority == "standard" else 1
            deadline_dt = datetime.now() + timedelta(days=days)
            deadline_str = deadline_dt.replace(hour=18, minute=0, second=0).strftime('%Y-%m-%d %H:%M:%S')

        try:
            amount = parse_amount(amount_text) if amount_text else 0.0

            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()

            if self.is_edit:
                cur.execute('''
                    UPDATE contracts 
                    SET contract_number = ?, title = ?, counterparty = ?, amount = ?, 
                        department = ?, file_path = ?, priority = ?, deadline_at = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (number, title_text, counterparty_id, amount, department, file_path or None,
                      priority, deadline_str, self.contract[0]))
                action_msg = "Договор обновлен"
            else:
                cur.execute('''
                    INSERT INTO contracts 
                    (contract_number, title, counterparty, amount, owner_id, department, file_path, status, priority, deadline_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Черновик', ?, ?)
                ''', (number, title_text, counterparty_id, amount, self.user_id, department, file_path or None,
                      priority, deadline_str))
                action_msg = "Договор создан"

            conn.commit()
            conn.close()

            messagebox.showinfo("Успех", action_msg)
            log_message(f"{action_msg}: {number}")
            self.win.destroy()

        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Договор с таким номером уже существует")
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить договор: {e}")


# ======================= ДИАЛОГ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ =======================
class UserManagementDialog(TextShortcutsMixin):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.win = tk.Toplevel(parent)
        self.win.title("Управление пользователями")
        self.win.geometry("800x600")
        self.win.transient(parent)
        self.win.grab_set()

        self.users_tree = None

        self.create_widgets()
        self.load_users()
        center_window(self.win)

    def create_widgets(self):
        main_frame = ttk.Frame(self.win, padding=15)
        main_frame.pack(fill="both", expand=True)

        # Панель инструментов
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(toolbar, text="➕ Добавить пользователя", command=self.add_user).pack(side="left", padx=2)
        ttk.Button(toolbar, text="✏️ Редактировать", command=self.edit_user).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🗑️ Удалить", command=self.delete_user).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🔄 Обновить", command=self.load_users).pack(side="left", padx=2)

        # Таблица пользователей
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True)

        columns = ("id", "username", "full_name", "department", "position", "status", "roles")
        self.users_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)

        headers = ["ID", "Логин", "ФИО", "Отдел", "Должность", "Статус", "Роли"]
        widths = [50, 100, 150, 100, 120, 80, 150]

        for col, header, width in zip(columns, headers, widths):
            self.users_tree.heading(col, text=header)
            self.users_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scrollbar.set)

        self.users_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def load_users(self):
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute('''
                SELECT u.id, u.username, u.full_name, u.department, u.position, 
                       CASE WHEN u.is_active = 1 THEN 'Активен' ELSE 'Неактивен' END as status,
                       GROUP_CONCAT(r.name, ', ') as roles
                FROM users u
                LEFT JOIN user_roles ur ON u.id = ur.user_id
                LEFT JOIN roles r ON ur.role_id = r.id
                GROUP BY u.id
                ORDER BY u.full_name
            ''')
            users = cur.fetchall()
            conn.close()

            for user in users:
                self.users_tree.insert("", "end", values=user)

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить пользователей: {e}")

    def add_user(self):
        self._show_user_dialog()

    def edit_user(self):
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите пользователя для редактирования")
            return

        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]

        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cur.fetchone()

            cur.execute('''
                SELECT r.name 
                FROM roles r 
                JOIN user_roles ur ON r.id = ur.role_id 
                WHERE ur.user_id = ?
            ''', (user_id,))
            user_roles = [row[0] for row in cur.fetchall()]
            conn.close()

            self._show_user_dialog(user, user_roles)

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные пользователя: {e}")

    def delete_user(self):
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите пользователя для удаления")
            return

        item = self.users_tree.item(selection[0])
        user_id, username, full_name = item['values'][0:3]

        if messagebox.askyesno("Подтверждение",f"Удалить пользователя '{full_name}' ({username})?\n\nВнимание: Это действие нельзя отменить."):
            try:
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()

                # Удаляем связи с ролями
                cur.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
                # Удаляем пользователя
                cur.execute("DELETE FROM users WHERE id = ?", (user_id,))

                conn.commit()
                conn.close()

                messagebox.showinfo("Успех", "Пользователь удален")
                self.load_users()
                log_message(f"Удален пользователь: {full_name} ({username})")

            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить пользователя: {e}")

    def _show_user_dialog(self, user=None, user_roles=None):
        dialog = tk.Toplevel(self.win)
        dialog.title("Редактирование пользователя" if user else "Добавление пользователя")
        dialog.transient(self.win)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Поля формы
        ttk.Label(main_frame, text="Логин:*").grid(row=0, column=0, sticky="w", pady=5)
        username_entry = ttk.Entry(main_frame, width=30)
        username_entry.grid(row=0, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(username_entry)

        ttk.Label(main_frame, text="ФИО:*").grid(row=1, column=0, sticky="w", pady=5)
        full_name_entry = ttk.Entry(main_frame, width=30)
        full_name_entry.grid(row=1, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(full_name_entry)

        ttk.Label(main_frame, text="Пароль:*").grid(row=2, column=0, sticky="w", pady=5)
        password_entry = ttk.Entry(main_frame, width=30, show="●")
        password_entry.grid(row=2, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(password_entry)

        ttk.Label(main_frame, text="Отдел:").grid(row=3, column=0, sticky="w", pady=5)
        department_combo = ttk.Combobox(main_frame, width=27, state="readonly")
        department_combo['values'] = ("Руководство", "Финансы", "Юридический", "Продажи", "Закупки", "Коммерция", "Безопасность", "Логистика", "ИТ", "Общий")
        department_combo.grid(row=3, column=1, sticky="w", pady=5, padx=(10, 0))

        ttk.Label(main_frame, text="Должность:").grid(row=4, column=0, sticky="w", pady=5)
        position_entry = ttk.Entry(main_frame, width=30)
        position_entry.grid(row=4, column=1, sticky="w", pady=5, padx=(10, 0))
        self.setup_text_shortcuts(position_entry)

        ttk.Label(main_frame, text="Статус:").grid(row=5, column=0, sticky="w", pady=5)
        status_var = tk.StringVar(value="Активен")
        ttk.Radiobutton(main_frame, text="Активен", variable=status_var, value="Активен").grid(row=5, column=1, sticky="w", padx=(10, 0))
        ttk.Radiobutton(main_frame, text="Неактивен", variable=status_var, value="Неактивен").grid(row=5, column=2, sticky="w")

        # Список ролей
        ttk.Label(main_frame, text="Роли:").grid(row=6, column=0, sticky="nw", pady=5)
        roles_frame = ttk.Frame(main_frame)
        roles_frame.grid(row=6, column=1, columnspan=2, sticky="w", pady=5, padx=(10, 0))

        # Получаем все доступные роли
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM roles ORDER BY name")
            all_roles = cur.fetchall()
            conn.close()
        except sqlite3.Error:
            all_roles = []

        role_vars = {}
        for i, (role_id, role_name) in enumerate(all_roles):
            var = tk.BooleanVar()
            if user_roles and role_name in user_roles:
                var.set(True)
            role_vars[role_id] = var
            cb = ttk.Checkbutton(roles_frame, text=role_name, variable=var)
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 20))

        # Заполняем данные если редактируем
        if user:
            user_id_val, username_val, full_name_val, password_val, department_val, position_val, is_active_val = user[:7]
            username_entry.insert(0, username_val)
            full_name_entry.insert(0, full_name_val)
            department_combo.set(department_val or "")
            position_entry.insert(0, position_val or "")
            status_var.set("Активен" if is_active_val else "Неактивен")
            password_entry.insert(0, "        ")  # Заглушка для пароля

        def save_user():
            username_input = username_entry.get().strip()
            full_name_input = full_name_entry.get().strip()
            password_input = password_entry.get().strip()
            department_input = department_combo.get().strip()
            position_input = position_entry.get().strip()
            is_active_input = 1 if status_var.get() == "Активен" else 0

            if not username_input or not full_name_input:
                messagebox.showwarning("Внимание", "Заполните обязательные поля (Логин и ФИО)")
                return

            if not user and not password_input:
                messagebox.showwarning("Внимание", "Введите пароль для нового пользователя")
                return

            try:
                db_connection = sqlite3.connect(DB_FILE)
                db_cursor = db_connection.cursor()

                if user:
                    # Обновление существующего пользователя
                    update_data = [username_input, full_name_input, department_input or None, position_input or None,
                                   is_active_input, user[0]]
                    if password_input and password_input != "        ":  # Если пароль изменен
                        update_sql = '''UPDATE users SET username=?, full_name=?, password=?, 
                                      department=?, position=?, is_active=? WHERE id=?'''
                        update_data.insert(2, hash_password(password_input))
                    else:
                        update_sql = '''UPDATE users SET username=?, full_name=?, department=?, 
                                      position=?, is_active=? WHERE id=?'''

                    db_cursor.execute(update_sql, update_data)
                    current_user_id = user[0]
                    action_msg = "Пользователь обновлен"
                else:
                    # Создание нового пользователя
                    hashed_password = hash_password(password_input)
                    db_cursor.execute('''INSERT INTO users (username, full_name, password, department, position, is_active)
                                VALUES (?, ?, ?, ?, ?, ?)''',
                                      (username_input, full_name_input, hashed_password, department_input or None,
                                       position_input or None, is_active_input))
                    current_user_id = db_cursor.lastrowid
                    action_msg = "Пользователь создан"

                # Обновляем роли
                db_cursor.execute("DELETE FROM user_roles WHERE user_id = ?", (current_user_id,))
                for role_id_value, role_var in role_vars.items():
                    if role_var.get():
                        db_cursor.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                                          (current_user_id, role_id_value))

                db_connection.commit()
                db_connection.close()

                messagebox.showinfo("Успех", action_msg)
                self.load_users()
                dialog.destroy()
                log_message(f"{action_msg}: {full_name_input} ({username_input})")

            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Пользователь с таким логином уже существует")
            except sqlite3.Error as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить пользователя: {e}")

        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, pady=20)

        save_text = "💾 Сохранить изменения" if user else "💾 Создать пользователя"
        ttk.Button(button_frame, text=save_text, command=save_user).pack(side="left", padx=5)
        ttk.Button(button_frame, text="❌ Отмена", command=dialog.destroy).pack(side="left", padx=5)

        ttk.Label(main_frame, text="* - обязательные поля", foreground="gray", font=('Arial', 8)).grid(row=8, column=0, columnspan=3, pady=(10, 0))

        center_window(dialog)


# ======================= ЗАПУСК ПРИЛОЖЕНИЯ =======================
def main():
    init_database()

    root = tk.Tk()
    root.title("Система управления договорами - ООО «Фастлэнд»")
    # делаем окно резиновым (чтобы можно было растягивать)
    root.resizable(True, True)

    # Создаем главное окно приложения
    app_window = None

    def start_app():
        nonlocal app_window

        login_dialog = LoginDialog(root)
        root.wait_window(login_dialog.win)

        if login_dialog.result:
            user_id, full_name, roles, department = login_dialog.result

            # Скрываем стартовое окно
            root.withdraw()

            # Создаем новое окно приложения
            app_window = tk.Toplevel(root)
            app_window.title(f"Система управления договорами — {full_name}")

            # Не устанавливаем протокол WM_DELETE_WINDOW - пусть приложение само обрабатывает закрытие
            FastlandApp(app_window, user_id, full_name, roles, department)

            # Ждем закрытия окна приложения
            app_window.wait_window(app_window)

            # Когда окно приложения закрыто, показываем стартовое окно
            if root.winfo_exists():
                root.deiconify()

    start_frame = ttk.Frame(root, padding=40)
    start_frame.pack(fill="both", expand=True)

    ttk.Label(start_frame, text="СИСТЕМА УПРАВЛЕНИЯ ДОГОВОРАМИ", font=("Arial", 16, "bold")).pack(pady=(0, 10))

    ttk.Label(start_frame, text="ООО «Фастлэнд»", font=("Arial", 14)).pack(pady=(0, 5))

    ttk.Label(start_frame, text="Производство готовых блюд и полуфабрикатов", font=("Arial", 10), foreground="#555").pack(pady=(0, 30))

    ttk.Button(start_frame, text="🚀 Войти в систему", command=start_app, width=20).pack(pady=10)

    ttk.Button(start_frame, text="❌ Выход", command=root.destroy, width=20).pack(pady=5)

    info_text = """Для входа используйте тестовые учетные записи:

• Администратор: admin / admin
• Генеральный директор: gen_dir / 123  
• Юрист: lawyer / 123
• Финансовый директор: finance / 123

Версия 1.1 | Разработано для дипломной работы Чубенко С.Д."""

    ttk.Label(start_frame, text=info_text, foreground="gray", justify="center").pack(side="bottom", pady=20)

    center_window(root)
    root.mainloop()


if __name__ == "__main__":
    main()
