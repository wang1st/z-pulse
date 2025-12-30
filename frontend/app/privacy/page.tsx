import Link from 'next/link'
import Icon, { Icons } from '@/components/Icon'

export default function PrivacyPage() {
  const effectiveDate = '2025-12-18'

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="container mx-auto px-4 py-10 md:py-14">
        <Link href="/" className="inline-flex items-center gap-2 text-sm text-white/70 hover:text-white transition-colors">
          <Icon name={Icons.arrowLeft} size={16} className="text-white/80" />
          返回首页
        </Link>

        <div className="mt-6 rounded-3xl border border-white/10 bg-white/5 p-7 md:p-10">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <h1 className="text-3xl md:text-4xl font-black tracking-tight">隐私政策</h1>
            <div className="text-sm text-white/60">生效日期：{effectiveDate}</div>
          </div>

          <div className="mt-6 space-y-6 text-sm md:text-[15px] leading-relaxed text-white/80">
            <section>
              <h2 className="text-lg font-black text-white">1. 我们是谁</h2>
              <p className="mt-2">
                “这里财动”是一个浙江财政信息聚合平台，致力于信息平权，帮助所有人了解浙江财政资金的使用方向和支持重点。本政策说明我们如何收集、使用、存储与保护你的个人信息。
              </p>
            </section>

            <section>
              <h2 className="text-lg font-black text-white">2. 我们收集哪些信息</h2>
              <ul className="mt-2 list-disc pl-5 space-y-1 text-white/80">
                <li>
                  <b>订阅邮箱</b>：当你在首页提交订阅时，我们会收集你输入的邮箱地址，用于发送你订阅的晨报/周报。
                </li>
                <li>
                  <b>基础访问日志</b>：为保障系统安全与可用性，服务器可能记录必要的访问日志（如请求时间、路径、响应状态等）。
                </li>
                <li>
                  <b>报告内容与引用</b>：系统会保存生成的报告结构化内容（含引用链接），用于展示与追溯；引用的文章链接来自公开来源。
                </li>
              </ul>
              <p className="mt-2 text-white/70">
                我们不会要求你提供身份证号、银行卡号等敏感身份信息；也不会将订阅邮箱用于广告营销。
              </p>
            </section>

            <section>
              <h2 className="text-lg font-black text-white">3. 我们如何使用信息</h2>
              <ul className="mt-2 list-disc pl-5 space-y-1 text-white/80">
                <li>用于发送你订阅的晨报/周报邮件。</li>
                <li>用于系统运维（故障排查、反滥用、防攻击、安全审计）。</li>
                <li>用于改进生成质量（例如去重、引用准确性、版式体验），但不会将你的订阅邮箱用于画像或对外分享。</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-black text-white">4. 信息共享与对外提供</h2>
              <p className="mt-2">
                我们不会出售你的个人信息。为完成邮件发送，我们可能使用第三方邮件服务商代发订阅邮件（仅在提供服务所必需的范围内处理邮箱地址）。
              </p>
            </section>

            <section>
              <h2 className="text-lg font-black text-white">5. 存储与保护</h2>
              <ul className="mt-2 list-disc pl-5 space-y-1 text-white/80">
                <li>订阅邮箱与订阅偏好存储在服务器数据库中，用于持续推送。</li>
                <li>我们采取合理的技术措施保护数据安全（访问控制、最小权限、日志审计等）。</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-black text-white">6. 你的权利</h2>
              <ul className="mt-2 list-disc pl-5 space-y-1 text-white/80">
                <li>你可以随时取消订阅（通过邮件中的退订入口或联系管理员处理）。</li>
                <li>你可以请求更正/删除你的订阅邮箱信息（联系管理员处理）。</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-black text-white">7. 政策更新</h2>
              <p className="mt-2">
                我们可能会更新本政策以反映功能变化或合规要求。更新后会在本页面发布。
              </p>
            </section>
          </div>
        </div>
      </div>
    </main>
  )
}


