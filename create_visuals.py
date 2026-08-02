# -*- coding: utf-8 -*-
"""
生成视频所需的可视化图表
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager
import numpy as np
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 输出目录
OUTPUT_DIR = Path("episodes/active/EP-20260801-QUANT-INTRO/input/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 竖屏尺寸 (1080x1920)
PORTRAIT_SIZE = (6, 10.67)  # inches, 16:9 ratio vertical
DPI = 180

def create_architecture_diagram():
    """创建6层架构图"""
    fig, ax = plt.subplots(figsize=PORTRAIT_SIZE, dpi=DPI, facecolor='#0A0E27')
    ax.set_facecolor('#0A0E27')

    layers = [
        ("复盘层\nReview Layer", "#FF6B6B", "每日复盘\n失败模式识别"),
        ("执行层\nExecution Layer", "#4ECDC4", "订单执行\nGatekeeper风控"),
        ("验证层\nValidation Layer", "#45B7D1", "回测→OOS→模拟盘"),
        ("AI Agent层", "#FFA07A", "Strategy/Risk/Review"),
        ("策略层\nStrategy Layer", "#98D8C8", "信号生成\n技术指标"),
        ("数据层\nData Layer", "#6C5CE7", "行情/新闻/资金费率")
    ]

    y_start = 0.85
    box_height = 0.12
    y_gap = 0.015

    for i, (label, color, desc) in enumerate(layers):
        y = y_start - i * (box_height + y_gap)

        # 主框
        rect = mpatches.FancyBboxPatch(
            (0.1, y), 0.8, box_height,
            boxstyle="round,pad=0.01",
            linewidth=2,
            edgecolor='white',
            facecolor=color,
            alpha=0.9,
            transform=ax.transAxes
        )
        ax.add_patch(rect)

        # 标题
        ax.text(0.5, y + box_height/2 + 0.02, label,
                ha='center', va='center', fontsize=18, fontweight='bold',
                color='white', transform=ax.transAxes)

        # 描述
        ax.text(0.5, y + box_height/2 - 0.025, desc,
                ha='center', va='center', fontsize=12,
                color='white', alpha=0.9, transform=ax.transAxes)

        # 箭头
        if i < len(layers) - 1:
            arrow_y = y - y_gap/2
            ax.annotate('', xy=(0.5, arrow_y - 0.02), xytext=(0.5, arrow_y + 0.02),
                       arrowprops=dict(arrowstyle='->', color='#00D9FF', lw=3),
                       transform=ax.transAxes)

    # 标题
    ax.text(0.5, 0.97, 'AI量化交易系统 - 6层架构',
            ha='center', va='top', fontsize=24, fontweight='bold',
            color='#00D9FF', transform=ax.transAxes)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    plt.tight_layout()
    output_path = OUTPUT_DIR / "architecture-6-layers.png"
    plt.savefig(output_path, dpi=DPI, bbox_inches='tight', facecolor='#0A0E27')
    plt.close()
    print(f"✅ 已创建: {output_path}")

def create_strategy_metrics():
    """创建策略数据可视化"""
    fig, ax = plt.subplots(figsize=PORTRAIT_SIZE, dpi=DPI, facecolor='#0A0E27')
    ax.set_facecolor('#0A0E27')

    metrics = [
        ("胜率\nWin Rate", 45.7, "%", "#00FF88"),
        ("盈亏比\nP/L Ratio", 1.49, "", "#00D9FF"),
        ("Profit Factor", 1.49, "", "#FFA07A"),
        ("最大回撤\nMax DD", 18.0, "%", "#FF6B6B")
    ]

    y_positions = [0.75, 0.55, 0.35, 0.15]

    for (label, value, unit, color), y_pos in zip(metrics, y_positions):
        # 背景框
        rect = mpatches.FancyBboxPatch(
            (0.1, y_pos - 0.08), 0.8, 0.16,
            boxstyle="round,pad=0.015",
            linewidth=2,
            edgecolor=color,
            facecolor='#1a1f3a',
            alpha=0.8,
            transform=ax.transAxes
        )
        ax.add_patch(rect)

        # 指标名称
        ax.text(0.5, y_pos + 0.05, label,
                ha='center', va='center', fontsize=16,
                color='white', transform=ax.transAxes)

        # 数值
        value_text = f"{value}{unit}"
        ax.text(0.5, y_pos - 0.03, value_text,
                ha='center', va='center', fontsize=32, fontweight='bold',
                color=color, transform=ax.transAxes)

    # 标题
    ax.text(0.5, 0.92, 'trend_momentum_v1 策略数据',
            ha='center', va='top', fontsize=22, fontweight='bold',
            color='#00D9FF', transform=ax.transAxes)

    # 副标题
    ax.text(0.5, 0.88, 'Binance Testnet | 35笔交易 | 15天',
            ha='center', va='top', fontsize=14,
            color='white', alpha=0.7, transform=ax.transAxes)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    plt.tight_layout()
    output_path = OUTPUT_DIR / "strategy-metrics-chart.png"
    plt.savefig(output_path, dpi=DPI, bbox_inches='tight', facecolor='#0A0E27')
    plt.close()
    print(f"✅ 已创建: {output_path}")

def create_ai_agents_workflow():
    """创建AI Agent工作流程图"""
    fig, ax = plt.subplots(figsize=PORTRAIT_SIZE, dpi=DPI, facecolor='#0A0E27')
    ax.set_facecolor('#0A0E27')

    agents = [
        ("Strategy Agent", "规则化策略", "#4ECDC4", 0.7),
        ("Risk Agent", "寻找反例", "#FFA07A", 0.45),
        ("Review Agent", "复盘失败", "#FF6B6B", 0.2)
    ]

    for name, desc, color, y_pos in agents:
        # 圆形图标
        circle = mpatches.Circle(
            (0.5, y_pos), 0.12,
            facecolor=color,
            edgecolor='white',
            linewidth=3,
            alpha=0.9,
            transform=ax.transAxes
        )
        ax.add_patch(circle)

        # Agent名称（圆内）
        ax.text(0.5, y_pos + 0.02, name.split()[0],
                ha='center', va='center', fontsize=16, fontweight='bold',
                color='white', transform=ax.transAxes)
        ax.text(0.5, y_pos - 0.03, name.split()[1] if len(name.split()) > 1 else "",
                ha='center', va='center', fontsize=14, fontweight='bold',
                color='white', transform=ax.transAxes)

        # 描述（圆外）
        ax.text(0.5, y_pos - 0.16, desc,
                ha='center', va='center', fontsize=18,
                color=color, fontweight='bold', transform=ax.transAxes)

        # 连接线到Claude API
        if y_pos < 0.7:
            ax.plot([0.5, 0.5], [y_pos + 0.12, y_pos + 0.21],
                   color='#00D9FF', linewidth=2, alpha=0.6, transform=ax.transAxes)

    # Claude API标识
    rect = mpatches.FancyBboxPatch(
        (0.25, 0.88), 0.5, 0.08,
        boxstyle="round,pad=0.01",
        linewidth=2,
        edgecolor='#00D9FF',
        facecolor='#1a1f3a',
        alpha=0.9,
        transform=ax.transAxes
    )
    ax.add_patch(rect)
    ax.text(0.5, 0.92, 'Claude API',
            ha='center', va='center', fontsize=18, fontweight='bold',
            color='#00D9FF', transform=ax.transAxes)

    # 标题
    ax.text(0.5, 0.05, 'AI的3个真实角色',
            ha='center', va='center', fontsize=20, fontweight='bold',
            color='white', transform=ax.transAxes)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    plt.tight_layout()
    output_path = OUTPUT_DIR / "ai-agents-workflow.png"
    plt.savefig(output_path, dpi=DPI, bbox_inches='tight', facecolor='#0A0E27')
    plt.close()
    print(f"✅ 已创建: {output_path}")

def create_validation_pipeline():
    """创建验证链路流程图"""
    fig, ax = plt.subplots(figsize=PORTRAIT_SIZE, dpi=DPI, facecolor='#0A0E27')
    ax.set_facecolor('#0A0E27')

    stages = [
        ("历史回测", "✓", "#00FF88", 0.75),
        ("样本外测试\n(OOS)", "✓", "#00FF88", 0.55),
        ("模拟盘\n(Testnet)", "✓", "#00FF88", 0.35),
        ("小资金实盘\n(主网)", "✗", "#FF6B6B", 0.15)
    ]

    for i, (stage, status, color, y_pos) in enumerate(stages):
        # 状态框
        rect = mpatches.FancyBboxPatch(
            (0.15, y_pos - 0.06), 0.7, 0.12,
            boxstyle="round,pad=0.01",
            linewidth=2,
            edgecolor=color,
            facecolor='#1a1f3a',
            alpha=0.9,
            transform=ax.transAxes
        )
        ax.add_patch(rect)

        # 阶段名称
        ax.text(0.35, y_pos, stage,
                ha='left', va='center', fontsize=18,
                color='white', transform=ax.transAxes)

        # 状态标记
        ax.text(0.75, y_pos, status,
                ha='center', va='center', fontsize=32, fontweight='bold',
                color=color, transform=ax.transAxes)

        # 箭头
        if i < len(stages) - 1:
            ax.annotate('', xy=(0.5, y_pos - 0.12), xytext=(0.5, y_pos - 0.06),
                       arrowprops=dict(arrowstyle='->', color='#00D9FF', lw=3),
                       transform=ax.transAxes)

    # 标题
    ax.text(0.5, 0.92, '严格验证链路',
            ha='center', va='top', fontsize=24, fontweight='bold',
            color='#00D9FF', transform=ax.transAxes)

    # 说明
    ax.text(0.5, 0.05, '主网未开启 | 置信区间包含0',
            ha='center', va='center', fontsize=16,
            color='#FF6B6B', fontweight='bold', transform=ax.transAxes)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    plt.tight_layout()
    output_path = OUTPUT_DIR / "validation-pipeline.png"
    plt.savefig(output_path, dpi=DPI, bbox_inches='tight', facecolor='#0A0E27')
    plt.close()
    print(f"✅ 已创建: {output_path}")

if __name__ == "__main__":
    print("开始生成可视化图表...")
    create_architecture_diagram()
    create_strategy_metrics()
    create_ai_agents_workflow()
    create_validation_pipeline()
    print("\n✅ 所有图表生成完成！")
