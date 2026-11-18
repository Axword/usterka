import { Link } from 'react-router-dom';

export default function ErrorNotFound() {
  return (
    <main className="wrap">
      <h1 className="h1">Nie znaleziono strony</h1>
      <Link className="btn primary" to="/">Wróć do inwestycji</Link>
    </main>
  );
}
