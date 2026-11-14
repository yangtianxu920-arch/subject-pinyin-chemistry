#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包：生成可以发给别人 / 传到手机的压缩包，输出到 dist/

    python tools/package.py [--rime-dir <已装好雾凇和化学拼音的 Rime 用户目录>]

    dist/化学拼音-完整包.zip      雾凇拼音 + 化学拼音，解压即用
    dist/化学拼音-仅化学词库.zip  只有本项目 rime/ 下的文件
"""
import argparse
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"build", "sync", ".git"}
SKIP_FILES = {"installation.yaml", "user.yaml", "weasel.custom.yaml", "squirrel.custom.yaml"}

NOTE = """化学拼音 · 安装说明
====================

这是一套 Rime 输入法配置：雾凇拼音（日常）+ 化学拼音（化学生僻字、术语、化学式、符号）。

【完整包】化学拼音-完整包.zip：含雾凇拼音，解压即用。
【仅化学】化学拼音-仅化学词库.zip：已经在用雾凇拼音的人用这个，
          解压后还要在 default.custom.yaml 的 schema_list 里加一行  - schema: chem_pinyin

一、电脑
  Windows：安装「小狼毫」 https://rime.im/download/
           把压缩包里的全部内容解压到  %APPDATA%/Rime
           右键任务栏小狼毫图标 →「重新部署」，等一两分钟
  macOS：  安装「鼠须管」，解压到  ~/Library/Rime ，然后重新部署

二、iPhone / iPad
  App Store 安装「仓输入法」，在 App 里把压缩包导入为输入方案
  （或用它的文件管理把内容放进 Rime 目录），然后重新部署，
  在输入方案列表里勾选「化学拼音」。

三、安卓
  安装「小企鹅输入法」和它的 Rime 插件（或「同文输入法」），
  把压缩包内容解压到该 App 的 Rime 用户目录（在 App 设置里能看到路径），然后重新部署。

四、使用
  Ctrl+` 或 F4（手机上是 App 的方案切换键）在「雾凇拼音」和「化学拼音」之间切换。
  qiangji → 羟基      sheshidu → ℃        liusuan → 硫酸 / H₂SO₄
  H2SO4 → H₂SO₄      Fe3+ → Fe³⁺         vhx → 化学符号面板
  vhxdw → 单位面板    vlizi → 常见离子

雾凇拼音来自 https://github.com/iDvel/rime-ice （GPL-3.0）。
"""

DEFAULT_CUSTOM = """patch:
  schema_list:
    - schema: rime_ice       # 雾凇拼音
    - schema: chem_pinyin    # 化学拼音
"""


def add_tree(z, base):
    n = 0
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith(".userdb")]
        for f in files:
            if f in SKIP_FILES or f.endswith((".bin", ".log", ".pyc")):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, base).replace(os.sep, "/"))
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    default_dir = os.path.join(os.environ.get("APPDATA", ""), "Rime")
    ap.add_argument("--rime-dir", default=default_dir)
    a = ap.parse_args()
    out = os.path.join(ROOT, "dist")
    os.makedirs(out, exist_ok=True)

    if not os.path.isfile(os.path.join(a.rime_dir, "rime_ice.schema.yaml")):
        raise SystemExit(f"{a.rime_dir} 里没有雾凇拼音，无法打完整包")

    full = os.path.join(out, "化学拼音-完整包.zip")
    with zipfile.ZipFile(full, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        n = add_tree(z, a.rime_dir)
        names = set(z.namelist())
        # 以项目里的版本为准
        for root, _, files in os.walk(os.path.join(ROOT, "rime")):
            for f in files:
                p = os.path.join(root, f)
                arc = os.path.relpath(p, os.path.join(ROOT, "rime")).replace(os.sep, "/")
                if arc not in names:
                    z.write(p, arc)
                    n += 1
        if "default.custom.yaml" not in names:
            z.writestr("default.custom.yaml", DEFAULT_CUSTOM)
        z.writestr("安装说明.txt", NOTE)
    print(f"{full}  {n} 个文件  {os.path.getsize(full) / 1e6:.1f} MB")

    chem = os.path.join(out, "化学拼音-仅化学词库.zip")
    with zipfile.ZipFile(chem, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        n = add_tree(z, os.path.join(ROOT, "rime"))
        z.writestr("安装说明.txt", NOTE)
    print(f"{chem}  {n} 个文件  {os.path.getsize(chem) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
