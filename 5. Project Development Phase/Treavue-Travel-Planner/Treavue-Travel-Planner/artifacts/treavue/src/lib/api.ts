import type { Destination, Trip } from './types';
import { getValidAccessToken, refreshAuthSession } from './auth';

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'
).replace(/\/+$/, '');

export type GenerateItineraryRequest = {
  destinationId: string;
  title?: string;
  startDate: string;
  endDate: string;
  travelerType?: string;
  travelerCount?: number;
  budget?: number;
  interests?: string[];
  pace?: string;
  transport?: string;
  accommodation?: string;
  dietaryNeeds?: string;
  accessibilityNeeds?: string;
  mustVisit?: string[];
  instructions?: string;
};

export type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

export type ChatRequest = {
  message: string;
  history?: ChatMessage[];
  context?: Partial<GenerateItineraryRequest>;
};

export type ChatResponse = {
  reply: string;
  itinerary: Trip | null;
};

function errorDetail(payload: unknown): string | undefined {
  if (!payload || typeof payload !== 'object' || !('detail' in payload)) {
    return undefined;
  }

  const detail = payload.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        item && typeof item === 'object' && 'msg' in item
          ? String(item.msg)
          : '',
      )
      .filter(Boolean)
      .join('; ');
  }
  return undefined;
}

async function request<T>(
  path: string,
  init?: RequestInit,
  expectedUserId?: string,
): Promise<T> {
  const authenticated = expectedUserId !== undefined;
  let accessToken = authenticated
    ? await getValidAccessToken(expectedUserId)
    : null;
  if (authenticated && !accessToken) {
    throw new Error('Sign in to access your saved trips.');
  }

  let response: Response | undefined;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      response = await fetch(`${API_BASE_URL}/api${path}`, {
        ...init,
        headers: {
          ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          ...init?.headers,
        },
      });
    } catch {
      throw new Error(
        `Cannot reach the Treavue API at ${API_BASE_URL}. Make sure the FastAPI backend is running, then try again.`,
      );
    }
    if (response.status !== 401 || !authenticated || attempt > 0) break;
    try {
      accessToken =
        (await refreshAuthSession(expectedUserId))?.access_token ?? null;
    } catch {
      throw new Error('Your session has expired. Sign in again to access your trips.');
    }
    if (!accessToken) {
      throw new Error('Your session has expired. Sign in again to access your trips.');
    }
  }

  if (!response) throw new Error('The API did not return a response.');
  if (!response.ok) {
    if (response.status === 401 && authenticated) {
      throw new Error(
        'The backend could not validate this access token. Your sign-in is still active; check that SUPABASE_AUTH_API_KEY is set to the project’s publishable/anon key.',
      );
    }
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      payload = undefined;
    }
    throw new Error(
      errorDetail(payload) || `The API request failed (HTTP ${response.status}).`,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function listDestinations(): Promise<Destination[]> {
  return request<Destination[]>('/destinations');
}

export function getDestination(id: string): Promise<Destination> {
  return request<Destination>(`/destinations/${encodeURIComponent(id)}`);
}

export function listTrips(userId: string): Promise<Trip[]> {
  return request<Trip[]>('/trips', undefined, userId);
}

export function getTrip(id: string, userId: string): Promise<Trip> {
  return request<Trip>(`/trips/${encodeURIComponent(id)}`, undefined, userId);
}

export function saveTrip(trip: Trip, userId: string): Promise<Trip> {
  return request<Trip>('/trips', {
    method: 'POST',
    body: JSON.stringify(trip),
  }, userId);
}

export function updateTrip(trip: Trip, userId: string): Promise<Trip> {
  return request<Trip>(`/trips/${encodeURIComponent(trip.id)}`, {
    method: 'PUT',
    body: JSON.stringify(trip),
  }, userId);
}

export function deleteTrip(id: string, userId: string): Promise<void> {
  return request<void>(`/trips/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  }, userId);
}

export function generateItinerary(
  itinerary: GenerateItineraryRequest,
): Promise<Trip> {
  return request<Trip>('/itineraries/generate', {
    method: 'POST',
    body: JSON.stringify(itinerary),
  });
}

export function chatWithGemini(chat: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(chat),
  });
}
