import { useEffect, useRef, useState } from 'react';
import { useUi } from 'src/stores/uiStore';
import { CloseIcon } from './Icons';

/** Toasty, blokada „Proszę czekać”, okna dialogowe i podgląd zdjęć - jeden host na całą aplikację. */
export default function UiHost() {
  const { toasts, busy, dialog, lightbox, setLightbox } = useUi();
  return (
    <>
      {dialog && <DialogBox key={dialog.title + (dialog.text || '')} />}
      {busy && (
        <div className="busy" role="status">
          <div><div className="spin" /><div>{busy}</div></div>
        </div>
      )}
      {lightbox && (
        <div className="lightbox" onClick={() => setLightbox(null)}>
          <img src={lightbox} alt="" />
          <button className="iconbtn" aria-label="Zamknij"><CloseIcon /></button>
        </div>
      )}
      {toasts.map((t, i) => (
        <div key={t.id} className="toast" role="status" style={{ transform: `translate(-50%, ${-i * 56}px)` }}>{t.text}</div>
      ))}
    </>
  );
}

function DialogBox() {
  const d = useUi((s) => s.dialog)!;
  const [value, setValue] = useState(d.input ?? '');
  const ref = useRef<HTMLInputElement | HTMLButtonElement>(null);
  const hasInput = d.input !== undefined;
  useEffect(() => {
    ref.current?.focus();
    if (ref.current instanceof HTMLInputElement) ref.current.select();
  }, []);
  const done = (ok: boolean) => d.resolve(ok ? (hasInput ? value.trim() : true) : hasInput ? null : false);
  return (
    <div className="modal-back" onClick={(e) => e.target === e.currentTarget && d.cancelLabel !== null && done(false)}>
      <div className="modal" role="alertdialog" aria-modal="true">
        <h3>{d.title}</h3>
        {d.text && <p>{d.text}</p>}
        {hasInput && (
          <input className="inp" value={value} ref={ref as React.RefObject<HTMLInputElement>} onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && done(true)} />
        )}
        <div className="row end">
          {d.cancelLabel && <button className="btn" onClick={() => done(false)}>{d.cancelLabel}</button>}
          <button className={`btn ${d.danger ? 'danger' : 'primary'}`} onClick={() => done(true)}
            ref={hasInput ? undefined : (ref as React.RefObject<HTMLButtonElement>)}>{d.okLabel}</button>
        </div>
      </div>
    </div>
  );
}
