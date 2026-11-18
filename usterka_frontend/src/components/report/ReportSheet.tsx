import { useState } from 'react';
import Sheet from 'src/components/common/Sheet';
import { errorMessage } from 'src/service/http';
import { ProjectService } from 'src/service/project';
import { ReportService } from 'src/service/report';
import { useAuth } from 'src/stores/authStore';
import { useProjectStore } from 'src/stores/projectStore';
import { busy, dialog, toast } from 'src/stores/uiStore';
import type { DefectFilter, ReportSettings } from 'src/types/api';
import { fmtDate, todayISO } from 'src/utils/dates';
import { safeName } from 'src/utils/defects';
import { downloadBlob } from 'src/utils/download';
import { selectDefects } from 'src/utils/report/gather';

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

export default function ReportSheet({ onClose, onCreated }: Props) {
  const { project, plans, defects, organization, setProject } = useProjectStore();
  const me = useAuth((s) => s.me);
  const spConfigured = !!organization?.sharepoint_configured;
  const rs = project!.report_settings || {};
  const [s, setS] = useState<ReportSettings>({
    date: rs.date ?? null,
    filter: rs.filter ?? 'all',
    plans: rs.plans !== false,
    logo: project!.has_logo && rs.logo !== false,
    sharepoint: rs.sharepoint !== false,
  });
  const [prog, setProg] = useState('');
  const docDate = s.date || todayISO();

  const persist = (next: ReportSettings) => {
    setS(next);
    ProjectService.saveReportSettings(project!.id, next).then(setProject).catch(() => {});
  };

  const generate = async (kind: 'pdf' | 'docx') => {
    const p = project!;
    const data = selectDefects(plans, defects, s.filter);
    if (!data.defects.length) return toast('Brak usterek spełniających wybrany warunek');
    const progress = (t: string) => {
      setProg(t);
      busy(t);
    };
    try {
      progress('Wczytywanie generatora…');
      const opts = { date: docDate, filter: s.filter, plans: s.plans, logo: s.logo };
      const blob = kind === 'pdf'
        ? await (await import('src/utils/report/pdf')).buildPDF(p, data, opts, progress)
        : await (await import('src/utils/report/docx')).buildDOCX(p, data, opts, progress);
      downloadBlob(`Protokol_usterek_${safeName(p.name)}_${fmtDate(docDate).replace(/\./g, '-')}.${kind}`, blob);
      const toSp = spConfigured && s.sharepoint;
      progress(toSp ? 'Archiwizacja i zapis w SharePoint…' : 'Archiwizacja raportu…');
      const rep = await ReportService.create(p.id, { kind, documentDate: docDate, filter: s.filter, count: data.defects.length, sharepoint: toSp, file: blob });
      busy(null);
      setProg('');
      onCreated();
      if (rep.sharepoint_status === 'ok') toast('Raport zapisany w SharePoint');
      else if (rep.sharepoint_status === 'error') await dialog({ title: 'SharePoint: nie zapisano', text: rep.sharepoint_error, okLabel: 'Rozumiem', cancelLabel: null });
      else toast('Raport pobrany i zarchiwizowany');
    } catch (e) {
      console.error(e);
      busy(null);
      setProg('');
      toast(`Nie udało się utworzyć raportu: ${errorMessage(e)}`, 5000);
    }
  };

  const filters: [DefectFilter, string][] = [['all', 'Wszystkie'], ['open', 'Otwarte'], ['fixed', 'Usunięte']];

  return (
    <Sheet title="Raport" onClose={onClose}>
      <p className="muted" style={{ marginTop: 0 }}>{project!.name}</p>
      <label className="field" style={{ marginBottom: 6 }}>
        <span className="lbl">Data dokumentu</span>
        <input className="inp" type="date" value={docDate}
          onChange={(e) => persist({ ...s, date: e.target.value && e.target.value !== todayISO() ? e.target.value : null })} />
      </label>
      <div className="row" style={{ alignItems: 'center', marginBottom: 18 }}>
        {s.date ? (
          <>
            <span className="muted small" style={{ flex: 1 }}>Zapamiętana data dokumentu.</span>
            <button className="btn small" onClick={() => persist({ ...s, date: null })}>Ustaw dzisiejszą</button>
          </>
        ) : <span className="muted small">Domyślnie dzisiejsza data.</span>}
      </div>
      <div className="field">
        <span className="lbl">Uwzględnij usterki</span>
        <div className="seg three">
          {filters.map(([k, l]) => <button key={k} aria-pressed={s.filter === k} onClick={() => persist({ ...s, filter: k })}>{l}</button>)}
        </div>
      </div>
      <label className="check"><input type="checkbox" checked={s.plans} onChange={(e) => persist({ ...s, plans: e.target.checked })} /> Dołącz całe plany z oznaczonymi usterkami</label>
      {project!.has_logo && <label className="check"><input type="checkbox" checked={s.logo} onChange={(e) => persist({ ...s, logo: e.target.checked })} /> Dodaj logo firmy</label>}
      <label className="check">
        <input type="checkbox" checked={spConfigured && s.sharepoint} disabled={!spConfigured} onChange={(e) => persist({ ...s, sharepoint: e.target.checked })} /> Zapisz kopię w SharePoint
      </label>
      <p className="muted small" style={{ margin: '0 0 4px', overflowWrap: 'anywhere' }}>
        {spConfigured
          ? `Witryna: ${organization!.sp_site_url} / ${organization!.sp_library} / ${organization!.sp_folder.replace('{inwestycja}', project!.name)}`
          : 'Administrator musi uzupełnić adres witryny i bibliotekę SharePoint w Ustawieniach.'}
        {spConfigured && !me?.microsoft && ' Zapis do SharePoint wymaga logowania kontem Microsoft.'}
      </p>
      <p className="muted small">Raport zawiera dane inwestycji, zestawienie usterek, karty usterek z wycinkiem planu i zdjęciami przed i po usunięciu oraz miejsce na podpisy. Każdy raport jest archiwizowany w historii inwestycji.</p>
      <button className="btn primary block" onClick={() => generate('pdf')}>Pobierz PDF</button>
      <button className="btn block" onClick={() => generate('docx')}>Pobierz Word (.docx) do edycji</button>
      <div className="progress" role="status">{prog}</div>
    </Sheet>
  );
}
