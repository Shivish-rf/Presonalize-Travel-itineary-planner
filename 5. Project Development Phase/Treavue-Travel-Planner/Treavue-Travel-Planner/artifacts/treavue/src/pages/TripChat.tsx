import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { useLocation } from 'wouter';
import { ArrowRight, Bot, LoaderCircle, Send, UserRound } from 'lucide-react';
import { Button } from '../components/ui';
import { chatWithGemini, type ChatMessage } from '../lib/api';
import type { Store, Trip } from '../lib/types';

export function TripChat({
  store,
  save,
}: {
  store: Store;
  save: (store: Store) => void;
}) {
  const [, setLocation] = useLocation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const requestInProgress = useRef(false);
  const [error, setError] = useState('');
  const [itinerary, setItinerary] = useState<Trip | null>(null);
  const [saving, setSaving] = useState(false);

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = input.trim();
    if (!message || requestInProgress.current) return;
    requestInProgress.current = true;

    const nextMessages = [
      ...messages,
      { role: 'user' as const, content: message },
    ];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);
    setError('');
    setItinerary(null);

    try {
      const response = await chatWithGemini({
        message,
        history: messages.slice(-10),
      });
      setMessages([...nextMessages, { role: 'assistant', content: response.reply }]);
      setItinerary(response.itinerary);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'The travel assistant could not respond. Use the sample itinerary option above instead.',
      );
    } finally {
      requestInProgress.current = false;
      setLoading(false);
    }
  }

  function useItinerary() {
    if (!itinerary || saving) return;
    setSaving(true);
    save({ ...store, trips: [itinerary, ...store.trips] });
    setLocation(`/trips/${itinerary.id}`);
  }

  return (
    <section className="trip-chat-panel" aria-labelledby="trip-chat-title">
      <div className="trip-chat-heading">
        <span className="trip-chat-icon" aria-hidden="true">
          <Bot size={19} />
        </span>
        <div>
          <div className="eyebrow">GEMINI AI · ENGLISH</div>
          <h2 id="trip-chat-title" className="serif">
            Plan it together
          </h2>
          <p>
            Share what you know. The assistant will ask for missing trip details
            before suggesting a day-by-day plan.
          </p>
        </div>
      </div>

      <div
        className="trip-chat-messages"
        aria-live="polite"
        aria-relevant="additions"
      >
        <div className="trip-chat-message assistant-message">
          <Bot size={15} aria-hidden="true" />
          <p>
            Tell me your destination, dates, total budget in INR, traveler count,
            interests, and preferred pace. I’ll ask about anything you haven’t
            decided yet.
          </p>
        </div>
        {messages.map((message, index) => (
          <div
            className={`trip-chat-message ${message.role}-message`}
            key={`${index}-${message.role}`}
          >
            {message.role === 'assistant' ? (
              <Bot size={15} aria-hidden="true" />
            ) : (
              <UserRound size={15} aria-hidden="true" />
            )}
            <p>{message.content}</p>
          </div>
        ))}
        {loading && (
          <div className="trip-chat-loading" role="status">
            <LoaderCircle size={16} className="trip-chat-spinner" />
            Planning a response…
          </div>
        )}
      </div>

      {error && (
        <div className="form-error trip-chat-error" role="alert">
          {error} The sample itinerary option above remains available.
        </div>
      )}

      {itinerary && (
        <div className="trip-chat-result">
          <p>
            <strong>{itinerary.title}</strong> · {itinerary.days.length}{' '}
            {itinerary.days.length === 1 ? 'day' : 'days'} ·{' '}
            {itinerary.days.reduce((count, day) => count + day.activities.length, 0)}{' '}
            suggested activities
          </p>
          <small>
            AI-assisted suggestion. Availability, opening hours, and prices are
            not verified.
          </small>
          <Button onClick={useItinerary} disabled={saving}>
            Use this itinerary <ArrowRight size={16} />
          </Button>
        </div>
      )}

      <form className="trip-chat-form" onSubmit={sendMessage}>
        <label className="sr-only" htmlFor="trip-chat-input">
          Message the travel assistant
        </label>
        <textarea
          id="trip-chat-input"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="For example: I’m thinking of Lisbon for four days…"
          maxLength={2000}
          rows={2}
          disabled={loading}
        />
        <Button
          type="submit"
          aria-label="Send message"
          disabled={loading || !input.trim()}
        >
          {loading ? (
            <LoaderCircle size={17} className="trip-chat-spinner" />
          ) : (
            <Send size={16} />
          )}
          Send
        </Button>
      </form>
      <p className="trip-chat-disclaimer">
        Suggestions only. Check local conditions, opening hours, availability,
        and prices before travel.
      </p>
    </section>
  );
}
