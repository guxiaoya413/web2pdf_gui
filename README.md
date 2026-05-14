# 链接列表转 PDF

一个小型桌面工具：把一组网页链接批量导出并合并成一个 PDF。

适合文档站点、API 页面、教程页面等场景。工具会保留顶部 logo/header，隐藏侧栏和目录，优化长代码块换行，并避免每个页面首页顶部内容被遮挡。

## 功能

- 直接粘贴链接，也支持 Python/JavaScript 风格的链接列表片段。
- 将多个网页导出并合并成一个 A4 PDF。
- 保留网站顶部 logo/header，同时避免遮挡正文。
- 隐藏侧栏和目录区域，扩大正文宽度。
- 长代码块自动换行，避免超出页面。
- 如果目标 PDF 正在打开，会自动生成带时间戳的新文件名。
- 同时支持图形界面和命令行。

## 安装

推荐 Python 3.10+。

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## 启动图形界面

```bash
python app.py
```

Windows 用户也可以双击 `run_gui.bat`。

把链接粘贴到输入框，选择输出 PDF 路径，然后点击 `生成 PDF`。

## 命令行使用

```bash
python cli.py urls.example.txt -o output.pdf
```

常用参数：

```bash
python cli.py urls.example.txt -o output.pdf --wait-ms 3000 --scale 0.8
```

## 链接输入格式

工具会自动从粘贴内容中提取 `http://` 和 `https://` 链接。可以一行一个链接，也可以直接复制代码里的链接列表片段。

```text
# docs
https://example.com/page-1
https://example.com/page-2
```

```text
'https://example.com/page-1',
"https://example.com/page-2"; # comments are OK
```

## 注意事项

- 如果目标 PDF 正被阅读器打开，工具会自动写入带时间戳的新文件名，例如 `网页文档_20260514_160059.pdf`。
- 如果页面内容加载较慢，可以调大 `加载后等待（毫秒）`。
- 如果内容太宽，可以适当调低 `缩放`。
