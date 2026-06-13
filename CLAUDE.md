# 音乐魔方 B60 Generator

## 目录结构
```
scorecard_gen/
├── run.bat              # 管理员启动，按顺序运行三个步骤
├── main.py              # PyInstaller 入口（导入三个子脚本）
├── get_token.py         # Step1: hosts劫持 + CA证书 + 捕获 token/roleid → config.json
├── crawl_scores.py      # Step2: rating_info → music_detail → player_info → best_scores.json
├── generate.py          # Step3: 检查资源 → 无头浏览器渲染 → 保存 jubeat_scorecard.png
├── requirements.txt     # cryptography, requests
├── b60_template.html    # 成绩单模板，浏览器渲染 + html2canvas 导出
├── .ca/                 # CA证书 (自动生成)
├── .static/             # 静态资源 (字体/背景/评级图标等)
├── .grade_cache/        # 等级图标 (grade_s.png 等)
├── .cover_cache/        # 歌曲封面 (运行时下载)
├── config.json          # 自动生成，存 token + roleid
├── best_scores.json     # 爬取结果
└── jubeat_scorecard.png # 最终生成的成绩单图片
```

## API 信息
- 目标: `wamusic.wahlap.net` → `https://wamusic.wahlap.net/api/info/mp`
- 项目名: `jubeat_release`
- 签名: SHA256(token + timestamp + nonce)
- Token 捕获: hosts 劫持 `wamusic.wahlap.net → 127.0.0.1` + 443 端口 HTTPS 反向代理

## 数据流
1. `rating_info` → list_pickup(30首) + list_common(30首) → 共 60 首
2. `music_detail` × 60 → 逐首取 song_score (lv/score/musicRate/grade/isTwo)
3. `player_info` → 头像/等级/经验/Jubility 排名

## best_scores.json 结构
```json
{
  "nickName": "", "monikerName": "",
  "rating_name": "PINK", "rating_lv": 8, "rating_value": 1234,
  "jubilityRank": 27, "photo": "...", "lv": 100,
  "exp": 600000, "expMax": 610000,
  "scores": [{
    "name": "", "artist": "", "diff": 3, "lv": 10.,
    "isHard": 0, "isTwo": 0, "score": 1000000,
    "musicRate": 120, "rating": 150, "grade": 7,
    "pic": "https://...", "pic_local": ".cover_cache/10000001.png",
    "type": "pickup", "songId": 10000001
  }]
}
```

## 打包分发
```
python -m PyInstaller --onedir --name JubeatB60 -y \
  --add-data ".static;.static" \
  --add-data ".grade_cache;.grade_cache" \
  --add-data "b60_template.html;." \
  --hidden-import=cryptography \
  --hidden-import=cryptography.hazmat.backends.openssl \
  main.py
cp -r .static .grade_cache b60_template.html dist/JubeatB60/
```
