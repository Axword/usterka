import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useFileUrl } from 'src/components/common/AuthImage';
import { BackIcon } from 'src/components/common/Icons';
import DefectForm from 'src/components/defect/DefectForm';
import PlanViewer, { type PlanViewerHandle } from 'src/components/plan/PlanViewer';
import { errorMessage } from 'src/service/http';
import { PlanService } from 'src/service/plan';
import { useAuth } from 'src/stores/authStore';
import { useProjectStore } from 'src/stores/projectStore';
import { dialog, toast } from 'src/stores/uiStore';
import type { Defect } from 'src/types/api';
import { isFixed } from 'src/utils/defects';
import { clearDraft, loadDraft, type DefectDraft } from 'src/utils/draft';

type Mode = { kind: 'browse' } | { kind: 'add' } | { kind: 'move'; resolve: (p: { x: number; y: number } | null) => void };
interface FormState {
  defect: Defect | null;
  at: { x: number; y: number };
  draft: DefectDraft | null;
}

export default function PlanPage() {
  const { projectId = '', planId = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const canWrite = useAuth((s) => s.canWrite());
  const { project, plans, defects, organization, load, upsertDefect, removeDefect, refreshProject } = useProjectStore();
  const plan = plans.find((p) => p.id === planId);
  const src = useFileUrl(plan ? PlanService.imageUrl(plan.id) : null);
  const viewer = useRef<PlanViewerHandle>(null);
  const [mode, setMode] = useState<Mode>({ kind: 'browse' });
  const [form, setForm] = useState<FormState | null>(null);
  const planDefects = defects.filter((d) => d.plan_id === planId);
  const opened = useRef(false);

  useEffect(() => {
    if (project?.id !== projectId) load(projectId).catch((e) => { toast(errorMessage(e)); nav('/'); });
  }, [projectId, project?.id, load, nav]);

  // otwarcie usterki z listy (?defect=) albo przywrócenie szkicu
  useEffect(() => {
    if (!plan || !src || opened.current) return;
    opened.current = true;
    const id = params.get('defect');
    requestAnimationFrame(async () => {
      viewer.current?.fit();
      const draft = loadDraft();
      if (draft && draft.planId === plan.id) {
        const what = draft.defectId ? `Usterka nr ${draft.no}` : 'Nowa usterka';
        const ok = await dialog({ title: 'Niedokończona usterka', text: `${what} na tym planie nie została zapisana. Wrócić do niej?`, okLabel: 'Wróć do usterki', cancelLabel: 'Odrzuć' });
        if (ok) {
          const d = draft.defectId ? defects.find((x) => x.id === draft.defectId) ?? null : null;
          viewer.current?.focus(draft.x, draft.y);
          setForm({ defect: d, at: { x: draft.x, y: draft.y }, draft });
          return;
        }
        clearDraft();
      }
      if (id) {
        const d = defects.find((x) => x.id === id);
        if (d) {
          viewer.current?.focus(d.x, d.y);
          viewer.current?.bounce(d.id);
          setTimeout(() => setForm({ defect: d, at: d, draft: null }), 450);
        }
        setParams({}, { replace: true });
      }
    });
  }, [plan, src, params, defects, setParams]);

  if (!project || !plan) return <main className="wrap"><p className="muted">Wczytywanie…</p></main>;

  const open = planDefects.filter((d) => !isFixed(d)).length;

  const onPlace = (x: number, y: number) => {
    if (mode.kind === 'add') {
      setMode({ kind: 'browse' });
      setForm({ defect: null, at: { x, y }, draft: null });
    } else if (mode.kind === 'move') {
      mode.resolve({ x, y });
      setMode({ kind: 'browse' });
    }
  };

  const cancelMode = () => {
    if (mode.kind === 'move') mode.resolve(null);
    setMode({ kind: 'browse' });
  };

  return (
    <div className="vscreen">
      <header className="vbar">
        <button className="iconbtn" aria-label="Wróć do inwestycji" onClick={() => nav(`/projects/${project.id}`)}><BackIcon /></button>
        <div className="vtitle"><span className="vt">{plan.name}</span><span className="vs">{project.name}</span></div>
        <button className="btn small" onClick={() => viewer.current?.fit()}>Cały plan</button>
      </header>
      <PlanViewer ref={viewer} plan={plan} src={src} defects={planDefects} placing={mode.kind !== 'browse'}
        onTapPin={(id) => { const d = planDefects.find((x) => x.id === id); if (d) setForm({ defect: d, at: d, draft: null }); }}
        onPlace={onPlace} />
      {mode.kind === 'browse' ? (
        <footer className="vtools">
          <div className="legend">
            <span><i className="dot" style={{ background: 'var(--open)' }} />otwarte: {open}</span>
            <span><i className="dot" style={{ background: 'var(--fixed)' }} />usunięte: {planDefects.length - open}</span>
          </div>
          {canWrite && <button className="btn primary" onClick={() => setMode({ kind: 'add' })}>Dodaj usterkę</button>}
        </footer>
      ) : (
        <footer className="vtools mode">
          <div className="tape" />
          <div className="mode-row">
            <div className="mode-t">{mode.kind === 'add' ? 'Stuknij w planie miejsce usterki' : 'Stuknij nowe miejsce usterki na planie'}</div>
            <button className="btn small" onClick={cancelMode}>Anuluj</button>
          </div>
        </footer>
      )}
      {form && (
        <DefectForm
          key={form.defect?.id ?? 'new'}
          projectId={project.id}
          plan={plan}
          defect={form.defect}
          at={form.at}
          draft={form.draft}
          defects={planDefects}
          types={organization?.defect_types ?? []}
          hidden={mode.kind === 'move'}
          requestMove={() => new Promise((resolve) => setMode({ kind: 'move', resolve }))}
          onClose={() => setForm(null)}
          onSaved={(d, isNew) => {
            upsertDefect(d);
            setForm(null);
            refreshProject();
            toast(isNew ? `Dodano usterkę nr ${d.no}` : `Zapisano usterkę nr ${d.no}`);
          }}
          onDeleted={(d) => {
            removeDefect(d.id);
            setForm(null);
            refreshProject();
            toast(`Usterka nr ${d.no} usunięta`);
          }}
        />
      )}
    </div>
  );
}
