import tkinter as tk
from tkinter import messagebox, ttk
import os
import sys
import json
import requests
import threading
import webbrowser
from PIL import Image, ImageTk


class DropdownCheckbox(ttk.Frame):
    """Создаёт выпадающий список категорий с флажками для фильтрации."""

    def __init__(self, master, categories, on_change=None, **kwargs):
        """Инициализирует список категорий и обработчик их изменения."""
        super().__init__(master, **kwargs)
        self.categories = list(categories)
        self.on_change = on_change

        self.vars = {c: tk.BooleanVar(value=True) for c in self.categories}
        self.visible_categories = {c: True for c in self.categories}

        # Кнопка, открывающая список
        self.button = tk.Button(self, text="Сортировка ▾", command=self.toggle, font=("Arial", 10))
        self.button.pack(fill="x")

        # Всплывающее окно (создаётся лениво)
        self.popup = None
        # Закрывать при клике вне — вешаем обработчик на root
        self.winfo_toplevel().bind("<Button-1>", self._on_global_click, add="+")

    # ---------- открытие/закрытие ----------
    def toggle(self):
        """Переключает видимость всплывающего списка категорий."""
        if self.popup is not None and self.popup.winfo_exists():
            self.close()
            self.button.config(text="Сортировка ▾")
        else:
            self.open()
            self.button.config(text="Сортировка ▴")

    def open(self):
        """Открывает всплывающий список категорий."""
        if self.popup is not None and self.popup.winfo_exists():
            return

        self.popup = tk.Toplevel(self)
        self.popup.wm_overrideredirect(True)   # без рамки и заголовка
        self.popup.attributes("-topmost", True)

        # Слегка «утопленная» рамка для вида
        border = tk.Frame(self.popup, bd=1, relief="solid")
        border.pack(fill="both", expand=True)

        for cat in self.categories:
            cb = tk.Checkbutton(
                border,
                text=cat,
                variable=self.vars[cat],
                anchor="w",
                command=self._on_check,
                font=("Arial", 10)
            )
            cb.pack(fill="x", padx=4, pady=1)

        # Позиционируем под кнопкой
        self.update_idletasks()
        x = self.button.winfo_rootx()
        y = self.button.winfo_rooty() + self.button.winfo_height()
        self.popup.geometry(f"+{x}+{y}")

    def close(self):
        """Закрывает всплывающий список категорий."""
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.destroy()
        self.popup = None
        self.button.config(text="Сортировка ▾")

    def _on_check(self):
        """Обновляет видимые категории и уведомляет внешний обработчик."""
        for cat in self.categories:
            self.visible_categories[cat] = self.vars[cat].get()
        if self.on_change:
            self.on_change(self.visible_categories)
        else:
            print(self.visible_categories)

    def _on_global_click(self, event):
        """Закрывает список при клике вне него и вне кнопки."""
        if self.popup is None or not self.popup.winfo_exists():
            return
        # Координаты клика
        widget = event.widget
        # Если клик внутри popup — не закрываем
        w = widget
        while w is not None:
            if w == self.popup:
                return
            w = getattr(w, "master", None)
        # Если клик по самой кнопке — toggle сам разберётся
        if widget == self.button:
            return
        self.close()


class App(tk.Tk):
    """Предоставляет главное окно приложения для выбора программ."""

    def __init__(self):
        """Инициализирует окно, данные программ и элементы интерфейса."""
        super().__init__()
        self.setup_styles()
        self.center_window()
        self.title("Установка программ")
        self.iconbitmap(sys.argv[0])
        self.resizable(True, True)

        self.json_name = "src/json/programs.json"
        self.programs = {}
        self.categories = []
        self.start_programs = {}
        self.undownloaded_programs_list = []

        self.program_download_frame = None
        self.program_list_frame = None
        self.program_icon_label = None
        self.program_install_icon_label = None
        self.current_icon_image = None
        self.current_install_icon_image = None
        self.program_name_label = None
        self.program_install_title_label = None
        self.success_text = None
        self.program_list_progress = None
        self.download_button = None
        self.agree_only_undownloaded = None
        self.programs_var = None
        self.programs_listbox = None

        self.page_index = 0
        self.loading_label = None
        self.install_loading_label = None

        self.load_folders()
        self.load_json()
        self.preload_all_icons()
        self.load_structure()
        self.show_current_program()
        self.update_progress()
        self.go_to_download_page()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Сохраняет прогресс по запросу и закрывает приложение."""
        if self.programs != self.start_programs:
            result = messagebox.askyesno(
                title="Подтверждение выхода",
                message="Сохранить ли прогресс загрузки? (JSON-файл будет перезаписан)",
                icon="question"
            )
            
            if result:
                try:
                    if os.path.exists(self.json_name):
                        backup_name = self.json_name + ".backup"
                        try:
                            import shutil
                            shutil.copy2(self.json_name, backup_name)
                        except:
                            pass
                    with open(self.json_name, "w", encoding='utf-8') as f:
                        json.dump(self.programs, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось сохранить прогресс: {e}")
        self.destroy()

    def setup_styles(self):
        """Настраивает стили кнопок и элементов интерфейса."""
        style = ttk.Style(self)
        style.theme_use('clam')
        
        style.configure('TButton', font=('Arial', 12, 'bold'), padding=6, borderwidth=0, relief='flat')
        style.configure('Green.TButton', foreground='white', background='green', borderwidth=0, relief='flat', font=('Arial', 12, 'bold'))
        style.map('Green.TButton', background=[('active', 'dark green')])
        style.configure('Blue.TButton', foreground='white', background='#0078D7', borderwidth=0, relief='flat', font=('Arial', 12, 'bold'))
        style.map('Blue.TButton', background=[('active', '#005a9e')])
        style.configure('WhiteBlue.TButton', foreground='#0078D7', background='white', borderwidth=0, relief='flat', font=('Arial', 12, 'bold'))
        style.map('WhiteBlue.TButton', background=[('active', '#e6e6e6')])
        style.configure('TransparentBlue.TButton', foreground='#0078D7', background=self.cget('bg'), borderwidth=0, relief='flat', font=('Arial', 36, 'bold'))
        style.map('TransparentBlue.TButton', background=[('active', '#e6e6e6')], relief=[('pressed', 'sunken')])

    def center_window(self):
        """Размещает окно приложения по центру экрана."""
        self.update_idletasks()
        w = 600
        h = 600
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def load_folders(self):
        """Создаёт каталоги для иконок и файла данных."""
        os.makedirs("src/icons/", exist_ok=True)
        os.makedirs("src/json/", exist_ok=True)

    def load_json(self):
        """Загружает список программ из локального или удалённого JSON-файла."""
        try:
            if not os.path.exists(self.json_name):
                url = 'https://raw.githubusercontent.com/DanShiriNi/list-installer/main/src/json/programs.json'
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                    'Referer': 'https://www.google.com/',
                }
                headers.update({
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'image',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'cross-site',
                })
                response = requests.get(url)
                response.raise_for_status()
                with open(self.json_name, "w", encoding='utf-8') as f:
                    f.write(response.text)
            with open(self.json_name, "r", encoding='utf-8') as f:
                self.start_programs = json.load(f)
                self.categories = list({category for item in self.start_programs.values() for category in item["Categories"]})
                self.programs = self.start_programs.copy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке JSON-файла: {e}")
            sys.exit(1)
        self.undownloaded_programs_list = [
            name for name, data in self.programs.items()
            if not data.get("IsDownloaded", False)
        ]

    def get_icon_cache_path(self, program_name):
        """Возвращает путь к кэшированной иконке программы."""
        safe_name = program_name.lower().replace(' ', '_').replace(':', '')
        return f"src/icons/{safe_name}.png"

    def download_and_cache_icon(self, show_loading_label_func, program_name, callback):
        """Загружает и кэширует иконку программы в фоновом потоке."""
        def task():
            """Получает и сохраняет иконку, затем передаёт её интерфейсу."""
            icon_url = self.programs[program_name].get("Icon")
            if not icon_url:
                self.after(0, callback, None)
                return

            cache_path = self.get_icon_cache_path(program_name)
            if os.path.exists(cache_path):
                self.after(0, lambda: self._load_icon_from_file(cache_path, callback))
                return
            
            show_loading_label_func()

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Referer': 'https://www.google.com/',
            }

            if "upload.wikimedia.org" in icon_url:
                headers.update({
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'image',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'cross-site',
                })
            try:
                response = requests.get(icon_url, stream=True, timeout=(5, 30), headers=headers)
                response.raise_for_status()
                img = Image.open(response.raw)
                img.save(cache_path, "PNG")
                self.after(0, lambda: self._load_icon_from_file(cache_path, callback))
            except requests.RequestException:
                self.after(0, callback, None)

        threading.Thread(target=task, daemon=True).start()

    def _load_icon_from_file(self, path, callback):
        """Читает иконку из файла, изменяет размер и вызывает callback."""
        try:
            img = Image.open(path)
            img = img.resize((256, 256), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            callback(photo)
        except Exception as e:
            messagebox.showwarning("Ошибка", f"Ошибка чтения иконки {path}: {e}")
            callback(None)

    def update_program_icon(self, program_name):
        """Обновляет иконку программы на основной странице."""
        def set_icon(photo):
            """Показывает загруженную иконку текущей программы."""
            if self.program_name_label.cget("text") == program_name:
                if photo:
                    self.hide_loading_label()
                    self.program_icon_label.config(image=photo, text="")
                    self.current_icon_image = photo
                else:
                    self.program_icon_label.config(image="", text="❌")
                    self.current_icon_image = None

        self.download_and_cache_icon(self.show_loading_label, program_name, set_icon)
    
    def show_loading_label(self):
        """Показывает индикатор загрузки вместо иконки программы."""
        if not self.loading_label:
            # Создаём лейбл загрузки, если его ещё нет
            self.loading_label = tk.Label(
                self.program_icon_label.master, 
                text="⏳ Загрузка...", 
                font=("Arial", 14)
            )
        
        # Скрываем лейбл иконки
        self.program_icon_label.pack_forget()
        self.loading_label.pack(pady=5, before=self.program_name_label)
    
    def hide_loading_label(self):
        """Скрывает индикатор загрузки и возвращает иконку программы."""
        if self.loading_label:
            self.loading_label.pack_forget()
        self.program_icon_label.pack(pady=5, before=self.program_name_label)

    def preload_all_icons(self):
        """Запускает предварительную загрузку отсутствующих иконок."""
        def task():
            """Сохраняет в кэш иконки программ, которых там ещё нет."""
            for prog_name, prog_data in self.programs.items():
                cache_path = self.get_icon_cache_path(prog_name)
                if os.path.exists(cache_path):
                    continue
                icon_url = prog_data.get("Icon")
                if not icon_url:
                    continue
                self._save_icon_from_url(icon_url, cache_path)
        threading.Thread(target=task, daemon=True).start()

    def _save_icon_from_url(self, url, cache_path):
        """Загружает и сохраняет иконку по URL."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Referer': 'https://www.google.com/',
        }

        if "upload.wikimedia.org" in url:
            headers.update({
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
            })
        try:
            response = requests.get(url, stream=True, timeout=(5, 30), headers=headers)
            response.raise_for_status()
            img = Image.open(response.raw)
            img.save(cache_path, "PNG")
            return True
        except Exception as e:
            return False

    def show_current_program(self):
        """Показывает текущую программу."""
        if len(self.undownloaded_programs_list) == 0:
            self.program_name_label.config(text="Все программы установлены!")
            self.download_button.config(state="disabled")
            self.hide_loading_label()
            self.program_icon_label.config(image="", text="✅")
            return
        if self.page_index >= len(self.undownloaded_programs_list):
            self.page_index = 0
        
        program_name = self.undownloaded_programs_list[self.page_index]
        self.program_name_label.config(text=program_name)
        self.program_categories_label.config(text="\n".join(self.programs[program_name]['Categories']))

        program_weight = self.programs[program_name]['Weight']
        if program_weight < 1:
            self.download_button.config(state="normal", text=f"Установить (~{self.programs[program_name]['Weight'] * 1024} MB)")
        else:
            self.download_button.config(state="normal", text=f"Установить (~{self.programs[program_name]['Weight']} GB)")
        
        self.update_program_icon(program_name)

    def update_progress(self):
        """Обновляет отображение количества установленных программ."""
        done = len(self.programs) - len(self.undownloaded_programs_list)
        total = len(self.programs)
        percent = (done / total * 100) if total else 0
        text = f"Готово: {done}/{total} ({percent:.1f}%)"
        if hasattr(self, 'success_text'):
            self.success_text.config(text=text)
        if hasattr(self, 'program_list_progress'):
            self.program_list_progress.config(text=text)

    def reload_download(self):
        """Сбрасывает отметки установки после подтверждения пользователя."""
        if not messagebox.askyesno(
            title="Подтверждение операции",
            message="Вы уверены, что хотите выполнить это действие?\nПрогресс установки начнётся с нуля."
        ):
            return
        for prog in self.programs.values():
            prog["IsDownloaded"] = False
        self.undownloaded_programs_list = list(self.programs.keys())
        self.page_index = 0
        self.show_current_program()
        self.update_progress()
        self.go_to_download_page()

    def go_to_prev(self):
        """Показывает предыдущую программу в списке."""
        if not self.undownloaded_programs_list:
            return
        self.page_index = (self.page_index - 1) % len(self.undownloaded_programs_list)
        self.show_current_program()

    def go_to_next(self):
        """Показывает следующую программу в списке."""
        if not self.undownloaded_programs_list:
            return
        self.page_index = (self.page_index + 1) % len(self.undownloaded_programs_list)
        self.show_current_program()

    def update_install_program_icon(self, program_name):
        """Обновляет иконку программы в окне установки."""
        install_icon_label = self.program_install_icon_label

        def set_icon(photo):
            """Показывает иконку, если окно установки ещё актуально."""
            if not install_icon_label or not install_icon_label.winfo_exists():
                return
            if self.program_install_icon_label is not install_icon_label:
                return
            try:
                if photo:
                    self.hide_install_loading_label(install_icon_label)
                    install_icon_label.config(image=photo, text="")
                    self.current_install_icon_image = photo
                else:
                    install_icon_label.config(image="", text="❌")
                    self.current_install_icon_image = None
            except tk.TclError:
                return

        self.download_and_cache_icon(self.show_install_loading_label, program_name, set_icon)

    def show_install_loading_label(self):
        """Показывает лейбл с текстом загрузки и скрывает лейбл иконки"""
        if not self.program_install_icon_label or not self.program_install_icon_label.winfo_exists():
            return
        if self.install_loading_label and (
            not self.install_loading_label.winfo_exists()
            or self.install_loading_label.master is not self.program_install_icon_label.master
        ):
            self.install_loading_label = None
        if not self.install_loading_label:
            # Создаём лейбл загрузки, если его ещё нет
            self.install_loading_label = tk.Label(
                self.program_install_icon_label.master, 
                text="⏳ Загрузка...", 
                font=("Arial", 14)
            )
        
        # Скрываем лейбл иконки
        self.program_install_icon_label.pack_forget()
        self.install_loading_label.pack(pady=5, before=self.program_install_title_label)
    
    def hide_install_loading_label(self, install_icon_label=None):
        """Скрывает индикатор загрузки и показывает иконку программы."""
        if self.install_loading_label:
            self.install_loading_label.pack_forget()
        if install_icon_label and install_icon_label.winfo_exists():
            install_icon_label.pack(pady=5, before=self.program_install_title_label)

    def show_install_window(self, program_name):
        """Показывает окно со способами установки выбранной программы."""
        previous_frame = None
        for frame in (self.program_download_frame, self.program_list_frame):
            if frame.winfo_ismapped():
                previous_frame = frame
                frame.pack_forget()
                break

        install_frame = tk.Frame(self)
        install_frame.pack(fill=tk.BOTH, expand=True)

        mousewheel_binding = None

        def close_install_frame():
            """Закрывает окно установки и возвращает предыдущую страницу."""
            if mousewheel_binding is not None:
                self.unbind_all("<MouseWheel>")
            install_frame.destroy()
            if previous_frame and previous_frame.winfo_exists():
                previous_frame.pack(fill=tk.BOTH, expand=True)

        close_button = tk.Button(
            install_frame,
            text="Закрыть",
            command=close_install_frame,
            takefocus=False
        )
        close_button.pack(fill=tk.X)

        canvas = tk.Canvas(install_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(install_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollable_frame = tk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def update_scroll_region(event=None):
            """Обновляет область прокрутки по размеру содержимого."""
            canvas.configure(scrollregion=canvas.bbox("all"))
            content_height = scrollable_frame.winfo_reqheight()
            if content_height <= canvas.winfo_height():
                canvas.yview_moveto(0)

        scrollable_frame.bind(
            "<Configure>",
            update_scroll_region
        )
        canvas.bind(
            "<Configure>",
            lambda e: (canvas.itemconfig(canvas_window, width=e.width), update_scroll_region())
        )

        def scroll_canvas(event):
            """Прокручивает содержимое окна колесом мыши."""
            if scrollable_frame.winfo_reqheight() > canvas.winfo_height():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        mousewheel_binding = canvas.bind_all(
            "<MouseWheel>",
            lambda e: scroll_canvas(e) if canvas.winfo_exists() else None
        )

        self.program_install_title_label = tk.Label(scrollable_frame, text=f"Установка программы\n{program_name}", font=("Arial", 14, "bold"))
        self.program_install_title_label.pack(pady=(10, 5))

        self.program_install_icon_label = tk.Label(scrollable_frame, text="", width=256, height=256)
        self.program_install_icon_label.pack(pady=5)

        self.show_install_loading_label()
        self.update_install_program_icon(program_name)

        installer_msg = "Чтобы установить программу, перейдите по ресурсам ниже:"
        tk.Label(scrollable_frame, text=installer_msg, font=("Arial", 10)).pack(pady=(20, 10))

        installation_method_frame = tk.Frame(scrollable_frame)
        installation_method_frame.pack(pady=5)

        installation_methods = self.programs[program_name]["URLs"]

        installer_frame = tk.Frame(scrollable_frame)
        installer_frame.pack(pady=5)

        method_buttons = {}


        def show_links(method_name):
            """Показывает ссылки выбранного способа установки."""
            # Очищаем фрейм со ссылками
            for widget in installer_frame.winfo_children():
                widget.destroy()

            # Обновляем подчёркивание у кнопок
            for name, btn in method_buttons.items():
                if name == method_name:
                    btn.config(font=("Arial", 10, "underline"))
                else:
                    btn.config(font=("Arial", 10))

            # Показываем ссылки выбранного метода
            for url in installation_methods[method_name]:
                url_text = url if len(url) <= 64 else url[:64] + "..."
                lbl = tk.Label(
                    installer_frame,
                    text=url_text,
                    fg="blue",
                    cursor="hand2",
                    font=("Arial", 9, "underline"),
                )
                lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
                lbl.pack(pady=2)


        # Создаём кнопки методов
        for method_name in installation_methods:
            btn = tk.Button(
                installation_method_frame,
                text=method_name,
                font=("Arial", 10),
                cursor="hand2",
                command=lambda m=method_name: show_links(m),
            )
            btn.pack(side="left", fill=tk.BOTH, expand=True)
            method_buttons[method_name] = btn

        # По умолчанию выбираем первый метод
        if installation_methods:
            first = next(iter(installation_methods))
            show_links(first)

        mods_urls = self.programs[program_name]["ModsURLs"]

        if len(mods_urls) > 0:
            mods_msg = "Также можно установить модификации:"
            tk.Label(scrollable_frame, text=mods_msg, font=("Arial", 10)).pack(pady=(20, 10))

            mods_frame = tk.Frame(scrollable_frame)
            mods_frame.pack(pady=5)
            for url in mods_urls:
                url_text = url if len(url) <= 72 else url[:72] + "..."
                lbl = tk.Label(mods_frame, text=url_text, fg="blue", cursor="hand2",
                            font=("Arial", 9, "underline"))
                lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
                lbl.pack(pady=2)

    def download_program(self):
        """Открывает окно установки текущей программы."""
        if not self.undownloaded_programs_list:
            return
        program_name = self.undownloaded_programs_list[self.page_index]
        self.show_install_window(program_name)

    def access_program(self):
        """Отмечает текущую программу установленной и обновляет список."""
        if not self.undownloaded_programs_list:
            return
        prog_name = self.undownloaded_programs_list[self.page_index]
        self.programs[prog_name]["IsDownloaded"] = True
        self.undownloaded_programs_list.pop(self.page_index)
        if self.page_index >= len(self.undownloaded_programs_list) and self.undownloaded_programs_list:
            self.page_index = 0
        self.update_progress()
        self.show_current_program()

    def go_to_download_page(self):
        """Переключает интерфейс на страницу загрузки программ."""
        self.program_list_frame.pack_forget()
        self.program_download_frame.pack(fill="both", expand=True)

    def go_to_list_page(self):
        """Переключает интерфейс на полный список программ."""
        self.program_download_frame.pack_forget()
        self.update_program_list()
        self.program_list_frame.pack(fill="both", expand=True)

    def update_program_list(self):
        """Обновляет элементы списка программ с учётом фильтра установки."""
        if self.agree_only_undownloaded.get() == 0:
            items = [f"❌ {name}" if not data["IsDownloaded"] else f"✔ {name}"
                     for name, data in self.programs.items()]
        else:
            items = [f"❌ {name}" for name in self.undownloaded_programs_list]
        self.programs_var.set(items)

    def select_program(self, event):
        """Открывает окно установки выбранной в списке программы."""
        sel = self.programs_listbox.curselection()
        if sel:
            name = self.programs_listbox.get(sel[0])[2:]
            self.show_install_window(name)

    def filter_by_categories(self, visible_categories):
        """Фильтрует список программ по выбранным категориям."""
        filtered_programs = []
        for name, data in self.programs.items():
            if any(visible_categories.get(cat, False) for cat in data["Categories"]):
                filtered_programs.append(name)
        if self.agree_only_undownloaded.get() == 1:
            filtered_programs = [name for name in filtered_programs if not self.programs[name]["IsDownloaded"]]
        items = [f"❌ {name}" if not self.programs[name]["IsDownloaded"] else f"✔ {name}"
                 for name in filtered_programs]
        self.programs_var.set(items)

    def load_structure(self):
        """Создаёт страницы, панели, кнопки и список программ."""
        self.program_download_frame = tk.Frame(self)

        reload_button = ttk.Button(self.program_download_frame, text="⟳", style="WhiteBlue.TButton", command=self.reload_download, takefocus=False)
        reload_button.grid(column=0, row=0, sticky="ewns")
        self.success_text = tk.Label(self.program_download_frame, text="Готово: ?/? (?%)", font=("Arial", 12), bg='white')
        self.success_text.grid(column=1, row=0, sticky="ewns")
        list_button = ttk.Button(self.program_download_frame, text="☰", style="WhiteBlue.TButton", command=self.go_to_list_page, takefocus=False)
        list_button.grid(column=2, row=0, sticky="ewns")

        prev_button = ttk.Button(self.program_download_frame, text="<", style="TransparentBlue.TButton", command=self.go_to_prev, takefocus=False)
        prev_button.grid(column=0, row=1, sticky="ewns")
        next_button = ttk.Button(self.program_download_frame, text=">", style="TransparentBlue.TButton", command=self.go_to_next, takefocus=False)
        next_button.grid(column=2, row=1, sticky="ewns")

        program_frame = tk.Frame(self.program_download_frame)
        program_frame.grid(column=1, row=1, sticky="nsew")

        self.program_categories_label = tk.Label(program_frame, text="", font=("Arial", 10))
        self.program_categories_label.pack()

        self.program_icon_label = tk.Label(program_frame, text="", width=256, height=256)
        self.program_icon_label.pack(pady=5)

        self.program_name_label = tk.Label(program_frame, text="", font=("Arial", 14, "bold"))
        self.program_name_label.pack()

        install_frame = tk.Frame(self.program_download_frame)
        install_frame.grid(column=0, row=2, columnspan=3, sticky="ewns")

        self.download_button = ttk.Button(install_frame, text="Установить (?)", style="Blue.TButton", command=self.download_program, takefocus=False)
        self.download_button.grid(column=0, row=0, sticky="ewns")
        access_button = ttk.Button(install_frame, text="✔ Установлено", style="Green.TButton", command=self.access_program, takefocus=False)
        access_button.grid(column=1, row=0, sticky="ewns")

        self.program_download_frame.grid_columnconfigure(0, weight=1)
        self.program_download_frame.grid_columnconfigure(1, weight=0)
        self.program_download_frame.grid_columnconfigure(2, weight=1)

        self.program_download_frame.grid_rowconfigure(0, weight=1)
        self.program_download_frame.grid_rowconfigure(1, weight=3)
        self.program_download_frame.grid_rowconfigure(2, weight=1)

        install_frame.grid_columnconfigure(0, weight=1)
        install_frame.grid_columnconfigure(1, weight=1)
        install_frame.grid_rowconfigure(0, weight=1)

        self.program_list_frame = tk.Frame(self)

        top_list_frame = tk.Frame(self.program_list_frame)
        top_list_frame.pack(fill=tk.X)

        reload_list_button = ttk.Button(top_list_frame, text="⟳", style="WhiteBlue.TButton", command=self.reload_download, takefocus=False)
        reload_list_button.grid(column=0, row=0, sticky="ewns")
        self.program_list_progress = tk.Label(top_list_frame, text="Готово: ?/? (?%)", font=("Arial", 12), bg='white')
        self.program_list_progress.grid(column=1, row=0, sticky="ewns")
        download_page_button = ttk.Button(top_list_frame, text="⊡", style="WhiteBlue.TButton", command=self.go_to_download_page, takefocus=False)
        download_page_button.grid(column=2, row=0, sticky="ewns")

        top_list_frame.grid_columnconfigure(0, weight=1)
        top_list_frame.grid_columnconfigure(1, weight=0)
        top_list_frame.grid_columnconfigure(2, weight=1)
        top_list_frame.grid_rowconfigure(0, weight=1)

        top_categories_agree_frame = tk.Frame(self.program_list_frame)
        top_categories_agree_frame.pack(fill=tk.X)

        categories_checkbox = DropdownCheckbox(top_categories_agree_frame, self.categories, on_change=self.filter_by_categories)
        categories_checkbox.pack(side=tk.LEFT, fill=tk.Y)

        self.agree_only_undownloaded = tk.IntVar()
        checkbox = tk.Checkbutton(top_categories_agree_frame, text="Только не установленные", variable=self.agree_only_undownloaded, command=self.update_program_list, font=("Arial", 10))
        checkbox.pack(side=tk.RIGHT)

        self.programs_var = tk.StringVar(value=[])
        self.programs_listbox = tk.Listbox(self.program_list_frame, listvariable=self.programs_var, font=("Arial", 10))
        self.programs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        programs_listbox_scrollbar = ttk.Scrollbar(self.program_list_frame, orient="vertical", command=self.programs_listbox.yview)
        programs_listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.programs_listbox["yscrollcommand"] = programs_listbox_scrollbar.set
        self.programs_listbox.bind('<<ListboxSelect>>', self.select_program)

if __name__ == "__main__":
    app = App()
    app.mainloop()