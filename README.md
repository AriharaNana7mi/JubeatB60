# 音乐魔方 B60 Scorecard Generator

生成 Jubeat 音乐魔方 B60 成绩单图片。

## 使用方法

1. 确保电脑装有 **Edge** 或 **Chrome** 浏览器
2. 准备游戏素材（见下方）
3. **管理员身份**运行 `run.bat`
4. 打开微信 → 音游街 → 音乐魔方
5. 等待自动捕获 → 爬取 → 渲染，输出 `jubeat_scorecard.png`

## 素材准备

由于版权原因，仓库不包含游戏图片资源。请从以下途径获取：

- `.static/` — 从 Jubeat 音乐魔方小程序包中提取
- `.grade_cache/` — 评级图标（grade_e ~ grade_exc 共 9 张 png）

完整文件列表参见 `generate.py` 中的 `STATIC_FILES`。

## 信用

- 本项目仅供学习交流，请勿用于商业用途
- 游戏素材版权归原权利人所有

## 构建

本项目使用 [Claude Code](https://github.com/anthropics/claude-code) 辅助开发构建。
