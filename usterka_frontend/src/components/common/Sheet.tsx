import { useEffect, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { CloseIcon } from './Icons';

interface Props {
  title: string;
  onClose: () => void;
  action?: ReactNode;
  hidden?: boolean;
  children: ReactNode;
}

/** Pełnoekranowy panel (formularze) - odpowiednik .sheet z prototypu. */
export default function Sheet({ title, onClose, action, hidden, children }: Props) {
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);
  return createPortal(
    <div className="sheet" role="dialog" aria-modal="true" style={hidden ? { display: 'none' } : undefined}>
      <header className="bar">
        <button className="iconbtn" onClick={onClose} aria-label="Zamknij"><CloseIcon /></button>
        <h2 className="bar-t">{title}</h2>
        {action}
      </header>
      <div className="wrap">{children}</div>
    </div>,
    document.body,
  );
}
