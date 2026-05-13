# stylekit 🎨

**AI 试发型 / 试发色 / 试穿搭 / 试配饰 / 试妆容 / 多视角** —— 在你走进理发店之前，先看看变身效果。

[English](#english) · [中文](#中文)

---

## 中文

`stylekit` 是一个命令行 + Python 库 + Web UI。给它一张你的正面照，它会自动分析你的脸型/肤色/气质，推荐合适的发型/发色/穿搭/配饰/妆容，并用 AI 生成写实变身图——还能换 3/4 侧脸、侧面、全身视角看效果。

### ⚡ 零门槛快速试（推荐先试这条）

不想注册账号、不想花钱？用免费 provider 直接看大概效果：

```bash
pipx install stylekit
stylekit transform --photo me.jpg --preset hairstyle:side_part --provider pollinations
```

**说明**：免费模式调用 [Pollinations.ai](https://pollinations.ai)（FLUX 模型，无需任何 key），速度快（1-3 秒），但**主要是文生图**——
会按 prompt 生成"一个戴着这个发型的人"，**不保留你的真实脸**，只能让你大概看看那个发型是什么样子。

### 🎨 高保真使用（认真用）

想把**你自己的脸**变身（保留 100% 五官）：

```bash
pipx install stylekit
stylekit setup           # 选 openrouter 路径，配 API key
stylekit recommend --photo me.jpg   # AI 自动推荐 + 生成 6 张候选 + 对比图
```

需要 [OpenRouter](https://openrouter.ai/) 账号，约 ¥36 起充。每张图 ¥0.4-1.8。
出来的是用 GPT-Image-2 / Nano Banana Pro 这种顶级模型，**脸部 100% 保留**，效果如下例。

### 两个 provider 对比

| | pollinations (默认 fallback) | openrouter |
|---|---|---|
| 注册账号 | ❌ 不需要 | ✅ 必须 |
| 花钱 | ❌ 完全免费 | $0.05-0.23 / 张 |
| 速度 | 1-3 秒 | 3-4 分钟 |
| 保留你的脸 | ❌ 只看风格效果 | ✅ 100% 保留 |
| AI 智能推荐 | ❌ 用 --gender 手动选 | ✅ 自动分析脸型/肤色 |
| 适合 | 试水、预览 | 决定剪发前最后确认 |

> 没有 pipx？用 `pip install --user stylekit` 或 `uv tool install stylekit` 也行。

### 命令一览

| 命令 | 用途 |
|---|---|
| `stylekit setup` | 🔧 首次配置 API key + 默认模型 |
| `stylekit doctor` | 🩺 诊断环境（key 是否能用、依赖是否齐） |
| `stylekit list -c hairstyle` | 📋 看所有内置预设（hairstyle/haircolor/outfit/accessory/makeup/multiview） |
| `stylekit web` | 🌐 启动 Gradio Web UI（浏览器拖图即用） |
| `stylekit analyze -p me.jpg` | 🔍 AI 看照片：脸型、肤色、气质、改造建议 |
| `stylekit transform -p me.jpg -s hairstyle:side_part` | ✨ 单个预设变体 |
| `stylekit batch -p me.jpg --presets a,b,c` | 🎁 批量生成 |
| **`stylekit recommend -p me.jpg`** | 🪄 **一键全自动**：分析+推荐+生图+对比图 |

加 `--help` 看每个命令的所有选项。

### API key 哪里来

1. 注册 [OpenRouter](https://openrouter.ai/)（用 Google / GitHub 一键登录）
2. 进入 [Keys](https://openrouter.ai/keys) 创建一个 key
3. 充值 $5（约 ¥36）够你试 20-30 张图
4. 运行 `stylekit setup` 粘贴 key，下次就不用再设

### 试什么

```bash
# 看自己适合哪些发型（AI 自动挑 6 款）
stylekit recommend -p me.jpg -c hairstyle

# 试一个新发色
stylekit transform -p me.jpg -s haircolor:misty_ash_brown

# 同一张照片对比 4 种穿搭风格
stylekit batch -p me.jpg --presets \
  outfit:business_casual,outfit:korean_campus,outfit:vintage_french,outfit:athleisure
```

### 内置预设（75+）

- **发型** · 男生 11 + 女生 10：商务、休闲、街头、复古、运动、约会、派对等
- **发色** · 16 款 自然棕系 / 时髦冷棕 / 蓝色系 / 粉色系
- **穿搭** · 20 款 按场合分：商务、约会、街头、运动、复古、夏冬季
- **配饰** · 8 款 眼镜（圆框/眉线/方框/飞行员）、帽子（棒球帽/毛帽）、耳环（金圈/珍珠）
- **妆容** · 5 款 干净裸妆 / 韩系水光 / 烟熏晚妆 / 蜜桃甜系 / 男士清透
- **多视角** · 6 款 侧脸/3-4/后脑/全身/街拍（同一个人换镜头角度）

所有预设都在 `stylekit/presets/*.yaml`，**自己加几行就能扩展**（无需改代码）。详见 [自定义预设指南](docs/presets_guide.md)。

```bash
# 试戴眼镜
stylekit transform -p me.jpg -s accessory:round_metal_glasses

# 试一个妆容
stylekit transform -p me.jpg -s makeup:korean_dewy

# 看自己的 3/4 侧脸（依赖高保真模型，建议 openrouter）
stylekit transform -p me.jpg -s multiview:three_quarter_view
```

### 切换图像模型

默认用 `openai/gpt-5.4-image-2`（效果最好但贵）。可切到便宜模型：

| 模型 | 单张约 | 适合 |
|---|---|---|
| `openai/gpt-5.4-image-2` | $0.20-0.25 | 默认，效果最佳 |
| `openai/gpt-5-image-mini` | $0.03-0.06 | 性价比高 |
| `google/gemini-3-pro-image-preview` | $0.04-0.08 | Nano Banana Pro，画质能打 |
| `google/gemini-2.5-flash-image` | $0.005-0.01 | 便宜大碗，差异度可能小 |

切换方式：

```bash
# 单次
stylekit transform -p me.jpg -s hairstyle:side_part -m google/gemini-3-pro-image-preview

# 全局默认（写入 config）
stylekit setup  # 再选一遍
```

### 作为 Python 库

```python
from stylekit import StyleGenerator, FaceAnalyzer, find_preset, get_api_key

key = get_api_key()

# 分析照片
face = FaceAnalyzer(key).analyze("me.jpg")
print(face.face_shape, face.skin_tone, face.vibe)

# 生成单张
style = find_preset("hairstyle:korean_layered")
result = StyleGenerator(key).transform("me.jpg", style, "out.png")
print(f"${result.cost_usd:.4f}")
```

### 隐私

- 你的照片**只发给 OpenRouter API**，不上传任何第三方服务器
- API key **明文存在本地 `~/.config/stylekit/config.json`**，权限 600（Linux/macOS）
- 没有任何遥测，没有任何分析

### Web UI

不想用命令行？一行启动浏览器版：

```bash
pip install "stylekit[web]"
stylekit web                  # 默认 http://127.0.0.1:7860
stylekit web --share          # 一次性公网链接（gradio.live, 72h）
stylekit web --host 0.0.0.0   # 局域网内其他设备也能访问
```

界面里可以：上传照片 → 一键 AI 分析 → 选类别（发型/发色/穿搭/配饰/妆容/多视角）→ 选预设 → 生成，结果带耗时和花费明细。

### 路线图

- [x] CLI + Python 库
- [x] 75+ 内置预设，YAML 可扩展
- [x] AI 推荐机制
- [x] 持久化配置
- [x] Gradio Web UI（`stylekit web`）
- [x] 配饰试戴（眼镜 / 帽子 / 耳环）
- [x] 妆容尝试
- [x] 多视角生成（侧面 / 后面 / 全身）
- [ ] Hugging Face Space 在线 demo（不用装就能玩）
- [ ] 结果本地缓存（同 photo+preset+model 不重复调 API）

### 开发

```bash
git clone https://github.com/Crazycreate/stylekit.git
cd stylekit
pip install -e ".[dev,web]"
pytest                            # 跑测试
ruff check stylekit               # 代码检查
stylekit web                      # 启动 Web UI
```

欢迎 PR！加新预设特别欢迎——按 `docs/presets_guide.md` 格式提交一个 YAML 即可。

### 许可

[MIT](LICENSE)

---

## English

`stylekit` is a CLI + Python library + Gradio Web UI that uses AI to analyze your front-facing portrait, then generates realistic hairstyle, hair-color, outfit, accessory, makeup, and multi-angle variations.

### ⚡ 30-second start

```bash
pipx install stylekit
stylekit setup           # one-time API key config
stylekit recommend --photo me.jpg
```

Done. Open `./stylekit-out/` to see 6 AI-recommended variants + a comparison grid.

### Commands

| Command | Purpose |
|---|---|
| `stylekit setup` | First-time API key config |
| `stylekit doctor` | Diagnose environment |
| `stylekit list -c hairstyle` | Browse presets |
| `stylekit analyze -p me.jpg` | AI face analysis |
| `stylekit transform -p me.jpg -s hairstyle:side_part` | Single variant |
| `stylekit batch -p me.jpg --presets a,b,c` | Batch |
| **`stylekit recommend -p me.jpg`** | **Fully automatic** |
| `stylekit web` | Launch Gradio Web UI (`pip install 'stylekit[web]'`) |

### Get an API key

Sign up at [openrouter.ai](https://openrouter.ai/), create a key, top up $5. Run `stylekit setup` and paste it in.

### License

MIT
