import { useEffect, useState } from 'react';
import Sheet from 'src/components/common/Sheet';
import FileButton from 'src/components/common/FileButton';
import { ImgIcon } from 'src/components/common/Icons';
import { useFileUrl } from 'src/components/common/AuthImage';
import { forgetFile } from 'src/service/files';
import { errorMessage } from 'src/service/http';
import { ProjectService } from 'src/service/project';
import { dialog, toast, withBusy } from 'src/stores/uiStore';
import type { Project, ProjectInput } from 'src/types/api';
import { todayISO } from 'src/utils/dates';
import { fileToImage, resizeImage } from 'src/utils/images';

const FIELDS: [keyof ProjectInput, string, string?][] = [
  ['name', 'Nazwa inwestycji'],
  ['address', 'Adres inwestycji'],
  ['investor', 'Inwestor'],
  ['contractor', 'Wykonawca'],
  ['inspection_date', 'Data przeglądu', 'date'],
  ['author', 'Osoba sporządzająca protokół'],
];

interface Props {
  project: Project | null;
  onClose: () => void;
  onSaved: (p: Project) => void;
  onDeleted?: () => void;
}

export default function ProjectForm({ project, onClose, onSaved, onDeleted }: Props) {
  const isNew = !project;
  const [v, setV] = useState<ProjectInput>(() => ({
    name: project?.name ?? '',
    address: project?.address ?? '',
    investor: project?.investor ?? '',
    contractor: project?.contractor ?? '',
    inspection_date: project?.inspection_date ?? todayISO(),
    author: project?.author ?? '',
  }));
  const [bad, setBad] = useState<Set<string>>(new Set());
  const [logo, setLogo] = useState<Blob | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [removeLogo, setRemoveLogo] = useState(false);
  const existingLogo = useFileUrl(project?.has_logo ? ProjectService.logoUrl(project.id) : null);

  useEffect(() => () => {
    if (logoPreview) URL.revokeObjectURL(logoPreview);
  }, [logoPreview]);

  const pickLogo = async ([f]: File[]) => {
    try {
      const r = await resizeImage(await fileToImage(f), 800, 0.92, 'image/png');
      setLogo(r.blob);
      setLogoPreview(URL.createObjectURL(r.blob));
      setRemoveLogo(false);
    } catch {
      toast('Nie udało się wczytać logo');
    }
  };

  const save = async () => {
    const missing = new Set(FIELDS.filter(([k]) => !String(v[k] ?? '').trim()).map(([k]) => k));
    setBad(missing);
    if (missing.size) return;
    try {
      let logoError: string | null = null;
      const saved = await withBusy('Zapisywanie…', async () => {
        let p = isNew ? await ProjectService.create(v) : await ProjectService.update(project.id, v);
        try {
          if (logo) {
            p = await ProjectService.uploadLogo(p.id, logo);
            forgetFile(ProjectService.logoUrl(p.id));
          } else if (removeLogo && p.has_logo) {
            p = await ProjectService.removeLogo(p.id);
            forgetFile(ProjectService.logoUrl(p.id));
          }
        } catch (e) {
          logoError = errorMessage(e); // dane inwestycji są już zapisane - nie tracimy ich przez logo
        }
        return p;
      });
      onSaved(saved);
      if (logoError) toast(`Dane zapisane, ale logo się nie wysłało: ${logoError}`, 6000);
    } catch (e) {
      toast(errorMessage(e));
    }
  };

  const remove = async () => {
    const ok = await dialog({ title: 'Usunąć inwestycję?', text: 'Usunięte zostaną wszystkie plany, usterki, zdjęcia i raporty tej inwestycji. Tego nie można cofnąć.', okLabel: 'Usuń', danger: true });
    if (!ok || !project) return;
    try {
      await withBusy('Usuwanie…', () => ProjectService.remove(project.id));
      onDeleted?.();
    } catch (e) {
      toast(errorMessage(e));
    }
  };

  const shownLogo = logoPreview ?? (!removeLogo ? existingLogo : undefined);

  return (
    <Sheet title={isNew ? 'Dane inwestycji' : 'Edycja danych inwestycji'} onClose={onClose}
      action={<button className="btn primary small" onClick={save}>Zapisz</button>}>
      <p className="muted small" style={{ marginTop: 0 }}>Wszystkie pola oprócz logo są obowiązkowe. Dane możesz zmienić w każdej chwili.</p>
      {FIELDS.map(([k, label, type]) => (
        <label className="field" key={k}>
          <span className="lbl">{label} <span className="req">*</span></span>
          <input className={`inp${bad.has(k) ? ' bad' : ''}`} type={type || 'text'} value={v[k] ?? ''} autoComplete="off"
            onChange={(e) => setV({ ...v, [k]: e.target.value })} />
          {bad.has(k) && <div className="ferr">To pole jest wymagane</div>}
        </label>
      ))}
      <div className="field">
        <span className="lbl">Logo firmy (opcjonalnie)</span>
        {shownLogo && (
          <div className="logo-prev">
            <img src={shownLogo} alt="Logo" />
            <button className="btn small danger" onClick={() => { setLogo(null); setLogoPreview(null); setRemoveLogo(true); }}>Usuń logo</button>
          </div>
        )}
        <FileButton accept="image/png,image/jpeg,image/webp" onFiles={pickLogo} label="Wybierz logo"><ImgIcon /> Wybierz logo</FileButton>
      </div>
      {bad.size > 0 && <p className="formerr">Uzupełnij wymagane pola.</p>}
      <button className="btn primary block" onClick={save}>{isNew ? 'Zapisz i przejdź dalej' : 'Zapisz zmiany'}</button>
      {!isNew && <button className="btn danger block" onClick={remove}>Usuń inwestycję</button>}
    </Sheet>
  );
}
