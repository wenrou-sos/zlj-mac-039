import { useEffect, useState } from 'react'
import { api } from '../api'
import { fmt } from '../utils'


export default function Gate() {
  const [inForm, setInForm] = useState({ container_no: '', truck_no: '', driver: '', gate: 'G1' })
  const [outForm, setOutForm] = useState({ container_no: '', truck_no: '', driver: '', gate: 'G1', pickup_no: '' })
  const [records, setRecords] = useState([])
  const [msg, setMsg] = useState({ in: '', out: '' })

  const load = () => api.get('/gate/records?limit=50').then(setRecords).catch(alert)
  useEffect(load, [])

  const doIn = async (e) => {
    e.preventDefault()
    setMsg({ ...msg, in: '' })
    try {
      const r = await api.post('/gate/in', inForm)
      setMsg({ ...msg, in: `✅ 进闸成功，${r.remark}` })
      setInForm({ ...inForm, container_no: '' })
      load()
    } catch (err) { setMsg({ ...msg, in: '❌ ' + err.message }); load() }
  }

  const doOut = async (e) => {
    e.preventDefault()
    setMsg({ ...msg, out: '' })
    try {
      const r = await api.post('/gate/out', outForm)
      setMsg({ ...msg, out: `✅ 出闸成功，${r.remark}` })
      setOutForm({ ...outForm, container_no: '', pickup_no: '' })
      load()
    } catch (err) { setMsg({ ...msg, out: '❌ ' + err.message }); load() }
  }

  return (
    <div>
      <h2>闸口作业</h2>
      <div className="two-col">
        <form className="panel" onSubmit={doIn}>
          <h3>进场（进闸）</h3>
          <p className="muted">校验预约 → 自动分配堆位</p>
          <input placeholder="箱号" value={inForm.container_no} required maxLength={11}
            onChange={(e) => setInForm({ ...inForm, container_no: e.target.value.toUpperCase() })} />
          <input placeholder="车牌号" value={inForm.truck_no}
            onChange={(e) => setInForm({ ...inForm, truck_no: e.target.value })} />
          <input placeholder="司机" value={inForm.driver}
            onChange={(e) => setInForm({ ...inForm, driver: e.target.value })} />
          <select value={inForm.gate} onChange={(e) => setInForm({ ...inForm, gate: e.target.value })}>
            <option>G1</option><option>G2</option>
          </select>
          <button type="submit">办理进闸</button>
          {msg.in && <p className="msg">{msg.in}</p>}
        </form>

        <form className="panel" onSubmit={doOut}>
          <h3>提箱（出闸）</h3>
          <p className="muted">校验在场状态 / 扣箱 / 提箱单号</p>
          <input placeholder="箱号" value={outForm.container_no} required maxLength={11}
            onChange={(e) => setOutForm({ ...outForm, container_no: e.target.value.toUpperCase() })} />
          <input placeholder="提箱单号 (至少6位)" value={outForm.pickup_no} required
            onChange={(e) => setOutForm({ ...outForm, pickup_no: e.target.value })} />
          <input placeholder="车牌号" value={outForm.truck_no}
            onChange={(e) => setOutForm({ ...outForm, truck_no: e.target.value })} />
          <input placeholder="司机" value={outForm.driver}
            onChange={(e) => setOutForm({ ...outForm, driver: e.target.value })} />
          <button type="submit">办理出闸</button>
          {msg.out && <p className="msg">{msg.out}</p>}
        </form>
      </div>

      <h3>进出闸记录</h3>
      <table>
        <thead>
          <tr><th>时间</th><th>箱号</th><th>方向</th><th>车牌</th><th>司机</th><th>闸口</th><th>结果</th><th>备注</th></tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={r.id}>
              <td>{fmt(r.time)}</td>
              <td className="mono">{r.container_no || r.container_id}</td>
              <td><span className={`tag ${r.direction === 'IN' ? 's-IN_YARD' : 's-OUT'}`}>
                {r.direction === 'IN' ? '进场' : '出场'}</span></td>
              <td>{r.truck_no}</td>
              <td>{r.driver}</td>
              <td>{r.gate}</td>
              <td>{r.result === 'OK' ? '✅' : '⛔'}</td>
              <td>{r.remark}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
