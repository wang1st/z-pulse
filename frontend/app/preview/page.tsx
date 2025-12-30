'use client'

import { SmartBrevityDaily } from '../components/SmartBrevityDaily'
import { WeeklyReview } from '../components/WeeklyReview'

const mockDailyReport = {
  reportDate: '2025-12-19',
  createdAt: '2025-12-19T14:02:36',
  articleCount: 54,
  contentJson: {
    schema: 'smart_brevity_v1',
    header: {
      title: '浙江多市体育场馆获中央补助开放',
      date: '2025-12-19',
      lede: '台州、三门及全省多地多家体育场馆入选2026年中央资金补助免费或低收费开放名单。',
      lede_citations: [7, 8, 9]
    },
    why_it_matters: '覆盖地市包括台州、丽水等,财政支持渠道为中央专项资金,降低公众健身成本。',
    why_citations: [7, 8],
    big_picture: '补助聚焦公益开放,申报流程由地方申报、省级审核、中央核定,2026年执行。',
    big_picture_citations: [9],
    recent_hotspots: [
      {
        event: '数字财政',
        hotness: 85,
        why_hot: '全省数字财政建设进入快车道，多项应用场景落地',
        category: '改革创新',
        source_ids: [1, 2, 7, 8],
        coverage_docs: 28,
        coverage_accounts: 12,
        last_seen: '2025-12-24'
      },
      {
        event: '专项债管理',
        hotness: 72,
        why_hot: '专项债项目全生命周期管理机制持续完善',
        category: '债务管理',
        source_ids: [3, 9, 10],
        coverage_docs: 18,
        coverage_accounts: 8,
        last_seen: '2025-12-23'
      },
      {
        event: '财政补贴',
        hotness: 68,
        why_hot: '惠企政策精准滴灌，补贴直达机制成效显著',
        category: '政策扶持',
        source_ids: [4, 11, 12, 13],
        coverage_docs: 22,
        coverage_accounts: 9,
        last_seen: '2025-12-24'
      },
      {
        event: '预算绩效',
        hotness: 65,
        why_hot: '预算绩效管理改革深化，评价结果应用加强',
        category: '预算改革',
        source_ids: [5, 14, 15],
        coverage_docs: 15,
        coverage_accounts: 7,
        last_seen: '2025-12-22'
      },
      {
        event: '税收政策',
        hotness: 61,
        why_hot: '减税降费政策持续优化，助企纾困效果显现',
        category: '收入管理',
        source_ids: [6, 16, 17],
        coverage_docs: 19,
        coverage_accounts: 8,
        last_seen: '2025-12-23'
      },
      {
        event: '政府采购',
        hotness: 58,
        why_hot: '政府采购数字化转型提速，营商环境持续优化',
        category: '制度改革',
        source_ids: [7, 18],
        coverage_docs: 12,
        coverage_accounts: 6,
        last_seen: '2025-12-21'
      },
      {
        event: '国企监管',
        hotness: 54,
        why_hot: '国资监管效能提升，国企改革纵深推进',
        category: '国资管理',
        source_ids: [8, 19, 20],
        coverage_docs: 14,
        coverage_accounts: 6,
        last_seen: '2025-12-24'
      }
    ],
    recent_hotspots_meta: {
      window_days: 7
    },
    sources: [
      { id: 1, account: '嘉兴发布', title: '结婚、养老都能"领钱"!嘉兴"民生礼包"超暖心', url: '#' },
      { id: 2, account: '富阳发布', title: '10万元补贴!277套!富阳迎来一波购房热', url: '#' },
      { id: 3, account: '婺城发布', title: '12月31日截止!这几笔补贴,符合条件的婺城人赶紧申领', url: '#' },
      { id: 4, account: '嘉兴发布', title: '这几笔补贴年底截止!嘉兴人抓紧', url: '#' },
      { id: 5, account: '开化发布', title: '12月31日截止!这几笔补贴,符合条件的开化人赶紧申领', url: '#' },
      { id: 6, account: '缙云发布', title: '符合条件的缙云人抓紧了!这几项补贴12月31日截止', url: '#' },
      { id: 7, account: '台州发布', title: '台州这些体育场馆,免费或低收费!', url: '#' },
      { id: 8, account: '温州发布', title: '这些体育场馆,免费或低收费!', url: '#' },
      { id: 9, account: '掌上三门', title: '三门这些体育场馆,免费或低收费!', url: '#' },
      { id: 10, account: '余杭发布', title: '数量全省第一!余杭新增109家', url: '#' },
      { id: 11, account: '平阳发布', title: '平阳,迈步向"新"!', url: '#' }
    ],
    easter_egg: {
      title: '玉环"三件套",申请出道!',
      account: '玉环发布',
      url: '#',
      teaser: '玉环版"三件套":海鲜面、锡饼、文旦,地道风味等你来尝!'
    },
    visual_focus: 'common_issue',
    focus_style: 'action_chain',
    keywords: [
      {
        word: '消费券',
        weight: 100,
        hotness: 100,
        citations: 2,
        source_ids: [1, 2],
        snippets: []
      },
      {
        word: '育儿补贴',
        weight: 80,
        hotness: 80,
        citations: 7,
        source_ids: [3, 4, 5, 6, 7, 8, 9],
        snippets: []
      },
      {
        word: 'R&D经费',
        weight: 60,
        hotness: 60,
        citations: 2,
        source_ids: [10, 11],
        snippets: []
      }
    ]
  }
}

// 12月22日（周一）生成的周报（Markdown格式）
const mockWeeklyReportMarkdown = {
  reportDate: '2025年12月16日 至 12月22日',
  createdAt: '2025-12-22T10:05:00',
  articleCount: 356,
  summaryMarkdown: `# 一周述评：2025年12月16日 至 12月22日

## 本周概览

本周浙江省财政系统围绕数字化转型、财政改革创新、民生保障等重点领域持续推进，各项工作取得阶段性成效。数字财政建设全面提速，预算绩效管理纵深推进，为全省经济社会高质量发展提供坚实保障[1]。

从整体来看，本周财政动态呈现出三个显著特点：一是数字化改革步伐加快，多地推出财政数字化应用场景；二是民生保障政策密集出台，涉及补贴、救助、医疗等多个领域；三是财政资金使用效率持续提升，预算绩效管理改革不断深化[2]。

## 核心主题分析

### 数字财政建设

本周数字财政建设成为全省关注焦点，多项创新应用落地。杭州、宁波、温州等地相继推出财政数字化平台，实现财政业务"一网通办"[3]。台州市财政局上线"智慧财政"系统，实现预算编制、执行、监督全流程数字化管理[4]。

数字财政建设不仅提升了财政管理效率，也为优化营商环境提供了有力支撑。通过数据共享和业务协同，财政服务更加便民高效[5]。

### 财政补贴政策

本周各地财政补贴政策密集出台，覆盖范围广泛。嘉兴市推出"民生礼包"，包括结婚补贴、养老补贴等多项惠民政策[6]。富阳区发放购房补贴，最高可达10万元，有效刺激了房地产市场[7]。

补贴政策的精准滴灌，体现了财政资金使用的精准性和有效性。通过直达机制，补贴资金能够快速到达受益对象，提升了政策执行效率[8]。

### 预算绩效管理

预算绩效管理改革持续深化，评价结果应用不断加强。本周多地发布预算绩效评价报告，对财政资金使用效果进行全面评估[9]。开化、缙云等地建立预算绩效管理长效机制，将评价结果与预算安排挂钩[10]。

预算绩效管理的深入推进，有助于提高财政资金使用效益，确保每一分钱都花在刀刃上[11]。

## 数据观察

本周全省财政相关文章共356篇，涉及15个不同公众号。从文章分布来看，数字财政、财政补贴、预算绩效管理是本周最热门的三个主题，分别占比28%、22%和18%[12]。

从时间分布来看，本周财政动态主要集中在周中（12月18日-20日），这与各地政策发布节奏相符[13]。

## 下周展望

基于本周趋势，预计下周财政工作将继续聚焦数字化转型和民生保障。数字财政建设有望在更多地区落地应用，民生补贴政策将继续精准发力[14]。同时，预算绩效管理改革将向纵深推进，评价结果应用机制将进一步完善[15]。`
}

const mockWeeklyReport = {
  reportDate: '2025-12-24',
  createdAt: '2025-12-24T22:00:00',
  articleCount: 356,
  contentJson: {
    schema: 'smart_brevity_v1',
    header: {
      title: '浙江财政周报：数字化转型引领高质量发展',
      lede: '本周浙江省财政系统围绕数字化转型、财政改革创新等重点领域持续推进，各项工作取得阶段性成效。数字财政建设全面提速，预算绩效管理纵深推进，为全省经济社会高质量发展提供坚实保障。',
      lede_citations: [1, 2, 3]
    },
    why_it_matters: '本周浙江财政在数字化改革、预算管理、债务风险防控等多个领域取得重要进展，彰显财政改革的浙江智慧，为全国财政改革提供可复制可推广的经验。',
    why_citations: [4, 5],
    // 周报没有 big_picture 字段
    recent_hotspots: [
      {
        event: '数字财政',
        hotness: 92,
        why_hot: '本周数字财政建设成为全省关注焦点，多项创新应用落地',
        category: '改革创新',
        source_ids: [1, 2, 6, 7, 8],
        coverage_docs: 45,
        coverage_accounts: 18,
        last_seen: '2025-12-24'
      },
      {
        event: '财政稳进提质',
        hotness: 88,
        why_hot: '全省财政稳进提质政策持续发力，经济支撑作用凸显',
        category: '宏观政策',
        source_ids: [3, 9, 10, 11],
        coverage_docs: 38,
        coverage_accounts: 15,
        last_seen: '2025-12-24'
      },
      {
        event: '共同富裕',
        hotness: 82,
        why_hot: '财政助力共同富裕示范区建设取得新进展',
        category: '发展战略',
        source_ids: [4, 12, 13, 14],
        coverage_docs: 32,
        coverage_accounts: 13,
        last_seen: '2025-12-23'
      },
      {
        event: '债务风险防控',
        hotness: 76,
        why_hot: '地方政府债务风险防控机制持续完善',
        category: '风险管理',
        source_ids: [5, 15, 16],
        coverage_docs: 28,
        coverage_accounts: 11,
        last_seen: '2025-12-24'
      },
      {
        event: '预算绩效管理',
        hotness: 71,
        why_hot: '预算绩效管理改革深化，评价结果应用加强',
        category: '预算改革',
        source_ids: [6, 17, 18, 19],
        coverage_docs: 25,
        coverage_accounts: 10,
        last_seen: '2025-12-23'
      },
      {
        event: '政府采购改革',
        hotness: 68,
        why_hot: '政府采购数字化转型提速，营商环境持续优化',
        category: '制度改革',
        source_ids: [7, 20, 21],
        coverage_docs: 22,
        coverage_accounts: 9,
        last_seen: '2025-12-22'
      },
      {
        event: '税收优惠政策',
        hotness: 65,
        why_hot: '减税降费政策持续优化，助企纾困效果显现',
        category: '收入管理',
        source_ids: [8, 22, 23, 24],
        coverage_docs: 20,
        coverage_accounts: 8,
        last_seen: '2025-12-24'
      }
    ],
    recent_hotspots_meta: {
      window_days: 7
    },
    sources: Array.from({ length: 30 }, (_, i) => ({
      id: i + 1,
      account: `浙江财政${(i % 10) + 1}`, // 模拟10个不同的公众号
      title: `财政改革相关政策文件 ${i + 1}`,
      url: '#'
    })),
    visual_focus: 'high_impact_event',
    focus_style: 'action_chain',
    easter_egg: {
      title: '浙江财政数字化转型典型案例集',
      account: '浙江财政',
      url: '#',
      teaser: '本周精选：深入解析浙江财政数字化转型的典型案例，展现财政改革的创新实践与成效。'
    },
    keywords: [
      {
        word: '数字财政',
        weight: 92,
        hotness: 92,
        citations: 18,
        source_ids: [1, 2, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
        snippets: []
      },
      {
        word: '财政稳进提质',
        weight: 88,
        hotness: 88,
        citations: 15,
        source_ids: [3, 9, 10, 11, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32],
        snippets: []
      },
      {
        word: '共同富裕',
        weight: 82,
        hotness: 82,
        citations: 13,
        source_ids: [4, 12, 13, 14, 33, 34, 35, 36, 37, 38, 39, 40, 41],
        snippets: []
      }
    ]
  }
}

export default function PreviewPage() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* 标题 */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">UI预览模式</h1>
        <p className="text-slate-600">最后一次提交的晨报布局和主题预览（晨报 + 周报）</p>
        </div>

        {/* 晨报预览 */}
        <div className="mb-16">
          <div className="mb-4 text-center">
            <h2 className="text-xl font-semibold text-slate-700">晨报效果预览</h2>
          </div>
          <SmartBrevityDaily
            reportTypeLabel="晨报"
            reportDate={mockDailyReport.reportDate}
            createdAt={mockDailyReport.createdAt}
            articleCount={mockDailyReport.articleCount}
            contentJson={mockDailyReport.contentJson}
          />
        </div>

        <div className="border-t border-slate-200 my-16"></div>

      {/* 周报预览（新格式：Markdown述评） */}
        <div>
          <div className="mb-4 text-center">
          <h2 className="text-xl font-semibold text-slate-700">周报效果预览（12月22日生成）</h2>
        </div>
        <WeeklyReview
          reportDate={mockWeeklyReportMarkdown.reportDate}
          createdAt={mockWeeklyReportMarkdown.createdAt}
          articleCount={mockWeeklyReportMarkdown.articleCount}
          summaryMarkdown={mockWeeklyReportMarkdown.summaryMarkdown}
        />
      </div>
    </div>
  )
}
