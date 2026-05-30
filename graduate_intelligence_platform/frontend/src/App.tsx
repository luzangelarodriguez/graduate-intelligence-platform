import { Navigate, Route, Routes } from 'react-router-dom';

import { AppProvider } from './context/AppContext';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import NarrativeLayout from './layouts/NarrativeLayout';
import { AppLayout } from './layouts/AppLayout';

// Narrative pages (new storytelling sections)
import ExecutiveSummaryPage from './pages/ExecutiveSummaryPage';
import MarketSignalsPage from './pages/MarketSignalsPage';
import CurriculumRiskPage from './pages/CurriculumRiskPage';
import FutureOfWorkPage from './pages/FutureOfWorkPage';
import RecommendationsCenterPage from './pages/RecommendationsCenterPage';
import AcademicCommitteePage from './pages/AcademicCommitteePage';

// Legacy pages
import { AlumniOnboardingPage } from './pages/AlumniOnboardingPage';
import { ConfiguracionPage } from './pages/ConfiguracionPage';
import { LoginPage } from './pages/LoginPage';
import { MicrocurriculumDemoPage } from './pages/MicrocurriculumDemoPage';
import { ProgramsPage } from './pages/ProgramsPage';

export default function App() {
  return (
    <AppProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/microcurriculum-demo" element={<MicrocurriculumDemoPage />} />
          <Route path="/observatorio-institucional" element={<MicrocurriculumDemoPage />} />
          
          {/* Main narrative observatory routes */}
          <Route element={<NarrativeLayout />}>
            <Route index element={<ExecutiveSummaryPage />} />
            <Route path="/mercado" element={<MarketSignalsPage />} />
            <Route path="/riesgos" element={<CurriculumRiskPage />} />
            <Route path="/futuro" element={<FutureOfWorkPage />} />
            <Route path="/recomendaciones" element={<RecommendationsCenterPage />} />
            <Route path="/comite" element={<AcademicCommitteePage />} />
          </Route>

          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/programas" element={<ProgramsPage />} />
              <Route path="/registro" element={<AlumniOnboardingPage />} />
              <Route path="/configuracion" element={<ConfiguracionPage />} />
            </Route>
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </AppProvider>
  );
}
