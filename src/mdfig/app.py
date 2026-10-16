"""Windows desktop UI and command-line entry point."""
from dataclasses import asdict
from collections import deque
from pathlib import Path
import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .converter import convert_file
from .renderer import RenderOptions
from .isolated import IsolatedRenderer, serve
from .windows import FileDrop, install_context_menu, remove_context_menu


def project_home():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    path = Path(__file__).resolve().parents[2]
    for parent in (path, *path.parents):
        if (parent / "project.json").is_file():
            return parent
    return path


class Application:
    def __init__(self, root, paths=(), auto=False):
        self.root = root
        self.events = queue.Queue()
        self.items = {}
        self.file_keys = set()
        self.results = {}
        self.running = False
        self.closed = False
        self.closing = False
        self.completed = 0
        self.poll_id = None
        self.cancel = threading.Event()
        self.log_lines = deque(maxlen=5000)
        self.home = project_home()
        self.settings_path = self.home / "data" / "settings.json"
        try:
            saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if not isinstance(saved, dict):
                saved = {}
        except (OSError, ValueError):
            saved = {}
        if not isinstance(saved.get('width', 960), int) or not 320 <= saved.get('width', 960) <= 2400:
            saved['width'] = 960
        if saved.get('scale', 2) not in (1, 2, 3):
            saved['scale'] = 2
        if not isinstance(saved.get('include_mermaid', True), bool):
            saved['include_mermaid'] = True
        if not isinstance(saved.get('browser_path', ''), str):
            saved['browser_path'] = ''
        root.title(f"Markdown 图形转图片  v{__version__}")
        root.geometry("940x700")
        root.minsize(800, 600)
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=29)
        style.configure("Heading.TLabel", font=("Microsoft YaHei UI", 17, "bold"))
        main = ttk.Frame(root, padding=22)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Markdown 图形转图片", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(main, text="将 HTML / 动态布局组件 / SVG / Canvas / Mermaid 渲染为 PNG，供 Typora 阅读。", padding=(0, 8, 0, 14)).pack(anchor="w")
        drop = tk.Label(main, text="将 Markdown 文件拖到这里，或点击「添加文件」\n支持一次添加多个文件", bg="#edf4fc", fg="#24578b", font=("Microsoft YaHei UI", 12), padx=16, pady=18, relief="groove", bd=1)
        drop.pack(fill="x", pady=(0, 12))
        drop.bind("<Button-1>", lambda _: self.choose_files())
        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=(0, 10))
        self.add_button = ttk.Button(controls, text="添加文件", command=self.choose_files)
        self.add_button.pack(side="left")
        ttk.Button(controls, text="移除所选", command=self.remove_selected).pack(side="left", padx=8)
        ttk.Button(controls, text="清空列表", command=self.clear_files).pack(side="left")
        ttk.Button(controls, text="右键菜单…", command=self.menu_dialog).pack(side="right")
        self.tree = ttk.Treeview(main, columns=("file", "status"), show="headings", height=6, selectmode="extended")
        self.tree.heading("file", text="文件")
        self.tree.heading("status", text="转换状态")
        self.tree.column("file", width=610)
        self.tree.column("status", width=170)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _: self.open_result())
        options = ttk.Frame(main, padding=(0, 14, 0, 8))
        options.pack(fill="x")
        self.width = tk.StringVar(value=str(saved.get("width", 960)))
        self.scale = tk.StringVar(value=str(saved.get("scale", 2)))
        self.mermaid = tk.BooleanVar(value=saved.get("include_mermaid", True))
        self.browser_path = tk.StringVar(value=saved.get("browser_path", ""))
        ttk.Label(options, text="图形宽度").pack(side="left")
        ttk.Combobox(options, textvariable=self.width, values=(720, 960, 1200, 1600), width=6).pack(side="left", padx=(6, 16))
        ttk.Label(options, text="清晰度").pack(side="left")
        ttk.Combobox(options, textvariable=self.scale, values=(1, 2, 3), width=4, state="readonly").pack(side="left", padx=(6, 16))
        ttk.Checkbutton(options, text="转换 Mermaid", variable=self.mermaid).pack(side="left")
        ttk.Button(options, text="选择浏览器…", command=self.choose_browser).pack(side="right")
        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=(2, 10))
        self.start_button = ttk.Button(actions, text="开始转换", command=self.start)
        self.start_button.pack(side="left")
        self.cancel_button = ttk.Button(actions, text="取消转换", command=self.cancel.set, state="disabled")
        self.cancel_button.pack(side="left", padx=8)
        ttk.Button(actions, text="打开结果文件", command=self.open_result).pack(side="right")
        ttk.Button(actions, text="打开所在目录", command=self.open_folder).pack(side="right", padx=8)
        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 8))
        self.status = tk.StringVar(value="原文件保留；新 Markdown 和图片文件夹保存到源目录。全程在本机处理。")
        ttk.Label(main, textvariable=self.status, wraplength=880).pack(anchor="w", pady=(0, 8))
        self.log = tk.Text(main, height=7, font=("Microsoft YaHei UI", 9), state="disabled", wrap="word", relief="solid", borderwidth=1)
        self.log.pack(fill="x")
        root.report_callback_exception = self.report_callback_exception
        self.drop = FileDrop(root, self.add_files)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.add_files(paths)
        self.poll_id = root.after(100, self.poll)
        if auto and paths:
            root.after(400, self.start)

    def append_log(self, text):
        if self.closed:
            return
        text = str(text)
        self.log_lines.append(text)
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        if int(self.log.index('end-1c').split('.')[0]) > 2200:
            self.log.configure(state='normal')
            self.log.delete('1.0', '201.0')
            self.log.configure(state='disabled')

    def report_callback_exception(self, kind, error, trace):
        details = ''.join(traceback.format_exception(kind, error, trace))
        self.append_log('界面操作未完成：' + str(error))
        if not self.closed:
            self.status.set('操作未完成，软件仍可继续使用；详情见日志。')
        self.log_lines.append(details)
        self.save_log()

    def choose_files(self):
        if self.running or self.closing:
            return
        self.add_files(filedialog.askopenfilenames(title="选择 Markdown 文件", filetypes=[("Markdown", "*.md *.markdown *.mdown"), ("所有文件", "*.*")]))

    def add_files(self, paths):
        if self.running:
            self.append_log("转换期间请稍后再添加文件。")
            return
        for raw in paths:
            # Do not stat/resolve dragged paths on the GUI thread: network and
            # cloud placeholder files can block. The conversion worker validates IO.
            try:
                path = Path(os.path.abspath(os.fspath(raw)))
            except (TypeError, ValueError, OSError) as error:
                self.append_log('无效文件路径：' + str(error))
                continue
            if path.suffix.lower() not in {".md", ".markdown", ".mdown"}:
                self.append_log(f"已跳过非 Markdown 文件：{path.name}")
                continue
            key = os.path.normcase(str(path))
            if key in self.file_keys:
                continue
            item = self.tree.insert("", "end", values=(str(path), "等待转换"))
            self.items[item] = str(path)
            self.file_keys.add(key)

    def remove_selected(self):
        if self.running or self.closing:
            return
        for item in self.tree.selection():
            path = self.items.pop(item, None)
            if path:
                self.file_keys.discard(os.path.normcase(path))
            self.results.pop(item, None)
            self.tree.delete(item)

    def clear_files(self):
        if not self.running:
            self.tree.delete(*self.tree.get_children())
            self.items.clear()
            self.file_keys.clear()
            self.results.clear()

    def choose_browser(self):
        selected = filedialog.askopenfilename(title="选择 Edge、Chrome 或 Chromium 的 exe", filetypes=[("浏览器程序", "*.exe")])
        if selected:
            self.browser_path.set(selected)
            self.append_log("浏览器已设为：" + selected)

    def start(self):
        if self.running or self.closing or self.closed:
            return
        if not self.items:
            messagebox.showinfo("添加文件", "请先拖入或添加 Markdown 文件。")
            return
        try:
            width, scale = int(self.width.get()), float(self.scale.get())
            if not 320 <= width <= 2400 or scale not in (1, 2, 3):
                raise ValueError()
        except ValueError:
            messagebox.showerror("设置有误", "宽度须为 320–2400 的整数，清晰度请选择 1、2 或 3。")
            return
        options = RenderOptions(width=width, scale=scale, include_mermaid=self.mermaid.get(), browser_path=self.browser_path.get())
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            pending = self.settings_path.with_name(f'.settings-{os.getpid()}.pending')
            try:
                pending.write_text(json.dumps(asdict(options), ensure_ascii=False, indent=2), encoding="utf-8")
                os.replace(pending, self.settings_path)
            finally:
                pending.unlink(missing_ok=True)
        except OSError as error:
            self.append_log('设置未能保存，本轮仍使用当前设置：' + str(error))
        self.running = True
        self.cancel.clear()
        self.completed = 0
        self.results.clear()
        for item in self.items:
            self.tree.set(item, 'status', '等待转换')
        self.start_button.configure(state="disabled")
        self.add_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.configure(maximum=len(self.items), value=0)
        work = list(self.items.items())
        self.append_log("开始转换。重复操作会生成带编号的新副本。")
        try:
            threading.Thread(target=self.worker, args=(work, options), daemon=True).start()
        except Exception as error:
            self.running = False
            self.start_button.configure(state='normal')
            self.add_button.configure(state='normal')
            self.cancel_button.configure(state='disabled')
            self.report_callback_exception(type(error), error, error.__traceback__)

    def worker(self, work, options):
        try:
            job_root = self.home / 'data' / 'jobs'
            try:
                job_root.mkdir(parents=True, exist_ok=True)
            except OSError:
                job_root = None
            with IsolatedRenderer(options, self.cancel.is_set, job_root) as renderer:
                self.events.put(("log", "渲染浏览器：" + renderer.browser_name))
                for item, path in work:
                    if self.cancel.is_set():
                        break
                    self.events.put(("state", item, "正在转换"))
                    try:
                        result = convert_file(path, renderer, lambda message: self.events.put(("log", message)), self.cancel.is_set)
                        self.events.put(("result", item, result))
                    except Exception as error:
                        self.events.put(("error", item, '已取消' if self.cancel.is_set() else str(error)))
            for warning in renderer.cleanup_warnings:
                self.events.put(('log', '临时目录被系统占用，未完全清理：' + warning['path']))
        except Exception as error:
            self.events.put(("fatal", str(error)))
        finally:
            self.events.put(("done",))

    def poll(self):
        if self.closed:
            return
        try:
            deadline = time.monotonic() + 0.016
            while time.monotonic() < deadline:
                event = self.events.get_nowait()
                if event[0] == "log":
                    self.append_log(event[1])
                    self.status.set(event[1][:160])
                elif event[0] == "state":
                    self.tree.set(event[1], "status", event[2])
                elif event[0] == "result":
                    result = event[2]
                    self.results[event[1]] = result
                    text = "无需转换" if not result.total else ((f"部分成功 {result.succeeded}/{result.total}" if result.failures else f"完成 {result.succeeded}/{result.total}") if result.succeeded else "失败，代码保留")
                    self.tree.set(event[1], "status", text)
                    self.tree.selection_set(event[1])
                    self.completed += 1
                    self.progress.configure(value=self.completed)
                elif event[0] == "error":
                    self.tree.set(event[1], "status", "未完成")
                    self.append_log(event[2])
                    self.completed += 1
                    self.progress.configure(value=self.completed)
                elif event[0] == "fatal":
                    self.append_log(event[1])
                    if not self.closing:
                        messagebox.showerror("无法开始转换", event[1])
                elif event[0] == "done":
                    self.running = False
                    self.start_button.configure(state="normal")
                    self.add_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    for item in self.items:
                        if self.tree.set(item, 'status') == '等待转换':
                            self.tree.set(item, 'status', '已取消' if self.cancel.is_set() else '未完成')
                    self.status.set("本轮已结束。可双击文件行打开结果；未成功的图形保留原代码并在日志中说明。")
                    self.save_log()
        except queue.Empty:
            pass
        except Exception:
            self.report_callback_exception(*sys.exc_info())
        finally:
            if not self.closed:
                self.poll_id = self.root.after(40, self.poll)

    def selected_path(self):
        selection = self.tree.selection()
        item = selection[0] if selection else next(iter(self.items), None)
        if not item:
            return None
        result = self.results.get(item)
        return Path(result.output if result and result.output else self.items[item])

    def open_result(self):
        selection = self.tree.selection()
        item = selection[0] if selection else next(iter(self.items), None)
        result = self.results.get(item)
        if not result or not result.output:
            messagebox.showinfo('尚无结果', '所选文件尚未生成图像版，请先转换并查看状态。')
            return
        try:
            os.startfile(result.output)
        except OSError as error:
            self.report_callback_exception(type(error), error, error.__traceback__)

    def open_folder(self):
        path = self.selected_path()
        if path:
            subprocess.Popen(["explorer.exe", "/select,", str(path)])

    def menu_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("文件右键菜单")
        dialog.transient(self.root)
        frame = ttk.Frame(dialog, padding=20)
        frame.pack()
        ttk.Label(frame, text="为当前用户添加「转换图形代码为图片」。\nWindows 11 中通常位于「显示更多选项」。\n不会改变 Markdown 的默认打开程序。", padding=(0, 0, 0, 14)).pack()

        def apply(action):
            try:
                action()
                messagebox.showinfo("右键菜单", "操作完成。", parent=dialog)
            except Exception as error:
                messagebox.showerror("操作失败", str(error), parent=dialog)
        ttk.Button(frame, text="添加右键菜单", command=lambda: apply(install_context_menu)).pack(side="left", padx=6)
        ttk.Button(frame, text="移除右键菜单", command=lambda: apply(remove_context_menu)).pack(side="left", padx=6)

    def save_log(self):
        folder = self.home / "data" / "logs"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            (folder / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".log")).write_text("\n".join(self.log_lines), encoding="utf-8")
        except OSError:
            pass

    def close(self):
        if self.closed:
            return
        self.closing = True
        if self.running:
            self.cancel.set()
            self.status.set("正在结束当前图形，请稍候；临时文件将自动清理。")
            self.root.after(150, self.close)
            return
        self.drop.close()
        self.closed = True
        if self.poll_id:
            self.root.after_cancel(self.poll_id)
        self.root.destroy()


def write_console(message):
    if sys.stdout:
        print(message, flush=True)


def main():
    parser = argparse.ArgumentParser(description="将 Markdown 中的图形代码转换为 PNG，原文件保持不变。")
    parser.add_argument("files", nargs="*")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--scale", type=float, default=2)
    parser.add_argument("--browser", default="")
    parser.add_argument("--no-mermaid", action="store_true")
    parser.add_argument("--report", default="")
    parser.add_argument("--install-menu", action="store_true")
    parser.add_argument("--remove-menu", action="store_true")
    parser.add_argument('--renderer-worker', default='', help=argparse.SUPPRESS)
    parser.add_argument('--diagnose-drop', default='', help=argparse.SUPPRESS)
    parser.add_argument('--diagnose-drop-count', type=int, default=1000, help=argparse.SUPPRESS)
    parser.add_argument('--diagnose-convert', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.renderer_worker:
        return serve(args.renderer_worker)
    if args.install_menu or args.remove_menu:
        (install_context_menu if args.install_menu else remove_context_menu)()
        return 0
    if args.cli:
        if not args.files:
            parser.error("--cli 需要至少一个 Markdown 文件路径")
        if not 320 <= args.width <= 2400 or args.scale not in (1, 2, 3):
            parser.error("宽度须为 320–2400，清晰度须为 1、2 或 3")
        results = []
        options = RenderOptions(width=args.width, scale=args.scale, browser_path=args.browser, include_mermaid=not args.no_mermaid)
        job_root = project_home() / 'data' / 'jobs'
        try:
            job_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            job_root = None
        with IsolatedRenderer(options, job_root=job_root) as renderer:
            for path in args.files:
                try:
                    results.append(asdict(convert_file(path, renderer, write_console)))
                except Exception as error:
                    results.append({"source": path, "error": str(error)})
        if args.report:
            Path(args.report).parent.mkdir(parents=True, exist_ok=True)
            Path(args.report).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        write_console(json.dumps(results, ensure_ascii=False))
        return 1 if any(result.get("error") or result.get("failures") for result in results) else 0
    root = tk.Tk()
    application = Application(root, args.files, args.auto and not args.diagnose_drop)
    if args.diagnose_drop:
        from .diagnostics import schedule_drop_diagnostic
        if not args.files or not 1 <= args.diagnose_drop_count <= 10000:
            parser.error('拖放诊断需要文件，消息数须为 1–10000')
        schedule_drop_diagnostic(application, args.diagnose_drop, args.diagnose_drop_count, args.diagnose_convert)
    root.mainloop()
    return 0


def entry():
    fault_file = None
    try:
        import faulthandler
        folder = project_home() / 'data' / 'logs'
        folder.mkdir(parents=True, exist_ok=True)
        fault_file = (folder / f'native-{os.getpid()}.log').open('a', encoding='utf-8')
        faulthandler.enable(fault_file, all_threads=True)
    except OSError:
        pass
    try:
        raise SystemExit(main())
    except Exception:
        details = traceback.format_exc()
        folder = project_home() / "data" / "logs"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "startup-error.log").write_text(details, encoding="utf-8")
        except OSError:
            pass
        if sys.stderr:
            print(details, file=sys.stderr)
        else:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Markdown 图形转图片", "程序未能完成操作，详细原因已写入软件目录 data/logs/startup-error.log。\n\n" + details.splitlines()[-1])
        raise SystemExit(1)
