import { BookOpen } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { api } from '../api/client';

interface LoginPageProps {
  onAuthenticated: (token: string) => void;
}

export function LoginPage({ onAuthenticated }: LoginPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const response = mode === 'login' ? await api.login(email, password) : await api.register(email, password);
      onAuthenticated(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setSubmitting(false);
    }
  }

  async function trySampleCourse() {
    setSubmitting(true);
    setError(null);
    try {
      const response = await api.demoLogin();
      onAuthenticated(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sample course is not available');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand-row">
          <BookOpen size={28} aria-hidden />
          <h1>StudyRAG</h1>
        </div>
        <form onSubmit={submit} className="auth-form">
          <div className="segmented-control" role="tablist" aria-label="Authentication mode">
            <button type="button" className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>
              Login
            </button>
            <button type="button" className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>
              Register
            </button>
          </div>
          <label>
            Email
            <input value={email} type="email" required onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            Password
            <input value={password} type="password" required minLength={8} onChange={(event) => setPassword(event.target.value)} />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-button" disabled={submitting} type="submit">
            {submitting ? 'Working...' : mode === 'login' ? 'Login' : 'Create account'}
          </button>
          <button className="secondary-button" disabled={submitting} type="button" onClick={trySampleCourse}>
            Try sample course
          </button>
        </form>
      </section>
    </main>
  );
}
