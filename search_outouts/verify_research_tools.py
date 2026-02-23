"""
验证 research_tools.py 修改是否符合 2.4修改.md
"""
import sys
sys.path.insert(0, "e:/研二上/毕业论文/开题/vibe writing")

from research_tools import (
    DOMAIN_KEYWORDS, STRONG_SYSTEM_KEYWORDS, REPRODUCIBILITY_KEYWORDS,
    TAG_ACQUISITION, TAG_PIPELINE, TAG_SOFTWARE, TAG_DATA,
    APP_HEAVY_KEYWORDS, EXCLUDE_KEYWORDS,
    gate_filter_relaxed, compute_tags, compute_system_score, detect_app_heavy
)

print("=" * 60)
print("验证 research_tools.py 是否符合 2.4修改.md")
print("=" * 60)

# 检查1：领域词是否宽松
print("\n【检查1】领域词配置")
expected_domain = ["gait", "walking", "locomotion", "stride", "step"]
for kw in expected_domain:
    if kw in DOMAIN_KEYWORDS:
        print(f"  ✅ 包含 '{kw}'")
    else:
        print(f"  ❌ 缺少 '{kw}'")

# 检查2：强系统词
print("\n【检查2】强系统词")
expected_system = ["system", "platform", "framework", "software", "toolkit", "pipeline"]
for kw in expected_system:
    if kw in STRONG_SYSTEM_KEYWORDS:
        print(f"  ✅ 包含 '{kw}'")
    else:
        print(f"  ❌ 缺少 '{kw}'")

# 检查3：4个Tag标签
print("\n【检查3】4个Tag标签组")
print(f"  Tag-A (Acquisition): {len(TAG_ACQUISITION)} 个词")
print(f"  Tag-B (Pipeline): {len(TAG_PIPELINE)} 个词")
print(f"  Tag-C (Software): {len(TAG_SOFTWARE)} 个词")
print(f"  Tag-D (Data): {len(TAG_DATA)} 个词")

# 检查4：应用强信号词
print("\n【检查4】应用强信号词")
expected_app = ["patient", "clinical trial", "intervention", "rehabilitation", "stroke", "parkinson"]
for kw in expected_app:
    if kw in APP_HEAVY_KEYWORDS:
        print(f"  ✅ 包含 '{kw}'")
    else:
        print(f"  ❌ 缺少 '{kw}'")

# 检查5：宽松Gate测试
print("\n【检查5】宽松Gate过滤测试")

# 测试用例1：纯步态文章，应该通过
test1 = gate_filter_relaxed(
    "A gait analysis system for elderly",
    "We developed a platform for gait event detection..."
)
print(f"  测试1 (步态+系统): pass={test1['pass']}, level={test1['level']} {'✅' if test1['pass'] else '❌'}")

# 测试用例2：只有walking，无系统词，应该通过（宽松）
test2 = gate_filter_relaxed(
    "Walking patterns in athletes",
    "This study investigates stride length and cadence..."
)
print(f"  测试2 (walking+算法): pass={test2['pass']}, level={test2['level']} {'✅' if test2['pass'] else '❌'}")

# 测试用例3：包含排除词+系统词，应该降权但不reject
test3 = gate_filter_relaxed(
    "A gait analysis software for stroke patients",
    "We developed a system for rehabilitation monitoring..."
)
print(f"  测试3 (排除词+系统词=降权): pass={test3['pass']}, exclude_hit={test3['exclude_hit']} {'✅' if test3['pass'] else '❌'}")

# 测试用例4：纯动物实验，应该reject
test4 = gate_filter_relaxed(
    "Gait analysis in rats",
    "We studied mouse locomotion patterns..."
)
print(f"  测试4 (纯动物实验): pass={test4['pass']} {'✅ (rejected)' if not test4['pass'] else '❌ (should reject)'}")

# 检查6：system_score 计算
print("\n【检查6】system_score 计算测试")
score1 = compute_system_score(
    "VIGMA: An Open-Source Framework for Visual Gait Analytics",
    "We developed a GitHub-available visualization dashboard for gait analysis..."
)
print(f"  测试1 (高分): score={score1} (应该>5)")

score2 = compute_system_score(
    "Gait analysis in stroke patients",
    "This clinical trial evaluated rehabilitation outcomes in cohort patients..."
)
print(f"  测试2 (低分): score={score2} (应该<0)")

# 检查7：Tags 计算
print("\n【检查7】Tags 计算测试")
tags = compute_tags(
    "A wearable sensor system for gait analysis",
    "We developed a GUI dashboard with real-time visualization and database logging..."
)
print(f"  命中Tags: {tags}")
print(f"  期望至少3个Tag: {'✅' if len(tags) >= 3 else '❌'}")

# 检查8：app_heavy 检测
print("\n【检查8】app_heavy 检测测试")
app1 = detect_app_heavy(
    "Gait outcomes in stroke rehabilitation",
    "This clinical trial included 50 patients with intervention and cohort comparison..."
)
print(f"  测试1 (纯应用): app_heavy={app1} {'✅' if app1 else '❌'}")

app2 = detect_app_heavy(
    "Open-source gait analysis platform",
    "Our GitHub-available system provides visualization dashboard..."
)
print(f"  测试2 (系统开发): app_heavy={app2} {'✅' if not app2 else '❌'}")

print("\n" + "=" * 60)
print("验证完成！")
