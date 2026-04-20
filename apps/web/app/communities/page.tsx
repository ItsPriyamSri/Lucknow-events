import { facetService } from "@/lib/api";
import { Users } from "lucide-react";
import Link from "next/link";

export const metadata = {
  title: "Communities",
  description: "Communities and groups with published events in Lucknow.",
};

export default async function CommunitiesPage() {
  let items: Awaited<ReturnType<typeof facetService.getCommunities>> = [];
  try {
    items = await facetService.getCommunities();
  } catch {
    /* empty */
  }

  return (
    <div className="max-w-3xl mx-auto py-12 px-6">
      <div className="flex items-center gap-3 mb-8">
        <Users className="w-8 h-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Communities</h1>
          <p className="text-muted-foreground text-sm">Filter the event list by organizer / community name.</p>
        </div>
      </div>
      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-12 text-center">
          <p className="text-muted-foreground mb-4">No communities indexed yet.</p>
          <Link href="/events" className="text-primary font-semibold hover:underline">
            Browse all events
          </Link>
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((c) => (
            <li key={c.name}>
              <Link
                href={`/events?community=${encodeURIComponent(c.name)}`}
                className="flex justify-between rounded-lg border border-border bg-card px-4 py-3 hover:border-primary transition-colors"
              >
                <span className="font-medium">{c.name}</span>
                <span className="text-muted-foreground text-sm">{c.count} events</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
