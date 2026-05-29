import type { LucideIcon } from 'lucide-react';

export interface AnalysisStoryStep {
  id: string;
  label: string;
  title: string;
  description: string;
  icon: LucideIcon;
}

interface AnalysisStorylineProps {
  steps: AnalysisStoryStep[];
  activeStep: string;
  onStepChange: (stepId: string) => void;
}

export function AnalysisStoryline({ steps, activeStep, onStepChange }: AnalysisStorylineProps) {
  function selectStep(stepId: string) {
    onStepChange(stepId);
    window.requestAnimationFrame(() => {
      document.getElementById(`story-${stepId}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  return (
    <nav className="analysis-storyline" aria-label="Lectura estrategica del analisis">
      {steps.map((step, index) => {
        const Icon = step.icon;
        const selected = activeStep === step.id;

        return (
          <button
            key={step.id}
            type="button"
            className={`analysis-storyline-step ${selected ? 'active' : ''}`}
            onClick={() => selectStep(step.id)}
          >
            <span className="analysis-storyline-index">{String(index + 1).padStart(2, '0')}</span>
            <span className="analysis-storyline-icon">
              <Icon />
            </span>
            <span>
              <strong>{step.label}</strong>
              <small>{step.description}</small>
            </span>
          </button>
        );
      })}
    </nav>
  );
}
