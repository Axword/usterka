import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import AuthImage from 'src/components/common/AuthImage';
import FileButton from 'src/components/common/FileButton';
import { BackIcon, MoreIcon } from 'src/components/common/Icons';
import PdfPagePicker from 'src/components/plan/PdfPagePicker';
import PlanMenu from 'src/components/project/PlanMenu';
import ProjectForm from 'src/components/project/ProjectForm';
import ReportSheet from 'src/components/report/ReportSheet';
import ReportList from 'src/components/report/ReportList';
import { errorMessage } from 'src/service/http';
import { PlanService } from 'src/service/plan';
import { useAuth } from 'src/stores/authStore';
import { useProjectStore } from 'src/stores/projectStore';
import { busy, dialog, toast } from 'src/stores/uiStore';
import type { Plan } from 'src/types/api';
import { fmtDate } from 'src/utils/dates';
import { isFixed, typeLabel } from 'src/utils/defects';
import { fileToImage, resizeImage } from 'src/utils/images';
import { openPdf, renderPdfPage } from 'src/utils/pdfImport';

export default function ProjectPage() {
  const { projectId = '' } = useParams();
  const nav = useNavigate();
  const canWrite = useAuth((s) => s.canWrite());
  const { project, plans, defects, load, setProject, upsertPlan } = useProjectStore();
  const [editing, setEditing] = useState(false);
  const [menu, setMenu] = useState<Plan | null>(null);
  const [report, setReport] = useState(false);
  const [reportsVersion, setReportsVersion] = useState(0);
  const [pdfPick, setPdfPick] = useState<{ pdf: PDFDocumentProxy; resolve: (n: number | null) => void } | null>(null);

  useEffect(() => {
    load(projectId).catch((e) => {
      toast(errorMessage(e));
      nav('/');
    });
  }, [projectId, load, nav]);

  if (!project || project.id !== projectId) return <main className="wrap"><p className="muted">Wczytywanie…</p></main>;

  const open = defects.filter((d) => !isFixed(d)).length;
  const planName = new Map(plans.map((p) => [p.id, p.name]));

  const addPlan = async ([file]: File[]) => {
    const isPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
    let baseName = file.name.replace(/\.[^.]+$/, '');
    let res: { blob: Blob; w: number; h: number };
    let page: number | null = null;
    try {
      if (isPdf) {
        busy('Wczytywanie pliku PDF…');
        const pdf = await openPdf(file);
        busy(null);
        page = 1;
        if (pdf.numPages > 1) {
          page = await new Promise<number | null>((resolve) => setPdfPick({ pdf, resolve }));
          setPdfPick(null);
          if (!page) return;
          baseName += ` – str. ${page}`;
        }
        busy('Przygotowanie planu…');
        res = await renderPdfPage(pdf, page);
        pdf.destroy();
      } else {
        busy('Przygotowanie planu…');
        res = await resizeImage(await fileToImage(file), 4000, 0.9);
      }
    } catch (e) {
      toast(`Nie udało się wczytać pliku: ${errorMessage(e)}`);
      return;
    } finally {
      busy(null);
    }
    const name = await dialog({ title: 'Nazwa planu', text: 'Na przykład: Parter, Piętro 1, Garaż.', input: baseName, okLabel: 'Zapisz plan' });
    if (name === null) return;
    try {
      busy('Wysyłanie planu…');
      const plan = await PlanService.create(project.id, { name: name || baseName, image: res.blob, sourceFilename: file.name, sourcePage: page },
        (p) => busy(`Wysyłanie planu… ${Math.round(p * 100)}%`));
      upsertPlan(plan);
      nav(`/projects/${project.id}/plans/${plan.id}`);
      toast('Plan dodany. Stuknij „Dodaj usterkę”.');
    } catch (e) {
      toast(errorMessage(e));
    } finally {
      busy(null);
    }
  };

  return (
    <>
      <header className="bar">
        <Link className="back" to="/"><BackIcon />Inwestycje</Link>
        <span style={{ flex: 1 }} />
        {canWrite && <button className="btn small" onClick={() => setEditing(true)}>Edytuj dane</button>}
      </header>
      <main className="wrap">
        <h1 className="h1">{project.name}</h1>
        <div className="muted">{project.address}</div>
        <div className="split">
        <aside>
        <dl className="data">
          {([['Inwestor', project.investor], ['Wykonawca', project.contractor], ['Data przeglądu', fmtDate(project.inspection_date)], ['Osoba sporządzająca protokół', project.author]] as const).map(([l, v]) => (
            <div key={l} style={{ display: 'contents' }}>
              <dt>{l}</dt>
              <dd>{v || <span className="req">brak</span>}</dd>
            </div>
          ))}
        </dl>
        {!project.is_complete && <p className="note">Uzupełnij wszystkie dane inwestycji, aby dodać plan.</p>}

        <h2 className="h2">Plany <span className="n">{plans.length}</span></h2>
        {!plans.length && <p className="muted" style={{ margin: '0 0 4px' }}>Dodaj podkład z pliku PDF albo zdjęcia JPG. Na nim zaznaczysz usterki.</p>}
        <ul className="plans">
          {plans.map((x) => {
            const ds = defects.filter((d) => d.plan_id === x.id);
            const o = ds.filter((d) => !isFixed(d)).length;
            return (
              <li className="plan" key={x.id}>
                <button className="plan-open" onClick={() => nav(`/projects/${project.id}/plans/${x.id}`)}>
                  <AuthImage path={PlanService.imageUrl(x.id)} alt="" />
                  <span style={{ minWidth: 0 }}>
                    <span className="plan-t">{x.name}</span>
                    <span className="counts"><span className="cnt open">otwarte: {o}</span><span className="cnt fixed">usunięte: {ds.length - o}</span></span>
                  </span>
                </button>
                {canWrite && <button className="iconbtn" aria-label={`Opcje planu ${x.name}`} onClick={() => setMenu(x)}><MoreIcon /></button>}
              </li>
            );
          })}
        </ul>
        {canWrite && (project.is_complete ? (
          <FileButton className={`btn ${plans.length ? '' : 'primary '}block`} accept=".pdf,application/pdf,image/jpeg,image/png,.jpg,.jpeg,.png" onFiles={addPlan} label="Dodaj plan z pliku PDF lub JPG">
            Dodaj plan (PDF lub JPG)
          </FileButton>
        ) : (
          <button className="btn block" onClick={() => setEditing(true)}>Uzupełnij dane inwestycji</button>
        ))}

        </aside>
        <section>
        <h2 className="h2" style={{ marginTop: 0 }}>Usterki <span className="n">otwarte: {open}, usunięte: {defects.length - open}</span></h2>
        {defects.length ? (
          <ul className="dlist">
            {defects.map((d) => (
              <li key={d.id}>
                <button className="ditem" onClick={() => nav(`/projects/${project.id}/plans/${d.plan_id}?defect=${d.id}`)}>
                  <span className={`badge${isFixed(d) ? ' fixed' : ''}`}>{d.no}</span>
                  <span className="txt">
                    <span className="ty">{typeLabel(d)}</span>
                    <span className="ds">{d.description}</span>
                    <span className="muted small">{planName.get(d.plan_id)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">Brak usterek. Otwórz plan i stuknij „Dodaj usterkę”.</p>
        )}
        <button className="btn primary block" disabled={!defects.length} onClick={() => setReport(true)}>Utwórz raport PDF lub Word</button>

        <ReportList projectId={project.id} version={reportsVersion} />
        </section>
        </div>
      </main>

      {editing && (
        <ProjectForm project={project} onClose={() => setEditing(false)}
          onSaved={(p) => { setEditing(false); setProject(p); toast('Zapisano zmiany'); }}
          onDeleted={() => { setEditing(false); nav('/'); toast('Inwestycja usunięta'); }} />
      )}
      {menu && <PlanMenu plan={menu} onClose={() => setMenu(null)} />}
      {pdfPick && <PdfPagePicker pdf={pdfPick.pdf} onPick={pdfPick.resolve} />}
      {report && <ReportSheet onClose={() => setReport(false)} onCreated={() => setReportsVersion((v) => v + 1)} />}
    </>
  );
}
