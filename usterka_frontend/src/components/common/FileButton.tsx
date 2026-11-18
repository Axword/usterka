import type { ReactNode } from 'react';

interface Props {
  accept: string;
  onFiles: (files: File[]) => void;
  multiple?: boolean;
  capture?: 'environment' | 'user';
  className?: string;
  disabled?: boolean;
  label: string;
  children: ReactNode;
}

/** Przycisk wyboru pliku/aparatu - input przykryty labelką (działa na iOS i Androidzie). */
export default function FileButton({ accept, onFiles, multiple, capture, className = 'btn', disabled, label, children }: Props) {
  return (
    <label className={`${className} filebtn`} aria-disabled={disabled}>
      {children}
      <input
        type="file"
        accept={accept}
        multiple={multiple}
        capture={capture}
        disabled={disabled}
        aria-label={label}
        onChange={(e) => {
          const files = [...(e.target.files || [])];
          e.target.value = '';
          if (files.length) onFiles(files);
        }}
      />
    </label>
  );
}
