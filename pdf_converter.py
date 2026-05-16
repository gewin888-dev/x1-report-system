#!/usr/bin/env python3
"""docx → PDF 转换工具（macOS Pages.app）"""

import subprocess
from pathlib import Path

from config_loader import load_x1_config

BASE_DIR = Path(__file__).resolve().parent
CFG = load_x1_config(BASE_DIR)
HOST_MODE = str(CFG.get('host_mode', 'desktop') or 'desktop').strip().lower()


def convert_docx_to_pdf(docx_path: str, pdf_path: str = None) -> str:
    """将 docx 文件转换为 PDF。
    
    Args:
        docx_path: 源 docx 文件路径
        pdf_path: 目标 PDF 路径（默认与 docx 同目录同名）
    
    Returns:
        生成的 PDF 文件路径，失败返回空字符串
    """
    src = Path(docx_path)
    if not src.exists():
        return ''
    
    if pdf_path:
        dst = Path(pdf_path)
    else:
        dst = src.with_suffix('.pdf')
    
    dst.parent.mkdir(parents=True, exist_ok=True)

    if HOST_MODE != 'desktop':
        print('[pdf_converter] server 模式下禁用 Pages PDF 转换')
        return ''

    script = f'''
set inputFile to POSIX file "{src}"
set outputFile to POSIX file "{dst}"
tell application "Pages"
    open inputFile
    delay 1
    export front document to outputFile as PDF
    close front document saving no
end tell
'''
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
            return str(dst)
        else:
            print(f"[pdf_converter] Failed: {result.stderr.strip()}")
            return ''
    except subprocess.TimeoutExpired:
        print("[pdf_converter] Timeout converting to PDF")
        return ''
    except Exception as e:
        print(f"[pdf_converter] Error: {e}")
        return ''


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_converter.py <input.docx> [output.pdf]")
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    result = convert_docx_to_pdf(src, dst)
    if result:
        print(f"✅ {result}")
    else:
        print("❌ Conversion failed")
        sys.exit(1)
