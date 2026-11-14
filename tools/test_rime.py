#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无界面测试：用 librime 直接部署配置并查询候选，不需要安装输入法。

用法：
    python tools/test_rime.py --rime-dll <rime.dll> --user-dir <Rime 用户目录> [输入串 ...]

<Rime 用户目录> 里要有雾凇拼音和本项目 rime/ 下的全部文件。
不给输入串时跑内置的检查清单。
"""
import argparse
import ctypes as C
import os
import sys


class Traits(C.Structure):
    _fields_ = [
        ("data_size", C.c_int),
        ("shared_data_dir", C.c_char_p),
        ("user_data_dir", C.c_char_p),
        ("distribution_name", C.c_char_p),
        ("distribution_code_name", C.c_char_p),
        ("distribution_version", C.c_char_p),
        ("app_name", C.c_char_p),
        ("modules", C.POINTER(C.c_char_p)),
        ("min_log_level", C.c_int),
        ("log_dir", C.c_char_p),
        ("prebuilt_data_dir", C.c_char_p),
        ("staging_dir", C.c_char_p),
    ]


class Candidate(C.Structure):
    _fields_ = [("text", C.c_char_p), ("comment", C.c_char_p), ("reserved", C.c_void_p)]


class Iterator(C.Structure):
    _fields_ = [("ptr", C.c_void_p), ("index", C.c_int), ("candidate", Candidate)]


class Rime:
    def __init__(self, dll, user_dir):
        os.add_dll_directory(os.path.dirname(os.path.abspath(dll)))
        self.lib = lib = C.CDLL(os.path.abspath(dll))
        t = Traits()
        t.data_size = C.sizeof(Traits) - C.sizeof(C.c_int)
        d = os.path.abspath(user_dir).encode("utf-8")
        t.shared_data_dir = d
        t.user_data_dir = d
        t.distribution_name = b"xueke-test"
        t.distribution_code_name = b"xueke-test"
        t.distribution_version = b"0.1"
        t.app_name = b"rime.xueke-test"
        t.min_log_level = 2
        t.log_dir = b""
        self.traits = t
        lib.RimeCreateSession.restype = C.c_size_t
        for fn in ("RimeSelectSchema", "RimeSimulateKeySequence", "RimeCandidateListBegin",
                   "RimeCandidateListNext", "RimeCandidateListEnd", "RimeClearComposition",
                   "RimeDestroySession", "RimeGetCurrentSchema"):
            getattr(lib, fn).argtypes = None
        lib.RimeSetup(C.byref(t))
        lib.RimeInitialize(C.byref(t))
        if lib.RimeStartMaintenance(1):
            lib.RimeJoinMaintenanceThread()
        self.sid = C.c_size_t(lib.RimeCreateSession())

    def select(self, schema):
        return bool(self.lib.RimeSelectSchema(self.sid, schema.encode()))

    def candidates(self, keys, n=8):
        lib = self.lib
        lib.RimeClearComposition(self.sid)
        lib.RimeSimulateKeySequence(self.sid, keys.encode("utf-8"))
        it = Iterator()
        out = []
        if lib.RimeCandidateListBegin(self.sid, C.byref(it)):
            while len(out) < n and lib.RimeCandidateListNext(C.byref(it)):
                out.append(it.candidate.text.decode("utf-8"))
            lib.RimeCandidateListEnd(C.byref(it))
        lib.RimeClearComposition(self.sid)
        return out


# (输入, 期望出现的候选, 最晚出现在第几位)
CHECKS = [
    ("qiangji", "羟基", 1), ("suoji", "羧基", 1), ("tangji", "羰基", 1), ("qiuji", "巯基", 2),
    ("qiang", "羟", 2), ("mi", "醚", 3), ("wo", "肟", 2), ("tong", "酮", 2), ("ting", "烃", 2),
    ("weng", "鎓", 2), ("zhuo", "䓬", 5), ("gua", "胍", 2),
    ("miding", "嘧啶", 1), ("biluo", "吡咯", 1), ("saifen", "噻吩", 1), ("bulin", "卟啉", 1),
    ("linbenerjiasuan", "邻苯二甲酸", 1), ("qinhequdai", "亲核取代", 1),
    ("yixianyisuanyizhi", "乙酰乙酸乙酯", 1), ("baocengsepu", "薄层色谱", 1),
    ("hecigongzhenqingpu", "核磁共振氢谱", 1), ("diersiaerdefanying", "狄尔斯阿尔德反应", 2),
    ("chongjiejing", "重结晶", 1), ("shiji", "试剂", 3), ("shiji", "实际", 1),
    ("sheshidu", "℃", 2), ("keni", "⇌", 3), ("moermeisheng", "mol/L", 1),
    ("qianjiaomeimoer", "kJ/mol", 1), ("aerfa", "α", 3), ("yuedengyu", "≈", 2),
    ("liusuan", "H₂SO₄", 3), ("qingyanghuana", "NaOH", 2), ("liusuangen", "SO₄²⁻", 2),
    ("gaomengsuanjia", "KMnO₄", 2), ("angenlizi", "NH₄⁺", 2),
    ("H2SO4", "H₂SO₄", 1), ("Ca(OH)2", "Ca(OH)₂", 1), ("Fe3+", "Fe³⁺", 1),
    ("NH4+", "NH₄⁺", 1), ("SO42-", "SO₄²⁻", 1), ("CuSO4.5H2O", "CuSO₄·5H₂O", 1),
    ("N2", "N₂", 1), ("Na+", "Na⁺", 1), ("Cr2O72-", "Cr₂O₇²⁻", 1),
    ("vhx", "⇌", 1), ("vlizi", "H⁺", 1),
    # 日常输入不应被破坏
    ("women", "我们", 1), ("jintiantianqihenhao", "今天天气很好", 1), ("wo", "我", 1),
    ("nihao", "你好", 1), ("Hello", "Hello", 1),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rime-dll", required=True)
    ap.add_argument("--user-dir", required=True)
    ap.add_argument("--schema", default="chem_pinyin")
    ap.add_argument("keys", nargs="*")
    a = ap.parse_args()
    r = Rime(a.rime_dll, a.user_dir)
    if not r.select(a.schema):
        sys.exit(f"无法切换到方案 {a.schema}（部署失败？）")
    if a.keys:
        for k in a.keys:
            print(k, "→", " | ".join(r.candidates(k, 10)))
        return
    bad = 0
    for keys, want, pos in CHECKS:
        cands = r.candidates(keys, 10)
        got = cands.index(want) + 1 if want in cands else 0
        ok = 0 < got <= pos
        bad += not ok
        print(f"{'✓' if ok else '✗'} {keys:<22} 期望「{want}」≤第{pos}位，实际第{got or '∞'}位   {' | '.join(cands[:6])}")
    print(f"\n{len(CHECKS) - bad}/{len(CHECKS)} 通过")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
