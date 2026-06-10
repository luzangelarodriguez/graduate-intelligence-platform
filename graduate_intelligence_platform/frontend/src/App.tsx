import { Navigate, Route, Routes } from 'react-router-dom';

import { AppProvider } from './context/AppContext';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './layouts/AppLayout';
import PertinenciaDashboard from './components/PertinenciaDashboard.tsx';
import { AlumniOnboardingPage } from './pages/AlumniOnboardingPage';
import { DashboardPage } from './pages/DashboardPage';
import { ExecutiveSummaryPage } from './pages/ExecutiveSummaryPage';
import { LoginPage } from './pages/LoginPage';
import { MicrocurriculumDemoPage } from './pages/MicrocurriculumDemoPage';
import { ProgramForecastPage } from './pages/ProgramForecastPage';
import { ProgramIntelligenceDetailPage } from './pages/ProgramIntelligenceDetailPage';
import { ProgramMicrocurriculumPage } from './pages/ProgramMicrocurriculumPage';
import { ProgramSimulationPage } from './pages/ProgramSimulationPage';
import { ProgramsPage } from './pages/ProgramsPage';

export default function App() {
  return (
    <AppProvider>
      <AuthProvider>
        <Routes>
          <Route path="/observatorio-institucional" element={<ExecutiveSummaryPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/microcurriculum-demo" element={<MicrocurriculumDemoPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/programas" element={<ProgramsPage />} />
              <Route path="/programs/:programId" element={<ProgramIntelligenceDetailPage />} />
              <Route path="/programs/:programId/microcurriculum" element={<ProgramMicrocurriculumPage />} />
              <Route path="/programs/:programId/forecast" element={<ProgramForecastPage />} />
              <Route path="/programs/:programId/simulation" element={<ProgramSimulationPage />} />
              <Route path="/registro" element={<AlumniOnboardingPage />} />
              <Route path="/pertinencia" element={<PertinenciaDashboard />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </AppProvider>
  );
}
