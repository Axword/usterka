import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import ProjectForm from 'src/components/project/ProjectForm';
import { errorMessage } from 'src/service/http';
import { ProjectService } from 'src/service/project';
import { useAuth } from 'src/stores/authStore';
import { toast } from 'src/stores/uiStore';
import type { Project } from 'src/types/api';

export default function ProjectListPage() {
  const { me, canWrite } = useAuth();
  const nav = useNavigate();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    ProjectService.list().then(setProjects).catch((e) => toast(errorMessage(e)));
  }, []);

  return (
    <>
      <header className="bar">
        <h1 className="brand">Usterki na planie</h1>
        <Link className="btn small" to="/subscription">Subskrypcja</Link>
        <Link className="btn small" to="/settings">Ustawienia</Link>
      </header>
      <main className="wrap">
        <p className="muted small" style={{ marginTop: 0 }}>{me?.organization_name}</p>
        {projects && !projects.length && (
          <div className="empty">
            <p className="empty-t">Zacznij od danych inwestycji</p>
            <p className="muted">Bez nich nie dodasz planu ani usterek.</p>
          </div>
        )}
        {!projects && <p className="muted">Wczytywanie…</p>}
        <ul className="cards">
          {projects?.map((p) => (
            <li key={p.id}>
              <button className="card" onClick={() => nav(`/projects/${p.id}`)}>
                <span className="card-t">{p.name}</span>
                <span className="card-s">{p.address}</span>
                <span className="counts">
                  <span className="cnt open">otwarte: {p.open_count}</span>
                  <span className="cnt fixed">usunięte: {p.fixed_count}</span>
                  <span className="cnt">plany: {p.plans_count}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
        {canWrite() && <button className="btn primary block" onClick={() => setCreating(true)}>Nowa inwestycja</button>}
      </main>
      {creating && (
        <ProjectForm
          project={null}
          onClose={() => setCreating(false)}
          onSaved={(p) => {
            setCreating(false);
            nav(`/projects/${p.id}`);
            toast('Zapisano dane. Teraz dodaj plan.');
          }}
        />
      )}
    </>
  );
}
