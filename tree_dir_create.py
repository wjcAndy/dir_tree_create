#!/usr/bin/env python3
"""
dir_create.py — 从 tree 命令输出创建目录结构
用法: python dir_create.py <tree.txt> <target_dir>
"""

import sys
import os
import re

# tree 命令使用的所有绘制字符
TREE_CHARS = set("│├└─┐┘┬┴┼")

def strip_tree_prefix(line: str) -> tuple[str, bool]:
    """
    去掉行首的 tree 绘制前缀，返回 (清理后的名称, 是否是目录)。

    tree 输出示例:
        ├── dir_name/
        │   └── sub_dir/
        └── file.txt
    """
    original = line.rstrip()
    if not original:
        return "", False

    # 逐字符扫描，跳过所有 tree 绘制字符和空白
    i = 0
    while i < len(original):
        ch = original[i]
        if ch in TREE_CHARS or ch in (' ', '\t'):
            i += 1
        else:
            break

    name = original[i:].strip()
    if not name:
        return "", False

    # 有些 tree 输出用 / 结尾表示目录
    is_dir = name.endswith("/")
    if is_dir:
        name = name[:-1]

    return name, is_dir


def infer_is_dir(name: str, next_line_indent: int, current_indent: int) -> bool:
    """如果下一行缩进更深，说明当前行是目录"""
    return next_line_indent > current_indent


def get_indent_level(line: str) -> int:
    """计算行的实际缩进层级（用于判断父子关系）"""
    # 把所有 tree 字符替换为空格来计算缩进深度
    normalized = ""
    for ch in line:
        if ch in TREE_CHARS:
            normalized += " "
        else:
            normalized += ch
    # 去掉尾部空白后，前面的空白数代表缩进
    stripped = normalized.rstrip()
    return len(stripped) - len(stripped.lstrip())


def parse_tree_file(filepath: str) -> list[dict]:
    """
    解析 tree 输出文件，返回路径列表。
    每个元素: {"path": "relative/path", "is_dir": bool}
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    # 预处理：提取每行的缩进层级和清理后的名称
    entries = []
    for line in raw_lines:
        stripped = line.rstrip("\n\r")
        if not stripped.strip():
            continue

        indent = get_indent_level(stripped)
        name, is_dir = strip_tree_prefix(stripped)

        if not name:
            continue

        # 跳过 tree 头部的统计行 (e.g., "3 directories, 2 files")
        if re.match(r'^\d+\s+(director|file)', name, re.IGNORECASE):
            continue

        entries.append({
            "name": name,
            "indent": indent,
            "is_dir_hint": is_dir,
        })

    if not entries:
        return []

    # 用栈维护路径层级
    result = []
    stack = []  # [(indent, path)]

    for i, entry in enumerate(entries):
        name = entry["name"]
        indent = entry["indent"]

        # 推断是否是目录：
        # 1. tree 标记了 / 结尾
        # 2. 下一行缩进更深
        # 3. 有扩展名的视为文件，否则视为目录
        next_indent = entries[i + 1]["indent"] if i + 1 < len(entries) else 0
        is_dir = entry["is_dir_hint"] or infer_is_dir(name, next_indent, indent)

        if not is_dir:
            # 根据扩展名再判断一次
            _, ext = os.path.splitext(name)
            if not ext:
                # 无扩展名 + 下一行更深 = 目录
                is_dir = next_indent > indent

        # 弹出栈中缩进 >= 当前的（兄弟或侄子节点）
        while stack and stack[-1][0] >= indent:
            stack.pop()

        # 构建路径
        if stack:
            parent_path = stack[-1][1]
            full_rel = os.path.join(parent_path, name)
        else:
            full_rel = name

        result.append({"path": full_rel, "is_dir": is_dir})

        if is_dir:
            stack.append((indent, full_rel))

    return result


def create_structure(entries: list[dict], target_dir: str):
    """创建目录和文件"""
    os.makedirs(target_dir, exist_ok=True)
    print(f"\n正在创建 → {target_dir}\n")

    dir_count = 0
    file_count = 0

    for entry in entries:
        full_path = os.path.join(target_dir, entry["path"])

        if entry["is_dir"]:
            os.makedirs(full_path, exist_ok=True)
            print(f"  [DIR]  {full_path}")
            dir_count += 1
        else:
            # 确保父目录存在
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            # 创建空文件
            if not os.path.exists(full_path):
                with open(full_path, "w", encoding="utf-8") as f:
                    pass
            print(f"  [FILE] {full_path}")
            file_count += 1

    print(f"\n完成: {dir_count}个目录, {file_count}个文件 已创建。")


def main():
    if len(sys.argv) != 3:
        print("用法: python dir_create.py <tree.txt> <target_directory>")
        print("示例: python dir_create.py project_tree.txt ./my_project")
        sys.exit(1)

    tree_file = sys.argv[1]
    target_dir = sys.argv[2]

    if not os.path.isfile(tree_file):
        print(f"错误: 找不到文件 '{tree_file}'")
        sys.exit(1)

    entries = parse_tree_file(tree_file)

    if not entries:
        print("警告: 未从 tree 文件中解析到任何条目")
        sys.exit(1)

    create_structure(entries, target_dir)


if __name__ == "__main__":
    main()
