#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学科输入法 · 词库生成脚本

读取 data/ 下的源表，结合雾凇拼音（rime-ice）现有词频，生成 rime/ 下的词库：
    rime/chem_pinyin.dict.yaml          主词库（挂载雾凇词库 + 化学词库）
    rime/xueke/chem_chars.dict.yaml     化学单字（提升字频）
    rime/xueke/chem_terms.dict.yaml     化学术语
    rime/xueke/chem_symbols.dict.yaml   符号、单位、化学式

用法：
    python tools/build.py --rime-ice <雾凇拼音目录>

<雾凇拼音目录> 是含有 rime_ice.dict.yaml 和 cn_dicts/ 的目录，
可以是 rime-ice 仓库，也可以是已装好雾凇的 Rime 用户目录。
不指定时会依次尝试 %APPDATA%\\Rime 和 ~/Library/Rime。

依赖：pip install pypinyin
"""
import argparse
import datetime
import os
import re
import sys
from collections import defaultdict

try:
    from pypinyin import lazy_pinyin
except ImportError:
    sys.exit("缺少依赖：请先运行  pip install pypinyin")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "rime")

# 单字档位 → 目标名次（在同音字中排第几）
TIER_RANK = {1: 2, 2: 4, 3: 7}
# 同音词里"日常高频词"的门槛：高于它的不去抢第一，只排到它后面
COMMON_WORD = 100000
DEFAULT_TERM_WEIGHT = 5000
DEFAULT_SYMBOL_WEIGHT = 3000

HAN = re.compile(
    r"[㐀-䶿一-鿿\U00020000-\U0002ebef\U00030000-\U0003134f]"
)
SUB = str.maketrans("0123456789+-", "₀₁₂₃₄₅₆₇₈₉₊₋")
SUP = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


# ───────────────────────── 读取雾凇词库 ─────────────────────────
def read_dict_body(path):
    """读 .dict.yaml 的词条部分，返回 [(text, code, weight)]"""
    rows = []
    body = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not body:
                if line.strip() == "...":
                    body = True
                continue
            if not line or line.startswith("#"):
                continue
            p = line.split("\t")
            if len(p) < 2:
                continue
            w = 0
            if len(p) > 2:
                try:
                    w = int(float(p[2]))
                except ValueError:
                    w = 0
            rows.append((p[0], p[1], w))
    return rows


def find_rime_ice(arg):
    cands = [arg] if arg else []
    if os.environ.get("APPDATA"):
        cands.append(os.path.join(os.environ["APPDATA"], "Rime"))
    cands.append(os.path.expanduser("~/Library/Rime"))
    cands.append(os.path.expanduser("~/.local/share/fcitx5/rime"))
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "cn_dicts", "8105.dict.yaml")):
            return c
    sys.exit(
        "找不到雾凇拼音词库。请用 --rime-ice 指定含有 cn_dicts/8105.dict.yaml 的目录。"
    )


# ───────────────────────── 读取源表 ─────────────────────────
def read_lines(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                yield line


def load_chars():
    chars = []  # (字, 拼音, 档位)
    for line in read_lines("chars.txt"):
        p = line.split()
        if len(p) != 3:
            sys.exit(f"chars.txt 格式错误：{line}")
        chars.append((p[0], p[1], int(p[2])))
    return chars


def load_terms():
    terms = []  # (词, 指定拼音或 None)
    for line in read_lines("terms.txt"):
        for tok in line.split():
            if "=" in tok:
                w, py = tok.split("=", 1)
                terms.append((w, py.replace("_", " ")))
            else:
                terms.append((tok, None))
    return terms


def load_formulas():
    out = []
    for line in read_lines("formulas.txt"):
        p = line.split()
        if len(p) != 2:
            sys.exit(f"formulas.txt 格式错误：{line}")
        out.append((p[0], p[1]))
    return out


def load_symbols():
    out = []
    for line in read_lines("symbols.txt"):
        p = line.split()
        if len(p) < 2:
            sys.exit(f"symbols.txt 格式错误：{line}")
        out.append((p[0], p[1:]))
    return out


# ───────────────────────── 工具 ─────────────────────────
def pretty_formula(s):
    """H2SO4 → H₂SO₄ ；SO4^2- → SO₄²⁻ ；CuSO4.5H2O → CuSO₄·5H₂O"""
    charge = ""
    if "^" in s:
        s, charge = s.split("^", 1)
        if charge in ("+", "-"):
            charge = charge.translate(SUP)
        else:
            charge = charge.translate(SUP)
    out = []
    prev = ""
    for ch in s:
        if ch == ".":
            out.append("·")
        elif ch.isdigit() and (prev.isalpha() or prev in ")]" or prev.isdigit() and out[-1] in "₀₁₂₃₄₅₆₇₈₉"):
            out.append(ch.translate(SUB))
        else:
            out.append(ch)
        prev = ch
    return "".join(out) + charge


class Pinyin:
    def __init__(self, chars):
        self.force = {}
        for ch, py, _ in chars:
            self.force.setdefault(ch, py)  # 第一个读音为化学读音

    def code(self, word):
        han = "".join(HAN.findall(word))
        if not han:
            return None
        pys = lazy_pinyin(han, errors=lambda x: ["?"] * len(x))
        if len(pys) != len(han):
            return None
        res = []
        for ch, py in zip(han, pys):
            py = self.force.get(ch, py)
            if not re.fullmatch(r"[a-z]+", py):
                return None
            res.append(py)
        return " ".join(res)


def is_codable(word):
    """词里除了汉字只允许连字符和间隔号"""
    rest = HAN.sub("", word)
    return all(c in "-·－—" for c in rest)


def write_dict(path, name, title, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    today = datetime.date.today().isoformat()
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# {title}\n")
        f.write("# 本文件由 tools/build.py 自动生成，请修改 data/ 下的源表后重新生成。\n")
        f.write("---\n")
        f.write(f"name: {name}\n")
        f.write(f'version: "{today}"\n')
        f.write("sort: by_weight\n")
        f.write("...\n")
        for text, code, w in rows:
            f.write(f"{text}\t{code}\t{w}\n")


# ───────────────────────── 主流程 ─────────────────────────
def main():
    ap = argparse.ArgumentParser(description="生成化学拼音词库")
    ap.add_argument("--rime-ice", help="雾凇拼音目录")
    ap.add_argument("--report", action="store_true", help="输出多音字复查清单")
    args = ap.parse_args()
    ice = find_rime_ice(args.rime_ice)
    print(f"雾凇拼音目录：{ice}")

    # 现有字频、词频
    char_rows = read_dict_body(os.path.join(ice, "cn_dicts", "8105.dict.yaml"))
    syl_chars = defaultdict(dict)  # 音节 → {字: 权重}
    for t, c, w in char_rows:
        syl_chars[c][t] = max(w, syl_chars[c].get(t, 0))
    word_w = {}  # (词, 码) → 权重
    code_words = defaultdict(dict)  # 码 → {词: 权重}
    for fn in ("base", "ext"):
        p = os.path.join(ice, "cn_dicts", fn + ".dict.yaml")
        if not os.path.isfile(p):
            continue
        for t, c, w in read_dict_body(p):
            if (t, c) not in word_w or w > word_w[(t, c)]:
                word_w[(t, c)] = w
                code_words[c][t] = w

    chars = load_chars()
    py = Pinyin(chars)

    # 1) 单字
    char_out = []
    bumped = defaultdict(int)
    for ch, syl, tier in chars:
        existing = syl_chars[syl].get(ch, 0)
        others = sorted(
            (w for c, w in syl_chars[syl].items() if c != ch), reverse=True
        )
        rank = TIER_RANK[tier]
        # 刚好超过目前排在第 rank 位的字
        if len(others) >= rank:
            target = others[rank - 1] + 10 - bumped[(syl, tier)]
        else:
            target = (others[-1] if others else 100) + 10
        bumped[(syl, tier)] += 1
        w = max(existing, target, 1)
        char_out.append((ch, syl, w))

    # 2) 术语
    def term_weight(word, code):
        own = word_w.get((word, code), 0)
        top = max((w for t, w in code_words[code].items() if t != word), default=0)
        if top == 0:
            return max(own, DEFAULT_TERM_WEIGHT)
        if top > COMMON_WORD:
            return max(own, int(top * 0.9))
        return max(own, int(top * 1.2) + 100)

    term_out = {}
    skipped = []
    fixed = []
    unknown_codes = {}
    word_codes = defaultdict(set)
    for (t, c) in word_w:
        word_codes[t].add(c)
    formulas = load_formulas()
    all_terms = load_terms() + [(n, None) for n, _ in formulas]
    for word, given in all_terms:
        if len(HAN.findall(word)) < 2:
            continue  # 单字由 chars.txt 负责
        if not is_codable(word):
            skipped.append(word)
            continue
        code = given or py.code(word)
        if not given and code:
            # 雾凇已收录且读音唯一的词，以雾凇的注音为准（人工校对过）
            known = word_codes.get(word)
            if known and len(known) == 1 and code not in known:
                fixed.append(f"{word}: {code} → {next(iter(known))}")
                code = next(iter(known))
            elif not known:
                unknown_codes[word] = code
        if not code or len(code.split()) != len(HAN.findall(word)):
            skipped.append(word)
            continue
        key = (word, code)
        if key not in term_out:
            term_out[key] = term_weight(word, code)
    # 让后面算符号权重时能看到新词
    for (word, code), w in term_out.items():
        code_words[code][word] = max(w, code_words[code].get(word, 0))

    # 3) 符号、化学式
    sym_out = {}
    sym_per_code = defaultdict(int)

    def add_symbol(sym, name, ratio):
        if len(HAN.findall(name)) < 2:
            return
        code = None
        for (t, c) in term_out:  # 名称若在词表里指定过读音，沿用
            if t == name:
                code = c
                break
        code = code or py.code(name)
        if not code:
            skipped.append(f"{sym}←{name}")
            return
        # 名称本身是词：排在名称后面；否则排在同音词里最高的那个后面
        ref = code_words[code].get(name) or max(code_words[code].values(), default=0)
        w = max(int(ref * ratio), 100) if ref else DEFAULT_SYMBOL_WEIGHT
        w = min(w, 60000)  # 符号不参与抢高频词的位置，也减少对整句的干扰
        w = max(w - sym_per_code[code], 1)  # 同码的多个符号按源表顺序排
        sym_per_code[code] += 1
        key = (sym, code)
        if key not in sym_out:
            sym_out[key] = w

    for sym, names in load_symbols():
        for n in names:
            add_symbol(sym, n, 0.8)
    for name, f in formulas:
        add_symbol(pretty_formula(f), name, 0.5)

    # 输出
    def rows(d):
        return [(t, c, w) for (t, c), w in sorted(d.items(), key=lambda x: (-x[1], x[0]))]

    write_dict(
        os.path.join(OUT, "xueke", "chem_chars.dict.yaml"),
        "chem_chars", "学科输入法 · 化学单字", char_out,
    )
    write_dict(
        os.path.join(OUT, "xueke", "chem_terms.dict.yaml"),
        "chem_terms", "学科输入法 · 化学术语", rows(term_out),
    )
    write_dict(
        os.path.join(OUT, "xueke", "chem_symbols.dict.yaml"),
        "chem_symbols", "学科输入法 · 符号 / 单位 / 化学式", rows(sym_out),
    )
    write_main_dict(ice)

    new_terms = [t for (t, c) in term_out if (t, c) not in word_w]
    print(f"单字 {len(char_out)}，术语 {len(term_out)}（其中雾凇原本没有的 {len(new_terms)}），"
          f"符号/化学式 {len(sym_out)}")
    if skipped:
        print(f"跳过 {len(skipped)} 条（含字母数字或无法注音）：{' '.join(skipped)}")
    if args.report:
        risky = set("重率薄给长相色强还散载着调量行和结降称解壳核单粘朝曾传乐卡折都合没为系石大似空参分干更发间倒当处冲差中种转数少度得地佛")
        print("\n── 多音字复查清单（请人工确认读音）──")
        print("（按雾凇注音修正的词：" + "；".join(fixed) + "）")
        for t, c in sorted(unknown_codes.items()):
            if set(t) & risky:
                print(f"{t}\t{c}")


def write_main_dict(ice):
    """生成 chem_pinyin.dict.yaml：沿用用户的雾凇词库挂载列表，把化学词库放在最前面"""
    src = os.path.join(ice, "rime_ice.dict.yaml")
    tables, body = [], []
    in_body = False
    in_tables = False
    with open(src, encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\n")
            if in_body:
                body.append(s)
                continue
            if s.strip() == "...":
                in_body = True
                continue
            if s.startswith("import_tables:"):
                in_tables = True
                continue
            if in_tables:
                m = re.match(r"\s+-\s+([^\s#]+)", s)
                if m:
                    tables.append(m.group(1))
                elif s and not s.startswith(" ") and not s.startswith("#"):
                    in_tables = False
    today = datetime.date.today().isoformat()
    path = os.path.join(OUT, "chem_pinyin.dict.yaml")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 学科输入法 · 化学拼音 主词库\n")
        f.write("# 本文件由 tools/build.py 自动生成。\n")
        f.write("# 有重复词条时最上面的权重生效，所以化学词库放在雾凇词库前面。\n")
        f.write("---\n")
        f.write("name: chem_pinyin\n")
        f.write(f'version: "{today}"\n')
        f.write("import_tables:\n")
        for t in ["xueke/chem_chars", "xueke/chem_terms", "xueke/chem_symbols"] + tables:
            f.write(f"  - {t}\n")
        f.write("...\n")
        f.write("\n".join(body).rstrip("\n") + "\n")


if __name__ == "__main__":
    main()
