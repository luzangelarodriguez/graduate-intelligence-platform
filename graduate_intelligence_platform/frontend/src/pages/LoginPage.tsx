import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { GraduationCap } from 'lucide-react';

import { useAuth } from '../context/AuthContext';

export function LoginPage() {
  const { isAuthenticated, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('admin@demo.local');
  const [password, setPassword] = useState('Admin12345');
  const [fullName, setFullName] = useState('Administrador Plataforma');
  const [role, setRole] = useState<'admin' | 'universidad' | 'egresado' | 'mentor'>('admin');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/';

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      if (mode === 'login') {
        await login({ email, password });
      } else {
        await register({ email, password, full_name: fullName, role });
      }
      navigate(from, { replace: true });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No fue posible autenticar la sesion.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-canvas flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-accent mb-4">
            <GraduationCap size={32} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-ink">Graduate Intelligence</h1>
          <p className="text-sm text-muted mt-1">Observatorio Curricular UNIR Colombia</p>
        </div>

        {/* Login Card */}
        <div className="exec-card p-6">
          {/* Auth Tabs */}
          <div className="tabs mb-6">
            <button
              type="button"
              className={`tab ${mode === 'login' ? 'active' : ''}`}
              onClick={() => setMode('login')}
            >
              Iniciar Sesion
            </button>
            <button
              type="button"
              className={`tab ${mode === 'register' ? 'active' : ''}`}
              onClick={() => setMode('register')}
            >
              Registro
            </button>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            {mode === 'register' && (
              <>
                <div className="form-group">
                  <label className="form-label">Nombre completo</label>
                  <input
                    type="text"
                    className="form-input"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    placeholder="Tu nombre completo"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Rol</label>
                  <select
                    className="form-select"
                    value={role}
                    onChange={(event) => setRole(event.target.value as typeof role)}
                  >
                    <option value="admin">Administrador</option>
                    <option value="universidad">Universidad</option>
                    <option value="egresado">Egresado</option>
                    <option value="mentor">Mentor</option>
                  </select>
                </div>
              </>
            )}

            <div className="form-group">
              <label className="form-label">Email</label>
              <input
                type="email"
                className="form-input"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="tu@email.com"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Contrasena</label>
              <input
                type="password"
                className="form-input"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="********"
              />
            </div>

            {error && (
              <div className="p-3 rounded border border-red-200 bg-red-50 text-red-700 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary w-full"
              disabled={isSubmitting}
            >
              {isSubmitting
                ? 'Validando...'
                : mode === 'login'
                ? 'Iniciar Sesion'
                : 'Crear Cuenta'}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-muted mt-6">
          Plataforma de inteligencia curricular y empleabilidad
        </p>
      </div>
    </main>
  );
}
