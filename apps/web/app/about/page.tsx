import { Telescope, Globe, Calendar, Mail, ArrowRight } from "lucide-react";
import Link from "next/link";

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto py-12 px-6 space-y-16">
      {/* Hero */}
      <section className="text-center space-y-4">
        <div className="inline-flex items-center justify-center p-3 bg-primary/10 text-primary rounded-2xl mb-2">
          <Telescope className="w-8 h-8" />
        </div>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight">About This Project</h1>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          Lucknow Tech Events is a community-driven aggregator that automatically discovers and indexes tech events happening across Lucknow and Uttar Pradesh.
        </p>
      </section>

      <div className="w-full h-px bg-border" />

      {/* How it works */}
      <section className="space-y-8">
        <h2 className="text-2xl font-bold tracking-tight">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              step: "1",
              title: "Automatic Discovery",
              description: "A Playwright-based scraper crawls community pages (GDG, Commudle, Devfolio, Unstop) on a schedule every 6 hours."
            },
            {
              step: "2",
              title: "AI Extraction",
              description: "Raw pages pass through Gemini Flash agents that extract structured event data: dates, venue, topics, registration links — even from messy HTML."
            },
            {
              step: "3",
              title: "Curated Feed",
              description: "Events are normalized, deduplicated, scored for Lucknow relevance, and published — then available via our REST API and calendar feeds."
            },
          ].map(({ step, title, description }) => (
            <div key={step} className="flex flex-col gap-3 bg-card rounded-xl border border-border p-6">
              <span className="text-3xl font-black text-primary">{step}</span>
              <h3 className="text-lg font-bold text-foreground">{title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Community */}
      <section className="space-y-4 bg-card border border-border rounded-2xl p-8">
        <div className="flex items-center gap-3">
          <Globe className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-bold">Powered by UP AI Labs</h2>
        </div>
        <p className="text-muted-foreground leading-relaxed">
          This project is part of the Lucknow Developers community initiative — dedicated to making AI-powered tools that serve Tier-2 cities across India. Founded in Lucknow, we unite researchers, engineers, and students across Uttar Pradesh.
        </p>
        <a href="https://upailabs.org" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-primary font-semibold hover:underline text-sm">
          Visit upailabs.org <ArrowRight className="w-4 h-4" />
        </a>
      </section>

      {/* Open Data */}
      <section className="space-y-6">
        <div className="flex items-center gap-3">
          <Calendar className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-bold">Open Data & Feeds</h2>
        </div>
        <p className="text-muted-foreground leading-relaxed">
          All event data is freely available via open feeds. Subscribe to our calendar or consume the JSON API to power your own applications.
        </p>
        <div className="flex flex-wrap gap-4">
          <a
            href="/api/v1/feeds/events.ics"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 border border-border bg-card rounded-full px-5 py-2.5 text-sm font-medium hover:border-primary/50 hover:text-primary transition-colors"
          >
            <Calendar className="w-4 h-4" /> Subscribe to ICS Calendar
          </a>
          <a
            href="/api/v1/feeds/events.json"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 border border-border bg-card rounded-full px-5 py-2.5 text-sm font-medium hover:border-primary/50 hover:text-primary transition-colors"
          >
            <Globe className="w-4 h-4" /> JSON Event Dataset
          </a>
        </div>
      </section>

      {/* CTA */}
      <section className="text-center space-y-4 bg-secondary/40 border border-border rounded-2xl p-10">
        <Mail className="w-8 h-8 text-primary mx-auto" />
        <h2 className="text-2xl font-bold">Know of an event we missed?</h2>
        <p className="text-muted-foreground">Submit it and our AI pipeline will extract, verify, and add it to the directory within minutes.</p>
        <Link href="/submit" className="inline-flex items-center gap-2 bg-primary text-primary-foreground font-semibold rounded-full px-8 py-3 hover:bg-primary/90 transition-all">
          Submit an Event <ArrowRight className="w-4 h-4" />
        </Link>
      </section>
    </div>
  );
}
