'use client'

import { useEffect, useState } from 'react'

export const dynamic = 'force-dynamic'

interface QRCodeResponse {
  success: boolean
  qr_url?: string
  uuid?: string
  code?: string
  msg?: string
  login_status?: boolean
}

function WeRSSQRCodeDirectContent() {
  const [status, setStatus] = useState<'loading' | 'ready' | 'error' | 'success'>('loading')
  const [qrCodeUrl, setQrCodeUrl] = useState<string>('')
  const [message, setMessage] = useState<string>('')
  const [error, setError] = useState<string>('')

  useEffect(() => {
    fetchQRCode()
  }, [])

  const fetchQRCode = async () => {
    try {
      console.log('Fetching QR code...')

      // 使用window.location.hostname来构建API URL
      const protocol = window.location.protocol
      const hostname = window.location.hostname
      const apiUrl = `${protocol}//${hostname}:8000/api/werss/qrcode`

      console.log('API URL:', apiUrl)
      const response = await fetch(apiUrl)
      console.log('Response status:', response.status)

      const data: QRCodeResponse = await response.json()
      console.log('Response data:', data)

      if (data.success && data.qr_url) {
        setQrCodeUrl(data.qr_url)
        if (data.msg) {
          setMessage(data.msg)
        }
        setStatus('ready')
        startPolling()
      } else {
        console.error('Invalid response:', data)
        setError(`获取二维码失败: ${JSON.stringify(data)}`)
        setStatus('error')
      }
    } catch (err) {
      console.error('Failed to fetch QR code:', err)
      setError(`服务器错误: ${err}`)
      setStatus('error')
    }
  }

  const startPolling = () => {
    const interval = setInterval(async () => {
      try {
        const protocol = window.location.protocol
        const hostname = window.location.hostname
        const apiUrl = `${protocol}//${hostname}:8000/api/werss/qrcode/status`

        const response = await fetch(apiUrl)
        const data: QRCodeResponse = await response.json()

        if (data.success && data.login_status === true) {
          clearInterval(interval)
          setStatus('success')
        }
      } catch (err) {
        console.error('Polling error:', err)
      }
    }, 2000)

    return () => clearInterval(interval)
  }

  const handleConfirm = () => {
    alert('✅ 登录成功！微信公众号Token已更新，此页面现在可以关闭了。')
  }

  if (status === 'loading') {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.spinner}></div>
          <p style={styles.loadingText}>正在获取二维码...</p>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.errorIcon}>⚠️</div>
          <h1 style={styles.title}>获取失败</h1>
          <p style={styles.message}>{error}</p>
          <button onClick={fetchQRCode} style={styles.retryButton}>
            🔄 重试
          </button>
        </div>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.successIcon}>✅</div>
          <h1 style={styles.title}>登录成功！</h1>
          <p style={styles.message}>
            微信公众号Token已成功更新，现在可以关闭此页面了。
          </p>
          <button onClick={handleConfirm} style={styles.successButton}>
            确定
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>📱 微信公众号扫码登录</h1>

        <div style={styles.qrContainer}>
          <img
            src={`${typeof window !== 'undefined' ? window.location.protocol : 'http:'}//${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:8080/${qrCodeUrl}`}
            alt="微信扫码登录"
            style={styles.qrImage}
          />
        </div>

        {message && (
          <div style={styles.messageBox}>
            <p style={styles.messageText}>{message}</p>
          </div>
        )}

        <div style={styles.instructions}>
          <h3 style={styles.instructionsTitle}>📋 操作步骤：</h3>
          <ol style={styles.stepsList}>
            <li>使用微信扫描上方二维码</li>
            <li>在手机上确认登录</li>
            <li>页面会自动显示"登录成功"</li>
            <li>关闭此页面即可</li>
          </ol>
        </div>

        <div style={styles.notice}>
          <p style={styles.noticeText}>
            💡 <strong>提示：</strong>二维码每30秒自动刷新，如果扫码无效请等待刷新
          </p>
        </div>
      </div>
    </div>
  )
}

export default function WeRSSQRCodeDirectPage() {
  return <WeRSSQRCodeDirectContent />
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
    fontSize: '64px',
    marginBottom: '20px',
  },
  successIcon: {
    fontSize: '64px',
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
    marginBottom: '20px',
  },
  retryButton: {
    padding: '14px 28px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  successButton: {
    padding: '14px 28px',
    backgroundColor: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  qrContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '20px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  qrImage: {
    width: '280px',
    height: '280px',
    objectFit: 'contain' as const,
  },
  messageBox: {
    backgroundColor: '#fff3cd',
    border: '1px solid #ffc107',
    padding: '12px',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  messageText: {
    fontSize: '14px',
    color: '#856404',
    margin: 0,
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
    fontSize: '18px',
  },
  stepsList: {
    margin: 0,
    paddingLeft: '20px',
    color: '#666',
    lineHeight: '1.8',
  },
  notice: {
    backgroundColor: '#e7f3ff',
    padding: '15px',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  noticeText: {
    fontSize: '14px',
    color: '#004085',
    margin: 0,
  },
}
