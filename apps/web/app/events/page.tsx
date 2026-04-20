import { eventService } from "@/lib/api";
import { EventCard } from "@/components/EventCard";
import { Search, SlidersHorizontal } from "lucide-react";
import Link from "next/link";

export default async function EventsPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}) {
  const params = await searchParams;
  
  const queryParams: Record<string, any> = {};
  if (params.q) queryParams.q = params.q;
  if (params.topic) queryParams.topic = params.topic;
  if (params.locality) queryParams.locality = params.locality;
  if (params.is_free === 'true') queryParams.is_free = true;
  if (params.is_student_friendly === 'true') queryParams.is_student_friendly = true;
  if (params.page) queryParams.page = Number(params.page);
  
  let response = { items: [], total: 0, page: 1, limit: 20 };
  try {
    response = await eventService.getEvents(queryParams);
  } catch (e) {
    console.error("Failed to fetch events list:", e);
  }

  const { items, total, page, limit } = response;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="flex flex-col md:flex-row min-h-full">
      {/* Sidebar Filters */}
      <aside className="w-full md:w-64 flex-shrink-0 border-r border-border bg-background p-6">
        <div className="flex items-center gap-2 mb-6">
          <SlidersHorizontal className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-bold">Filters</h2>
        </div>
        
        <form className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Search</label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <input 
                name="q" 
                defaultValue={params.q as string || ""}
                placeholder="Keywords..." 
                className="w-full rounded-md border border-border bg-input py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Topic</label>
            <input 
                name="topic" 
                defaultValue={params.topic as string || ""}
                placeholder="e.g. AI, Web..." 
                className="w-full rounded-md border border-border bg-input py-2 px-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
          </div>

          <div className="space-y-3 pt-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" name="is_free" value="true" defaultChecked={params.is_free === 'true'} className="rounded border-border text-primary focus:ring-accent bg-input" />
              <span className="text-sm font-medium">Free Events Only</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" name="is_student_friendly" value="true" defaultChecked={params.is_student_friendly === 'true'} className="rounded border-border text-primary focus:ring-accent bg-input" />
              <span className="text-sm font-medium">Student Friendly</span>
            </label>
          </div>

          <button type="submit" className="w-full rounded-md bg-secondary text-secondary-foreground py-2 text-sm font-semibold hover:bg-secondary/80 transition-colors border border-border">
            Apply Filters
          </button>
          
          {(Object.keys(queryParams).length > 0) && (
            <Link href="/events" className="block text-center text-xs text-muted-foreground mt-2 hover:text-foreground">
              Clear All
            </Link>
          )}
        </form>
      </aside>
      
      {/* Main Events Grid */}
      <div className="flex-1 p-6 lg:p-10">
        <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">All Events</h1>
          <p className="text-muted-foreground text-sm font-medium px-4 py-1.5 rounded-full bg-secondary uppercase tracking-wider">{total} events</p>
        </div>
        
        {items.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((event: any) => <EventCard key={event.id} event={event} />)}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-border py-24 text-center flex flex-col items-center bg-card shadow-inner">
            <Search className="w-12 h-12 text-muted mb-4" />
            <h3 className="text-xl font-bold mb-2">No events found</h3>
            <p className="text-muted-foreground mb-8">Adjust your filters or check back later once more events are indexed.</p>
            <Link href="/submit" className="rounded-full bg-primary text-primary-foreground px-8 py-3 font-semibold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 hover:scale-105">
              Submit an Event
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
