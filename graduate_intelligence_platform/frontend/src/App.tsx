import { Navigate, Route, Routes } from 'react-router-dom';

import { AppProvider } from './context/AppContext';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './layouts/AppLayout';
import { AlumniOnboardingPage } from './pages/AlumniOnboardingPage';
import { DashboardPage } from './pages/DashboardPage';
import { ExecutiveSummaryPage } from './pages/ExecutiveSummaryPage';
import { LoginPage } from './pages/LoginPage';
import { MicrocurriculumDemoPage } from './pages/MicrocurriculumDemoPage';
import { ProgramsPage } from './pages/ProgramsPage';

export default function App() {
  return (
    <AppProvider>
      <AuthProvider>
        <Routes>
          <Route index element={<ExecutiveSummaryPage />} />
          <Route path="/observatorio-institucional" element={<ExecutiveSummaryPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/microcurriculum-demo" element={<MicrocurriculumDemoPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/programas" element={<ProgramsPage />} />
              <Route path="/registro" element={<AlumniOnboardingPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </AppProvider>
  );
}
