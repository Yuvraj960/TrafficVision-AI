import { useCallback, useEffect, useRef, useState } from 'react';

export type Bbox = { x: number; y: number; w: number; h: number; label?: string };

export type BboxLayers = {
  vehicles?: Bbox[];
  rider_seats?: Bbox[];
  helmets?: Bbox[];
  plates?: Bbox[];
  violations?: Bbox[];
  direction_arrow?: Bbox;
  stop_line?: Bbox;
  cargo?: Bbox[];
  intersection?: Bbox[];
};

type BboxLayerKey = keyof BboxLayers;

const LAYER_META: { key: BboxLayerKey; label: string; color: string }[] = [
  { key: 'vehicles',     label: 'Vehicles',  color: '#60a5fa' },
  { key: 'plates',       label: 'Plates',   color: '#fbbf24' },
  { key: 'helmets',      label: 'Helmets',  color: '#34d399' },
  { key: 'violations',   label: 'Violations', color: '#f87171' },
  { key: 'cargo',        label: 'Cargo',    color: '#fb923c' },
  { key: 'stop_line',    label: 'Stop Line', color: '#facc15' },
  { key: 'rider_seats',  label: 'Riders',   color: '#a78bfa' },
  { key: 'direction_arrow', label: 'Wrong Way', color: '#f87171' },
];

function drawLayer(
  ctx: CanvasRenderingContext2D,
  bboxes: Bbox | Bbox[] | undefined,
  color: string,
  scale: number
) {
  if (!bboxes) return;
  const list = Array.isArray(bboxes) ? bboxes : [bboxes];
  for (const bbox of list) {
    const x = bbox.x * scale;
    const y = bbox.y * scale;
    const w = bbox.w * scale;
    const h = bbox.h * scale;

    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);

    if (bbox.label) {
      const label = bbox.label;
      ctx.font = `bold ${Math.max(11, Math.round(12 * scale))}px monospace`;
      const tw = ctx.measureText(label).width;
      const lx = Math.round(x - 1);
      const ly = Math.round(y - 2);
      const lw = Math.round(tw + 6);
      ctx.fillStyle = color;
      ctx.fillRect(lx, ly, lw, 20 * scale);
      ctx.fillStyle = '#000';
      ctx.fillText(label, lx + 3, ly + 14 * scale);
    }
  }
}

export function drawBboxes(
  canvas: HTMLCanvasElement,
  layers: BboxLayers,
  activeKeys: Set<BboxLayerKey>,
  imgNaturalW: number,
  imgNaturalH: number
) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (imgNaturalW === 0 || imgNaturalH === 0) return;

  const scaleX = canvas.width / imgNaturalW;
  const scaleY = canvas.height / imgNaturalH;
  const scale = Math.min(scaleX, scaleY);

  for (const meta of LAYER_META) {
    if (!activeKeys.has(meta.key)) continue;
    const data = layers[meta.key] as Bbox[] | Bbox | undefined;
    drawLayer(ctx, data, meta.color, scale);
  }
}

interface ImageViewerProps {
  imageUrl: string;
  bboxes?: BboxLayers;
}

export default function ImageViewer({ imageUrl, bboxes }: ImageViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [imgError, setImgError] = useState(false);
  const [activeKeys, setActiveKeys] = useState<Set<BboxLayerKey>>(
    () => new Set(['vehicles', 'plates', 'violations'] as BboxLayerKey[])
  );

  // Sync canvas size with container on resize
  const syncCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const { width, height } = container.getBoundingClientRect();
    canvas.width = width;
    canvas.height = height;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const img = imgRef.current;
    if (!img || !img.naturalWidth) return;

    const scaleX = width / img.naturalWidth;
    const scaleY = height / img.naturalHeight;
    const s = Math.min(scaleX, scaleY);
    const drawW = img.naturalWidth * s;
    const drawH = img.naturalHeight * s;
    const offsetX = (width - drawW) / 2;
    const offsetY = (height - drawH) / 2;
    img.style.width = `${drawW}px`;
    img.style.height = `${drawH}px`;
    img.style.position = 'absolute';
    img.style.left = `${offsetX}px`;
    img.style.top = `${offsetY}px`;

    if (bboxes) {
      drawBboxes(canvas, bboxes, activeKeys, img.naturalWidth, img.naturalHeight);
    }
  }, [bboxes, activeKeys]);

  useEffect(() => {
    syncCanvas();
    const ro = new ResizeObserver(syncCanvas);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [syncCanvas]);

  // Redraw when active keys or bboxes change
  useEffect(() => {
    const img = imgRef.current;
    if (!img || !img.naturalWidth) return;
    if (bboxes) {
      drawBboxes(canvasRef.current!, bboxes, activeKeys, img.naturalWidth, img.naturalHeight);
    }
  }, [activeKeys, bboxes]);

  const toggleKey = (key: BboxLayerKey) => {
    setActiveKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const availableToggles = LAYER_META.filter((m) => {
    const data = bboxes?.[m.key];
    if (!data) return false;
    if (Array.isArray(data)) return data.length > 0;
    return true;
  });

  const hasBboxes = availableToggles.length > 0;

  return (
    <div className="flex flex-col h-full gap-2">
      {/* Toggle row */}
      {hasBboxes && (
        <div className="flex flex-wrap items-center gap-2 px-1">
          <span className="text-xs text-primary-400">Overlay:</span>
          {availableToggles.map((meta) => (
            <button
              key={meta.key}
              onClick={() => toggleKey(meta.key)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border transition-colors"
              style={{
                borderColor: activeKeys.has(meta.key) ? meta.color : '#334155',
                background: activeKeys.has(meta.key) ? `${meta.color}22` : 'transparent',
                color: activeKeys.has(meta.key) ? meta.color : '#64748b',
              }}
            >
              <span
                className="w-2 h-2 rounded-sm inline-block"
                style={{ background: activeKeys.has(meta.key) ? meta.color : '#475569' }}
              />
              {meta.label}
            </button>
          ))}
        </div>
      )}

      {/* Image + canvas */}
      <div
        ref={containerRef}
        className="relative flex-1 bg-black rounded-lg overflow-hidden"
        style={{ minHeight: 360 }}
      >
        {!imgError ? (
          <img
            ref={imgRef}
            src={imageUrl}
            alt="Violation"
            className="object-contain max-w-full max-h-full mx-auto rounded-lg"
            onLoad={() => {
              syncCanvas();
            }}
            onError={() => setImgError(true)}
            style={{ display: 'block' }}
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-primary-500">
            <svg className="w-14 h-14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p className="text-xs">Image unavailable</p>
          </div>
        )}

        {/* Canvas overlay on top of image */}
        <canvas
          ref={canvasRef}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            pointerEvents: 'none',
            zIndex: 10,
            borderRadius: '0.5rem',
          }}
        />
      </div>
    </div>
  );
}