export type AuthUser = {
  id: string;
  email?: string;
};

export type AuthSession = {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  user: AuthUser;
};

const AUTH_STORAGE_KEY = 'treavue-auth-session-v1';
const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || '').replace(/\/+$/, '');
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
export const isSupabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

let currentSession: AuthSession | null = null;
const refreshInFlight = new Map<string, Promise<AuthSession>>();
const listeners = new Set<(session: AuthSession | null) => void>();

function configured(): void {
  const missing = [
    !SUPABASE_URL ? 'VITE_SUPABASE_URL' : null,
    !SUPABASE_ANON_KEY ? 'VITE_SUPABASE_ANON_KEY' : null,
  ].filter((name): name is string => name !== null);
  if (missing.length > 0) {
    throw new Error(
      `Supabase Auth cannot start because ${missing.join(', ')} ${missing.length === 1 ? 'is' : 'are'} missing. Set the missing variable${missing.length === 1 ? '' : 's'} in artifacts/treavue/.env.local, use only the public publishable/anon key, and restart Vite. Never use the backend service-role/secret key in frontend settings.`,
    );
  }
}

function publish(session: AuthSession | null): void {
  currentSession = session;
  try {
    if (session) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  } catch (error) {
    console.warn('Unable to persist the Treavue auth session in this browser.', error);
  }
  listeners.forEach((listener) => listener(session));
}

function normalizeSession(payload: Record<string, unknown>): AuthSession {
  const user = payload.user;
  if (
    typeof payload.access_token !== 'string' ||
    typeof payload.refresh_token !== 'string' ||
    !user ||
    typeof user !== 'object' ||
    !('id' in user) ||
    typeof user.id !== 'string'
  ) {
    throw new Error('Supabase returned an invalid authentication session.');
  }
  const expiresIn =
    typeof payload.expires_in === 'number' ? payload.expires_in : 3600;
  return {
    access_token: payload.access_token,
    refresh_token: payload.refresh_token,
    expires_at:
      typeof payload.expires_at === 'number'
        ? payload.expires_at
        : Math.floor(Date.now() / 1000) + expiresIn,
    user: {
      id: user.id,
      ...('email' in user && typeof user.email === 'string'
        ? { email: user.email }
        : {}),
    },
  };
}

async function authRequest(
  path: string,
  body: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  configured();
  let response: Response;
  try {
    response = await fetch(`${SUPABASE_URL}/auth/v1/${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        apikey: SUPABASE_ANON_KEY,
      },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error('Cannot reach Supabase Auth. Check your connection and try again.');
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = undefined;
  }
  if (!response.ok) {
    const error = payload as
      | { msg?: unknown; message?: unknown; error_description?: unknown }
      | undefined;
    const message =
      error && typeof error === 'object'
        ? [error.msg, error.message, error.error_description].find(
            (item): item is string => typeof item === 'string',
          )
        : undefined;
    throw new Error(message || `Supabase Auth failed (HTTP ${response.status}).`);
  }
  if (!payload || typeof payload !== 'object') {
    throw new Error('Supabase Auth returned an invalid response.');
  }
  return payload as Record<string, unknown>;
}

export function readAuthSession(): AuthSession | null {
  if (currentSession) return currentSession;
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed === 'object' &&
      'access_token' in parsed &&
      'refresh_token' in parsed &&
      'expires_at' in parsed &&
      'user' in parsed
    ) {
      currentSession = parsed as AuthSession;
      return currentSession;
    }
  } catch (error) {
    console.warn('Unable to read the saved Treavue auth session.', error);
    publish(null);
  }
  return null;
}

export function subscribeToAuth(
  listener: (session: AuthSession | null) => void,
): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function makeDemoId(email: string): string {
  try {
    return `demo-${btoa(email.toLowerCase()).replace(/[^a-zA-Z0-9]/g, '').slice(0, 16) || 'user'}`;
  } catch {
    return `demo-${email.replace(/[^a-zA-Z0-9]/g, '').slice(0, 16) || 'user'}`;
  }
}

export async function signUp(
  email: string,
  password: string,
  name = '',
): Promise<AuthSession | null> {
  if (!isSupabaseConfigured) {
    const id = makeDemoId(email);
    const session: AuthSession = {
      access_token: `demo-token-${id}`,
      refresh_token: `demo-refresh-${id}`,
      expires_at: Math.floor(Date.now() / 1000) + 86400 * 30,
      user: { id, email },
    };
    publish(session);
    return session;
  }
  const payload = await authRequest('signup', {
    email,
    password,
    ...(name.trim() ? { data: { full_name: name.trim() } } : {}),
  });
  if (!payload.access_token) return null;
  const session = normalizeSession(payload);
  publish(session);
  return session;
}

export async function signIn(email: string, password: string): Promise<AuthSession> {
  if (!isSupabaseConfigured) {
    const id = makeDemoId(email);
    const session: AuthSession = {
      access_token: `demo-token-${id}`,
      refresh_token: `demo-refresh-${id}`,
      expires_at: Math.floor(Date.now() / 1000) + 86400 * 30,
      user: { id, email },
    };
    publish(session);
    return session;
  }
  const payload = await authRequest('token?grant_type=password', { email, password });
  const session = normalizeSession(payload);
  publish(session);
  return session;
}

export async function refreshAuthSession(
  expectedUserId?: string,
): Promise<AuthSession | null> {
  const previous = currentSession ?? readAuthSession();
  if (!previous) return null;
  if (expectedUserId && previous.user.id !== expectedUserId) {
    throw new Error('The signed-in account changed. Retry the request.');
  }

  const existing = refreshInFlight.get(previous.refresh_token);
  if (existing) return existing;

  const refreshing = refreshAuthSessionOnce(previous);
  refreshInFlight.set(previous.refresh_token, refreshing);
  try {
    return await refreshing;
  } finally {
    if (refreshInFlight.get(previous.refresh_token) === refreshing) {
      refreshInFlight.delete(previous.refresh_token);
    }
  }
}

async function refreshAuthSessionOnce(
  previous: AuthSession,
): Promise<AuthSession> {
  if (!isSupabaseConfigured) {
    const renewed: AuthSession = {
      ...previous,
      expires_at: Math.floor(Date.now() / 1000) + 86400 * 30,
    };
    publish(renewed);
    return renewed;
  }
  try {
    const payload = await authRequest('token?grant_type=refresh_token', {
      refresh_token: previous.refresh_token,
    });
    const session = normalizeSession(payload);
    const latest = currentSession ?? readAuthSession();
    if (latest?.refresh_token !== previous.refresh_token) {
      throw new Error('The signed-in account changed during session refresh.');
    }
    publish(session);
    return session;
  } catch (error) {
    const latest = currentSession ?? readAuthSession();
    if (latest?.refresh_token === previous.refresh_token) {
      publish(null);
    }
    throw error;
  }
}

export async function getValidAccessToken(
  expectedUserId?: string,
): Promise<string | null> {
  const session = currentSession ?? readAuthSession();
  if (!session) return null;
  if (expectedUserId && session.user.id !== expectedUserId) {
    throw new Error('The signed-in account changed. Retry the request.');
  }
  if (!isSupabaseConfigured) {
    return session.access_token;
  }
  if (session.expires_at > Math.floor(Date.now() / 1000) + 30) {
    return session.access_token;
  }
  const refreshed = await refreshAuthSession(expectedUserId);
  if (expectedUserId && refreshed?.user.id !== expectedUserId) {
    throw new Error('Your session expired. Sign in again to access your trips.');
  }
  return refreshed?.access_token ?? null;
}

export async function signOut(expectedUserId?: string): Promise<void> {
  const session = currentSession ?? readAuthSession();
  if (!session) {
    publish(null);
    return;
  }
  if (expectedUserId && session.user.id !== expectedUserId) return;

  publish(null);
  if (!isSupabaseConfigured) return;
  try {
    await fetch(`${SUPABASE_URL}/auth/v1/logout`, {
      method: 'POST',
      headers: {
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${session.access_token}`,
      },
    });
  } catch {
    // ignore network errors on logout
  }
}

export async function sendPasswordReset(email: string): Promise<void> {
  if (!isSupabaseConfigured) {
    return;
  }
  await authRequest('recover', { email });
}
