'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'

export const dynamic = 'force-dynamic'

interface TokenVerifyResponse {
  valid: boolean
  account_id: string | null
  account_name: string | null
  message: string
}

function WeRSSReloginContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [accountInfo, setAccountInfo] = useState<{
    account_id: string
    account_name: string
  } | null>(null)

  useEffect(() => {
    if (!token) {
      setError('缺少访问令牌，请从邮件链接访问此页面')
      setLoading(false)
      return
    }

    verifyToken()
  }, [token ?? ''])

  const verifyToken = async () => {
    if (!token) return

    try {
      const response = await fetch(
        `/api/werss-relogin/verify?token=${encodeURIComponent(token)}`
      )
      const data: TokenVerifyResponse = await response.json()

      if (data.valid && data.account_id) {
        setAccountInfo({
          account_id: data.account_id,
          account_name: data.account_name || '未知公众号'
        })
      } else {
        setError(data.message || '令牌验证失败')
      }
    } catch (err) {
      console.error('Token verification error:', err)
      setError('服务器错误，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async () => {
    if (!token) {
      alert('令牌无效')
      return
    }

    try {
      await fetch(
        `/api/werss-relogin/confirm?token=${encodeURIComponent(token)}`,
        { method: 'POST' }
      )
      alert('重新登录成功！此页面现在可以关闭了。')
    } catch (err) {
      console.error('Confirm error:', err)
      alert('确认失败，但登录可能已成功，请关闭此页面。')
    }
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.spinner}></div>
          <p style={styles.loadingText}>正在验证令牌...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.errorIcon}>⚠️</div>
          <h1 style={styles.title}>访问失败</h1>
          <p style={styles.message}>{error}</p>
          <p style={styles.hint}>
            此链接已失效或无效。如果您需要重新登录微信公众号，请联系管理员重新发送提醒邮件。
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.successIcon}>✅</div>
        <h1 style={styles.title}>微信公众号重新登录</h1>

        {accountInfo && (
          <div style={styles.accountInfo}>
            <p><strong>公众号：</strong>{accountInfo.account_name}</p>
            <p><strong>Feed ID：</strong>{accountInfo.account_id}</p>
          </div>
        )}

        <div style={styles.instructions}>
          <h3 style={styles.instructionsTitle}>📱 操作步骤：</h3>
          <ol style={styles.stepsList}>
            <li>点击下方按钮打开WeRSS扫码页面</li>
            <li>使用微信扫描二维码</li>
            <li>确认登录</li>
            <li>完成后返回点击"已完成登录"按钮</li>
          </ol>
        </div>

        <div style={styles.buttonGroup}>
          <a
            href={`http://localhost:8080/manage/feed/${accountInfo?.account_id}`}
            target="_blank"
            rel="noopener noreferrer"
            style={styles.primaryButton}
            onClick={() => {}}
          >
            📱 打开扫码页面
          </a>

          <button
            onClick={handleConfirm}
            style={styles.secondaryButton}
          >
            ✅ 已完成登录
          </button>
        </div>

        <p style={styles.note}>
          <strong>注意：</strong>此令牌24小时内有效。完成后请点击"已完成登录"按钮。
        </p>

        <Link href="/" style={styles.homeLink}>
          返回首页
        </Link>
      </div>
    </div>
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f5f5',
    padding: '20px',
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '40px',
    maxWidth: '500px',
    width: '100%',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
    textAlign: 'center' as const,
  },
  spinner: {
    border: '4px solid #f3f3f3',
    borderTop: '4px solid #007bff',
    borderRadius: '50%',
    width: '40px',
    height: '40px',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 20px',
  },
  loadingText: {
    fontSize: '16px',
    color: '#666',
    margin: 0,
  },
  errorIcon: {
    fontSize: '48px',
    marginBottom: '20px',
  },
  successIcon: {
    fontSize: '48px',
    marginBottom: '20px',
  },
  title: {
    fontSize: '24px',
    fontWeight: 'bold',
    marginBottom: '20px',
    color: '#333',
  },
  message: {
    fontSize: '16px',
    color: '#666',
    marginBottom: '15px',
  },
  hint: {
    fontSize: '14px',
    color: '#999',
    lineHeight: '1.6',
    marginTop: '20px',
    paddingTop: '20px',
    borderTop: '1px solid #eee',
  },
  accountInfo: {
    backgroundColor: '#f8f9fa',
    padding: '15px',
    borderRadius: '8px',
    marginBottom: '20px',
    textAlign: 'left' as const,
  },
  instructions: {
    textAlign: 'left' as const,
    backgroundColor: '#f8f9fa',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  instructionsTitle: {
    marginTop: 0,
    marginBottom: '15px',
    color: '#333',
  },
  stepsList: {
    margin: 0,
    paddingLeft: '20px',
    color: '#666',
    lineHeight: '1.8',
  },
  buttonGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '10px',
    marginBottom: '20px',
  },
  primaryButton: {
    display: 'block',
    padding: '14px 24px',
    backgroundColor: '#007bff',
    color: 'white',
    textDecoration: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: 'bold',
    transition: 'background-color 0.2s',
    border: 'none',
    cursor: 'pointer',
  },
  secondaryButton: {
    padding: '14px 24px',
    backgroundColor: 'white',
    color: '#007bff',
    border: '2px solid #007bff',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: 'bold',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  note: {
    fontSize: '13px',
    color: '#999',
    marginBottom: '20px',
  },
  homeLink: {
    display: 'block',
    fontSize: '14px',
    color: '#007bff',
    textDecoration: 'none',
  },
}

export default function WeRSSReloginPage() {
  return (
    <Suspense fallback={
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.spinner}></div>
          <p style={styles.loadingText}>加载中...</p>
        </div>
      </div>
    }>
      <WeRSSReloginContent />
    </Suspense>
  )
}
