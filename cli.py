import argparse
from pathlib import Path

from core import convert_pdf_to_docx, export_urls_to_pdf, parse_urls


DEFAULT_OUTPUT = "网页文档.pdf"


def main():
    parser = argparse.ArgumentParser(description="网页转 PDF，或把 PDF 转为 DOCX。")
    parser.add_argument("input", help="包含链接的文本文件；使用 --pdf-to-docx 时为输入 PDF。")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help="输出路径。")
    parser.add_argument("--wait-ms", type=int, default=2000, help="每个页面加载后的额外等待时间。")
    parser.add_argument("--scale", type=float, default=0.8, help="PDF 渲染缩放比例。")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时分页 PDF 文件。")
    parser.add_argument("--pdf-to-docx", action="store_true", help="把输入 PDF 转换为 DOCX。")
    args = parser.parse_args()

    if args.pdf_to_docx:
        output_path = args.output
        if output_path == DEFAULT_OUTPUT:
            output_path = str(Path(args.input).with_suffix(".docx"))
        output = convert_pdf_to_docx(args.input, output_path, log=print)
        print(f"DOCX 已生成：{output}")
        return

    input_text = Path(args.input).read_text(encoding="utf-8")
    urls = parse_urls(input_text)
    output = export_urls_to_pdf(
        urls,
        args.output,
        wait_ms=args.wait_ms,
        scale=args.scale,
        keep_temp=args.keep_temp,
        log=print,
    )
    print(f"PDF 已生成：{output}")


if __name__ == "__main__":
    main()
