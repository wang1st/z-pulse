'use client'

import { useEffect, useState, useRef } from 'react'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import Icon, { Icons } from '@/components/Icon'
import { useToast } from '@/components/ui/toast'
import { useConfirm } from '@/components/ui/confirm'
import { formatBeijingDateTimeFromApi } from '@/lib/datetime'

interface OfficialAccount {
  id: number
  name: string
  wechat_id: string | null
  werss_feed_id: string | null
  is_active: boolean
  total_articles: number
  last_collection_time: string | null
  created_at: string
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<OfficialAccount[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingAccount, setEditingAccount] = useState<OfficialAccount | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<any>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterActive, setFilterActive] = useState<string>('all')
  const { toast } = useToast()
  const { confirm } = useConfirm()
  const [page, setPage] = useState<number>(0)
  const [limit, setLimit] = useState<number>(20)
  const [hasNext, setHasNext] = useState<boolean>(false)

  useEffect(() => {
    setPage(0)
    fetchAccounts()
  }, [limit, filterActive])

  const fetchAccounts = async () => {
    try {
      const params: any = { skip: page * limit, limit }
      if (filterActive === 'active') params.is_active = true
      if (filterActive === 'inactive') params.is_active = false
      const response = await api.get('/admin/accounts', { params })
      const list: OfficialAccount[] = response.data || []
      setAccounts(list)
      setHasNext(list.length === limit)
    } catch (error) {
      console.error('Failed to fetch accounts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    const ok = await confirm({
      title: '删除公众号',
      description: '确定要删除这个公众号吗？相关的文章记录也会被级联删除。',
      confirmText: '删除',
      cancelText: '取消',
      variant: 'destructive',
    })
    if (!ok) {
      return
    }

    try {
      await api.delete(`/admin/accounts/${id}`)
      fetchAccounts()
    } catch (error) {
      console.error('Failed to delete account:', error)
      toast({ title: '删除失败', description: '请稍后重试', variant: 'error' })
    }
  }

  const handleToggleActive = async (account: OfficialAccount) => {
    try {
      await api.put(`/admin/accounts/${account.id}`, {
        is_active: !account.is_active,
      })
      fetchAccounts()
      toast({
        title: '已更新',
        description: `公众号已${account.is_active ? '停用' : '启用'}`,
        variant: 'success',
      })
    } catch (error) {
      console.error('Failed to update account:', error)
      toast({ title: '更新失败', description: '请稍后重试', variant: 'error' })
    }
  }

  const handleEdit = (account: OfficialAccount) => {
    setEditingAccount(account)
    setShowForm(true)
  }

  const handleImport = async (file: File) => {
    setImporting(true)
    setImportResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await api.post('/admin/accounts/import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setImportResult(response.data)
      if (response.data.success_count > 0) {
        fetchAccounts()
        setTimeout(() => {
          setShowImport(false)
          setImportResult(null)
        }, 2000)
      }
    } catch (error: any) {
      setImportResult({
        success: false,
        message: error.response?.data?.detail || '导入失败',
        errors: error.response?.data?.errors || [],
      })
    } finally {
      setImporting(false)
    }
  }

  const handleExport = async () => {
    try {
      const response = await api.get('/admin/accounts/export', {
        responseType: 'blob',
      })

      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = `accounts_export_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast({ title: '导出成功', description: '已开始下载文件', variant: 'success' })
    } catch (error: any) {
      console.error('Failed to export:', error)
      let errorMsg = '导出失败，请检查网络连接'
      if (error.response) {
        // 尝试读取blob错误响应
        if (error.response.data instanceof Blob) {
          const text = await error.response.data.text()
          try {
            const json = JSON.parse(text)
            errorMsg = json.detail || errorMsg
          } catch {
            errorMsg = text || errorMsg
          }
        } else {
          errorMsg = error.response.data?.detail || errorMsg
        }
      }
      toast({ title: '导出失败', description: errorMsg, variant: 'error' })
    }
  }

  // 过滤和搜索
  const filteredAccounts = accounts.filter(account => {
    const matchesSearch = !searchTerm || 
      account.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (account.wechat_id && account.wechat_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (account.werss_feed_id && account.werss_feed_id.toLowerCase().includes(searchTerm.toLowerCase()))
    
    const matchesActive = filterActive === 'all' || 
      (filterActive === 'active' && account.is_active) ||
      (filterActive === 'inactive' && !account.is_active)
    
    return matchesSearch && matchesActive
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题区域 - 带渐变背景 */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 p-6 sm:p-8 shadow-xl">
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="text-white">
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2">公众号管理</h1>
            <p className="text-indigo-100 text-sm sm:text-base">管理和监控所有公众号账号</p>
          </div>
          <div className="flex flex-wrap gap-2 sm:gap-3">
            <Button 
              variant="secondary" 
              onClick={handleExport} 
              className="bg-white/90 hover:bg-white text-indigo-600 shadow-md hover:shadow-lg transition-all"
            >
              <Icon name={Icons.download} size={16} className="mr-2" />
              <span className="hidden sm:inline">导出</span>
              <span className="sm:hidden">导出</span>
            </Button>
            <Button 
              variant="secondary" 
              onClick={() => setShowImport(true)} 
              className="bg-white/90 hover:bg-white text-indigo-600 shadow-md hover:shadow-lg transition-all"
            >
              <Icon name={Icons.upload} size={16} className="mr-2" />
              <span className="hidden sm:inline">导入</span>
              <span className="sm:hidden">导入</span>
            </Button>
            <Button 
              onClick={() => {
                setEditingAccount(null)
                setShowForm(true)
              }} 
              className="bg-white hover:bg-indigo-50 text-indigo-600 shadow-md hover:shadow-lg transition-all font-semibold"
            >
              <Icon name={Icons.add} size={16} className="mr-2" />
              <span className="hidden sm:inline">添加公众号</span>
              <span className="sm:hidden">添加</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 搜索和过滤卡片 - 带玻璃态效果 */}
      <Card className="shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.7)' }}>
        <CardHeader className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-t-lg">
          <CardTitle className="flex items-center gap-2">
            <Icon name={Icons.search} size={20} className="text-indigo-600" />
            搜索和过滤
          </CardTitle>
          <CardDescription>使用以下选项筛选公众号列表</CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="relative">
              <Icon name={Icons.search} size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground z-10" />
              <Input
                placeholder="搜索名称、微信ID、Feed ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-white/80 border-indigo-200 focus:border-indigo-400 focus:ring-indigo-400"
              />
            </div>
            <Select value={filterActive} onValueChange={setFilterActive}>
              <SelectTrigger className="bg-white/80 border-indigo-200">
                <SelectValue placeholder="选择状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="active">仅启用</SelectItem>
                <SelectItem value="inactive">仅停用</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {filteredAccounts.length !== accounts.length && (
            <div className="mt-4 p-3 bg-indigo-50 rounded-lg border border-indigo-200">
              <p className="text-sm text-indigo-700 font-medium">
                显示 <span className="font-bold">{filteredAccounts.length}</span> / <span className="font-bold">{accounts.length}</span> 个公众号
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 数据表格卡片 - 带玻璃态效果 */}
      <Card className="shadow-xl border-0 backdrop-blur-sm" style={{ background: 'rgba(255, 255, 255, 0.7)' }}>
        <CardHeader className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-t-lg">
          <CardTitle className="flex items-center gap-2">
            <Icon name={Icons.fileText} size={20} className="text-indigo-600" />
            公众号列表
          </CardTitle>
          <CardDescription>管理所有已注册的公众号账号</CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          {filteredAccounts.length === 0 ? (
            <div className="text-center py-16">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 mb-4">
                <Icon name={Icons.fileText} size={40} className="text-indigo-400" />
              </div>
              <h3 className="mt-4 text-xl font-semibold text-gray-900">暂无数据</h3>
              <p className="mt-2 text-sm text-gray-500">
                {accounts.length === 0 ? '还没有添加任何公众号' : '没有找到匹配的公众号'}
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-indigo-200 overflow-hidden bg-white/50">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-gradient-to-r from-indigo-50 to-purple-50">
                    <TableRow className="border-indigo-200">
                      <TableHead className="font-semibold text-gray-700">状态</TableHead>
                      <TableHead className="font-semibold text-gray-700">名称</TableHead>
                      <TableHead className="font-semibold text-gray-700 hidden md:table-cell">微信ID</TableHead>
                      <TableHead className="font-semibold text-gray-700 hidden lg:table-cell">Feed ID</TableHead>
                      <TableHead className="font-semibold text-gray-700">文章数</TableHead>
                      <TableHead className="font-semibold text-gray-700 hidden lg:table-cell">最后采集</TableHead>
                      <TableHead className="text-right font-semibold text-gray-700">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredAccounts.map((account, index) => (
                      <TableRow 
                        key={account.id}
                        className="border-indigo-100 hover:bg-indigo-50/50 transition-colors"
                        style={{ animationDelay: `${index * 50}ms` }}
                      >
                        <TableCell>
                          <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${account.is_active ? 'bg-gray-100 text-gray-700' : 'bg-gray-100 text-gray-500'}`}>
                            {account.is_active ? '已启用' : '已停用'}
                          </span>
                        </TableCell>
                        <TableCell className="font-medium">
                          <div className="font-semibold text-gray-900">{account.name}</div>
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-gray-700">
                          {account.wechat_id || '-'}
                        </TableCell>
                        <TableCell className="hidden lg:table-cell text-gray-600">
                          {account.werss_feed_id || '-'}
                        </TableCell>
                        <TableCell>
                          <span className="font-semibold text-indigo-600">{account.total_articles}</span>
                        </TableCell>
                        <TableCell className="hidden lg:table-cell text-gray-500 text-sm">
                          {account.last_collection_time 
                            ? formatBeijingDateTimeFromApi(account.last_collection_time)
                            : '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleEdit(account)}
                              title="编辑"
                              className="h-8 w-8 hover:bg-indigo-100 hover:text-indigo-600"
                            >
                              <Icon name={Icons.edit} size={16} />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleToggleActive(account)}
                              title={account.is_active ? '停用' : '启用'}
                              className="h-8 w-8 hover:bg-yellow-100"
                            >
                              {account.is_active ? (
                                <Icon name={Icons.powerOff} size={16} className="text-yellow-600" />
                              ) : (
                                <Icon name={Icons.power} size={16} className="text-green-600" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDelete(account.id)}
                              title="删除"
                              className="h-8 w-8 hover:bg-red-100 hover:text-red-600"
                            >
                              <Icon name={Icons.delete} size={16} />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="flex items-center justify-between px-4 py-3 bg-white border-t border-indigo-200">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">每页</span>
                  <Select value={String(limit)} onValueChange={(v) => setLimit(Number(v))}>
                    <SelectTrigger className="w-20">
                      <SelectValue placeholder="20" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10</SelectItem>
                      <SelectItem value="20">20</SelectItem>
                      <SelectItem value="50">50</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    className="text-gray-700 hover:bg-indigo-100"
                    disabled={page === 0}
                    onClick={() => {
                      if (page > 0) {
                        setPage(page - 1)
                        fetchAccounts()
                      }
                    }}
                  >
                    上一页
                  </Button>
                  <span className="text-sm text-gray-600">第 {page + 1} 页</span>
                  <Button
                    variant="ghost"
                    className="text-gray-700 hover:bg-indigo-100"
                    disabled={!hasNext}
                    onClick={() => {
                      if (hasNext) {
                        setPage(page + 1)
                        fetchAccounts()
                      }
                    }}
                  >
                    下一页
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 添加/编辑表单对话框 */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingAccount ? '编辑公众号' : '添加公众号'}</DialogTitle>
            <DialogDescription>
              {editingAccount ? '修改公众号信息' : '添加一个新的公众号账号'}
            </DialogDescription>
          </DialogHeader>
          <AccountForm
            account={editingAccount}
            onClose={() => {
              setShowForm(false)
              setEditingAccount(null)
            }}
            onSuccess={() => {
              setShowForm(false)
              setEditingAccount(null)
              fetchAccounts()
            }}
          />
        </DialogContent>
      </Dialog>

      {/* 导入对话框 */}
      <Dialog open={showImport} onOpenChange={setShowImport}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>批量导入公众号</DialogTitle>
            <DialogDescription>
              从CSV或Excel文件批量导入公众号数据
            </DialogDescription>
          </DialogHeader>
          <ImportDialog
            onClose={() => {
              setShowImport(false)
              setImportResult(null)
            }}
            onImport={handleImport}
            importing={importing}
            result={importResult}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}

function AccountForm({
  account,
  onClose,
  onSuccess,
}: {
  account: OfficialAccount | null
  onClose: () => void
  onSuccess: () => void
}) {
  const [formData, setFormData] = useState({
    name: account?.name || '',
    wechat_id: account?.wechat_id || '',
    werss_feed_id: account?.werss_feed_id || '',
    is_active: account?.is_active ?? true,
  })
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      if (account) {
        await api.put(`/admin/accounts/${account.id}`, formData)
      } else {
        await api.post('/admin/accounts', formData)
      }
      onSuccess()
    } catch (error) {
      console.error('Failed to save account:', error)
      toast({ title: '保存失败', description: '请检查输入或稍后重试', variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">名称 *</Label>
          <Input
            id="name"
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="wechat_id">微信ID</Label>
          <Input
            id="wechat_id"
            value={formData.wechat_id}
            onChange={(e) => setFormData({ ...formData, wechat_id: e.target.value })}
          />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="werss_feed_id">we-mp-rss Feed ID</Label>
          <Input
            id="werss_feed_id"
            value={formData.werss_feed_id}
            onChange={(e) => setFormData({ ...formData, werss_feed_id: e.target.value })}
            placeholder="从 we-mp-rss 获取的 Feed ID"
          />
        </div>
      </div>
      <div className="flex items-center space-x-2">
        <input
          type="checkbox"
          id="is_active"
          checked={formData.is_active}
          onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
          className="h-4 w-4 rounded border-gray-300"
        />
        <Label htmlFor="is_active">启用此公众号</Label>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          取消
        </Button>
        <Button type="submit" disabled={loading}>
          {loading ? '保存中...' : '保存'}
        </Button>
      </DialogFooter>
    </form>
  )
}

function ImportDialog({
  onClose,
  onImport,
  importing,
  result,
}: {
  onClose: () => void
  onImport: (file: File) => void
  importing: boolean
  result: any
}) {
  const [file, setFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [downloadingTemplate, setDownloadingTemplate] = useState(false)
  const { toast } = useToast()

  const handleDownloadTemplate = async () => {
    setDownloadingTemplate(true)
    try {
      const response = await api.get('/admin/accounts/export', {
        params: { template: 'true' },
        responseType: 'blob',
      })

      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = 'accounts_template.csv'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error: any) {
      console.error('Failed to download template:', error)
      let errorMsg = '下载模板失败'
      if (error.response) {
        if (error.response.data instanceof Blob) {
          const text = await error.response.data.text()
          try {
            const json = JSON.parse(text)
            errorMsg = json.detail || errorMsg
          } catch {
            errorMsg = text || errorMsg
          }
        } else {
          errorMsg = error.response.data?.detail || errorMsg
        }
      }
      toast({ title: '下载失败', description: errorMsg, variant: 'error' })
    } finally {
      setDownloadingTemplate(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (file) {
      onImport(file)
    }
  }

  return (
    <div className="space-y-4">
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Icon name={Icons.info} size={20} className="text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-blue-900 font-medium mb-2">
                请先下载模板文件，在模板文件上填写数据后上传
              </p>
              <div className="text-xs text-blue-700 mb-3 space-y-1">
                <p className="font-semibold">重要提示：</p>
                <p>1. 模板文件第一行是说明文字，导入前请删除第一行</p>
                <p>2. 删除说明后，列名行（werss_feed_id,name,is_active,wechat_id）必须保留在第一行</p>
                <p>3. 所有字段都是必填项：werss_feed_id（Feed ID）、name（名称）、is_active（1表示启用，0表示停用）、wechat_id（微信ID）</p>
                <p>4. 请勿修改列名，只需在模板上填写数据</p>
              </div>
              <Button
                onClick={handleDownloadTemplate}
                disabled={downloadingTemplate}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                {downloadingTemplate ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    下载中...
                  </>
                ) : (
                  <>
                    <Icon name={Icons.download} size={16} />
                    下载模板文件
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label>选择文件</Label>
          <div
            className="flex flex-col items-center justify-center w-full border-2 border-dashed rounded-lg p-6 cursor-pointer hover:border-primary transition-colors"
            onClick={() => fileInputRef.current?.click()}
            onDrop={(e) => {
              e.preventDefault()
              if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                setFile(e.dataTransfer.files[0])
              }
            }}
            onDragOver={(e) => e.preventDefault()}
          >
            <Icon name={Icons.upload} size={48} className="text-muted-foreground mb-4" />
            <p className="text-sm text-muted-foreground mb-2">
              {file ? file.name : '点击或拖拽文件到此处'}
            </p>
            <p className="text-xs text-muted-foreground">CSV, Excel文件</p>
            {file && (
              <p className="mt-2 text-sm text-primary font-medium">
                ✓ {file.name} ({(file.size / 1024).toFixed(2)} KB)
              </p>
            )}
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".csv,.xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
              onChange={handleFileChange}
              disabled={importing}
            />
          </div>
        </div>

        {result && (
          <Card className={result.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                {result.success ? (
                  <Icon name={Icons.success} size={20} className="text-green-600 mt-0.5" />
                ) : (
                  <Icon name={Icons.error} size={20} className="text-red-600 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`font-medium ${result.success ? 'text-green-800' : 'text-red-800'}`}>
                    {result.message || result.detail}
                  </p>
                  {result.success && (
                    <div className="mt-2 text-sm text-green-700">
                      <p>成功: {result.success_count} 个</p>
                      {result.error_count > 0 && (
                        <p>失败: {result.error_count} 个</p>
                      )}
                    </div>
                  )}
                  {result.errors && result.errors.length > 0 && (
                    <div className="mt-2 text-sm text-red-700">
                      <p className="font-medium">错误详情：</p>
                      <ul className="list-disc list-inside mt-1 space-y-1">
                        {result.errors.slice(0, 10).map((error: string, idx: number) => (
                          <li key={idx}>{error}</li>
                        ))}
                        {result.errors.length > 10 && (
                          <li>... 还有 {result.errors.length - 10} 个错误</li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose} disabled={importing}>
            关闭
          </Button>
          <Button type="submit" disabled={!file || importing}>
            {importing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                导入中...
              </>
            ) : (
              <>
                <Icon name={Icons.upload} size={16} className="mr-2" />
                开始导入
              </>
            )}
          </Button>
        </DialogFooter>
      </form>
    </div>
  )
}
