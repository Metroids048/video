# -*- coding: utf-8 -*-
"""
使用剪映TTS生成配音
"""
import subprocess
import json
from pathlib import Path
import time

# 配音文稿
VOICEOVER_SCRIPT = """
15天，用AI搭建的量化交易系统，把模拟盘的5000 USDT做到了7000+。

不是靠AI猜涨跌，而是用AI搭建了一个完整的量化研究平台。系统分6层：数据采集、策略生成、AI辅助决策、严格验证、自动执行和每日复盘。

AI在这里不是直接决定买卖，而是做三件事：把交易想法规则化成可回测的代码，主动寻找策略失效的反例，每天复盘找出失败模式。

风控比策略更重要。系统第一条铁律：禁止取消机器人止损。每笔交易前，Gatekeeper会检查成本后净期望，低于零直接拒绝。

当前在Binance测试网运行，只做BTC和ETH。trend momentum v1策略：35笔交易，胜率45.7%，盈亏比1.49，Profit Factor 1.49。

策略不是拍脑袋，必须走完验证链路：历史回测、样本外测试、模拟盘、再到小资金实盘。当前置信区间还包含0，所以主网仍然关闭。

特别感谢GitHub上这些高星开源项目：TradingAgents、Freqtrade、Hummingbot、QuantConnect Lean。我借鉴了它们的架构思想，但所有策略都是从零验证的。

这个系统还在持续优化中。我会持续更新开发日志、策略复盘和踩坑记录。关注我，一起见证AI量化交易的真实过程。
"""

OUTPUT_DIR = Path("episodes/active/EP-20260801-QUANT-INTRO/input/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 先生成文本文件供剪映读取
script_file = OUTPUT_DIR / "voiceover_script.txt"
with open(script_file, 'w', encoding='utf-8') as f:
    f.write(VOICEOVER_SCRIPT.strip())

print(f"✅ 配音文稿已保存到: {script_file}")
print(f"\n📝 配音内容预览:")
print("="*60)
print(VOICEOVER_SCRIPT.strip())
print("="*60)

# 尝试使用Windows自带的TTS生成音频
output_audio = OUTPUT_DIR / "voice-narrator.mp3"

print(f"\n🎙️ 正在使用Windows TTS生成配音...")
print(f"输出文件: {output_audio}")

# 使用PowerShell的SAPI TTS
ps_script = f"""
Add-Type -AssemblyName System.Speech
$synthesizer = New-Object System.Speech.Synthesis.SpeechSynthesizer

# 设置语速（稍快）
$synthesizer.Rate = 2

# 选择中文语音
$voices = $synthesizer.GetInstalledVoices()
foreach ($voice in $voices) {{
    if ($voice.VoiceInfo.Culture.Name -eq "zh-CN") {{
        $synthesizer.SelectVoice($voice.VoiceInfo.Name)
        break
    }}
}}

# 读取文本
$text = Get-Content -Path '{script_file.absolute()}' -Encoding UTF8 -Raw

# 设置输出为WAV（SAPI不直接支持MP3）
$wavPath = '{OUTPUT_DIR.absolute()}/voice-narrator-temp.wav'
$synthesizer.SetOutputToWaveFile($wavPath)
$synthesizer.Speak($text)
$synthesizer.SetOutputToDefaultAudioDevice()

Write-Host "✅ WAV文件已生成: $wavPath"
"""

ps_script_path = OUTPUT_DIR / "generate_tts.ps1"
with open(ps_script_path, 'w', encoding='utf-8') as f:
    f.write(ps_script)

try:
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps_script_path)],
        capture_output=True,
        text=True,
        timeout=180,
        encoding='utf-8'
    )

    if result.returncode == 0:
        print(result.stdout)

        # 转换WAV到MP3（如果有ffmpeg）
        wav_file = OUTPUT_DIR / "voice-narrator-temp.wav"
        if wav_file.exists():
            print("\n🔄 正在转换WAV到MP3...")
            ffmpeg_result = subprocess.run(
                ["ffmpeg", "-i", str(wav_file), "-codec:a", "libmp3lame", "-qscale:a", "2",
                 str(output_audio), "-y"],
                capture_output=True,
                timeout=60
            )

            if ffmpeg_result.returncode == 0:
                print(f"✅ MP3文件已生成: {output_audio}")
                wav_file.unlink()  # 删除临时WAV
            else:
                print(f"⚠️ FFmpeg转换失败，保留WAV文件")
                print(f"WAV文件位置: {wav_file}")
    else:
        print(f"❌ TTS生成失败:")
        print(result.stderr)

except Exception as e:
    print(f"❌ 执行出错: {e}")

# 备选方案：提示用户使用剪映手动生成
print("\n" + "="*60)
print("📌 备选方案：使用剪映手动生成配音")
print("="*60)
print(f"""
1. 打开剪映专业版: D:\\JianyingPro\\JianyingPro.exe
2. 创建新项目（1080x1920竖屏）
3. 点击【文本】→【智能配音】
4. 粘贴配音文稿（已保存在 {script_file}）
5. 选择【标准男声】
6. 调整语速为 1.2x（稍快）
7. 生成并导出音频到: {output_audio}

配音要点：
- 语速稍快，保持清晰
- 数字部分要读准（45.7读作"四十五点七"）
- 关键词加重音（AI、风控、验证链路等）
- 总时长控制在70-80秒
""")

print("\n✅ 配音脚本准备完成！")
