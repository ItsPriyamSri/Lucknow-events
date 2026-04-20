import { EventGridSkeleton } from "@/components/EventGridSkeleton";
import { EventsExplorer } from "./events-explorer";
import { Suspense } from "react";

export default function EventsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col md:flex-row min-h-full">
          <aside className="hidden md:block w-64 flex-shrink-0 border-r border-border bg-background p-6 animate-pulse">
            <div className="h-6 w-32 bg-muted rounded mb-8" />
            <div className="space-y-4">
              <div className="h-10 bg-muted rounded" />
              <div className="h-10 bg-muted rounded" />
              <div className="h-10 bg-muted rounded" />
            </div>
          </aside>
          <div className="flex-1 p-6 lg:p-10">
            <div className="flex justify-between mb-8">
              <div className="h-9 w-48 bg-muted rounded" />
              <div className="h-8 w-24 bg-muted rounded-full" />
            </div>
            <EventGridSkeleton count={6} />
          </div>
        </div>
      }
    >
      <EventsExplorer />
    </Suspense>
  );
}
