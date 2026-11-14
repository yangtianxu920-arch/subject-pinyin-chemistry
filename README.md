# 学科中文拼音输入法 · 化学

基于 [Rime](https://rime.im) 和[雾凇拼音](https://github.com/iDvel/rime-ice)的学科拼音方案。
先做化学：让化学生僻字、术语、化学式和常用符号排在候选前面。

同一套配置文件可用于 Windows、macOS、Linux、Android、iOS。

## 能做什么

| 功能 | 输入 | 候选 |
|---|---|---|
| 生僻字提前 | `qiang` / `wo` / `weng` | 强 **羟** … / 我 **肟** … / 翁 **鎓** … |
| 术语整词 | `qiangji` `miding` `qinhequdai` | 羟基、嘧啶、亲核取代 |
| 名称出化学式 | `liusuan` `liusuangen` | 硫酸 **H₂SO₄**、硫酸根 **SO₄²⁻** |
| 直接打化学式 | `H2SO4` `Ca(OH)2` `Fe3+` `SO42-` `CuSO4.5H2O` | H₂SO₄、Ca(OH)₂、Fe³⁺、SO₄²⁻、CuSO₄·5H₂O |
| 名称出符号 | `sheshidu` `keni` `yuedengyu` `aerfa` | ℃、⇌、≈、α |
| 名称出单位 | `moermeisheng` `qianjiaomeimoer` `weimi` | mol/L、kJ/mol、μm |
| 符号面板 | `vhx` / `vhxdw` / `vlizi` | 化学符号 / 化学单位 / 常见离子 |

「化学拼音」是一个独立方案：日常用雾凇拼音，写化学内容时切过去（`Ctrl+`` 或 `F4`）。
两个方案的用户词库互不影响。雾凇原有功能（英文、日期、计算器、`v` 符号等）在化学拼音里照常可用。

当前规模：254 个单字、约 2500 条术语（其中约 1100 条雾凇原本没有）、376 条符号 / 单位 / 化学式。

## 安装

### 第一步：装 Rime 和雾凇拼音

| 平台 | 输入法 | Rime 用户目录 |
|---|---|---|
| Windows | [小狼毫](https://rime.im/download/) | `%APPDATA%\Rime` |
| macOS | [鼠须管](https://rime.im/download/) | `~/Library/Rime` |
| Linux | ibus-rime / fcitx5-rime | `~/.config/ibus/rime` / `~/.local/share/fcitx5/rime` |
| iOS | 仓输入法（App Store，自带雾凇） | App 内的 Rime 文件目录 |
| Android | 小企鹅输入法 + Rime 插件，或同文输入法 | 各 App 设置里显示的 Rime 用户目录 |

电脑端把[雾凇拼音](https://github.com/iDvel/rime-ice)仓库里的全部文件复制到 Rime 用户目录即可。

### 第二步：放入本项目的文件

把 `rime/` 文件夹**里面的内容**复制到 Rime 用户目录（与雾凇的文件合并，不会覆盖雾凇的任何文件）：

```
chem_pinyin.schema.yaml
chem_pinyin.dict.yaml
xueke/chem_chars.dict.yaml
xueke/chem_terms.dict.yaml
xueke/chem_symbols.dict.yaml
lua/chem_formula.lua
```

### 第三步：启用方案

在用户目录的 `default.custom.yaml` 里把 `chem_pinyin` 加入方案列表（没有这个文件就新建）：

```yaml
patch:
  schema_list:
    - schema: rime_ice       # 雾凇拼音
    - schema: chem_pinyin    # 化学拼音
```

然后「重新部署」（Windows：右键任务栏的小狼毫图标）。首次部署要编译词库，需要一两分钟。

不想手动复制的话，可以直接下载 Releases 里的「化学拼音-完整包.zip」，
里面已经包含雾凇拼音和上面的配置，解压到 Rime 用户目录后重新部署即可。

手机端：用 App 自带的文件管理、Wi-Fi 传输或 iCloud / 文件 App 把同样的文件放进 Rime 目录，
在 App 的「输入方案」里勾选「化学拼音」，再重新部署。各 App 菜单名称随版本略有不同。

## 目录结构

```
data/                源表（改这里）
  chars.txt            单字：字 拼音 档位
  terms.txt            术语：空格分隔，多音字可写 词=pin_yin
  formulas.txt         名称 → 化学式
  symbols.txt          符号 → 中文名称
tools/
  build.py             由源表生成 rime/ 下的词库
  test_rime.py         用 librime 无界面测试候选排序
  package.py           打包成可分发的 zip（输出到 dist/）
rime/                成品（复制到 Rime 用户目录）
```

## 增删词条

1. 编辑 `data/` 下的源表。
2. 重新生成（需要 `pip install pypinyin`）：

   ```
   python tools/build.py --rime-ice <雾凇拼音目录> --report
   ```

   `--report` 会列出雾凇没收录、又含多音字的词，供人工核对读音。
3. 把 `rime/` 重新复制到各设备并重新部署。

### 排序规则

- **单字**：按档位提到同音字的第 2 / 4 / 7 位，只升不降。
- **术语**：排到同音词第一；但若同音词里有日常高频词（如"实际""秋季"），则排在它后面。
- **符号、化学式**：排在对应名称之后。
- 之后 Rime 会按你的实际使用继续调整顺序。

## 已知限制

- 含字母、数字的术语（如 pH 试纸、X 射线衍射）暂未收录。
- 配合物的方括号不能直接键入（方括号是雾凇的"以词定字"键），可用名称输入，如 `tieqinghuajia` → K₃[Fe(CN)₆]。
- 化学拼音里「N + 数字」的农历转换改为输满 8 位日期才触发，以便输入 N₂、N₂O₄。
- 少数生僻字（䓬、鿏、𬬻 等）在扩展区，设备字体不支持时显示为方框。
- 手机上直接键入化学式要切换大写和数字，通常不如打名称方便。

## 加入其他学科

复制化学的做法：新建 `data/` 源表，生成 `xueke/<学科>_*.dict.yaml`，
再建一个 `<学科>_pinyin.schema.yaml`，或把多个学科词库挂到同一个方案里。

## 许可与致谢

本项目以 [GPL-3.0](LICENSE) 发布。

方案继承自[雾凇拼音（rime-ice）](https://github.com/iDvel/rime-ice)（GPL-3.0），词频也以它为基准校准；
输入法引擎是 [Rime](https://rime.im)。Releases 中的完整包内含雾凇拼音的文件，版权归原作者所有。

化学词表为人工整理加自动注音，难免有错漏，欢迎提 Issue 或 PR 补词、纠正读音。
