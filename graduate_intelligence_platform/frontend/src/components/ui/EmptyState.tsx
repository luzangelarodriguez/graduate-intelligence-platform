import { FileQuestion } from 'lucide-react';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  body?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, body, icon, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">
        {icon ?? <FileQuestion size={20} strokeWidth={1.5} />}
      </div>
      <h4 className="empty-state-title">{title}</h4>
      {body && <p className="empty-state-body">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
