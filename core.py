import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


PRINT_CLEANUP_CSS = """
@media screen, print {
    .sidebar,
    aside,
    .menu-container,
    .docs-menu,
    #toc,
    .table-of-contents {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        visibility: hidden !important;
    }

    header,
    header.navbar,
    .navbar,
    .navbar-header,
    .docs-header {
        display: block !important;
        visibility: visible !important;
        position: static !important;
        top: auto !important;
        left: auto !important;
        right: auto !important;
        width: 100% !important;
        height: auto !important;
        min-height: 3.6rem !important;
        overflow: visible !important;
        z-index: auto !important;
        transform: none !important;
    }

    html,
    body,
    #app,
    .theme-container {
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        max-width: none !important;
        overflow: visible !important;
    }

    .page,
    main,
    article,
    .docs-content,
    .content-wrapper,
    .theme-default-content,
    .content__default {
        box-sizing: border-box !important;
        margin: 0 !important;
        padding: 0 50px !important;
        left: 0 !important;
        right: auto !important;
        top: 0 !important;
        width: 100% !important;
        max-width: none !important;
        transform: none !important;
    }

    .theme-default-content,
    .content__default {
        padding-top: 8mm !important;
    }

    pre,
    code {
        white-space: pre-wrap !important;
        word-break: break-word !important;
        overflow-wrap: anywhere !important;
        max-width: 100% !important;
    }
}
"""


def parse_urls(text):
    urls = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for match in re.finditer(r"https?://[^\s'\",;]+", line):
            url = match.group(0).rstrip(".,;，；'\"")
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def apply_print_cleanup(page):
    page.add_style_tag(content=PRINT_CLEANUP_CSS)
    page.evaluate(
        """
        () => {
            document.querySelectorAll('body *').forEach(el => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                const isTopOverlay =
                    (style.position === 'fixed' || style.position === 'sticky') &&
                    rect.top <= 90 &&
                    rect.height > 0 &&
                    rect.width > 100;

                const isHeader = el.matches('header, header.navbar, .navbar, .navbar-header, .docs-header');

                if (isTopOverlay && !isHeader) {
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('visibility', 'hidden', 'important');
                    el.style.setProperty('height', '0', 'important');
                    el.style.setProperty('overflow', 'hidden', 'important');
                } else if (isHeader) {
                    el.style.setProperty('display', 'block', 'important');
                    el.style.setProperty('visibility', 'visible', 'important');
                    el.style.setProperty('position', 'static', 'important');
                    el.style.setProperty('width', '100%', 'important');
                    el.style.setProperty('height', 'auto', 'important');
                    el.style.setProperty('overflow', 'visible', 'important');
                }
            });

            document.querySelectorAll('pre, code').forEach(el => {
                el.style.setProperty('white-space', 'pre-wrap', 'important');
                el.style.setProperty('word-break', 'break-word', 'important');
                el.style.setProperty('overflow-wrap', 'anywhere', 'important');
                el.style.setProperty('max-width', '100%', 'important');
            });
        }
        """
    )


def pick_output_path(preferred_path):
    preferred = Path(preferred_path)
    preferred.parent.mkdir(parents=True, exist_ok=True)
    if not preferred.exists():
        return str(preferred)

    try:
        with open(preferred, "ab"):
            pass
        return str(preferred)
    except OSError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(preferred.with_name(f"{preferred.stem}_{timestamp}{preferred.suffix}"))


def merge_pdf_files(pdf_paths, output_path):
    try:
        from pypdf import PdfWriter

        writer = PdfWriter()
        for pdf_path in pdf_paths:
            writer.append(pdf_path)
        with open(output_path, "wb") as output_file:
            writer.write(output_file)
        writer.close()
        return
    except ImportError:
        pdfunite = shutil.which("pdfunite")
        if pdfunite:
            subprocess.run([pdfunite, *pdf_paths, output_path], check=True)
            return
        raise RuntimeError("缺少 PDF 合并依赖，请运行：pip install pypdf") from None


def merge_with_fallback_name(pdf_paths, preferred_path, log=None):
    output_path = pick_output_path(preferred_path)
    if output_path != preferred_path and log:
        log(f"目标 PDF 正在被占用，改为生成：{output_path}")

    try:
        merge_pdf_files(pdf_paths, output_path)
        return output_path
    except (OSError, subprocess.CalledProcessError):
        if output_path != preferred_path:
            raise
        preferred = Path(preferred_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(preferred.with_name(f"{preferred.stem}_{timestamp}{preferred.suffix}"))
        if log:
            log(f"目标 PDF 写入失败，改为生成：{output_path}")
        merge_pdf_files(pdf_paths, output_path)
        return output_path


def export_urls_to_pdf(
    urls,
    output_path,
    *,
    wait_ms=2000,
    scale=0.8,
    keep_temp=False,
    log=None,
):
    if not urls:
        raise ValueError("没有提供链接。")

    temp_dir_obj = tempfile.TemporaryDirectory(prefix="web2pdf_")
    temp_dir = Path(temp_dir_obj.name)
    pdf_paths = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()

            for index, url in enumerate(urls, start=1):
                if log:
                    log(f"[{index}/{len(urls)}] 正在加载 {url}")
                page.goto(url, wait_until="networkidle", timeout=90000)
                page.wait_for_timeout(wait_ms)
                apply_print_cleanup(page)

                pdf_path = temp_dir / f"page_{index:04d}.pdf"
                page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "15mm", "bottom": "15mm", "left": "10mm", "right": "10mm"},
                    scale=scale,
                )
                pdf_paths.append(str(pdf_path))

            browser.close()

        if log:
            log("正在合并 PDF...")
        final_output = merge_with_fallback_name(pdf_paths, output_path, log=log)
        if log:
            log(f"已生成：{final_output}")
        return final_output
    finally:
        if keep_temp:
            if log:
                log(f"临时分页 PDF 已保留在：{temp_dir}")
        else:
            temp_dir_obj.cleanup()
