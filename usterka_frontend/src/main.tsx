import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './css/app.css';
import './css/extra.css';
import './css/landing.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
