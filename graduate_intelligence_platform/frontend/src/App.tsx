import { Navigate, Route, Routes } from 'react-router-dom';

import { AppProvider } from './context/AppContext';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './layouts/AppLayout';
import { AlumniOnboardingPage } from './pages/AlumniOnboardingPage';
import { BrechasCurricularesPage } from './pages/BrechasCurricularesPage';
import { ConfiguracionPage } from './pages/ConfiguracionPage';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { MercadoLaboralPage } from './pages/MercadoLaboralPage';
import { MicrocurriculumDemoPage } from './pages/MicrocurriculumDemoPage';
import { OfertaAcademicaPage } from './pages/OfertaAcademicaPage';
import { ProgramsPage } from './pages/ProgramsPage';
import { RecomendacionesPage } from './pages/RecomendacionesPage';

export default function App() {
  return (
    <AppProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/microcurriculum-demo" element={<MicrocurriculumDemoPage />} />
          <Route path="/observatorio-institucional" element={<MicrocurriculumDemoPage />} />
          {/* Observatory routes - public access */}
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="/oferta-academica" element={<OfertaAcademicaPage />} />
            <Route path="/mercado-laboral" element={<MercadoLaboralPage />} />
            <Route path="/brechas-curriculares" element={<BrechasCurricularesPage />} />
            <Route path="/recomendaciones" element={<RecomendacionesPage />} />
            <Route path="/configuracion" element={<ConfiguracionPage />} />
            <Route path="/dashboard" element={<Navigate to="/" replace />} />
          </Route>
          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
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
