# 音乐魔方 B60 Scorecard Generator

生成 Jubeat 音乐魔方 B60 成绩单图片。

## 使用

### 1. 准备环境

```bash
# Python 3.8+
pip install -r requirements.txt
```

电脑需装有 **Edge** 或 **Chrome**。

### 2. 准备素材

仓库不含游戏图片资源，需自行获取后放入以下目录：

```
./
├── .grade_cache/       # 评级图标 (9 张)
│   ├── grade_e.png
│   ├── grade_d.png
│   ├── grade_c.png
│   ├── grade_b.png
│   ├── grade_a.png
│   ├── grade_s.png
│   ├── grade_ss.png
│   ├── grade_sss.png
│   └── grade_exc.png
│
├── .static/fonts/      # 字体
│   └── LINESeedSans_A_Bd.otf
│
└── .static/jubeat/     # 游戏资源 (17 张)
    ├── avatar.png               # 默认头像
    ├── bg_icon.png              # 背景
    ├── exp_not_bg.png           # 经验条
    ├── jubeat_progress.png      # 进度条
    ├── center/
    │   └── player_jubility.png  # Jubility 表盘
    └── rating/
        ├── moniker_1.png        # 称号背景
        └── jby_ttljby_gauge_00.png ~ 10.png  # 等级图标
```

> 完整清单见 `generate.py` 中的 `STATIC_FILES`。素材可从 Jubeat 小程序包中提取。

### 3. 运行

**管理员身份** 运行 `run.bat`，按提示打开微信 → 音游街 → 音乐魔方，自动完成：

1. 捕获 Token
2. 爬取成绩
3. 渲染图片 → `jubeat_scorecard.png`

## 信用

- 本项目使用 [Claude Code](https://github.com/anthropics/claude-code) 辅助开发
- 仅供学习交流，请勿用于商业用途
- 游戏素材版权归原权利人所有
