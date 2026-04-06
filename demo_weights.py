"""权重系统演示 - 展示内容优先级分配"""
import sys
sys.path.insert(0, '.')

from processors.content_prioritizer import ContentPrioritizer
from datetime import datetime


def demo_weight_system():
    """演示权重系统"""
    print("=" * 70)
    print("MI7 内容权重分配系统演示")
    print("=" * 70)

    # 初始化权重系统
    prioritizer = ContentPrioritizer()

    # 显示配置摘要
    summary = prioritizer.get_weight_summary()
    print("\n[权重配置摘要]")
    print(f"  持仓直接关联权重: {summary['weights']['holdings_direct']}%")
    print(f"  宏观/全球市场权重: {summary['weights']['macro_global']}%")
    print(f"  专家观点权重: {summary['weights']['expert_opinion']}%")
    print(f"  辅助信息权重: {summary['weights']['auxiliary']}%")
    print(f"  优先级关键词: {summary['priority_keywords_count']} 个")
    print(f"  来源权重配置: {summary['source_weights_count']} 个")
    print(f"  监控持仓: {summary['holdings_count']} 只")

    # 示例内容
    test_items = [
        {
            'title': '贵州茅台发布年报，净利润增长20%，拟每10股派现200元',
            'source': '东方财富公告',
            'content': '公司2025年实现营业收入...',
            'published_at': datetime.now()
        },
        {
            'title': '美联储宣布加息25个基点，通胀预期上升',
            'source': 'Bloomberg',
            'content': 'Federal Reserve announced...',
            'published_at': datetime.now()
        },
        {
            'title': 'Peter Schiff: 黄金是抵御通胀的最佳工具',
            'source': 'Nitter',
            'content': 'Gold remains the best hedge...',
            'published_at': datetime.now()
        },
        {
            'title': 'GitHub推出新的AI编程助手功能',
            'source': 'GitHub Blog',
            'content': 'We are excited to announce...',
            'published_at': datetime.now()
        },
        {
            'title': '中煤能源产能扩张计划获批复',
            'source': '财联社',
            'content': '公司近日获得发改委批复...',
            'published_at': datetime.now()
        }
    ]

    print("\n" + "=" * 70)
    print("内容优先级评估")
    print("=" * 70)

    # 计算优先级
    for item in test_items:
        priority, score = prioritizer.calculate_priority(item)

        # 显示图标
        icon = {
            'critical': '[C]',
            'high': '[H]',
            'medium': '[M]',
            'low': '[L]'
        }.get(priority, '[L]')

        print(f"\n{icon} [{priority.upper()}] (得分: {score})")
        print(f"   标题: {item['title'][:50]}...")
        print(f"   来源: {item['source']}")

        # 显示评分详情
        holdings_score = prioritizer.calculate_holdings_relevance(item)
        keyword_score = prioritizer.calculate_keyword_relevance(item)
        if holdings_score > 0:
            print(f"   持仓匹配: +{holdings_score}分")
        if keyword_score > 0:
            print(f"   关键词匹配: +{keyword_score}分")

    # 按优先级排序
    print("\n" + "=" * 70)
    print("按优先级排序")
    print("=" * 70)

    sorted_items = prioritizer.sort_by_priority(test_items)

    for i, item in enumerate(sorted_items, 1):
        icon = {
            'critical': '[C]',
            'high': '[H]',
            'medium': '[M]',
            'low': '[L]'
        }.get(item['priority'], '[L]')

        print(f"{i}. {icon} [{item['priority']}] {item['title'][:40]}...")

    # 分组统计
    print("\n" + "=" * 70)
    print("优先级分组统计")
    print("=" * 70)

    grouped = prioritizer.group_by_priority(test_items)

    for priority in ['critical', 'high', 'medium', 'low']:
        count = len(grouped.get(priority, []))
        icon = {'critical': '[C]', 'high': '[H]', 'medium': '[M]', 'low': '[L]'}.get(priority)
        print(f"{icon} {priority.capitalize()}: {count} 条")

    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)


if __name__ == '__main__':
    demo_weight_system()
