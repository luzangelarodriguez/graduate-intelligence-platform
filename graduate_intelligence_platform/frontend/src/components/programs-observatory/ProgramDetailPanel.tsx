import { useState } from 'react';
import type { Program } from '../../types/api';

interface ProgramDetailPanelProps {
  program: Program | null;
  alignment: number;
  risk: number;
  employability: number;
  gapCount: number;
  topGap: string;
  topRecommendation: string;
  forecastSignal: string;
}

type TabType = 'overview' | 'skills' | 'intelligence';

export function ProgramDetailPanel({
  program,
  alignment,
  risk,
  employability,
  gapCount,
  topGap,
  topRecommendation,
  forecastSignal,
}: ProgramDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  if (!program) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white shadow-sm p-8 flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-slate-600">Select a program to view details</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <div className="border-b border-slate-200 px-6 py-4">
        <h2 className="text-lg font-bold text-slate-900">{program.nombre_especializacion}</h2>
        <p className="text-sm text-slate-600 mt-1">{program.rol || 'Academic Area'}</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 flex bg-slate-50">
        <button
          onClick={() => setActiveTab('overview')}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'overview'
              ? 'bg-white border-b-2 border-blue-500 text-blue-600'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('skills')}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'skills'
              ? 'bg-white border-b-2 border-blue-500 text-blue-600'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Skills & Jobs
        </button>
        <button
          onClick={() => setActiveTab('intelligence')}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'intelligence'
              ? 'bg-white border-b-2 border-blue-500 text-blue-600'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Intelligence
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Metrics Grid */}
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg bg-emerald-50 border border-emerald-100 p-4">
                <span className="block text-xs font-semibold uppercase text-slate-600">Alignment</span>
                <strong className="mt-2 block text-2xl font-bold text-emerald-900">{alignment.toFixed(1)}%</strong>
                <span className="mt-1 block text-xs text-emerald-700">Market positioned</span>
              </div>
              <div className="rounded-lg bg-rose-50 border border-rose-100 p-4">
                <span className="block text-xs font-semibold uppercase text-slate-600">Risk</span>
                <strong className="mt-2 block text-2xl font-bold text-rose-900">{risk.toFixed(1)}%</strong>
                <span className="mt-1 block text-xs text-rose-700">Monitoring required</span>
              </div>
              <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
                <span className="block text-xs font-semibold uppercase text-slate-600">Employability</span>
                <strong className="mt-2 block text-2xl font-bold text-blue-900">{employability.toFixed(1)}%</strong>
                <span className="mt-1 block text-xs text-blue-700">Projection quality</span>
              </div>
            </div>

            {/* Key Insights */}
            <div className="space-y-4">
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs font-semibold uppercase text-slate-600">Primary Gap</p>
                <p className="mt-2 text-sm text-slate-900">{topGap}</p>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs font-semibold uppercase text-slate-600">Strategic Action</p>
                <p className="mt-2 text-sm text-slate-900">{topRecommendation}</p>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs font-semibold uppercase text-slate-600">Forecast Signal</p>
                <p className="mt-2 text-sm text-slate-900">{forecastSignal}</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'skills' && (
          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold uppercase text-slate-600 mb-2">Total Program Skills</p>
              <p className="text-sm text-slate-700">
                {program.total_skills_programa} academic skills, {program.total_herramientas} tools, {program.total_competencias} competencies
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-slate-600 mb-2">Covered Skills</p>
              <p className="text-sm text-slate-700">
                {program.skills_cubiertas || 0} skills visible in curriculum
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-slate-600 mb-2">Related Jobs</p>
              <p className="text-sm text-slate-700">
                {program.total_empleos_relacionados && program.total_empleos_relacionados > 0
                  ? `${program.total_empleos_relacionados} related job positions identified`
                  : 'No related jobs identified'}
              </p>
            </div>
          </div>
        )}

        {activeTab === 'intelligence' && (
          <div className="space-y-4">
            <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
              <p className="text-xs font-semibold uppercase text-blue-900 mb-2">Coverage Status</p>
              <p className="text-sm text-blue-800">
                {alignment >= 70
                  ? 'High curricular coverage with emerging market signals'
                  : 'Moderate coverage - strategic updates recommended'}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 border border-slate-200 p-4">
              <p className="text-xs font-semibold uppercase text-slate-600 mb-2">Analysis Depth</p>
              <p className="text-sm text-slate-700">
                Based on {program.total_empleos_relacionados || 0} labor market signals and academic curriculum mapping
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
