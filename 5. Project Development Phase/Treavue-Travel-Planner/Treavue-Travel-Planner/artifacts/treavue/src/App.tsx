import { useEffect, useRef, useState } from 'react';
import { Route, Switch } from 'wouter';
import type { Store, Trip } from './lib/types';
import {
  readStore,
  readUserStore,
  writeStore,
  writeUserStore,
} from './lib/storage';
import {
  deleteTrip,
  listDestinations,
  listTrips,
  saveTrip,
  updateTrip,
} from './lib/api';
import {
  getValidAccessToken,
  readAuthSession,
  signOut,
  subscribeToAuth,
  type AuthSession,
} from './lib/auth';
import { replaceDestinations } from './lib/data';
import { Shell } from './components/Shell';
import {
  Auth,
  Dashboard,
  DestinationDetail,
  Explore,
  Guides,
  NotFound,
  Plan,
  Profile,
  Saved,
  Trips,
  TripWorkspace,
} from './pages/Pages';
import { TripChat } from './pages/TripChat';

function App() {
  const [authSession, setAuthSession] = useState<AuthSession | null>(() =>
    readAuthSession(),
  );
  const [store, setStore] = useState<Store>(() =>
    authSession ? readUserStore(authSession.user.id) : readStore(),
  );
  const storeRef = useRef(store);
  const activeUserId = useRef<string | null>(authSession?.user.id ?? null);
  activeUserId.current = authSession?.user.id ?? null;
  const [authLoading, setAuthLoading] = useState(true);
  const [tripStorageMessage, setTripStorageMessage] = useState<string | null>(
    null,
  );
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [legacyTrips] = useState<Trip[]>(() => readStore().trips);
  const tripQueues = useRef(new Map<string, Promise<void>>());
  const serverTripIds = useRef(new Set<string>());
  const [apiState, setApiState] = useState<{
    loading: boolean;
    error: string | null;
  }>({ loading: true, error: null });

  useEffect(() => {
    let active = true;
    listDestinations()
      .then((destinations) => {
        if (!active) return;
        replaceDestinations(destinations);
        setStore((current) => {
          const next = { ...current, destinations };
          storeRef.current = next;
          if (authSession) writeUserStore(authSession.user.id, next);
          else writeStore(next);
          return next;
        });
        setApiState({ loading: false, error: null });
      })
      .catch((error) => {
        if (active) {
          setApiState({
            loading: false,
            error:
              error instanceof Error
                ? error.message
                : 'Unable to load destinations from the backend.',
          });
        }
      });
    return () => {
      active = false;
    };
  }, [authSession]);

  useEffect(() => {
    let active = true;
    const unsubscribe = subscribeToAuth((session) => {
      setAuthSession(session);
    });
    const restoreSession = async () => {
      try {
        await getValidAccessToken();
      } catch {
        setTripStorageMessage(
          'Your saved session expired. Sign in again to access account trips.',
        );
      } finally {
        if (active) setAuthLoading(false);
      }
    };
    void restoreSession();
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    let active = true;
    tripQueues.current.clear();
    serverTripIds.current = new Set<string>();
    setTripStorageMessage(null);
    setImportMessage(null);

    if (!authSession) {
      const local = readStore();
      storeRef.current = local;
      setStore(local);
      return () => {
        active = false;
      };
    }

    const userId = authSession.user.id;
    const accountStore = readUserStore(userId);
    storeRef.current = accountStore;
    setStore(accountStore);

    async function syncAccountTrips() {
      try {
        let remoteTrips = await listTrips(userId);
        const remoteIds = new Set(remoteTrips.map((trip) => trip.id));
        for (const trip of accountStore.trips) {
          if (!active || activeUserId.current !== userId) return;
          if (remoteIds.has(trip.id)) continue;
          await saveTrip(trip, userId);
          remoteIds.add(trip.id);
        }
        remoteTrips = await listTrips(userId);
        if (!active || activeUserId.current !== userId) return;
        serverTripIds.current = new Set(remoteTrips.map((trip) => trip.id));
        setStore((current) => {
          const unsynced = current.trips.filter(
            (trip) => !serverTripIds.current.has(trip.id),
          );
          const next = { ...current, trips: [...unsynced, ...remoteTrips] };
          storeRef.current = next;
          writeUserStore(userId, next);
          return next;
        });
      } catch (error) {
        if (active && activeUserId.current === userId) {
          setTripStorageMessage(
            `Account trips could not be synchronized. Your account-specific browser cache is preserved. ${error instanceof Error ? error.message : 'Try signing in again.'}`,
          );
        }
      }
    }
    void syncAccountTrips();
    return () => {
      active = false;
    };
  }, [authSession?.user.id]);

  function enqueueTripOperation(
    id: string,
    userId: string,
    operation: () => Promise<unknown>,
  ): Promise<void> {
    const previous = tripQueues.current.get(id) ?? Promise.resolve();
    const queued = previous
      .then(() => {
        if (activeUserId.current !== userId) {
          throw new Error('The signed-in account changed before this trip synced.');
        }
        return operation();
      })
      .then(() => {
        if (activeUserId.current !== userId) return;
        serverTripIds.current.add(id);
        setTripStorageMessage(null);
      })
      .catch((error: unknown) => {
        if (activeUserId.current !== userId) return;
        setTripStorageMessage(
          `Trip changes are preserved in this browser but could not be synced. ${error instanceof Error ? error.message : 'Check your session and try again.'}`,
        );
      });
    tripQueues.current.set(id, queued);
    return queued;
  }

  const save = (next: Store) => {
    const previous = storeRef.current;
    storeRef.current = next;
    setStore(next);
    if (authSession) writeUserStore(authSession.user.id, next);
    else writeStore(next);

    const previousTrips = new Map(previous.trips.map((trip) => [trip.id, trip]));
    const nextTrips = new Map(next.trips.map((trip) => [trip.id, trip]));
    if (!authSession) return;
    const userId = authSession.user.id;

    for (const [id] of previousTrips) {
      if (!nextTrips.has(id) && serverTripIds.current.has(id)) {
        void enqueueTripOperation(id, userId, () => deleteTrip(id, userId));
      }
    }
    for (const [id, trip] of nextTrips) {
      const priorTrip = previousTrips.get(id);
      if (!priorTrip || JSON.stringify(priorTrip) !== JSON.stringify(trip)) {
        const existsRemotely = serverTripIds.current.has(id);
        void enqueueTripOperation(
          id,
          userId,
          () =>
            existsRemotely
              ? updateTrip(trip, userId)
              : saveTrip(trip, userId),
        );
      }
    }
  };

  async function importLocalTrips() {
    if (!authSession || !legacyTrips.length) return;
    const userId = authSession.user.id;
    setImportMessage('Importing browser trips into this signed-in account…');
    const imported: Trip[] = [];
    try {
      for (const trip of legacyTrips) {
        const id = `trip-${crypto.randomUUID()}`;
        const accountTrip = { ...trip, id };
        await saveTrip(accountTrip, userId);
        if (activeUserId.current !== userId) return;
        imported.push(accountTrip);
        serverTripIds.current.add(id);
      }
      setStore((current) => {
        if (activeUserId.current !== userId) return current;
        const next = { ...current, trips: [...imported, ...current.trips] };
        storeRef.current = next;
        writeUserStore(authSession.user.id, next);
        return next;
      });
      setImportMessage(
        `Imported ${imported.length} browser trip${imported.length === 1 ? '' : 's'} to this account. Original local trips remain in this browser.`,
      );
    } catch (error) {
      if (activeUserId.current !== userId) return;
      setImportMessage(
        `Import stopped after ${imported.length} trip${imported.length === 1 ? '' : 's'}. Completed imports remain in your account; the original browser trips are unchanged. ${error instanceof Error ? error.message : 'Try again later.'}`,
      );
    }
  }

  async function logOut() {
    try {
      await signOut();
    } catch {
      setTripStorageMessage(
        'Signed out in this browser, but Supabase could not confirm the remote logout. Close other sessions from your account security settings if needed.',
      );
    } finally {
      const local = readStore();
      storeRef.current = local;
      setStore(local);
      setAuthSession(null);
    }
  }

  const handleAuthenticated = (session: AuthSession) => {
    setAuthSession(session);
  };

  return (
    <AppRouter
      store={store}
      save={save}
      apiState={apiState}
      tripStorageMessage={tripStorageMessage}
      importMessage={importMessage}
      legacyTripCount={legacyTrips.length}
      authSession={authSession}
      authLoading={authLoading}
      onImportLocalTrips={importLocalTrips}
      onAuthenticated={handleAuthenticated}
      onLogout={logOut}
    />
  );
}

type AppRouterProps = {
  store: Store;
  save: (store: Store) => void;
  apiState: { loading: boolean; error: string | null };
  tripStorageMessage: string | null;
  importMessage: string | null;
  legacyTripCount: number;
  authSession: AuthSession | null;
  authLoading: boolean;
  onImportLocalTrips: () => void;
  onAuthenticated: (session: AuthSession) => void;
  onLogout: () => void;
};

function AppRouter({
  store,
  save,
  apiState,
  tripStorageMessage,
  importMessage,
  legacyTripCount,
  authSession,
  authLoading,
  onImportLocalTrips,
  onAuthenticated,
  onLogout,
}: AppRouterProps) {
  return (
    <Shell
      user={authSession?.user ?? null}
      authLoading={authLoading}
      onLogout={onLogout}
    >
      {apiState.loading && (
        <div className="inline-message" role="status">
          Connecting to the Treavue backend…
        </div>
      )}
      {apiState.error && (
        <div className="form-error" role="alert">
          The backend is unavailable. Showing destinations saved in this
          browser; live destination details and itinerary generation require the
          backend. {apiState.error}
        </div>
      )}
      {tripStorageMessage && (
        <div className="form-error" role="alert">
          {tripStorageMessage}
        </div>
      )}
      {authSession && legacyTripCount > 0 && (
        <div className="inline-message" role="status">
          {importMessage ??
            `${legacyTripCount} trip${legacyTripCount === 1 ? '' : 's'} remain saved in this browser.`}
          {!importMessage && (
            <button type="button" onClick={onImportLocalTrips}>
              Import to my account
            </button>
          )}
        </div>
      )}
      <Switch>
        <Route path="/">
          <Dashboard store={store} save={save} />
        </Route>
        <Route path="/explore">
          <Explore store={store} save={save} />
        </Route>
        <Route path="/destinations/:id">
          {(params) => (
            <DestinationDetail store={store} save={save} id={params.id} />
          )}
        </Route>
        <Route path="/plan">
          <>
            <Plan store={store} save={save} />
            <TripChat store={store} save={save} />
          </>
        </Route>
        <Route path="/trips">
          <Trips store={store} save={save} />
        </Route>
        <Route path="/trips/:id">
          {(params) => (
            <TripWorkspace store={store} save={save} id={params.id} />
          )}
        </Route>
        <Route path="/saved">
          <Saved store={store} save={save} />
        </Route>
        <Route path="/guides">
          <Guides />
        </Route>
        <Route path="/profile">
          <Profile store={store} save={save} />
        </Route>
        <Route path="/auth/sign-in">
          <Auth mode="sign-in" onAuthenticated={onAuthenticated} />
        </Route>
        <Route path="/auth/sign-up">
          <Auth mode="sign-up" onAuthenticated={onAuthenticated} />
        </Route>
        <Route path="/auth/forgot-password">
          <Auth mode="forgot-password" onAuthenticated={onAuthenticated} />
        </Route>
        <Route>
          <NotFound />
        </Route>
      </Switch>
    </Shell>
  );
}

export default App;
