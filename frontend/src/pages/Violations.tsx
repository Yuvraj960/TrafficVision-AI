import { useEffect, useState, useCallback, useRef } from 'react';
import { violationsApi, type ViolationListItem, type ViolationDetailItem, type ViolationStatus } from '../services/api';
import ImageViewer from '../components/ImageViewer';

type FilterParams = {
  page: number;
  limit: number;
  status?: string;
  violation_type?: string;
  plate?: string;
};

const STATUS_COLORS: Record<ViolationStatus, string> = {
  pending: '#fbbf24',
  approved: '#34d399',
  rejected: '#94a3b8',
};

const TYPE_COLORS: Record<string, string> = {
  helmet: '#f87171',
  triple_riding: '#fb923c',
  wrong_side: '#facc15',
  stop_line: '#a78bfa',
  overloading: '#34d399',
  no_violation: '#94a3b8',
  pending: '#94a3b8',
};

const VIOLATION_TYPES = ['helmet', 'triple_riding', 'wrong_side', 'stop_line', 'overloading'];

// ── Detail Modal ──────────────────────────────────────────────────────────────
function DetailModal({
  violationId,
  onClose,
  onUpdate,
}: {
  violationId: string;
  onClose: () => void;
  onUpdate: (id: string, status: ViolationStatus) => Promise<void>;
}) {
  const [item, setItem] = useState<ViolationDetailItem | null>(null);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  // Poll for updates every 15s while modal is open
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchDetail = useCallback(async () => {
    try {
      const data = await violationsApi.get(violationId);
      setItem(data);
      setLoading(false);
    } catch {
      setLoading(false);
    }
  }, [violationId]);

  useEffect(() => {
    fetchDetail();
    pollRef.current = setInterval(fetchDetail, 15000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchDetail]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-primary-800 border border-primary-600 rounded-2xl shadow-2xl w-full max-w-5xl mx-4 flex overflow-hidden max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Left pane — image viewer */}
        <div className="w-3/5 flex flex-col p-4 bg-primary-950">
          {loading || !item ? (
            <div className="flex-1 flex items-center justify-center">
              <svg className="animate-spin w-8 h-8 text-primary-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
            </div>
          ) : (
            <>
              <div className="text-xs text-primary-400 flex-shrink-0 mb-2">
                <span className="capitalize">{item.violation_type.replace('_', ' ')}</span>
                {' · '}
                <span>{new Date(item.timestamp).toLocaleString()}</span>
              </div>
              <div className="flex-1 min-h-0">
                <ImageViewer
                  imageUrl={item.image_url}
                  bboxes={item.bounding_boxes}
                />
              </div>
            </>
          )}
        </div>

        {/* Right pane — metadata + actions */}
        <div className="w-2/5 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="px-6 py-5 border-b border-primary-700 flex items-start justify-between flex-shrink-0">
            <div>
              <h3 className="text-white font-semibold text-base capitalize">
                {item?.violation_type.replace('_', ' ') ?? 'Loading...'}
              </h3>
              <p className="text-primary-400 text-xs mt-0.5">
                {item?.timestamp ? new Date(item.timestamp).toLocaleString() : ''}
              </p>
            </div>
            {item && (
              <span
                className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium text-primary-900 flex-shrink-0"
                style={{ background: STATUS_COLORS[item.status as ViolationStatus] }}
              >
                {item.status}
              </span>
            )}
          </div>

          {/* Scrollable fields */}
          {item && (
            <div className="flex-1 overflow-auto px-6 py-5 space-y-4 text-sm">
              <DataField label="Plate Number">
                <span className="font-mono text-accent-indigo-300">{item.plate_number ?? 'Not detected'}</span>
              </DataField>
              <DataField label="Vehicle Type">
                <span className="text-primary-200">{item.vehicle_type ?? '—'}</span>
              </DataField>
              <DataField label="Confidence">
                <span className="text-primary-200">
                  {item.confidence_score != null
                    ? `${(item.confidence_score * 100).toFixed(1)}%`
                    : '—'}
                </span>
              </DataField>
              {item.camera_id && (
                <DataField label="Camera ID">
                  <span className="font-mono text-primary-400 text-xs">{item.camera_id}</span>
                </DataField>
              )}
              <DataField label="Violation ID">
                <span className="font-mono text-primary-400 text-xs">{item.id}</span>
              </DataField>

              <div className="border-t border-primary-700 pt-4">
                <p className="text-primary-500 text-xs mb-1.5">OCR Correction</p>
                <input
                  type="text"
                  defaultValue={item.plate_number ?? ''}
                  className="w-full bg-primary-900 border border-primary-600 rounded-lg px-3 py-2 text-sm text-white placeholder-primary-600 focus:outline-none focus:ring-1 focus:ring-accent-indigo-500"
                  placeholder="Enter corrected plate number..."
                />
              </div>

              <div>
                <p className="text-primary-500 text-xs mb-1.5">Review Notes</p>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  className="w-full bg-primary-900 border border-primary-600 rounded-lg px-3 py-2 text-sm text-white placeholder-primary-600 focus:outline-none focus:ring-1 focus:ring-accent-indigo-500 resize-none"
                  placeholder="Optional notes..."
                />
              </div>
            </div>
          )}

          {/* Sticky approve/reject */}
          {item && (
            <div className="px-6 py-4 border-t border-primary-700 flex-shrink-0 flex gap-3">
              <button
                disabled={submitting || item.status === 'approved'}
                onClick={async () => {
                  setSubmitting(true);
                  await onUpdate(item.id, 'approved');
                  setSubmitting(false);
                  onClose();
                }}
                className="flex-1 bg-accent-success-600 hover:bg-accent-success-500 disabled:bg-accent-success-800 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
              >
                Approve
              </button>
              <button
                disabled={submitting || item.status === 'rejected'}
                onClick={async () => {
                  setSubmitting(true);
                  await onUpdate(item.id, 'rejected');
                  setSubmitting(false);
                  onClose();
                }}
                className="flex-1 bg-primary-700 hover:bg-primary-600 disabled:bg-primary-800 disabled:cursor-not-allowed text-primary-300 font-semibold py-2.5 rounded-lg text-sm transition-colors border border-primary-600"
              >
                Reject
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DataField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-primary-500 text-xs mb-0.5">{label}</p>
      <div>{children}</div>
    </div>
  );
}

// ── Violations Page ───────────────────────────────────────────────────────────
export default function Violations() {
  const [items, setItems] = useState<ViolationListItem[]>([]);
  const [meta, setMeta] = useState({ total: 0, page: 1, limit: 20 });
  const [loading, setLoading] = useState(true);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterParams>({ page: 1, limit: 20, status: '' });

  const load = useCallback(async (f: FilterParams) => {
    setLoading(true);
    try {
      const params = Object.fromEntries(
        Object.entries({
          ...f,
          status: f.status || undefined,
          violation_type: f.violation_type || undefined,
          plate: f.plate || undefined,
        }).filter(([, v]) => v !== undefined)
      );
      const res = await violationsApi.list(params);
      setItems(res.data);
      setMeta(res.meta);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + polling every 15s
  useEffect(() => {
    load(filters);
    const interval = setInterval(() => load(filters), 15000);
    return () => clearInterval(interval);
  }, [load, filters]);

  const handleUpdate = async (id: string, status: ViolationStatus) => {
    setUpdating(id);
    await violationsApi.updateStatus(id, { status });
    setItems((prev) => prev.map((v) => (v.id === id ? { ...v, status } : v)));
    setUpdating(null);
  };

  const handleFilter = (key: keyof FilterParams, value: string) => {
    setFilters((f) => ({ ...f, [key]: value, page: 1 }));
  };

  return (
    <div className="min-h-screen bg-primary-900/50">
      {/* Header */}
      <header className="px-8 py-4 border-b border-primary-800 bg-primary-950/60 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Violation Explorer</h2>
          <p className="text-xs text-primary-400">
            {meta.total} records · auto-refreshes every 15s
          </p>
        </div>
        <button
          onClick={() => load(filters)}
          className="text-xs text-primary-400 hover:text-primary-200 border border-primary-600 rounded-lg px-3 py-1.5 transition-colors flex items-center gap-1.5"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh Now
        </button>
      </header>

      <div className="p-8 space-y-5">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={filters.status ?? ''}
            onChange={(e) => handleFilter('status', e.target.value)}
            className="bg-primary-800 border border-primary-600 text-primary-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>

          <select
            value={filters.violation_type ?? ''}
            onChange={(e) => handleFilter('violation_type', e.target.value)}
            className="bg-primary-800 border border-primary-600 text-primary-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent-indigo-500"
          >
            <option value="">All Types</option>
            {VIOLATION_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          <div className="relative flex-1 max-w-xs">
            <input
              type="text"
              placeholder="Search plate..."
              value={filters.plate ?? ''}
              onChange={(e) => handleFilter('plate', e.target.value)}
              className="w-full bg-primary-800 border border-primary-600 text-white text-sm placeholder-primary-500 rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent-indigo-500"
            />
            <svg className="w-4 h-4 text-primary-500 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <button
            onClick={() => setFilters((f) => ({ ...f, status: '', violation_type: '', plate: '', page: 1 }))}
            className="text-xs text-primary-400 hover:text-primary-200 border border-primary-600 rounded-lg px-3 py-2 transition-colors"
          >
            Clear
          </button>
        </div>

        {/* Table */}
        <div className="bg-primary-800/60 border border-primary-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-primary-900/60">
              <tr className="text-primary-400 border-b border-primary-700">
                {['Type', 'Plate', 'Status', 'Time', 'Actions'].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-primary-700/50">
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-primary-400">
                    <div className="flex items-center justify-center gap-2">
                      <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                      </svg>
                      Loading...
                    </div>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-primary-500">No violations found</td>
                </tr>
              ) : items.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-primary-700/30 transition-colors cursor-pointer"
                  onClick={() => setDetailId(item.id)}
                >
                  <td className="px-4 py-3">
                    <span
                      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                      style={{
                        background: `${TYPE_COLORS[item.violation_type] ?? '#94a3b8'}22`,
                        color: TYPE_COLORS[item.violation_type] ?? '#94a3b8',
                      }}
                    >
                      {item.violation_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-primary-200 text-xs">{item.plate_number ?? '—'}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1.5 text-xs" style={{ color: STATUS_COLORS[item.status] }}>
                      <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ background: STATUS_COLORS[item.status] }} />
                      {item.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-primary-400 text-xs">
                    {new Date(item.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <div className="flex gap-2">
                      <button
                        disabled={updating !== null || item.status !== 'pending'}
                        onClick={() => handleUpdate(item.id, 'approved')}
                        className="text-xs px-3 py-1 rounded-md bg-accent-success-600/20 text-accent-success-400 hover:bg-accent-success-600/40 disabled:opacity-40 transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        disabled={updating !== null || item.status !== 'pending'}
                        onClick={() => handleUpdate(item.id, 'rejected')}
                        className="text-xs px-3 py-1 rounded-md bg-primary-700/60 text-primary-400 hover:bg-primary-700 disabled:opacity-40 transition-colors"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => setDetailId(item.id)}
                        className="text-xs px-3 py-1 rounded-md bg-accent-indigo-600/20 text-accent-indigo-300 hover:bg-accent-indigo-600/40 transition-colors"
                      >
                        View
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-primary-700/50">
            <p className="text-xs text-primary-400">
              {items.length === 0 ? 'No results' : `Showing ${items.length} of ${meta.total}`}
            </p>
            <div className="flex gap-2">
              <button
                disabled={meta.page <= 1}
                onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
                className="px-3 py-1.5 text-xs rounded-lg border border-primary-600 text-primary-300 hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Prev
              </button>
              <span className="px-3 py-1.5 text-xs text-primary-400">Page {meta.page}</span>
              <button
                disabled={items.length < 20}
                onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
                className="px-3 py-1.5 text-xs rounded-lg border border-primary-600 text-primary-300 hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Detail modal */}
      {detailId && (
        <DetailModal
          violationId={detailId}
          onClose={() => setDetailId(null)}
          onUpdate={handleUpdate}
        />
      )}
    </div>
  );
}