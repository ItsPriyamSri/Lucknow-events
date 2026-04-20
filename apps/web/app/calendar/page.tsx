import { eventService, Event } from "@/lib/api";
import { CalendarDays } from "lucide-react";
import Link from "next/link";

export const revalidate = 300;

// Use backend public URL for ICS so external calendar clients can subscribe.
// Falls back to Next.js rewrite in dev.
const ICS_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL
    ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/feeds/events.ics`
    : "/api/v1/feeds/events.ics";

function groupByDate(events: Event[]): Record<string, Event[]> {
  return events.reduce((acc, event) => {
    const date = new Date(event.start_at).toLocaleDateString("en-IN", {
      timeZone: "Asia/Kolkata",
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    if (!acc[date]) acc[date] = [];
    acc[date].push(event);
    return acc;
  }, {} as Record<string, Event[]>);
}

export default async function CalendarPage() {
  let events: Event[] = [];
  try {
    const res = await eventService.getEvents({ limit: 50 });
    events = res.items;
  } catch (e) {
    console.error("Failed to fetch calendar events:", e);
  }

  const grouped = groupByDate(events);
  const dates = Object.keys(grouped);

  return (
    <div className="max-w-4xl mx-auto py-12 px-6 space-y-10">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <CalendarDays className="w-7 h-7 text-primary" />
          <h1 className="text-4xl font-extrabold tracking-tight">Event Calendar</h1>
        </div>
        <a
          href={ICS_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 rounded-full border border-border bg-card px-5 py-2 text-sm font-semibold hover:border-primary/60 hover:text-primary transition-colors"
        >
          <CalendarDays className="w-4 h-4" /> Subscribe to Calendar
        </a>
      </div>

      {dates.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border py-24 text-center flex flex-col items-center bg-card">
          <CalendarDays className="w-12 h-12 text-muted mb-4" />
          <h3 className="text-xl font-bold mb-2">No upcoming events</h3>
          <p className="text-muted-foreground mb-8">
            No events are currently scheduled. Submit one to get things started!
          </p>
          <Link
            href="/submit"
            className="rounded-full bg-primary text-primary-foreground px-8 py-3 font-semibold hover:bg-primary/90 transition-all"
          >
            Submit an Event
          </Link>
        </div>
      ) : (
        <div className="space-y-8">
          {dates.map((date) => (
            <div key={date}>
              {/* Date heading */}
              <div className="flex items-center gap-4 mb-4">
                <div className="h-px flex-1 bg-border" />
                <span className="text-xs font-bold uppercase tracking-widest text-primary px-3">
                  {date}
                </span>
                <div className="h-px flex-1 bg-border" />
              </div>

              <div className="space-y-3">
                {grouped[date].map((event) => {
                  const registerUrl = event.registration_url || event.canonical_url;
                  const time = new Date(event.start_at).toLocaleTimeString("en-IN", {
                    timeZone: "Asia/Kolkata",
                    hour: "2-digit",
                    minute: "2-digit",
                  });
                  return (
                    <div
                      key={event.id}
                      className="flex items-center gap-4 bg-card border border-border rounded-xl px-5 py-4 hover:border-primary/50 transition-all group"
                    >
                      <div className="w-16 text-center flex-shrink-0">
                        <span className="text-sm font-bold text-primary tabular-nums">{time}</span>
                      </div>
                      <div className="w-px h-8 bg-border" />
                      <div className="flex-1 min-w-0">
                        <Link
                          href={`/events/${event.slug}`}
                          className="font-semibold text-foreground group-hover:text-primary transition-colors hover:underline truncate block"
                        >
                          {event.title}
                        </Link>
                        <span className="text-xs text-muted-foreground">
                          {event.mode === "online" ? "Online" : event.venue || event.locality || "TBD"}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {event.is_free && (
                          <span className="hidden sm:inline-flex text-xs font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded-full">
                            FREE
                          </span>
                        )}
                        <a
                          href={registerUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs font-bold bg-primary/10 text-primary border border-primary/20 rounded-full px-3 py-1 hover:bg-primary hover:text-primary-foreground transition-colors"
                        >
                          Register →
                        </a>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
