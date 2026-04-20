"use client";

import { EventCard } from "@/components/EventCard";
import { EventGridSkeleton } from "@/components/EventGridSkeleton";
import { eventService, facetService, type EventsResponse, type FacetItem } from "@/lib/api";
import { buildEventsHref, searchParamsToEventQuery } from "@/lib/events-query";
import { ChevronLeft, ChevronRight, Loader2, Search, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import useSWR from "swr";

const emptyResponse: EventsResponse = { items: [], total: 0, page: 1, limit: 20 };

async function fetchEvents(qs: string): Promise<EventsResponse> {
  const params = searchParamsToEventQuery(new URLSearchParams(qs));
  return eventService.getEvents(params);
}

export function EventsExplorer() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryKey = searchParams.toString();

  const { data, error, isLoading, isValidating } = useSWR(
    ["events", queryKey],
    ([, qs]) => fetchEvents(qs),
    {
      revalidateOnFocus: false,
      keepPreviousData: true,
    },
  );

  const { data: topics = [] } = useSWR<FacetItem[]>("facets-topics", () => facetService.getTopics(), {
    revalidateOnFocus: false,
  });
  const { data: localities = [] } = useSWR<FacetItem[]>(
    "facets-localities",
    () => facetService.getLocalities(),
    { revalidateOnFocus: false },
  );

  const response = data ?? emptyResponse;
  const { items, total, page, limit } = response;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  const filterBase: Record<string, string | undefined> = {
    q: searchParams.get("q") ?? undefined,
    topic: searchParams.get("topic") ?? undefined,
    locality: searchParams.get("locality") ?? undefined,
    community: searchParams.get("community") ?? undefined,
    is_free: searchParams.get("is_free") === "true" ? "true" : undefined,
    is_student_friendly: searchParams.get("is_student_friendly") === "true" ? "true" : undefined,
  };

  const hasActiveFilters =
    !!(
      filterBase.q ||
      filterBase.topic ||
      filterBase.locality ||
      filterBase.community ||
      filterBase.is_free ||
      filterBase.is_student_friendly
    ) ||
    (searchParams.get("page") && Number(searchParams.get("page")) > 1);

  const replaceQuery = useCallback(
    (mutate: (sp: URLSearchParams) => void) => {
      const sp = new URLSearchParams(searchParams.toString());
      mutate(sp);
      sp.delete("page");
      const s = sp.toString();
      router.replace(s ? `/events?${s}` : "/events", { scroll: false });
    },
    [router, searchParams],
  );

  const applySearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const q = String(fd.get("q") ?? "").trim();
    replaceQuery((sp) => {
      if (q) sp.set("q", q);
      else sp.delete("q");
    });
  };

  const onTopicChange = (value: string) => {
    replaceQuery((sp) => {
      if (value) sp.set("topic", value);
      else sp.delete("topic");
    });
  };

  const onLocalityChange = (value: string) => {
    replaceQuery((sp) => {
      if (value) sp.set("locality", value);
      else sp.delete("locality");
    });
  };

  const toggleBoolParam = (name: "is_free" | "is_student_friendly", checked: boolean) => {
    replaceQuery((sp) => {
      if (checked) sp.set(name, "true");
      else sp.delete(name);
    });
  };

  const prevHref =
    page > 1 ? buildEventsHref(filterBase, { page: page > 2 ? String(page - 1) : null }) : null;
  const nextHref =
    page < totalPages ? buildEventsHref(filterBase, { page: String(page + 1) }) : null;

  const currentTopic = searchParams.get("topic") ?? "";
  const currentLocality = searchParams.get("locality") ?? "";

  return (
    <div className="flex flex-col md:flex-row min-h-full">
      <aside className="w-full md:w-64 flex-shrink-0 border-r border-border bg-background p-6">
        <div className="flex items-center gap-2 mb-6">
          <SlidersHorizontal className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-bold">Filters</h2>
        </div>

        <form onSubmit={applySearch} className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Search</label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                key={queryKey}
                name="q"
                defaultValue={searchParams.get("q") ?? ""}
                placeholder="Keywords..."
                className="w-full rounded-md border border-border bg-input py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Topic</label>
            <select
              value={currentTopic}
              onChange={(e) => onTopicChange(e.target.value)}
              className="w-full rounded-md border border-border bg-input py-2 px-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">Any topic</option>
              {topics.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name} ({t.count})
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Locality</label>
            <select
              value={currentLocality}
              onChange={(e) => onLocalityChange(e.target.value)}
              className="w-full rounded-md border border-border bg-input py-2 px-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">Any locality</option>
              {localities.map((l) => (
                <option key={l.name} value={l.name}>
                  {l.name} ({l.count})
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-3 pt-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={searchParams.get("is_free") === "true"}
                onChange={(e) => toggleBoolParam("is_free", e.target.checked)}
                className="rounded border-border text-primary focus:ring-accent bg-input"
              />
              <span className="text-sm font-medium">Free Events Only</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={searchParams.get("is_student_friendly") === "true"}
                onChange={(e) => toggleBoolParam("is_student_friendly", e.target.checked)}
                className="rounded border-border text-primary focus:ring-accent bg-input"
              />
              <span className="text-sm font-medium">Student Friendly</span>
            </label>
          </div>

          <button
            type="submit"
            className="w-full rounded-md bg-secondary text-secondary-foreground py-2 text-sm font-semibold hover:bg-secondary/80 transition-colors border border-border"
          >
            Apply search
          </button>

          {hasActiveFilters && (
            <Link href="/events" className="block text-center text-xs text-muted-foreground mt-2 hover:text-foreground">
              Clear All
            </Link>
          )}
        </form>
      </aside>

      <div className="flex-1 p-6 lg:p-10">
        <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">All Events</h1>
          <div className="flex items-center gap-3">
            {isValidating && (
              <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Updating
              </span>
            )}
            <p className="text-muted-foreground text-sm font-medium px-4 py-1.5 rounded-full bg-secondary uppercase tracking-wider">
              {total} events
            </p>
          </div>
        </div>

        {error && (
          <p className="text-destructive text-sm mb-4">Could not load events. Check your connection or API URL.</p>
        )}

        {isLoading && !data ? (
          <EventGridSkeleton />
        ) : items.length > 0 ? (
          <>
            <div
              className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 transition-opacity ${isValidating ? "opacity-80" : "opacity-100"}`}
            >
              {items.map((event) => (
                <EventCard key={event.id} event={event} />
              ))}
            </div>

            {totalPages > 1 && (
              <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
                {prevHref ? (
                  <Link
                    href={prevHref}
                    scroll={false}
                    className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:border-primary hover:text-primary transition-colors"
                  >
                    <ChevronLeft className="h-4 w-4" /> Previous
                  </Link>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground opacity-50 cursor-not-allowed">
                    <ChevronLeft className="h-4 w-4" /> Previous
                  </span>
                )}
                <span className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </span>
                {nextHref ? (
                  <Link
                    href={nextHref}
                    scroll={false}
                    className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:border-primary hover:text-primary transition-colors"
                  >
                    Next <ChevronRight className="h-4 w-4" />
                  </Link>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground opacity-50 cursor-not-allowed">
                    Next <ChevronRight className="h-4 w-4" />
                  </span>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="rounded-xl border border-dashed border-border py-24 text-center flex flex-col items-center bg-card shadow-inner">
            <Search className="w-12 h-12 text-muted mb-4" />
            <h3 className="text-xl font-bold mb-2">No events found</h3>
            <p className="text-muted-foreground mb-8">
              Adjust your filters or check back later once more events are indexed.
            </p>
            <Link
              href="/submit"
              className="rounded-full bg-primary text-primary-foreground px-8 py-3 font-semibold hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 hover:scale-105"
            >
              Submit an Event
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
