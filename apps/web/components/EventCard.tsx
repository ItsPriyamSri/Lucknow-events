import { Event } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ArrowRight, MapPin, Calendar, Clock, Link as LinkIcon } from "lucide-react";
import Link from 'next/link';

export function EventCard({ event }: { event: Event }) {
  const registerUrl = event.registration_url || event.canonical_url;
  
  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-border bg-card transition-all hover:border-primary/50 group h-full">
      {event.poster_url ? (
        <div className="h-40 w-full overflow-hidden border-b border-border">
          <img src={event.poster_url} alt={event.title} className="h-full w-full object-cover transition-transform group-hover:scale-105" />
        </div>
      ) : (
        <div className="h-40 w-full border-b border-border bg-gradient-to-br from-background to-card flex items-center justify-center p-6 text-center">
           <span className="text-xl font-bold tracking-tight text-primary/80 line-clamp-2">{event.title}</span>
        </div>
      )}
      
      <div className="flex flex-1 flex-col p-5">
        <div className="mb-3 flex items-center gap-2 flex-wrap">
          <span className="inline-flex rounded-full border border-border bg-background px-2 py-0.5 text-xs font-semibold text-muted-foreground">
            {event.event_type}
          </span>
          {event.is_free && (
            <span className="inline-flex rounded-full bg-primary/10 text-primary px-2 py-0.5 text-xs font-semibold">
              FREE
            </span>
          )}
          {event.is_student_friendly && (
            <span className="inline-flex rounded-full border border-border bg-background px-2 py-0.5 text-xs font-semibold text-muted-foreground">
              Student Friendly
            </span>
          )}
        </div>
        
        <Link href={`/events/${event.slug}`} className="mb-2 text-lg font-bold leading-tight text-foreground line-clamp-2 hover:text-primary transition-colors hover:underline" title={event.title}>
          {event.title}
        </Link>
        
        <div className="mb-4 space-y-1.5 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Calendar className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{formatDate(event.start_at)}</span>
          </div>
          <div className="flex items-center gap-2">
            <MapPin className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">
              {event.mode === 'online' ? 'Online' : event.venue || event.locality || 'TBD'}
            </span>
          </div>
        </div>
        
        <div className="mt-auto pt-4 flex gap-2 w-full justify-between items-center border-t border-border/50">
          <a
            href={registerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-semibold transition-colors hover:bg-primary/90"
          >
            Register Now <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </div>
    </div>
  );
}
