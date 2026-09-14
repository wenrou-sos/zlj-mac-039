import { useEffect, useState } from 'react'
import { api } from '../api'
import { fmt } from '../utils'

export default function Yard() {
  const [block, setBlock] = useState('A')
  const [positions, setPositions] = useState([])
  const [summary, setSummary] = useState([])
  const [selected, setSelected] = useState(null)      // 选中的占用格 {position, container}
  const [targetBlock, setTargetBlock] = useState('')
  const [reason, setReason] = useState('')
  const [msg, setMsg] = useState('')
  const [moves, setMoves] = useState([])

  const loadPositions = () =>
    api.get(`/yard/positions?block=${block}`).then(setPositions).catch(alert)
  const loadSummary = () => api.get('/yard/summary').then(setSummary).catch(alert)
  const loadMoves = () => api.get('/yard/moves?limit=20').then(setMoves).catch(alert)

  useEffect(() => { loadPositions() }, [block])
  useEffect(() => { loadSummary(); loadMoves() }, [])

  // 选中占用格: 查询箱详情
  const selectCell = async (p) => {
    if (!p.occupied || !p.container_no) return
    try {
      const list = await api.get('/containers?q=' + p.container_no)
      const c = list.find((x) => x.container_no === p.container_no)
      setSelected({ position: p, container: c })
      setMsg('')
    } catch (e) { alert(e.message) }
  }

  // 移箱: exact=确切堆位 / block=指定区 / 空=系统全场找位
  const doMove = async (positionId) => {
    if (!selected) return
    try {
      const body = { container_no: selected.container.container_no, reason }
      if (positionId) body.position_id = positionId
      else if (targetBlock) body.block = targetBlock
      const r = await api.post('/yard/move', body)
      setMsg(`✅ ${r.container_no} 已从 ${r.from_code} 移至 ${r.to_code}`)
      setSelected(null)
      setReason('')
      loadPositions(); loadSummary(); loadMoves()
    } catch (e) { setMsg('❌ ' + e.message) }
  }

  // 释放预分配堆位
  const doRelease = async () => {
    if (!selected) return
    try {
      const r = await api.post(`/yard/release/${selected.container.id}`)
      setMsg(`✅ 已释放预分配堆位 ${r.code}`)
      setSelected(null)
      loadPositions(); loadSummary()
    } catch (e) { setMsg('❌ ' + e.message) }
  }

  // 按 排(bay) 分组渲染
  const bays = {}
  positions.forEach((p) => { ;(bays[p.bay] = bays[p.bay] || []).push(p) })

  const c = selected?.container
  return (
    <div>
      <h2>堆位图</h2>
      <div className="summary-bar">
        {summary.map((s) => (
          <button key={s.block} className={`block-btn ${block === s.block ? 'active' : ''}`}
            onClick={() => setBlock(s.block)}>
            {s.block} 区 <span className="muted">{s.occupied}/{s.total} ({s.rate}%)</span>
          </button>
        ))}
      </div>
      <div className="legend">
        <span className="cell free"></span> 空位
        <span className="cell used"></span> 占用(点击查看箱信息)
        <span className="cell sel"></span> 选中
      </div>
      <div className="yard-grid">
        {Object.keys(bays).sort().map((bay) => (
          <div key={bay} className="bay">
            <div className="bay-title">排 {bay}</div>
            <div className="bay-cells">
              {bays[bay].map((p) => (
                <div key={p.id}
                  className={`cell ${p.occupied ? 'used' : 'free'} ${selected?.position.id === p.id ? 'sel' : ''}`}
                  title={p.occupied ? `${p.code} · ${p.container_no}` : `${p.code} (空)`}
                  onClick={() => p.occupied ? selectCell(p) : null}>
                  {p.occupied ? p.container_no?.slice(-4) : ''}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {selected && c && (
        <div className="panel move-panel">
          <h3>📦 {c.container_no} <span className="muted">@ {selected.position.code}</span></h3>
          <div className="info-row">
            <span>尺寸/箱型: {c.size}'{c.ctype}</span>
            <span>状态: {{ BOOKED: '已预约未进场', IN_YARD: '在场', OUT: '已出场' }[c.status] || c.status}</span>
            <span>在场天数: {c.days_in_yard != null ? c.days_in_yard + ' 天' : '-'}</span>
            <span>货主: {c.consignee || '-'}</span>
            {c.overdue && <span className="tag s-over">超期</span>}
            {c.has_hold && <span className="tag s-over">🔒扣箱</span>}
          </div>
          <div className="form-row">
            {c.status === 'IN_YARD' ? (
              <>
                <select value={targetBlock} onChange={(e) => setTargetBlock(e.target.value)}>
                  <option value="">系统自动找位</option>
                  {summary.map((s) => <option key={s.block} value={s.block}>{s.block} 区</option>)}
                </select>
                <input placeholder="移箱原因(可选)" value={reason} style={{ width: 200 }}
                  onChange={(e) => setReason(e.target.value)} />
                <button onClick={() => doMove(null)}>移箱</button>
              </>
            ) : (
              <>
                <span className="muted">该箱尚未进场，当前为预分配堆位</span>
                <button onClick={doRelease}>释放预分配</button>
              </>
            )}
            <button className="btn-sm" onClick={() => { setSelected(null); setMsg('') }}>关闭</button>
          </div>
        </div>
      )}
      {msg && <p className="msg">{msg}</p>}

      <h3>移箱记录</h3>
      <table>
        <thead>
          <tr><th>时间</th><th>箱号</th><th>原堆位</th><th>新堆位</th><th>原因</th></tr>
        </thead>
        <tbody>
          {moves.map((m) => (
            <tr key={m.id}>
              <td>{fmt(m.time)}</td>
              <td className="mono">{m.container_no}</td>
              <td>{m.from_code}</td>
              <td>{m.to_code}</td>
              <td>{m.reason || '-'}</td>
            </tr>
          ))}
          {moves.length === 0 && <tr><td colSpan={5} className="muted">暂无移箱记录</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
