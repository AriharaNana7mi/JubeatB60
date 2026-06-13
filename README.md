# 音乐魔方 B60  Generator

生成 Jubeat 音乐魔方 B60 成绩单图片。

## 使用

```bash
pip install -r requirements.txt
```

**管理员身份** 运行 `run.bat`，首次运行会自动解压素材。然后按提示打开微信 → 音游街 → 音乐魔方，即可自动完成捕获 → 爬取 → 渲染，输出 `jubeat_scorecard.png`。

> 需安装 Edge 或 Chrome。
> 如出现使用后无法正常打开小程序，请手动清理hosts残留，这可能是程序没有正常退出导致的。

## Credits

- 本项目使用 [Claude Code](https://github.com/anthropics/claude-code) 辅助开发
- 仅供学习交流，请勿用于商业用途
