'use client'

import { useState, useEffect } from 'react'
import Icon, { Icons } from '@/components/Icon'
import { formatBeijingYmd } from '@/lib/datetime'

interface Report {
  id: number
  report_type: string
  report_date: string
  title: string
  content_json?: any
  summary_markdown?: string
}

interface CalendarReport {
  [date: string]: {
    daily?: Report
    weekly?: Report
  }
}

interface ReportCalendarProps {
  onDateClick?: (date: string, report: Report | null) => void
  selectedDate?: string | null
}

export function ReportCalendar({ onDateClick, selectedDate }: ReportCalendarProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [reports, setReports] = useState<CalendarReport>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchReportsForMonth()
  }, [currentMonth])

  const fetchReportsForMonth = async () => {
    setLoading(true)
    try {
      // 获取当前月份的所有报告
      const year = currentMonth.getFullYear()
      const month = currentMonth.getMonth() + 1
      const startDate = `${year}-${String(month).padStart(2, '0')}-01`
      const lastDay = new Date(year, month, 0)
      const endDate = `${year}-${String(month).padStart(2, '0')}-${String(lastDay.getDate()).padStart(2, '0')}`
      
      const response = await fetch(`/api/reports/?start_date=${startDate}&end_date=${endDate}&limit=100`)
      if (!response.ok) {
        throw new Error('Failed to fetch reports')
      }
      const data = await response.json()
      
      // 按日期组织报告
      const reportsByDate: CalendarReport = {}
      for (const report of data) {
        const date = report.report_date.split('T')[0]
        if (!reportsByDate[date]) {
          reportsByDate[date] = {}
        }
        const isDaily = report.report_type === 'daily' || report.report_type === 'DAILY'
        if (isDaily) {
          reportsByDate[date].daily = report
        } else {
          reportsByDate[date].weekly = report
        }
      }
      setReports(reportsByDate)
    } catch (error) {
      console.error('Failed to fetch reports:', error)
    } finally {
      setLoading(false)
    }
  }

  const getReportTitle = (report: Report): string => {
    if (report.report_type === 'weekly' || report.report_type === 'WEEKLY') {
      // 从Markdown提取H1标题
      if (report.summary_markdown) {
        const h1Match = report.summary_markdown.match(/^#\s+(.+)$/m)
        if (h1Match) return h1Match[1].trim()
      }
      return report.title
    } else {
      // 晨报：从content_json提取
      const header = report.content_json?.header || {}
      return header.title || report.title || '晨报'
    }
  }

  const navigateMonth = (direction: 'prev' | 'next') => {
    setCurrentMonth((prev) => {
      const newDate = new Date(prev)
      if (direction === 'prev') {
        newDate.setMonth(newDate.getMonth() - 1)
      } else {
        newDate.setMonth(newDate.getMonth() + 1)
      }
      return newDate
    })
  }

  const goToToday = () => {
    setCurrentMonth(new Date())
  }

  // 生成日历网格
  const generateCalendar = () => {
    const year = currentMonth.getFullYear()
    const month = currentMonth.getMonth()
    
    // 获取月份的第一天和最后一天
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    
    // 获取第一天是星期几（0=周日，1=周一...）
    const startDay = firstDay.getDay()
    // 转换为周一为0的格式
    const startDayAdjusted = startDay === 0 ? 6 : startDay - 1
    
    const days: (Date | null)[] = []
    
    // 填充前面的空位
    for (let i = 0; i < startDayAdjusted; i++) {
      days.push(null)
    }
    
    // 填充当月的日期
    for (let day = 1; day <= lastDay.getDate(); day++) {
      days.push(new Date(year, month, day))
    }
    
    return days
  }

  const calendarDays = generateCalendar()
  const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']
  const weekDays = ['一', '二', '三', '四', '五', '六', '日']
  const today = new Date()
  const isCurrentMonth = currentMonth.getFullYear() === today.getFullYear() && currentMonth.getMonth() === today.getMonth()

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
      {/* 日历头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigateMonth('prev')}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            aria-label="上一个月"
          >
            <Icon name={Icons.arrowLeft} size={20} className="text-slate-600" />
          </button>
          <h3 className="text-xl font-bold text-slate-900">
            {currentMonth.getFullYear()}年 {monthNames[currentMonth.getMonth()]}
          </h3>
          <button
            onClick={() => navigateMonth('next')}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            aria-label="下一个月"
          >
            <Icon name={Icons.arrowLeft} size={20} className="text-slate-600 rotate-180" />
          </button>
        </div>
        {!isCurrentMonth && (
          <button
            onClick={goToToday}
            className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
          >
            今天
          </button>
        )}
      </div>

      {/* 星期标题 */}
      <div className="grid grid-cols-7 gap-2 mb-2">
        {weekDays.map((day) => (
          <div key={day} className="text-center text-sm font-medium text-slate-500 py-2">
            {day}
          </div>
        ))}
      </div>

      {/* 日历网格 */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">加载中...</div>
      ) : (
        <div className="grid grid-cols-7 gap-2">
          {calendarDays.map((date, index) => {
            if (!date) {
              return <div key={`empty-${index}`} className="aspect-square" />
            }
            
            // 格式化日期为 YYYY-MM-DD
            const year = date.getFullYear()
            const month = String(date.getMonth() + 1).padStart(2, '0')
            const day = String(date.getDate()).padStart(2, '0')
            const dateStr = `${year}-${month}-${day}`
            
            const dateReports = reports[dateStr]
            const isToday = date.toDateString() === today.toDateString()
            const isCurrentMonthDate = date.getMonth() === currentMonth.getMonth()
            
            // 优先显示晨报，如果有周报也显示
            const dailyReport = dateReports?.daily
            const weeklyReport = dateReports?.weekly
            const hasWeekly = !!weeklyReport
            const isSelected = selectedDate === dateStr
            
            const handleClick = (e: React.MouseEvent) => {
              e.preventDefault()
              if (onDateClick) {
                // 仅在存在周报时传递周报，否则传递 null（避免下方显示晨报）
                const report = weeklyReport || null
                onDateClick(dateStr, report || null)
              }
            }
            
            return (
              <button
                key={dateStr}
                onClick={handleClick}
                className={`
                  aspect-square border rounded-lg p-1.5 sm:p-2 transition-all text-left
                  ${isToday ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300'}
                  ${!isCurrentMonthDate ? 'opacity-40' : ''}
                  ${dailyReport || weeklyReport ? 'hover:shadow-md cursor-pointer' : 'cursor-default'}
                  ${dailyReport || weeklyReport ? 'bg-slate-50' : 'bg-white'}
                  ${isSelected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}
                  ${hasWeekly ? 'border-purple-300 bg-purple-50/30' : ''}
                `}
              >
                <div className="flex flex-col h-full">
                  <div className="flex items-center gap-1 mb-1">
                    <div className={`text-xs sm:text-sm font-medium ${isToday ? 'text-blue-600' : 'text-slate-700'}`}>
                      {date.getDate()}
                    </div>
                    {hasWeekly && (
                      <div className="w-1.5 h-1.5 rounded-full bg-purple-500" title="有周报" />
                    )}
                  </div>
                  <div className="flex-1 flex items-center justify-center">
                    {dailyReport ? (
                      <div className="w-full">
                        <div className="hidden sm:block text-sm font-medium leading-tight line-clamp-2 text-slate-700">
                          {getReportTitle(dailyReport)}
                        </div>
                        <div className="sm:hidden flex items-center justify-center" title="晨报">
                          <Icon
                            name={Icons.fileText}
                            size={16}
                            className="text-blue-600"
                          />
                        </div>
                        {weeklyReport && (
                          <div className="mt-1">
                            <div className="hidden sm:block text-xs text-purple-600 font-medium">+ 周报</div>
                            <div className="mt-0.5 hidden sm:block text-xs sm:text-sm font-medium leading-tight text-purple-700 line-clamp-2">
                              {getReportTitle(weeklyReport)}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : weeklyReport ? (
                      <div className="w-full">
                        <div className="hidden sm:block text-xs text-purple-600 font-medium">+ 周报</div>
                        <div className="hidden sm:block mt-0.5 text-xs sm:text-sm font-medium leading-tight text-purple-700 line-clamp-2">
                          {getReportTitle(weeklyReport)}
                        </div>
                        <div className="sm:hidden flex items-center justify-center" title="周报">
                          <Icon
                            name={Icons.fileText}
                            size={16}
                            className="text-purple-600"
                          />
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
