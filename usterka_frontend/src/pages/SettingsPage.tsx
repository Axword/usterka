import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BackIcon } from 'src/components/common/Icons';
import { errorMessage } from 'src/service/http';
import { OrganizationService } from 'src/service/organization';
import { useAuth } from 'src/stores/authStore';
import { useProjectStore } from 'src/stores/projectStore';
import { toast, withBusy } from 'src/stores/uiStore';
import type { Member, Organization, Role } from 'src/types/api';

const ROLES: [Role, string][] = [['admin', 'Administrator'], ['inspector', 'Inspektor'], ['viewer', 'Podgląd']];

export default function SettingsPage() {
  const { me, logout } = useAuth();
  const isAdmin = me?.role === 'admin';
  const [org, setOrg] = useState<Organization | null>(null);
  const [form, setForm] = useState({ name: '', sp_site_url: '', sp_library: '', sp_folder: '', types: '' });
  const [members, setMembers] = useState<Member[]>([]);

  useEffect(() => {
    OrganizationService.get().then((o) => {
      setOrg(o);
      setForm({ name: o.name, sp_site_url: o.sp_site_url, sp_library: o.sp_library, sp_folder: o.sp_folder, types: o.defect_types.join('\n') });
    }).catch((e) => toast(errorMessage(e)));
    OrganizationService.members().then(setMembers).catch(() => {});
  }, []);

  const save = async () => {
    try {
      const o = await withBusy('Zapisywanie…', () => OrganizationService.update({
        name: form.name, sp_site_url: form.sp_site_url, sp_library: form.sp_library, sp_folder: form.sp_folder,
        defect_types: form.types.split('\n').map((t) => t.trim()).filter(Boolean),
      }));
      setOrg(o);
      useProjectStore.setState({ organization: o });
      toast('Zapisano ustawienia');
    } catch (e) {
      toast(errorMessage(e), 5000);
    }
  };

  const setRole = async (m: Member, role: Role) => {
    try {
      const n = await OrganizationService.setRole(m.id, role);
      setMembers((ms) => ms.map((x) => (x.id === n.id ? n : x)));
    } catch (e) {
      toast(errorMessage(e));
    }
  };

  const preview = form.sp_site_url && form.sp_library
    ? `${form.sp_site_url.replace(/\/+$/, '')}/${form.sp_library}/${form.sp_folder.replace('{inwestycja}', 'Inwestycja A')}/Protokol_usterek.pdf`
    : 'Uzupełnij adres witryny i bibliotekę, aby zapisywać raporty w SharePoint.';

  return (
    <>
      <header className="bar">
        <Link className="back" to="/"><BackIcon />Inwestycje</Link>
        <h1 className="bar-t">Ustawienia</h1>
        {isAdmin && <button className="btn primary small" onClick={save}>Zapisz</button>}
      </header>
      <main className="wrap">
        <h2 className="h2" style={{ marginTop: 0 }}>Konto</h2>
        <dl className="data">
          <dt>Zalogowano</dt><dd>{me?.display_name} ({me?.email})</dd>
          <dt>Logowanie</dt><dd>{me?.microsoft ? 'Konto Microsoft' : 'E-mail i hasło'}</dd>
          <dt>Organizacja</dt><dd>{me?.organization_name}</dd>
          <dt>Rola</dt><dd>{ROLES.find(([r]) => r === me?.role)?.[1]}</dd>
        </dl>
        <button className="btn block" onClick={logout}>Wyloguj</button>

        {org && (
          <fieldset disabled={!isAdmin} style={{ border: 0, padding: 0, margin: 0 }}>
            {!isAdmin && <p className="note">Ustawienia organizacji zmienia administrator.</p>}
            <h2 className="h2">Organizacja</h2>
            <label className="field"><span className="lbl">Nazwa</span>
              <input className="inp" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
            <label className="field"><span className="lbl">Rodzaje usterek (jeden w wierszu)</span>
              <textarea className="inp" rows={6} value={form.types} onChange={(e) => setForm({ ...form, types: e.target.value })} />
              <span className="muted small">„Inna” pozwala doprecyzować rodzaj w formularzu.</span></label>

            <h2 className="h2">SharePoint</h2>
            <p className="muted small" style={{ marginTop: 0 }}>Tu trafiają kopie raportów. Każda osoba zapisuje je swoim kontem Microsoft, więc musi mieć prawo zapisu w tej bibliotece.</p>
            <label className="field"><span className="lbl">Adres witryny</span>
              <input className="inp" type="url" value={form.sp_site_url} placeholder="https://firma.sharepoint.com/sites/Odbiory" autoCapitalize="off" spellCheck={false}
                onChange={(e) => setForm({ ...form, sp_site_url: e.target.value })} /></label>
            <label className="field"><span className="lbl">Biblioteka dokumentów</span>
              <input className="inp" value={form.sp_library} placeholder="Dokumenty" onChange={(e) => setForm({ ...form, sp_library: e.target.value })} /></label>
            <label className="field"><span className="lbl">Folder</span>
              <input className="inp" value={form.sp_folder} autoCapitalize="off" spellCheck={false} onChange={(e) => setForm({ ...form, sp_folder: e.target.value })} />
              <span className="muted small">{'{inwestycja}'} zostanie zastąpione nazwą inwestycji.</span></label>
            <p className="muted small" style={{ overflowWrap: 'anywhere' }}>{preview}</p>
            {isAdmin && <button className="btn primary block" onClick={save}>Zapisz ustawienia</button>}
          </fieldset>
        )}

        <h2 className="h2">Osoby <span className="n">{members.length}</span></h2>
        <ul className="dlist">
          {members.map((m) => (
            <li key={m.id} className="ritem">
              <div className="txt"><span className="ty">{m.display_name || m.email}</span><span className="muted small">{m.email}</span></div>
              <select className="inp" style={{ width: 'auto' }} value={m.role} disabled={!isAdmin || m.email === me?.email}
                onChange={(e) => setRole(m, e.target.value as Role)}>
                {ROLES.map(([r, l]) => <option key={r} value={r}>{l}</option>)}
              </select>
            </li>
          ))}
        </ul>
        <p className="muted small">Nowe osoby dołączają automatycznie po pierwszym zalogowaniu kontem Microsoft z tej samej firmy (rola: Inspektor).</p>
      </main>
    </>
  );
}
