import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core import export_urls_to_pdf, parse_urls


DEFAULT_OUTPUT = "网页文档.pdf"
EXAMPLE_URLS = """https://help.tdx.com.cn/quant/docs/markdown/mindoc-1cfsjkbf8f3is
https://help.tdx.com.cn/quant/docs/markdown/mindoc-1h1525ci3mnkc/mindoc-1h1526nmnk5n4.html"""


class WebToPdfApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("链接列表转 PDF")
        self.geometry("920x680")
        self.minsize(760, 560)

        self.log_queue = queue.Queue()
        self.worker = None
        self.output_var = tk.StringVar(value=str(Path.cwd() / DEFAULT_OUTPUT))
        self.keep_temp_var = tk.BooleanVar(value=False)
        self.wait_var = tk.IntVar(value=2000)
        self.scale_var = tk.DoubleVar(value=0.8)

        self._build_ui()
        self.after(100, self._drain_log_queue)

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(5, weight=1)

        ttk.Label(root, text="链接列表（可直接粘贴 Python/JS 列表片段）").grid(row=0, column=0, sticky="w")
        self.url_text = tk.Text(root, height=14, wrap=tk.NONE, undo=True)
        self.url_text.insert("1.0", EXAMPLE_URLS)
        self.url_text.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(6, 12))

        output_frame = ttk.Frame(root)
        output_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        ttk.Label(output_frame, text="输出 PDF").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(output_frame, textvariable=self.output_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(output_frame, text="浏览", command=self._browse_output).grid(row=0, column=2, padx=(8, 0))

        options = ttk.Frame(root)
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

        actions = ttk.Frame(root)
        actions.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self.run_button = ttk.Button(actions, text="生成 PDF", command=self._start)
        self.run_button.pack(side=tk.LEFT)
        ttk.Button(actions, text="清空日志", command=self._clear_log).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(root, text="日志").grid(row=5, column=0, sticky="sw")
        self.log_text = tk.Text(root, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(6, 0))

    def _browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="保存 PDF",
            defaultextension=".pdf",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
            initialfile=DEFAULT_OUTPUT,
        )
        if filename:
            self.output_var.set(filename)

    def _start(self):
        if self.worker and self.worker.is_alive():
            return

        urls = parse_urls(self.url_text.get("1.0", tk.END))
        if not urls:
            messagebox.showerror("没有识别到链接", "请至少输入或粘贴一个 http/https 链接。")
            return

        output_path = self.output_var.get().strip()
        if not output_path:
            messagebox.showerror("没有输出路径", "请选择输出 PDF 的保存位置。")
            return

        self.run_button.configure(state=tk.DISABLED)
        self._log(f"已识别 {len(urls)} 个链接。")
        self._log(f"开始导出 {len(urls)} 个页面。")

        self.worker = threading.Thread(
            target=self._run_export,
            args=(urls, output_path, self.wait_var.get(), self.scale_var.get(), self.keep_temp_var.get()),
            daemon=True,
        )
        self.worker.start()

    def _run_export(self, urls, output_path, wait_ms, scale, keep_temp):
        try:
            final_path = export_urls_to_pdf(
                urls,
                output_path,
                wait_ms=wait_ms,
                scale=scale,
                keep_temp=keep_temp,
                log=self.log_queue.put,
            )
            self.log_queue.put(("done", final_path))
        except Exception as exc:
            self.log_queue.put(("error", str(exc)))

    def _drain_log_queue(self):
        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if isinstance(item, tuple) and item[0] == "done":
                self._log(f"完成：{item[1]}")
                self.run_button.configure(state=tk.NORMAL)
                messagebox.showinfo("完成", f"PDF 已生成：\n{item[1]}")
            elif isinstance(item, tuple) and item[0] == "error":
                self._log(f"错误：{item[1]}")
                self.run_button.configure(state=tk.NORMAL)
                messagebox.showerror("导出失败", item[1])
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
