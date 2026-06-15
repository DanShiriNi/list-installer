import tkinter as tk
from tkinter import messagebox, ttk
import os
import sys
import json
import requests
import threading
import webbrowser
from PIL import Image, ImageTk

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.setup_styles()
        self.center_window()
        self.title("Установка программ")
        self.iconbitmap(sys.argv[0])
        self.resizable(True, True)

        self.json_name = "src/json/programs.json"
        self.programs = {}
        self.undownloaded_programs_list = []

        self.program_download_frame = None
        self.program_list_frame = None
        self.program_icon_label = None
        self.current_icon_image = None
        self.program_name_label = None
        self.success_text = None
        self.program_list_progress = None
        self.download_button = None
        self.agree_only_undownloaded = None
        self.programs_var = None
        self.programs_listbox = None

        self.page_index = 0
        self.loading_label = None  # Для хранения лейбла загрузки

        self.load_folders()
        self.load_json()
        self.preload_all_icons()
        self.load_structure()
        self.show_current_program()
        self.update_progress()
        self.go_to_download_page()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Обработчик закрытия окна"""
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
        self.update_idletasks()
        w = 600
        h = 600
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def load_folders(self):
        os.makedirs("src/icons/", exist_ok=True)
        os.makedirs("src/json/", exist_ok=True)

    def load_json(self):
        try:
            if not os.path.exists(self.json_name):
                url = 'https://raw.githubusercontent.com/DanShiriNi/list-installer/main/src/json/programs.json'
                response = requests.get(url)
                response.raise_for_status()
                with open(self.json_name, "w", encoding='utf-8') as f:
                    f.write(response.text)
            with open(self.json_name, "r", encoding='utf-8') as f:
                self.programs = json.load(f)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке JSON-файла: {e}")
            sys.exit(1)
        self.undownloaded_programs_list = [
            name for name, data in self.programs.items()
            if not data.get("IsDownloaded", False)
        ]

    def get_icon_cache_path(self, program_name):
        safe_name = program_name.lower().replace(' ', '_').replace(':', '')
        return f"src/icons/{safe_name}.png"

    def download_and_cache_icon(self, program_name, callback):
        def task():
            icon_url = self.programs[program_name].get("Icon")
            if not icon_url:
                self.after(0, callback, None)
                return

            cache_path = self.get_icon_cache_path(program_name)
            if os.path.exists(cache_path):
                self.after(0, lambda: self._load_icon_from_file(cache_path, callback))
                return
            
            self.show_loading_label()

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
                response = requests.get(icon_url, stream=True, timeout=10, headers=headers)
                response.raise_for_status()
                img = Image.open(response.raw)
                img.save(cache_path, "PNG")
                self.after(0, lambda: self._load_icon_from_file(cache_path, callback))
            except Exception as e:
                print(e)
                self.after(0, callback, None)

        threading.Thread(target=task, daemon=True).start()

    def _load_icon_from_file(self, path, callback):
        try:
            img = Image.open(path)
            img = img.resize((256, 256), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            callback(photo)
        except Exception as e:
            messagebox.showwarning("Ошибка", f"Ошибка чтения иконки {path}: {e}")
            callback(None)

    def update_program_icon(self, program_name):
        def set_icon(photo):
            if self.program_name_label.cget("text") == program_name:
                if photo:
                    self.hide_loading_label()
                    self.program_icon_label.config(image=photo, text="")
                    self.current_icon_image = photo
                else:
                    self.program_icon_label.config(image="", text="❌")
                    self.current_icon_image = None

        self.download_and_cache_icon(program_name, set_icon)
    
    def show_loading_label(self):
        """Показывает лейбл с текстом загрузки и скрывает лейбл иконки"""
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
        """Скрывает лейбл загрузки и показывает лейбл иконки"""
        if self.loading_label:
            self.loading_label.pack_forget()
        self.program_icon_label.pack(pady=5, before=self.program_name_label)

    def preload_all_icons(self):
        def task():
            for prog_name, prog_data in self.programs.items():
                cache_path = self.get_icon_cache_path(prog_name)
                if os.path.exists(cache_path):
                    continue
                icon_url = prog_data.get("Icon")
                if not icon_url:
                    continue
                self._save_icon_from_url(prog_name, icon_url, cache_path)
        threading.Thread(target=task, daemon=True).start()

    def _save_icon_from_url(self, program_name, url, cache_path):
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
            response = requests.get(url, stream=True, timeout=10, headers=headers)
            response.raise_for_status()
            img = Image.open(response.raw)
            img.save(cache_path, "PNG")
            return True
        except Exception as e:
            return False

    def show_current_program(self):
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

        program_weight = self.programs[program_name]['Weight']
        if program_weight < 1:
            self.download_button.config(state="normal", text=f"Установить (~{self.programs[program_name]['Weight'] * 1024} MB)")
        else:
            self.download_button.config(state="normal", text=f"Установить (~{self.programs[program_name]['Weight']} GB)")
        
        self.update_program_icon(program_name)

    def update_progress(self):
        done = len(self.programs) - len(self.undownloaded_programs_list)
        total = len(self.programs)
        percent = (done / total * 100) if total else 0
        text = f"Готово: {done}/{total} ({percent:.1f}%)"
        if hasattr(self, 'success_text'):
            self.success_text.config(text=text)
        if hasattr(self, 'program_list_progress'):
            self.program_list_progress.config(text=text)

    def reload_download(self):
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
        if not self.undownloaded_programs_list:
            return
        self.page_index = (self.page_index - 1) % len(self.undownloaded_programs_list)
        self.show_current_program()

    def go_to_next(self):
        if not self.undownloaded_programs_list:
            return
        self.page_index = (self.page_index + 1) % len(self.undownloaded_programs_list)
        self.show_current_program()

    def show_install_window(self, urls):
        win = tk.Toplevel(self)
        win.title("Установка программы")
        win.iconbitmap(sys.argv[0])
        win.resizable(False, False)
        win.geometry("500x200")
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - 250
        y = (win.winfo_screenheight() // 2) - 100
        win.geometry(f"+{x}+{y}")

        msg = "Чтобы установить программу, перейдите по ресурсам ниже:" if len(urls) > 1 \
              else "Чтобы установить программу, перейдите по ссылке ниже:"
        tk.Label(win, text=msg, font=("Arial", 10)).pack(pady=(20, 10))

        frame = tk.Frame(win)
        frame.pack(pady=5)
        for url in urls:
            lbl = tk.Label(frame, text=url, fg="blue", cursor="hand2",
                           font=("Arial", 9, "underline"))
            lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
            lbl.pack(anchor="center", pady=2)

    def download_program_by_name(self, program_name):
        urls = self.programs[program_name]["URLs"]
        self.show_install_window(urls)

    def download_program(self):
        if not self.undownloaded_programs_list:
            return
        program_name = self.undownloaded_programs_list[self.page_index]
        self.download_program_by_name(program_name)

    def access_program(self):
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
        self.program_list_frame.pack_forget()
        self.program_download_frame.pack(fill="both", expand=True)

    def go_to_list_page(self):
        self.program_download_frame.pack_forget()
        self.update_program_list()
        self.program_list_frame.pack(fill="both", expand=True)

    def update_program_list(self):
        if self.agree_only_undownloaded.get() == 0:
            items = [f"❌ {name}" if not data["IsDownloaded"] else f"✔ {name}"
                     for name, data in self.programs.items()]
        else:
            items = [f"❌ {name}" for name in self.undownloaded_programs_list]
        self.programs_var.set(items)

    def select_program(self, event):
        sel = self.programs_listbox.curselection()
        if sel:
            name = self.programs_listbox.get(sel[0])[2:]
            self.download_program_by_name(name)

    def load_structure(self):
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

        self.agree_only_undownloaded = tk.IntVar()
        checkbox = tk.Checkbutton(self.program_list_frame, text="Только не установленные", variable=self.agree_only_undownloaded, command=self.update_program_list, font=("Arial", 10))
        checkbox.pack(anchor=tk.W)

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