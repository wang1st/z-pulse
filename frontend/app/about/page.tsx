import Link from 'next/link'
import Icon, { Icons } from '@/components/Icon'

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="container mx-auto px-4 py-10 md:py-14">
        <Link href="/" className="inline-flex items-center gap-2 text-sm text-white/70 hover:text-white transition-colors">
          <Icon name={Icons.arrowLeft} size={16} className="text-white/80" />
          返回首页
        </Link>

        <div className="mt-6 rounded-3xl border border-white/10 bg-white/5 p-7 md:p-10">
          <h1 className="text-3xl md:text-4xl font-black tracking-tight">关于我们</h1>
          <p className="mt-4 text-white/75 leading-relaxed">
            <b>这里财动</b> 是一个面向所有人的浙江财政信息聚合平台，
            致力于信息平权，帮助大家了解浙江财政资金的使用方向和支持重点。无论您是否在浙江，无论是否有监督权，
            都可以通过这里财动学习财政知识、了解政策动态、参与公共监督。我们通过大模型聚合每日财政信息，
            让您在 1 分钟内掌握当天全省财政相关信息的主脉络，并且做到<b>来源可查</b>、<b>事实优先</b>。
          </p>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-5">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-white/85">
                <Icon name={Icons.search} size={16} className="text-white/80" />
                数据来源
              </div>
              <div className="mt-2 text-sm text-white/70 leading-relaxed">
                以各地官方公众号文章为主，系统会保留文章链接用于引用跳转与复核。
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-5">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-white/85">
                <Icon name={Icons.fileText} size={16} className="text-white/80" />
                生成逻辑
              </div>
              <div className="mt-2 text-sm text-white/70 leading-relaxed">
                规则化 NLP 负责清洗与候选提取，大模型负责摘要、聚合与成文，并配合去重与护栏约束。
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-5">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-white/85">
                <Icon name={Icons.shield} size={16} className="text-white/80" />
                使用边界
              </div>
              <div className="mt-2 text-sm text-white/70 leading-relaxed">
                输出为信息摘要与引用索引，不构成政策解读、投资建议或任何法律意见。
              </div>
            </div>
          </div>

          <div className="mt-7 text-sm text-white/70 leading-relaxed">
            本项目为浙江省新征程财税研究院“智研未来”AI智能体创新大赛参赛作品，可根据业务反馈持续迭代生成结构与展示体验。
          </div>
        </div>
      </div>
    </main>
  )
}


