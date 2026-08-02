# -*- coding: utf-8 -*-
"""
剪映自动化视频制作脚本
"""
import subprocess
from pathlib import Path
import json
import time

JIANYING_PATH = Path("D:/JianyingPro/JianyingPro.exe")
PROJECT_ROOT = Path("C:/Users/Windows11/Desktop/video")
EPISODE_DIR = PROJECT_ROOT / "episodes/active/EP-20260801-QUANT-INTRO"
INPUT_DIR = EPISODE_DIR / "input"
OUTPUT_DIR = EPISODE_DIR / "renders"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 素材路径
IMAGES_DIR = INPUT_DIR / "images"
AUDIO_DIR = INPUT_DIR / "audio"
VOICEOVER = AUDIO_DIR / "voice-narrator.mp3"

# 视频参数
VIDEO_CONFIG = {
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "duration": 90,  # 90秒
    "format": "mp4"
}

# 生成剪映草稿JSON
def create_jianying_draft():
    """创建剪映草稿配置"""

    draft = {
        "version": "5.9.0",
        "materials": {
            "videos": [],
            "audios": [
                {
                    "id": "audio_voiceover",
                    "path": str(VOICEOVER.absolute()),
                    "type": "extract_music",
                    "volume": 1.0
                }
            ],
            "images": [
                {
                    "id": "img_architecture",
                    "path": str((IMAGES_DIR / "architecture-6-layers.png").absolute())
                },
                {
                    "id": "img_metrics",
                    "path": str((IMAGES_DIR / "strategy-metrics-chart.png").absolute())
                },
                {
                    "id": "img_agents",
                    "path": str((IMAGES_DIR / "ai-agents-workflow.png").absolute())
                },
                {
                    "id": "img_validation",
                    "path": str((IMAGES_DIR / "validation-pipeline.png").absolute())
                }
            ],
            "texts": []
        },
        "canvas": {
            "width": VIDEO_CONFIG["width"],
            "height": VIDEO_CONFIG["height"]
        }
    }

    draft_path = OUTPUT_DIR / "jianying_draft.json"
    with open(draft_path, 'w', encoding='utf-8') as f:
        json.dump(draft, f, indent=2, ensure_ascii=False)

    print(f"✅ 剪映草稿已生成: {draft_path}")
    return draft_path

# 检查剪映是否安装
if not JIANYING_PATH.exists():
    print(f"❌ 剪映未找到，请确认路径: {JIANYING_PATH}")
    print("请手动安装剪映专业版")
else:
    print(f"✅ 剪映路径确认: {JIANYING_PATH}")

# 生成草稿
draft_path = create_jianying_draft()

# 视频制作指南
print("\n" + "="*80)
print("📹 剪映视频制作完整指南")
print("="*80)

print(f"""
🎬 步骤1：打开剪映并创建项目
----------------------------------------
1. 运行剪映: {JIANYING_PATH}
2. 点击【开始创作】
3. 设置画布比例为 9:16（竖屏）
4. 分辨率选择 1080x1920

🎵 步骤2：导入配音（主音频）
----------------------------------------
1. 点击【音频】→【导入音频】
2. 选择配音文件: {VOICEOVER}
3. 拖拽到时间轴【音频轨道】
4. 音量设置为 100%
5. 确认音频时长（应该在70-80秒）

🖼️ 步骤3：按分镜添加图片素材
----------------------------------------
时间轴规划（根据配音实际时长调整）:

分镜1 (0-3秒) - Hook
  📁 素材: 需要用户提供的截图
  💡 说明: Binance交易界面、账户盈利数据

分镜2 (3-15秒) - 系统架构
  📁 素材: {IMAGES_DIR / 'architecture-6-layers.png'}
  🎨 效果: 从下往上展开动画（渐现）

分镜3 (15-28秒) - AI角色
  📁 素材: {IMAGES_DIR / 'ai-agents-workflow.png'}
  🎨 效果: 放大进入 + 淡入

分镜4 (28-38秒) - 风控优先
  📁 素材: 需要用户提供的风控代码截图
  🎨 效果: 代码高亮效果

分镜5 (38-52秒) - 真实数据
  📁 素材: {IMAGES_DIR / 'strategy-metrics-chart.png'}
  🎨 效果: 数字逐个跳动出现

分镜6 (52-64秒) - 验证链路
  📁 素材: {IMAGES_DIR / 'validation-pipeline.png'}
  🎨 效果: 流程图逐步展示

分镜7 (64-74秒) - 开源感谢
  📁 素材: 需要用户提供的GitHub项目截图
  🎨 效果: 滚动展示

分镜8 (74-90秒) - 结尾CTA
  📁 素材: 需要用户提供的运维控制台截图
  🎨 效果: 淡出 + 文字叠加

📝 步骤4：添加字幕（自动识别）
----------------------------------------
1. 选中配音轨道
2. 点击【文本】→【智能字幕】→【识别字幕】
3. 选择语言: 中文
4. 等待识别完成（约1-2分钟）
5. 字幕样式:
   - 字体: 思源黑体 Bold
   - 大小: 48px
   - 颜色: 白色 #FFFFFF
   - 描边: 黑色 2px
   - 位置: 底部安全区（距离底部200px）
6. 关键数字字幕设置为**加粗 + 颜色强调**（绿色 #00FF88）

🎨 步骤5：添加转场和特效
----------------------------------------
1. 图片间转场: 使用【叠化】或【闪白】（0.3秒）
2. 标题动画:
   - Hook部分: 数字跳动动画
   - 各分镜标题: 从下飞入
3. 背景音乐（可选）:
   - 点击【音频】→【音乐库】
   - 搜索"科技"或"未来"
   - 音量设置为 20-30%（不要盖过配音）

⚠️ 步骤6：添加风险声明
----------------------------------------
在视频最后1-2秒添加静态文字卡片:
---
本视频仅记录个人项目开发过程
不构成投资建议
加密货币交易存在高风险
当前系统处于测试阶段
---
- 字体: 思源黑体 Regular
- 大小: 32px
- 颜色: 红色 #FF6B6B
- 背景: 半透明黑色蒙版

💾 步骤7：导出视频
----------------------------------------
1. 点击右上角【导出】
2. 导出设置:
   - 分辨率: 1080x1920
   - 帧率: 30fps
   - 码率: 10000 kbps（高质量）
   - 格式: MP4 (H.264)
3. 导出文件名: EP-20260801-QUANT-INTRO-final.mp4
4. 导出路径: {OUTPUT_DIR}
5. 等待渲染完成（约3-5分钟）

✅ 步骤8：质量检查
----------------------------------------
播放导出的视频，检查:
□ 配音清晰，无杂音
□ 字幕准确，无错别字
□ 画面切换流畅
□ 数字显示准确（45.7%、1.49等）
□ 风险声明完整展示
□ 总时长在75-90秒之间
□ 无卡顿或黑屏

📤 步骤9：准备发布
----------------------------------------
1. 封面制作（在剪映中）:
   - 使用第一帧或关键数据图
   - 添加标题文字: "0代码搭建AI量化系统"
   - 添加副标题: "15天5000→7000"
2. 导出封面: EP-20260801-QUANT-INTRO-cover.jpg

""")

print("="*80)
print("📊 素材清单总结")
print("="*80)
print(f"""
✅ 已生成的素材:
  - 配音文件: {VOICEOVER.relative_to(PROJECT_ROOT)}
  - 架构图: {(IMAGES_DIR / 'architecture-6-layers.png').relative_to(PROJECT_ROOT)}
  - 数据图表: {(IMAGES_DIR / 'strategy-metrics-chart.png').relative_to(PROJECT_ROOT)}
  - AI工作流: {(IMAGES_DIR / 'ai-agents-workflow.png').relative_to(PROJECT_ROOT)}
  - 验证流程: {(IMAGES_DIR / 'validation-pipeline.png').relative_to(PROJECT_ROOT)}

⚠️ 需要手动添加的素材（从聊天记录保存）:
  - P1: Binance交易界面
  - P2-P3: AI Quant账户总览
  - P4-P5: 决策面板和拒单记录
  - P6: GitHub开源项目列表
  - P7: 验证中心界面
  - P8: 复盘中心
  - P9: 运维控制台

💡 提示:
  1. 所有截图需要提前保存到: {INPUT_DIR / 'screenshots'}
  2. 敏感信息（API Key、订单ID）需要打码
  3. 可以边制作边调整时间轴，以配音为准

🎯 预计完成时间: 2-3小时
""")

print("\n✅ 剪映自动化脚本准备完成！")
print(f"💾 草稿文件已保存: {draft_path}")
print("\n🚀 现在可以打开剪映开始制作视频了！")
