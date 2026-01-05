import Link from 'next/link'
import { LatestReports } from './components/LatestReports'
import { SubscribeForm } from './components/SubscribeForm'
import Icon, { Icons } from '@/components/Icon'

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      {/* Hero */}
      <div className="relative overflow-hidden bg-gradient-to-b from-slate-50 to-white">
        <div className="container mx-auto px-4 py-14 md:py-20">
          <div className="mx-auto max-w-4xl">
            <div className="inline-flex flex-wrap items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600">
              <span className="inline-flex items-center gap-2">
                <Icon name={Icons.shield} size={14} className="text-slate-500" />
                参赛作品｜"智研未来"AI智能体创新大赛
              </span>
              <span className="text-slate-300">·</span>
              <span className="inline-flex items-center gap-2">
                <Icon name={Icons.reports} size={14} className="text-slate-500" />
                大模型聚合的财政情报
              </span>
            </div>

            <h1 className="mt-6 text-[42px] md:text-[64px] leading-[1.05] font-black tracking-tight text-slate-900">
              浙财脉动
            </h1>
            <p className="mt-4 text-base md:text-lg text-slate-600 leading-relaxed">
              每天 1 分钟，把浙江各地官微发布的财政相关动态浓缩成一份可追溯、可点击引用的"今日焦点"。
              我们用大模型技术，做到"短而密、事实为主、来源可查"。
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-3">
              <Link
                href="/reports/daily"
                className="inline-flex items-center gap-2 rounded-full bg-slate-900 text-white px-5 py-2.5 text-sm font-semibold hover:bg-slate-800 transition-colors"
              >
                查看最新晨报
                <Icon name={Icons.arrowLeft} size={16} className="rotate-180" />
              </Link>
              <Link
                href="/reports/weekly"
                className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-900 hover:bg-slate-50 transition-colors"
              >
                查看周报
                <Icon name={Icons.reports} size={16} className="text-slate-600" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 py-12 md:py-16">
        {/* Feature strip */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-indigo-600 text-white">
              <Icon name={Icons.search} size={18} className="text-white" />
            </div>
            <div className="mt-4 text-lg font-semibold text-slate-900">筛选更克制</div>
            <div className="mt-2 text-sm text-slate-600 leading-relaxed">
              先筛财政相关，再做逐篇摘要与关键词聚合，避免"全都算相关"的信息噪声。
            </div>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-emerald-600 text-white">
              <Icon name={Icons.fileText} size={18} className="text-white" />
            </div>
            <div className="mt-4 text-lg font-semibold text-slate-900">焦点更突出</div>
            <div className="mt-2 text-sm text-slate-600 leading-relaxed">
              每天只写一个主事件/共性问题，用"事实句 + 引用"呈现，阅读路径更短。
            </div>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-sky-600 text-white">
              <Icon name={Icons.link} size={18} className="text-white" />
            </div>
            <div className="mt-4 text-lg font-semibold text-slate-900">来源可点击</div>
            <div className="mt-2 text-sm text-slate-600 leading-relaxed">
              关键词/焦点引用直接跳转到公众号原文，方便复核与深读。
            </div>
          </div>
        </div>

        {/* Latest Reports */}
        <div className="mt-10 md:mt-14">
          <div className="flex items-end justify-between gap-4">
            <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">最新报告</h2>
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Link href="/reports/daily" className="hover:text-slate-900 transition-colors">更多晨报</Link>
              <span className="text-slate-300">/</span>
              <Link href="/reports/weekly" className="hover:text-slate-900 transition-colors">更多周报</Link>
            </div>
          </div>
          <div className="mt-5">
            <LatestReports />
          </div>
        </div>

        {/* Subscribe */}
        <div className="mt-12 md:mt-16">
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-7 md:p-10">
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
              <div className="max-w-xl">
                <div className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">订阅每日晨报</div>
                <div className="mt-2 text-sm md:text-base text-slate-600 leading-relaxed">
                  用邮箱接收"浙财脉动"每日财政信息摘要。我们只发送你订阅的内容，不做营销邮件。
                </div>
              </div>
              <div className="w-full md:max-w-md">
                <SubscribeForm />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-slate-50 py-10">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm text-slate-600">© {new Date().getFullYear()} 浙财脉动 · Z-Pulse</p>
          <div className="mt-4 text-sm">
            <Link href="/about" className="text-slate-600 hover:text-slate-900 mx-2 transition-colors">
              关于我们
            </Link>
            <Link href="/privacy" className="text-slate-600 hover:text-slate-900 mx-2 transition-colors">
              隐私政策
            </Link>
            <Link href="/contact" className="text-slate-600 hover:text-slate-900 mx-2 transition-colors">
              联系我们
            </Link>
          </div>
        </div>
      </footer>
    </main>
  )
}

