import Link from 'next/link'
import Icon, { Icons } from '@/components/Icon'

export default function SubscriptionConfirmedPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="container mx-auto px-4 py-16">
        <div className="mx-auto max-w-2xl rounded-3xl border border-white/10 bg-white/5 p-8 md:p-10">
          <div className="flex items-start gap-4">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-emerald-500/15 border border-emerald-400/20">
              <Icon name={Icons.success} size={22} className="text-emerald-300" />
            </div>
            <div className="flex-1">
              <h1 className="text-2xl md:text-3xl font-black tracking-tight">订阅已成功激活</h1>
              <p className="mt-2 text-sm md:text-base text-white/70 leading-relaxed">
                之后我们会将“这里财动”每日晨报发送到你的邮箱。若未收到，请先检查垃圾邮件/广告邮件。
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  href="/reports/daily"
                  className="inline-flex items-center gap-2 rounded-full bg-white text-slate-950 px-5 py-2.5 text-sm font-semibold hover:bg-white/90 transition-colors"
                >
                  查看最新晨报
                  <Icon name={Icons.arrowLeft} size={16} className="rotate-180" />
                </Link>
                <Link
                  href="/"
                  className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/10 transition-colors"
                >
                  返回首页
                  <Icon name={Icons.dashboard} size={16} className="text-white/80" />
                </Link>
              </div>

              <div className="mt-6 rounded-2xl border border-white/10 bg-slate-900/40 p-4 text-sm text-white/70">
                <div className="font-semibold text-white/85">小提示</div>
                <ul className="mt-2 space-y-1">
                  <li>1) 将发件人加入白名单，可提升送达率</li>
                  <li>2) 若你误订阅，可在后续邮件中取消订阅</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}


