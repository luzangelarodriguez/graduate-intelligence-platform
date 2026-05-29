import { X } from 'lucide-react';
import type { ReactNode } from 'react';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export function Drawer({ open, onClose, title, subtitle, children }: DrawerProps) {
  if (!open) return null;

  return (
    <div className="drawer-overlay" role="presentation" onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="drawer-header">
          <div>
            <h3 className="text-lg font-bold text-ink">{title}</h3>
            {subtitle && <p className="text-sm text-muted mt-1">{subtitle}</p>}
          </div>
          <button
            type="button"
            className="drawer-close"
            aria-label="Cerrar"
            onClick={onClose}
          >
            <X size={18} strokeWidth={1.5} />
          </button>
        </div>
        <div className="drawer-content">{children}</div>
      </aside>
    </div>
  );
}
