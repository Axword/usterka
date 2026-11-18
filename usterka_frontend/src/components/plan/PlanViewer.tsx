import { forwardRef, useCallback, useEffect, useImperativeHandle, useLayoutEffect, useRef } from 'react';
import { PinSvg } from 'src/components/common/Icons';
import type { Defect, Plan } from 'src/types/api';
import { clamp, isFixed } from 'src/utils/defects';

export interface PlanViewerHandle {
  fit: () => void;
  focus: (x: number, y: number, zoom?: number) => void;
  bounce: (id: string) => void;
}

interface Props {
  plan: Plan;
  src: string | undefined;
  defects: Defect[];
  placing: boolean;
  onTapPin: (id: string) => void;
  onPlace: (x: number, y: number) => void;
}

/** Przeglądarka planu: pan (1 palec), pinch (2 palce), kółko, dwuklik. Transformacja CSS bez re-renderów Reacta. */
const PlanViewer = forwardRef<PlanViewerHandle, Props>(function PlanViewer({ plan, src, defects, placing, onTapPin, onPlace }, ref) {
  const viewer = useRef<HTMLDivElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const pins = useRef<HTMLDivElement>(null);
  const t = useRef({ s: 1, tx: 0, ty: 0, minS: 0.05, maxS: 3, fitted: false });
  const cb = useRef({ placing, onTapPin, onPlace });
  cb.current = { placing, onTapPin, onPlace };

  const apply = useCallback(() => {
    const { s, tx, ty } = t.current;
    if (stage.current) stage.current.style.transform = `translate(${tx}px,${ty}px) scale(${s})`;
    pins.current?.querySelectorAll<HTMLElement>('.pin').forEach((p) => (p.style.transform = `translate(-50%,-100%) scale(${1 / s})`));
  }, []);

  const baseScale = useCallback(() => {
    const r = viewer.current!.getBoundingClientRect();
    return { r, f: Math.min(r.width / plan.width, r.height / plan.height) * 0.94 };
  }, [plan.width, plan.height]);

  const fit = useCallback(() => {
    const { r, f } = baseScale();
    if (!r.width || !r.height) return;
    Object.assign(t.current, { s: f, minS: f * 0.6, maxS: Math.max(3, f * 4), tx: (r.width - plan.width * f) / 2, ty: (r.height - plan.height * f) / 2, fitted: true });
    apply();
  }, [apply, baseScale, plan.width, plan.height]);

  const focus = useCallback((x: number, y: number, zoom = 5) => {
    const { r, f } = baseScale();
    const s = clamp(f * zoom, t.current.minS, t.current.maxS);
    Object.assign(t.current, { s, tx: r.width / 2 - x * plan.width * s, ty: r.height / 2 - y * plan.height * s + 30 });
    apply();
  }, [apply, baseScale, plan.width, plan.height]);

  useImperativeHandle(ref, () => ({
    fit,
    focus,
    bounce: (id) => {
      const el = pins.current?.querySelector(`[data-pin="${id}"]`);
      el?.classList.remove('hl');
      requestAnimationFrame(() => el?.classList.add('hl'));
    },
  }), [fit, focus]);

  useLayoutEffect(() => {
    t.current.fitted = false;
    const ro = new ResizeObserver(() => !t.current.fitted && fit());
    ro.observe(viewer.current!);
    return () => ro.disconnect();
  }, [fit]);

  useEffect(apply, [defects, apply]);

  useEffect(() => {
    const v = viewer.current!;
    const pts = new Map<number, { x: number; y: number }>();
    type G = { sx: number; sy: number; tx0: number; ty0: number; moved: boolean; multi: boolean; t0: number; pin: string | null; d0?: number; s0?: number; m0?: { x: number; y: number } };
    let g: G | null = null;
    const rel = (e: PointerEvent | WheelEvent | MouseEvent) => {
      const r = v.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    };
    const zoomAt = (cx: number, cy: number, ns: number) => {
      const T = t.current;
      ns = clamp(ns, T.minS, T.maxS);
      const px = (cx - T.tx) / T.s;
      const py = (cy - T.ty) / T.s;
      Object.assign(T, { s: ns, tx: cx - px * ns, ty: cy - py * ns });
      apply();
    };
    const down = (e: PointerEvent) => {
      if (e.button > 0) return;
      try { v.setPointerCapture(e.pointerId); } catch { /* ignore */ }
      pts.set(e.pointerId, rel(e));
      const T = t.current;
      if (pts.size === 1) {
        const p = rel(e);
        const pinEl = (e.target as HTMLElement).closest<HTMLElement>('.pin');
        g = { sx: p.x, sy: p.y, tx0: T.tx, ty0: T.ty, moved: false, multi: false, t0: Date.now(), pin: pinEl?.dataset.pin ?? null };
      } else if (pts.size === 2 && g) {
        const [a, b] = [...pts.values()];
        Object.assign(g, { multi: true, d0: Math.hypot(a.x - b.x, a.y - b.y) || 1, s0: T.s, m0: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, tx0: T.tx, ty0: T.ty });
      }
    };
    const move = (e: PointerEvent) => {
      if (!pts.has(e.pointerId) || !g) return;
      pts.set(e.pointerId, rel(e));
      const T = t.current;
      if (pts.size >= 2 && g.d0) {
        const [a, b] = [...pts.values()];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        const m = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
        const ns = clamp(g.s0! * d / g.d0, T.minS, T.maxS);
        const px = (g.m0!.x - g.tx0) / g.s0!;
        const py = (g.m0!.y - g.ty0) / g.s0!;
        Object.assign(T, { s: ns, tx: m.x - px * ns, ty: m.y - py * ns });
        apply();
      } else if (pts.size === 1) {
        const p = rel(e);
        const dx = p.x - g.sx;
        const dy = p.y - g.sy;
        if (Math.hypot(dx, dy) > 7) g.moved = true;
        if (g.moved) {
          Object.assign(T, { tx: g.tx0 + dx, ty: g.ty0 + dy });
          apply();
        }
      }
    };
    const up = (e: PointerEvent) => {
      if (!pts.has(e.pointerId)) return;
      const p = pts.get(e.pointerId)!;
      pts.delete(e.pointerId);
      if (!g) return;
      const T = t.current;
      if (pts.size === 1) {
        const [q] = [...pts.values()];
        Object.assign(g, { sx: q.x, sy: q.y, tx0: T.tx, ty0: T.ty, d0: 0, moved: true });
        return;
      }
      if (pts.size === 0) {
        const tap = !g.moved && !g.multi && Date.now() - g.t0 < 600 && e.type === 'pointerup';
        const pin = g.pin;
        g = null;
        if (!tap) return;
        if (!cb.current.placing) {
          if (pin) cb.current.onTapPin(pin);
          return;
        }
        const x = (p.x - T.tx) / T.s / plan.width;
        const y = (p.y - T.ty) / T.s / plan.height;
        if (x < 0 || y < 0 || x > 1 || y > 1) return;
        cb.current.onPlace(x, y);
      }
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const p = rel(e);
      zoomAt(p.x, p.y, t.current.s * Math.exp(-e.deltaY * 0.0015));
    };
    const dbl = (e: MouseEvent) => {
      const p = rel(e);
      zoomAt(p.x, p.y, t.current.s * 2);
    };
    const noGesture = (e: Event) => e.preventDefault();
    v.addEventListener('pointerdown', down);
    v.addEventListener('pointermove', move);
    v.addEventListener('pointerup', up);
    v.addEventListener('pointercancel', up);
    v.addEventListener('wheel', wheel, { passive: false });
    v.addEventListener('dblclick', dbl);
    document.addEventListener('gesturestart', noGesture);
    return () => {
      v.removeEventListener('pointerdown', down);
      v.removeEventListener('pointermove', move);
      v.removeEventListener('pointerup', up);
      v.removeEventListener('pointercancel', up);
      v.removeEventListener('wheel', wheel);
      v.removeEventListener('dblclick', dbl);
      document.removeEventListener('gesturestart', noGesture);
    };
  }, [apply, plan.width, plan.height]);

  return (
    <div className={`viewer${placing ? ' adding' : ''}`} ref={viewer}>
      <div className="stage" ref={stage} style={{ width: plan.width, height: plan.height }}>
        {src && <img src={src} alt={`Plan ${plan.name}`} draggable={false} />}
        <div className="pins" ref={pins}>
          {[...defects].sort((a, b) => a.y - b.y).map((d) => (
            <button key={d.id} className={`pin${isFixed(d) ? ' fixed' : ''}`} data-pin={d.id}
              style={{ left: d.x * plan.width, top: d.y * plan.height, transform: `translate(-50%,-100%) scale(${1 / t.current.s})` }}
              aria-label={`Usterka nr ${d.no}`}>
              <PinSvg no={d.no} />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
});

export default PlanViewer;
