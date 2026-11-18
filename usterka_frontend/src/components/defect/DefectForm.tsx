import { useEffect, useMemo, useRef, useState } from 'react';
import AuthImage from 'src/components/common/AuthImage';
import FileButton from 'src/components/common/FileButton';
import { CamIcon, ImgIcon } from 'src/components/common/Icons';
import Sheet from 'src/components/common/Sheet';
import { DefectService } from 'src/service/defect';
import { fileImage, fileUrl } from 'src/service/files';
import { errorMessage } from 'src/service/http';
import { PlanService } from 'src/service/plan';
import { useAuth } from 'src/stores/authStore';
import { dialog, toast, useUi, withBusy } from 'src/stores/uiStore';
import type { Defect, DueMode, PhotoKind, Plan } from 'src/types/api';
import { todayISO } from 'src/utils/dates';
import { uuid } from 'src/utils/defects';
import { clearDraft, saveDraft, type DefectDraft } from 'src/utils/draft';
import { fileToImage, renderCrop, resizeImage, toPin } from 'src/utils/images';

interface Pending {
  key: string;
  kind: PhotoKind;
  blob: Blob;
  url: string;
}

interface Props {
  projectId: string;
  plan: Plan;
  defect: Defect | null;
  at: { x: number; y: number };
  draft: DefectDraft | null;
  defects: Defect[];
  types: string[];
  hidden: boolean;
  requestMove: () => Promise<{ x: number; y: number } | null>;
  onClose: () => void;
  onSaved: (d: Defect, isNew: boolean) => void;
  onDeleted: (d: Defect) => void;
}

export default function DefectForm({ projectId, plan, defect, at, draft, defects, types, hidden, requestMove, onClose, onSaved, onDeleted }: Props) {
  const canWrite = useAuth((s) => s.canWrite());
  const isNew = !defect;
  const [f, setF] = useState(() => ({
    type: draft?.type ?? defect?.type ?? '',
    typeOther: draft?.typeOther ?? defect?.type_other ?? '',
    desc: draft?.desc ?? defect?.description ?? '',
    dueMode: (draft?.dueMode ?? defect?.due_mode ?? '') as DueMode | '',
    dueDate: draft?.dueDate ?? defect?.due_date ?? '',
    zoom: draft?.zoom ?? defect?.zoom ?? 0.3,
    x: draft?.x ?? at.x,
    y: draft?.y ?? at.y,
    fixedDate: draft?.fixedDate ?? defect?.fixed_date ?? '',
  }));
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  const [pending, setPending] = useState<Pending[]>([]);
  const [dirty, setDirty] = useState(!!draft);
  const [errors, setErrors] = useState<{ type?: boolean; desc?: boolean; due?: boolean }>({});
  const [autosaved, setAutosaved] = useState('');
  const crop = useRef<HTMLCanvasElement>(null);
  const [img, setImg] = useState<HTMLImageElement | null>(null);

  const existing = (defect?.photos || []).filter((p) => !removed.has(p.id));
  const afterCount = existing.filter((p) => p.kind === 'after').length + pending.filter((p) => p.kind === 'after').length;
  const fixed = afterCount > 0;

  useEffect(() => {
    fileImage(PlanService.imageUrl(plan.id)).then(setImg).catch(() => {});
  }, [plan.id]);

  const pin = useMemo(() => ({ ...toPin({ id: defect?.id ?? 'new', plan_id: plan.id, no: defect?.no ?? null, x: f.x, y: f.y, zoom: f.zoom }), fixed }), [defect, plan.id, f.x, f.y, f.zoom, fixed]);
  useEffect(() => {
    if (img && crop.current) renderCrop(img, pin, defects.map(toPin), crop.current, 800, 600);
  }, [img, pin, defects]);

  useEffect(() => {
    if (fixed && !f.fixedDate) setF((v) => ({ ...v, fixedDate: todayISO() }));
  }, [fixed, f.fixedDate]);

  // autosave szkicu 400 ms po zmianie
  useEffect(() => {
    if (!dirty) return;
    const t = setTimeout(() => {
      saveDraft({ projectId, planId: plan.id, defectId: defect?.id ?? null, no: defect?.no ?? null, ...f, savedAt: Date.now() });
      setAutosaved(`Szkic zapisany ${new Date().toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' })}`);
    }, 400);
    return () => clearTimeout(t);
  }, [f, dirty, projectId, plan.id, defect]);

  useEffect(() => () => pending.forEach((p) => URL.revokeObjectURL(p.url)), [pending]);

  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => {
    setF((x) => ({ ...x, [k]: v }));
    setDirty(true);
  };

  const addPhotos = async (kind: PhotoKind, files: File[]) => {
    try {
      const out: Pending[] = [];
      await withBusy('Dodawanie zdjęć…', async () => {
        for (const file of files) {
          const r = await resizeImage(await fileToImage(file), 1600, 0.82);
          out.push({ key: uuid(), kind, blob: r.blob, url: URL.createObjectURL(r.blob) });
        }
      });
      setPending((p) => [...p, ...out]);
      setDirty(true);
    } catch {
      toast('Nie udało się dodać zdjęcia');
    }
  };

  const close = async () => {
    if (dirty || pending.length) {
      const ok = await dialog({ title: 'Odrzucić zmiany?', text: 'Niezapisane zmiany w tej usterce zostaną utracone.', okLabel: 'Odrzuć', cancelLabel: 'Wróć do edycji', danger: true });
      if (!ok) return;
    }
    clearDraft();
    onClose();
  };

  const move = async () => {
    const p = await requestMove();
    if (p) {
      setF((v) => ({ ...v, ...p }));
      setDirty(true);
    }
  };

  const save = async () => {
    const e = { type: !f.type, desc: !f.desc.trim(), due: !f.dueMode || (f.dueMode === 'data' && !f.dueDate) };
    setErrors(e);
    if (e.type || e.desc || e.due) return;
    const body = {
      plan_id: plan.id, x: f.x, y: f.y, type: f.type, type_other: f.type === 'Inna' ? f.typeOther.trim() : '',
      description: f.desc.trim(), due_mode: f.dueMode as DueMode, due_date: f.dueMode === 'data' ? f.dueDate : null, zoom: f.zoom,
    };
    try {
      const saved = await withBusy('Zapisywanie…', async () => {
        let d = isNew ? await DefectService.create(projectId, { id: uuid(), ...body }) : await DefectService.update(defect.id, body);
        for (let i = 0; i < pending.length; i++) {
          useUi.getState().setBusy(`Wysyłanie zdjęć ${i + 1} z ${pending.length}…`);
          d = await DefectService.addPhoto(d.id, pending[i].kind, pending[i].blob);
        }
        for (const id of removed) d = await DefectService.removePhoto(id);
        if (d.status === 'fixed' && f.fixedDate && d.fixed_date !== f.fixedDate) d = await DefectService.update(d.id, { fixed_date: f.fixedDate });
        return d;
      });
      clearDraft();
      onSaved(saved, isNew);
    } catch (err) {
      toast(`Nie udało się zapisać: ${errorMessage(err)}`, 5000);
    }
  };

  const remove = async () => {
    if (!defect) return;
    const ok = await dialog({ title: `Usunąć usterkę nr ${defect.no}?`, text: 'Usunięte zostaną też jej zdjęcia.', okLabel: 'Usuń', danger: true });
    if (!ok) return;
    try {
      await withBusy('Usuwanie…', () => DefectService.remove(defect.id));
      clearDraft();
      onDeleted(defect);
    } catch (err) {
      toast(errorMessage(err));
    }
  };

  const view = async (photoId: string) => useUi.getState().setLightbox(await fileUrl(DefectService.photoUrl(photoId)));

  const photos = (kind: PhotoKind) => (
    <div className="photos">
      {existing.filter((p) => p.kind === kind).map((p, i) => (
        <div className="ph" key={p.id}>
          <AuthImage path={DefectService.photoUrl(p.id)} alt={`Zdjęcie ${i + 1}`} onClick={() => view(p.id)} />
          {canWrite && <button type="button" className="x" aria-label="Usuń zdjęcie" onClick={() => { setRemoved(new Set(removed).add(p.id)); setDirty(true); }}>✕</button>}
        </div>
      ))}
      {pending.filter((p) => p.kind === kind).map((p) => (
        <div className="ph" key={p.key}>
          <img src={p.url} alt="Nowe zdjęcie" onClick={() => useUi.getState().setLightbox(p.url)} />
          <button type="button" className="x" aria-label="Usuń zdjęcie" onClick={() => setPending((x) => x.filter((y) => y.key !== p.key))}>✕</button>
        </div>
      ))}
    </div>
  );

  const photoButtons = (kind: PhotoKind) => canWrite && (
    <div className="row">
      <FileButton accept="image/*" capture="environment" onFiles={(fs) => addPhotos(kind, fs)} label="Zrób zdjęcie"><CamIcon /> Zrób zdjęcie</FileButton>
      <FileButton accept="image/*" multiple onFiles={(fs) => addPhotos(kind, fs)} label="Dodaj z galerii"><ImgIcon /> Z galerii</FileButton>
    </div>
  );

  return (
    <Sheet title={isNew ? 'Nowa usterka' : `Usterka nr ${defect.no}`} onClose={close} hidden={hidden}
      action={canWrite ? <button className="btn primary small" onClick={save}>Zapisz</button> : undefined}>
      {draft && <p className="note" style={{ margin: '0 0 16px' }}>Przywrócono niezapisaną wersję (bez nowych zdjęć). Sprawdź dane i naciśnij „Zapisz”.</p>}
      <fieldset disabled={!canWrite} style={{ border: 0, padding: 0, margin: 0 }}>
        <div className="field">
          <span className="lbl">Rodzaj usterki <span className="req">*</span></span>
          <div className={`chips${errors.type ? ' bad' : ''}`}>
            {types.map((t) => <button type="button" key={t} aria-pressed={f.type === t} onClick={() => set('type', t)}>{t}</button>)}
          </div>
          {f.type === 'Inna' && <input className="inp mt" placeholder="Doprecyzuj rodzaj (opcjonalnie)" value={f.typeOther} onChange={(e) => set('typeOther', e.target.value)} />}
          {errors.type && <div className="ferr">Wybierz rodzaj usterki</div>}
        </div>
        <label className="field">
          <span className="lbl">Opis <span className="req">*</span></span>
          <textarea className={`inp${errors.desc ? ' bad' : ''}`} rows={4} placeholder="Co jest nie tak i gdzie dokładnie" value={f.desc} onChange={(e) => set('desc', e.target.value)} />
          {errors.desc && <div className="ferr">Wpisz opis usterki</div>}
        </label>
        <div className="field">
          <span className="lbl">Termin usunięcia <span className="req">*</span></span>
          <div className={`seg${errors.due ? ' bad' : ''}`}>
            <button type="button" aria-pressed={f.dueMode === 'umowa'} onClick={() => set('dueMode', 'umowa')}>Zgodnie z umową</button>
            <button type="button" aria-pressed={f.dueMode === 'data'} onClick={() => { set('dueMode', 'data'); if (!f.dueDate) set('dueDate', todayISO()); }}>Konkretna data</button>
          </div>
          {f.dueMode === 'data' && <input className="inp mt" type="date" value={f.dueDate} onChange={(e) => set('dueDate', e.target.value)} />}
          {errors.due && <div className="ferr">Wybierz termin usunięcia</div>}
        </div>
        <div className="field">
          <span className="lbl">Wycinek planu do raportu</span>
          <canvas className="crop" ref={crop} />
          <label className="range">
            <span>Bliżej</span>
            <input type="range" min={0.1} max={0.6} step={0.01} value={f.zoom} aria-label="Zasięg wycinka planu" onChange={(e) => set('zoom', +e.target.value)} />
            <span>Dalej</span>
          </label>
          <p className="muted small" style={{ margin: '0 0 8px' }}>Ustaw tak, żeby było widać pomieszczenie i jego otoczenie.</p>
          <button type="button" className="btn" onClick={move}>Przesuń znacznik</button>
        </div>
        <div className="field">
          <span className="lbl">Zdjęcia usterki</span>
          {photos('before')}
          {photoButtons('before')}
        </div>
        <div className={`field fixbox${fixed ? ' on' : ''}`}>
          <span className="lbl">Po usunięciu usterki</span>
          <p className="muted small" style={{ margin: '0 0 8px' }}>Dodanie zdjęcia po usunięciu oznacza usterkę jako usuniętą.</p>
          {photos('after')}
          {photoButtons('after')}
          {fixed && (
            <label className="field mt" style={{ marginBottom: 0 }}>
              <span className="lbl">Data usunięcia</span>
              <input className="inp" type="date" value={f.fixedDate} onChange={(e) => set('fixedDate', e.target.value)} />
            </label>
          )}
        </div>
      </fieldset>
      {(errors.type || errors.desc || errors.due) && <p className="formerr">Uzupełnij wymagane pola.</p>}
      <p className="muted small" style={{ margin: 0 }} aria-live="polite">{autosaved}</p>
      {canWrite && <button className="btn primary block" onClick={save}>Zapisz usterkę</button>}
      {canWrite && !isNew && <button className="btn danger block" onClick={remove}>Usuń usterkę</button>}
    </Sheet>
  );
}
