# 自定义预设指南

## 文件位置

所有预设都在 `stylekit/presets/*.yaml`：

| 文件 | 内容 |
|---|---|
| `hairstyles_male.yaml` | 男生发型 |
| `hairstyles_female.yaml` | 女生发型 |
| `haircolors.yaml` | 通用发色 |
| `outfits.yaml` | 穿搭 |

也可以新建 `something.yaml`，会被自动加载。

## 字段说明

```yaml
- id: my_style              # 必填，全局唯一（同 category 内）
  name_zh: 我的发型          # 必填，中文显示名
  name_en: My Style          # 必填，英文显示名
  category: hairstyle        # 必填，hairstyle | haircolor | outfit
  subcategory: trendy        # 可选，分类标签
  description_zh: 简短描述    # 可选
  description_en: Short desc # 可选
  best_for:                  # 可选，全部不填等于"适合所有人"
    face_shapes: [oval, round, square, oblong, heart, diamond]
    skin_tones: [warm, cool, neutral]
    gender: male             # male | female (不填=不限)
    occasions: [business, casual, daily, ...]
  prompt: |                  # 必填，英文 prompt 喂给图像模型
    Detailed photorealistic description of the new style...
```

## prompt 设计技巧

1. **写英文**：GPT-Image-2 对英文响应更稳定，复杂中文术语容易理解错
2. **足够具体**：颜色用准确词（"deep navy" 不是 "blue"），发型描述分前/侧/后/顶
3. **加参考词**：写 "Korean salon level", "K-pop idol style" 等帮模型对齐
4. **避免冲突**：不要在 prompt 里描述脸/眼镜/衣服，那些会被框架的 PRESERVE 指令保护
5. **测一次再批量**：新 prompt 先 `transform` 单跑一次确认效果，再 `batch` 跑

## 例子

加一个"工装风发型"：

```yaml
# stylekit/presets/my_custom.yaml
- id: workwear_inspired_crop
  name_zh: 工装风短发
  name_en: Workwear Inspired Crop
  category: hairstyle
  subcategory: street
  description_zh: 实用主义不修边幅
  best_for:
    face_shapes: [oval, square, oblong]
    gender: male
    occasions: [casual, street]
  prompt: |
    A practical workwear-inspired short crop: medium-short hair (3-5cm) on top with natural
    unstyled texture, slightly longer at the front falling messily over the forehead, sides
    medium-short with rough scissor-cut blending (no tight fade). Hair looks lived-in and
    unfussed, like a craftsman or laborer aesthetic. Natural deep black or dark brown.
```

然后：

```bash
stylekit list --category hairstyle | grep workwear
stylekit transform --photo me.jpg --preset hairstyle:workwear_inspired_crop --output test.png
```

## 推荐机制如何工作

`stylekit recommend` 的逻辑：

1. 把照片发给 Claude 视觉模型，分析脸型 / 肤色 / 性别 / 年龄等
2. 遍历所有 `category` 匹配的预设
3. 对每个预设调用 `Style.fits(face_shape, skin_tone, gender)`：
   - `best_for` 里没填的维度 = 通过
   - 填了的维度，照片属性必须在列表里
4. 取前 N 个生成

所以**给预设的 `best_for` 填得越准，推荐越合理**。如果想让某个预设永远不被推荐（只能手动选）：

```yaml
best_for:
  face_shapes: [none]  # 没人是 'none' 脸型，所以永远不匹配
```
