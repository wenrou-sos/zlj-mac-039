// 后端时间统一为 UTC（无时区后缀），解析时按 UTC 处理再转浏览器本地时区
export const parseServerDate = (s) =>
  new Date(/Z$|[+-]\d{2}:?\d{2}$/.test(s) ? s : s + 'Z')

export const fmt = (s) =>
  s ? parseServerDate(s).toLocaleString('zh-CN', { hour12: false }) : '-'

export const fmtShort = (s) =>
  s ? parseServerDate(s).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: false }) : '-'

// datetime-local 值(浏览器本地时间) -> UTC ISO，供提交后端
export const toUTCISO = (local) => (local ? new Date(local).toISOString() : local)

// UTC ISO -> datetime-local 输入框所需的本地格式 (用于改期回填)
export const toLocalInput = (s) => {
  if (!s) return ''
  const d = parseServerDate(s)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
