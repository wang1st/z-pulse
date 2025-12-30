import Link from 'next/link'
import Icon, { Icons } from '@/components/Icon'

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="container mx-auto px-4 py-10 md:py-14">
        <Link href="/" className="inline-flex items-center gap-2 text-sm text-white/70 hover:text-white transition-colors">
          <Icon name={Icons.arrowLeft} size={16} className="text-white/80" />
          返回首页
        </Link>

        <div className="mt-6 rounded-3xl border border-white/10 bg-white/5 p-7 md:p-10">
          <h1 className="text-3xl md:text-4xl font-black tracking-tight">联系我们</h1>
          <p className="mt-4 text-white/75 leading-relaxed">
            如果你希望接入更多公众号源、调整“今日焦点/关键词”规则、或对信息聚合风格提出建议，欢迎联系我们。
          </p>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-5">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-white/85">
                <Icon name={Icons.user} size={16} className="text-white/80" />
                项目联系
              </div>
              <div className="mt-2 text-sm text-white/70 leading-relaxed">
                默认通过系统管理员渠道沟通（可在部署时补充公开邮箱/工单入口）。
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-5">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-white/85">
                <Icon name={Icons.shield} size={16} className="text-white/80" />
                安全与合规
              </div>
              <div className="mt-2 text-sm text-white/70 leading-relaxed">
                如发现不当内容/引用错误/数据问题，请提供对应报告链接与截图，便于快速定位修复。
              </div>
            </div>
          </div>

          <div className="mt-7 text-sm text-white/60">
            提示：当前页面为静态信息页，不提供在线提交表单（避免存储额外个人信息）。
          </div>
        </div>
      </div>
    </main>
  )
}


