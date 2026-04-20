import Link from 'next/link';
import { Sparkles, Calendar, Search, PlusCircle, Users, Mail, Globe, Send, Hash, Shield, BookOpen } from 'lucide-react';

export function Sidebar() {
  return (
    <div className="flex h-full flex-col py-6">
      <div className="px-6 pb-8 border-b border-border">
        <Link href="/" className="flex flex-col gap-1 items-center justify-center">
          <Sparkles className="w-5 h-5 text-primary mb-1" />
          <div className="text-xl tracking-wider font-light text-foreground text-center leading-tight">
            Nawab <span className="font-medium text-primary">AI</span>
            <br />
            <span className="text-[10px] tracking-[0.2em] font-normal text-muted-foreground uppercase">Lucknow Events</span>
          </div>
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        <div>
          <div className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Discover</div>
          <div className="space-y-1">
            <SidebarLink href="/events" icon={<Search className="w-4 h-4" />}>All Events</SidebarLink>
            <SidebarLink href="/calendar" icon={<Calendar className="w-4 h-4" />}>Calendar</SidebarLink>
            <SidebarLink href="/topics" icon={<Hash className="w-4 h-4" />}>Topics</SidebarLink>
            <SidebarLink href="/communities" icon={<Users className="w-4 h-4" />}>Communities</SidebarLink>
          </div>
        </div>

        <div>
          <div className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Interact</div>
          <div className="space-y-1">
            <SidebarLink href="/submit" icon={<PlusCircle className="w-4 h-4" />}>Submit Event</SidebarLink>
            <SidebarLink href="/about" icon={<BookOpen className="w-4 h-4" />}>About Community</SidebarLink>
            <SidebarLink href="/admin" icon={<Shield className="w-4 h-4" />}>Admin</SidebarLink>
          </div>
        </div>
        
        <div>
          <div className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Feeds</div>
          <div className="space-y-1">
            <a href="/api/v1/feeds/events.ics" className="flex items-center gap-3 rounded-md px-2 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors" target="_blank" rel="noreferrer">
              <Calendar className="w-4 h-4" />
              Subscribe ICS
            </a>
            <a href="/api/v1/feeds/events.json" className="flex items-center gap-3 rounded-md px-2 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors" target="_blank" rel="noreferrer">
              <Globe className="w-4 h-4" />
              JSON Dataset
            </a>
          </div>
        </div>
      </nav>

      <div className="px-6 pt-6 border-t border-border mt-auto">
        <a href="mailto:contact@upailabs.org" className="text-xs text-muted-foreground hover:text-primary transition-colors flex items-center gap-2 mb-2">
          <Mail className="w-3 h-3" /> contact@upailabs.org
        </a>
        <div className="flex gap-4 mt-4 text-muted-foreground">
          {/* Socials placeholder */}
          <Link href="#" className="hover:text-foreground"><Send className="w-4 h-4" /></Link>
        </div>
      </div>
    </div>
  );
}

function SidebarLink({ href, icon, children }: { href: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-md px-2 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
    >
      {icon}
      {children}
    </Link>
  );
}
