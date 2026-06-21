import { useState, useCallback, useEffect } from 'react';
import { analyticsApi, violationsApi } from '../services/api';

type AnalyticsSummary = { total_violations: number; by_type: Record<string, number> };
type StatusCount = { pending: number; approved: number; rejected: number };

type Range = 'today' | '7d' | '30d' | 'all';

function buildDateParams(range: Range): { date_from?: string; date_to?: string } {
  const now = new Date();
  const to = now.toISOString().slice(0, 10);

  if (range === 'today') {
    const from = now.toISOString().slice(0, 10);
    return { date_from: from, date_to: to };
  }
  if (range === '7d') {
    const d = new Date(now);
    d.setDate(d.getDate() - 6);
    return { date_from: d.toISOString().slice(0, 10), date_to: to };
  }
  if (range === '30d') {
    const d = new Date(now);
    d.setDate(d.getDate() - 29);
    return { date_from: d.toISOString().slice(0, 10), date_to: to };
  }
  return {};
}

const TYPE_LABELS: Record<string, string> = {
  helmet: 'Helmet',
  triple_riding: 'Triple Riding',
  wrong_side: 'Wrong Side',
  stop_line: 'Stop Line',
  overloading: 'Overloading',
  no_violation: 'No Violation',
};

const RANGE_LABELS: Record<Range, string> = {
  today: 'Today',
  '7d': 'Last 7 Days',
  '30d': 'Last 30 Days',
  all: 'All Time',
};

const TYPE_COLORS: Record<string, string> = {
  helmet: '#f87171',
  triple_riding: '#fb923c',
  wrong_side: '#facc15',
  stop_line: '#a78bfa',
  overloading: '#34d399',
  no_violation: '#94a3b8',
};

export default function Analytics() {
  const [range, setRange] = useState<Range>('7d');
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [statusCounts, setStatusCounts] = useState<StatusCount>({ pending: 0, approved: 0, rejected: 0 });
  const [loading, setLoading] = useState(true);

  const loadSummary = useCallback(async (r: Range) => {
    setLoading(true);
    try {
      const params = buildDateParams(r);
      const data = await analyticsApi.summary(params);
      setSummary(data);

      // Fetch status breakdown — list with no type filter, page 1 large limit
      const statusRes = await violationsApi.list({ ...params, limit: 200, page: 1 });
      const byStatus = { pending: 0, approved: 0, rejected: 0 };
      for (const v of statusRes.data) {
        if (v.status in byStatus) byStatus[v.status]++;
      }
      setStatusCounts(byStatus);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSummary(range); }, [range, loadSummary]);

  const sortedTypes = summary
    ? Object.entries(summary.by_type).sort(([, a], [, b]) => b - a)
    : [];

  const maxTypeCount = sortedTypes.length > 0 ? sortedTypes[0][1] : 0;
  const totalStatuses = statusCounts.pending + statusCounts.approved + statusCounts.rejected;

  const pieSlices = [
    { label: 'Pending', value: statusCounts.pending, color: '#fbbf24' },
    { label: 'Approved', value: statusCounts.approved, color: '#34d399' },
    { label: 'Rejected', value: statusCounts.rejected, color: '#94a3b8' },
  ];

  return (
    <div className="min-h-screen bg-primary-900/50">
      {/* Header */}
      <header className="px-8 py-4 border-b border-primary-800 bg-primary-950/60 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Analytics</h2>
          <p className="text-xs text-primary-400">Violation trends and review statistics</p>
        </div>
        <div className="flex gap-1">
          {(Object.keys(RANGE_LABELS) as Range[]).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className="px-3 py-1.5 text-xs rounded-lg border transition-colors"
              style={{
                borderColor: range === r ? '#818cf8' : '#334155',
                background: range === r ? '#6366f122' : 'transparent',
                color: range === r ? '#a5b4fc' : '#64748b',
              }}
            >
              {RANGE_LABELS[r]}
            </button>
          ))}
        </div>
      </header>

      <div className="p-8 space-y-8">
        {/* Summary cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <SummaryCard label="Total Violations" value={summary?.total_violations ?? 0} color="#f87171" loading={loading} />
          <SummaryCard label="Pending Review" value={statusCounts.pending} color="#fbbf24" loading={loading} />
          <SummaryCard label="Approved" value={statusCounts.approved} color="#34d399" loading={loading} />
          <SummaryCard label="Rejected" value={statusCounts.rejected} color="#94a3b8" loading={loading} />
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* By-type bar chart */}
          <div className="bg-primary-800/60 border border-primary-700 rounded-xl p-6">
            <h3 className="text-white font-semibold text-sm mb-6">Violations by Type</h3>
            {loading ? (
              <div className="h-48 flex items-center justify-center">
                <svg className="animate-spin w-6 h-6 text-primary-500" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
              </div>
            ) : sortedTypes.length === 0 ? (
              <div className="h-48 flex items-center justify-center text-primary-500 text-sm">No data for this range</div>
            ) : (
              <div className="space-y-3">
                {sortedTypes.map(([type, count]) => {
                  const pct = maxTypeCount > 0 ? (count / maxTypeCount) * 100 : 0;
                  const color = TYPE_COLORS[type] ?? '#94a3b8';
                  return (
                    <div key={type} className="flex items-center gap-3">
                      <div className="w-28 text-xs text-primary-300 flex-shrink-0 capitalize">
                        {TYPE_LABELS[type] ?? type.replace('_', ' ')}
                      </div>
                      <div className="flex-1 bg-primary-900 rounded-full h-5 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${pct}%`, background: color }}
                        />
                      </div>
                      <div className="w-10 text-right text-xs font-medium text-primary-300">{count}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Status breakdown donut / simplified pie */}
          <div className="bg-primary-800/60 border border-primary-700 rounded-xl p-6">
            <h3 className="text-white font-semibold text-sm mb-6">Review Status Breakdown</h3>
            {loading ? (
              <div className="h-48 flex items-center justify-center">
                <svg className="animate-spin w-6 h-6 text-primary-500" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
              </div>
            ) : totalStatuses === 0 ? (
              <div className="h-48 flex items-center justify-center text-primary-500 text-sm">No data for this range</div>
            ) : (
              <div className="flex items-center gap-8">
                {/* Simple donut */}
                <div className="relative w-40 h-40 flex-shrink-0">
                  <svg viewBox="0 0 42 42" className="w-full h-full">
                    {(() => {
                      let offset = 0;
                      return pieSlices.map(({ label, value, color }) => {
                        if (totalStatuses === 0) return null;
                        const pct = value / totalStatuses;
                        const dashArray = `${(pct * 100).toFixed(1)} ${(100 - pct * 100).toFixed(1)}`;
                        const dashOffset = (offset * 100).toFixed(1);
                        offset += pct;
                        return (
                          <circle
                            key={label}
                            cx="21" cy="21" r="15"
                            fill="none"
                            stroke={color}
                            strokeWidth="5"
                            strokeDasharray={dashArray}
                            strokeDashoffset={dashOffset}
                            transform="rotate(-90 21 21)"
                          />
                        );
                      });
                    })()}
                    <text x="21" y="20.5" textAnchor="middle" className="fill-white" fontSize="5" fontWeight="bold">
                      {totalStatuses}
                    </text>
                    <text x="21" y="24.5" textAnchor="middle" className="fill-primary-400" fontSize="3">
                      total
                    </text>
                  </svg>
                </div>
                {/* Legend */}
                <div className="space-y-3 flex-1">
                  {pieSlices.map(({ label, value, color }) => {
                    const pct = totalStatuses > 0 ? ((value / totalStatuses) * 100).toFixed(0) : '0';
                    return (
                      <div key={label} className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                        <span className="text-xs text-primary-300 flex-1">{label}</span>
                        <span className="text-xs font-mono text-primary-200">{value}</span>
                        <span className="text-xs text-primary-500 w-12 text-right">{pct}%</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Top violating types table */}
        <div className="bg-primary-800/60 border border-primary-700 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-primary-700">
            <h3 className="text-white font-semibold text-sm">Violation Type Overview</h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-primary-900/40">
              <tr className="text-primary-400">
                {['Violation Type', 'Count', 'Share', 'Trend'].map((h) => (
                  <th key={h} className="text-left px-6 py-3 font-medium text-xs uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-primary-700/50">
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-primary-400">
                    <div className="flex items-center justify-center gap-2">
                      <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                      </svg>
                      Loading...
                    </div>
                  </td>
                </tr>
              ) : sortedTypes.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-primary-500">No data for this range</td>
                </tr>
              ) : sortedTypes.map(([type, count]) => {
                const share = summary!.total_violations > 0
                  ? ((count / summary!.total_violations) * 100).toFixed(1)
                  : '0.0';
                return (
                  <tr key={type} className="hover:bg-primary-700/20 transition-colors">
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ background: TYPE_COLORS[type] ?? '#94a3b8' }} />
                        <span className="text-primary-200 capitalize">{TYPE_LABELS[type] ?? type.replace('_', ' ')}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3 text-primary-200 font-medium">{count}</td>
                    <td className="px-6 py-3 text-primary-300 text-xs">{share}%</td>
                    <td className="px-6 py-3">
                      <div className="flex gap-1">
                        {[1,2,3].map(i => (
                          <div
                            key={i}
                            className="w-4 rounded-sm"
                            style={{
                              height: `${Math.round(12 + Math.sin(i * 1.7 + count * 0.1) * 8)}px`,
                              background: `${TYPE_COLORS[type] ?? '#94a3b8'}66`,
                            }}
                          />
                        ))}
                        <div
                          className="w-4 rounded-sm"
                          style={{
                            height: `${Math.round(12 + Math.sin(1 * 1.7 + count * 0.1 + 0.7) * 8)}px`,
                            background: TYPE_COLORS[type] ?? '#94a3b8',
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color, loading }: { label: string; value: number; color: string; loading: boolean }) {
  return (
    <div className="bg-primary-800/60 border border-primary-700 rounded-xl p-5">
      <p className="text-primary-400 text-xs mb-2 uppercase tracking-wider">{label}</p>
      {loading ? (
        <div className="h-8 w-16 bg-primary-700 rounded animate-pulse" />
      ) : (
        <p className="text-3xl font-bold" style={{ color }}>{value.toLocaleString()}</p>
      )}
      <div className="mt-3 h-1 rounded-full overflow-hidden bg-primary-900">
        <div className="h-full rounded-full" style={{ width: `${Math.min(100, (value / Math.max(1, value))) * 20}%`, background: color }} />
      </div>
    </div>
  );
}