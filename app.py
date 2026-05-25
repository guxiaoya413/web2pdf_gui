import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core import convert_pdf_to_docx, export_urls_to_pdf, parse_urls


DEFAULT_PDF_OUTPUT = "网页文档.pdf"
DEFAULT_DOCX_OUTPUT = "转换文档.docx"
EXAMPLE_URLS = """https://help.tdx.com.cn/quant/docs/markdown/mindoc-1cfsjkbf8f3is
https://help.tdx.com.cn/quant/docs/markdown/mindoc-1h1525ci3mnkc/mindoc-1h1526nmnk5n4.html"""


class WebToPdfApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("网页 PDF / PDF 转 DOCX")
        self.geometry("920x720")
        self.minsize(780, 600)

        self.log_queue = queue.Queue()
        self.worker = None
        self.web_pdf_output_var = tk.StringVar(value=str(Path.cwd() / DEFAULT_PDF_OUTPUT))
        self.keep_temp_var = tk.BooleanVar(value=False)
        self.wait_var = tk.IntVar(value=2000)
        self.scale_var = tk.DoubleVar(value=0.8)
        self.pdf_input_var = tk.StringVar()
        self.docx_output_var = tk.StringVar(value=str(Path.cwd() / DEFAULT_DOCX_OUTPUT))

        self._build_ui()
        self.after(100, self._drain_log_queue)

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self._build_web_to_pdf_tab(self.notebook)
        self._build_pdf_to_docx_tab(self.notebook)

        ttk.Label(root, text="日志").grid(row=1, column=0, sticky="sw", pady=(12, 0))
        self.log_text = tk.Text(root, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=2, column=0, sticky="nsew", pady=(6, 0))

    def _build_web_to_pdf_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="网页转 PDF")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        ttk.Label(tab, text="链接列表（可直接粘贴 Python/JS 列表片段）").grid(row=0, column=0, sticky="w")
        self.url_text = tk.Text(tab, height=14, wrap=tk.NONE, undo=True)
        self.url_text.insert("1.0", EXAMPLE_URLS)
        self.url_text.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(6, 12))

        output_frame = ttk.Frame(tab)
        output_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        ttk.Label(output_frame, text="输出 PDF").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(output_frame, textvariable=self.web_pdf_output_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(output_frame, text="浏览", command=self._browse_web_pdf_output).grid(row=0, column=2, padx=(8, 0))

        options = ttk.Frame(tab)
        options.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        ttk.Label(options, text="加载后等待（毫秒）").pack(side=tk.LEFT)
        ttk.Spinbox(options, from_=0, to=15000, increment=500, textvariable=self.wait_var, width=8).pack(
            side=tk.LEFT, padx=(6, 18)
        )
        ttk.Label(options, text="缩放").pack(side=tk.LEFT)
        ttk.Spinbox(options, from_=0.4, to=1.2, increment=0.05, textvariable=self.scale_var, width=6).pack(
            side=tk.LEFT, padx=(6, 18)
        )
        ttk.Checkbutton(options, text="保留临时分页 PDF", variable=self.keep_temp_var).pack(side=tk.LEFT)

        actions = ttk.Frame(tab)
        actions.grid(row=4, column=0, columnspan=3, sticky="ew")
        self.web_pdf_button = ttk.Button(actions, text="生成 PDF", command=self._start_web_to_pdf)
        self.web_pdf_button.pack(side=tk.LEFT)
        ttk.Button(actions, text="清空日志", command=self._clear_log).pack(side=tk.LEFT, padx=(8, 0))

    def _build_pdf_to_docx_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="PDF 转 DOCX")
        tab.columnconfigure(1, weight=1)

        ttk.Label(tab, text="输入 PDF").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 10))
        ttk.Entry(tab, textvariable=self.pdf_input_var).grid(row=0, column=1, sticky="ew", pady=(0, 10))
        ttk.Button(tab, text="浏览", command=self._browse_pdf_input).grid(row=0, column=2, padx=(8, 0), pady=(0, 10))

        ttk.Label(tab, text="输出 DOCX").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 12))
        ttk.Entry(tab, textvariable=self.docx_output_var).grid(row=1, column=1, sticky="ew", pady=(0, 12))
        ttk.Button(tab, text="浏览", command=self._browse_docx_output).grid(
            row=1, column=2, padx=(8, 0), pady=(0, 12)
        )

        actions = ttk.Frame(tab)
        actions.grid(row=2, column=0, columnspan=3, sticky="ew")
        self.pdf_docx_button = ttk.Button(actions, text="转换为 DOCX", command=self._start_pdf_to_docx)
        self.pdf_docx_button.pack(side=tk.LEFT)
        ttk.Button(actions, text="清空日志", command=self._clear_log).pack(side=tk.LEFT, padx=(8, 0))

    def _browse_web_pdf_output(self):
        filename = filedialog.asksaveasfilename(
            title="保存 PDF",
            defaultextension=".pdf",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
            initialfile=DEFAULT_PDF_OUTPUT,
        )
        if filename:
            self.web_pdf_output_var.set(filename)

    def _browse_pdf_input(self):
        filename = filedialog.askopenfilename(
            title="选择 PDF",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if filename:
            self.pdf_input_var.set(filename)
            current_output = self.docx_output_var.get().strip()
            if not current_output or Path(current_output).name == DEFAULT_DOCX_OUTPUT:
                self.docx_output_var.set(str(Path(filename).with_suffix(".docx")))

    def _browse_docx_output(self):
        filename = filedialog.asksaveasfilename(
            title="保存 DOCX",
            defaultextension=".docx",
            filetypes=[("Word 文档", "*.docx"), ("所有文件", "*.*")],
            initialfile=Path(self.docx_output_var.get().strip() or DEFAULT_DOCX_OUTPUT).name,
        )
        if filename:
            self.docx_output_var.set(filename)

    def _start_web_to_pdf(self):
        if self._worker_is_running():
            return

        urls = parse_urls(self.url_text.get("1.0", tk.END))
        if not urls:
            messagebox.showerror("没有识别到链接", "请至少输入或粘贴一个 http/https 链接。")
            return

        output_path = self.web_pdf_output_var.get().strip()
        if not output_path:
            messagebox.showerror("没有输出路径", "请选择输出 PDF 的保存位置。")
            return

        self._set_buttons_state(tk.DISABLED)
        self._log(f"已识别 {len(urls)} 个链接。")
        self._log(f"开始导出 {len(urls)} 个页面。")

        self.worker = threading.Thread(
            target=self._run_web_to_pdf,
            args=(urls, output_path, self.wait_var.get(), self.scale_var.get(), self.keep_temp_var.get()),
            daemon=True,
        )
        self.worker.start()

    def _start_pdf_to_docx(self):
        if self._worker_is_running():
            return

        input_pdf = self.pdf_input_var.get().strip()
        if not input_pdf:
            messagebox.showerror("没有输入 PDF", "请选择要转换的 PDF 文件。")
            return

        output_docx = self.docx_output_var.get().strip()
        if not output_docx:
            messagebox.showerror("没有输出路径", "请选择输出 DOCX 的保存位置。")
            return

        self._set_buttons_state(tk.DISABLED)
        self.worker = threading.Thread(
            target=self._run_pdf_to_docx,
            args=(input_pdf, output_docx),
            daemon=True,
        )
        self.worker.start()

    def _worker_is_running(self):
        return self.worker and self.worker.is_alive()

    def _set_buttons_state(self, state):
        self.web_pdf_button.configure(state=state)
        self.pdf_docx_button.configure(state=state)

    def _run_web_to_pdf(self, urls, output_path, wait_ms, scale, keep_temp):
        try:
            final_path = export_urls_to_pdf(
                urls,
                output_path,
                wait_ms=wait_ms,
                scale=scale,
                keep_temp=keep_temp,
                log=self.log_queue.put,
            )
            self.log_queue.put(("done", "PDF 已生成", final_path))
        except Exception as exc:
            self.log_queue.put(("error", "导出失败", str(exc)))

    def _run_pdf_to_docx(self, input_pdf, output_docx):
        try:
            final_path = convert_pdf_to_docx(input_pdf, output_docx, log=self.log_queue.put)
            self.log_queue.put(("done", "DOCX 已生成", final_path))
        except Exception as exc:
            self.log_queue.put(("error", "转换失败", str(exc)))

    def _drain_log_queue(self):
        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if isinstance(item, tuple) and item[0] == "done":
                _, title, path = item
                self._log(f"完成：{path}")
                self._set_buttons_state(tk.NORMAL)
                messagebox.showinfo("完成", f"{title}：\n{path}")
            elif isinstance(item, tuple) and item[0] == "error":
                _, title, message = item
                self._log(f"错误：{message}")
                self._set_buttons_state(tk.NORMAL)
                messagebox.showerror(title, message)
            else:
                self._log(str(item))

        self.after(100, self._drain_log_queue)

    def _log(self, message):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)


if __name__ == "__main__":
    WebToPdfApp().mainloop()
