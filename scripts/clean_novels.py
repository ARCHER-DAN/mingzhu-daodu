"""四大名著清洗——转码、分回目、去前言、输出到 data/"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

NOVELS = {
    '西游记': {'file': '西游记.txt', 'enc': 'utf-8'},
    '三国演义': {'file': '三国演义.txt', 'enc': 'utf-8'},
    '水浒传': {'file': '水浒传.txt', 'enc': 'gb18030'},
    '红楼梦': {'file': '红楼梦.txt', 'enc': 'utf-8'},
}

# 回目标题：匹配「第X回 标题」或「第X回：标题」
CHAPTER_PAT = re.compile(
    r'^第[一二三四五六七八九十百千\d]+回[\s：:]+(.+)$', re.MULTILINE
)


def clean_text(text: str) -> str:
    """去除前言、简介、版权声明等"""
    # 找第一个回目位置
    m = CHAPTER_PAT.search(text)
    if m:
        text = text[m.start():]
    # 去多余的空白行
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip()


def split_chapters(text: str) -> list[tuple[str, str]]:
    """返回 [(回目标题, 正文), ...]"""
    matches = list(CHAPTER_PAT.finditer(text))
    if not matches:
        return [(text[:50], text)]

    chapters = []
    for i, m in enumerate(matches):
        title = m.group(0).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if len(body) > 50:  # 过滤空章节
            chapters.append((title, body))
    return chapters


def fix_gbk_file(path: str) -> str:
    """读取GBK文件，转UTF-8写入，返回新路径"""
    import tempfile
    with open(path, encoding='gbk') as f:
        content = f.read()
    new_path = path.replace('.txt', '_utf8.txt')
    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return new_path


def process_novel(name: str, config: dict):
    """处理单部名著"""
    fpath = os.path.join(ROOT, config['file'])
    enc = config['enc']

    # 读取文件
    text = None
    for e in [enc, 'gb18030', 'gbk', 'utf-8']:
        try:
            with open(fpath, encoding=e, errors='replace') as f:
                text = f.read()
            break
        except:
            continue
    if text is None:
        raise RuntimeError(f'无法读取 {fpath}')

    # 清洗
    text = clean_text(text)
    chapters = split_chapters(text)

    # 输出目录
    out_dir = os.path.join(DATA, name, '01_原著原文')
    os.makedirs(out_dir, exist_ok=True)

    # 写入各回
    for i, (title, body) in enumerate(chapters, 1):
        # 从title提取回目描述
        desc = re.sub(r'^第[一二三四五六七八九十百千\d]+回[：:\s]*', '', title)
        if not desc:
            desc = title
        fname = f'第{i:03d}回_{desc[:30]}.txt'
        fname = re.sub(r'[\\/:*?"<>|]', '', fname)
        with open(os.path.join(out_dir, fname), 'w', encoding='utf-8') as f:
            f.write(f'{title}\n\n{body}')

    print(f'{name}: {len(chapters)}回 -> {out_dir}')
    return len(chapters)


if __name__ == '__main__':
    total = 0
    for name, cfg in NOVELS.items():
        total += process_novel(name, cfg)
    print(f'\n清洗完成，共 {total} 回')
