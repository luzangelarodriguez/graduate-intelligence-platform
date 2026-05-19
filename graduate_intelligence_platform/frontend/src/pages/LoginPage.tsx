import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

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
    <main className="login-shell">
      <section className="login-panel">
        <div className="login-copy">
          <div className="brand-lockup">
            <span>gi</span>
            <div>
              <strong>Graduate Intelligence</strong>
              <small>Powered for UNIR Colombia</small>
            </div>
          </div>
          <h1>Plataforma de inteligencia curricular y empleabilidad</h1>
          <p>
            Centraliza analítica académica, matching profesional y recomendaciones inteligentes para fortalecer el
            impacto de los egresados.
          </p>
        </div>

        <form className="login-card" onSubmit={onSubmit}>
          <div className="auth-tabs">
            <button type="button" className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>
              Login
            </button>
            <button type="button" className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>
              Registro
            </button>
          </div>

          {mode === 'register' && (
            <>
              <label className="field">
                <span>Nombre completo</span>
                <input value={fullName} onChange={(event) => setFullName(event.target.value)} />
              </label>
              <label className="field">
                <span>Rol</span>
                <select value={role} onChange={(event) => setRole(event.target.value as typeof role)}>
                  <option value="admin">admin</option>
                  <option value="universidad">universidad</option>
                  <option value="egresado">egresado</option>
                  <option value="mentor">mentor</option>
                </select>
              </label>
            </>
          )}

          <label className="field">
            <span>Email</span>
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>

          {error && <div className="notice error">{error}</div>}

          <button className="btn-primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Validando...' : mode === 'login' ? 'Entrar' : 'Crear usuario'}
          </button>
        </form>
      </section>
    </main>
  );
}
