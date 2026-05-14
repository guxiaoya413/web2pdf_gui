import argparse
from pathlib import Path

from core import export_urls_to_pdf, parse_urls


def main():
    parser = argparse.ArgumentParser(description="把链接列表导出为一个 PDF。")
    parser.add_argument("input", help="包含链接的文本文件。")
    parser.add_argument("-o", "--output", default="网页文档.pdf", help="输出 PDF 路径。")
    parser.add_argument("--wait-ms", type=int, default=2000, help="每个页面加载后的额外等待时间。")
    parser.add_argument("--scale", type=float, default=0.8, help="PDF 渲染缩放比例。")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时分页 PDF 文件。")
    args = parser.parse_args()

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
