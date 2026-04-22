"use client";

import { useEffect, useState } from "react";
import { adminService, type ModerationItem } from "@/lib/admin-api";
import { Loader2, CheckCircle, XCircle, Inbox } from "lucide-react";

export function ModerationTab() {
  const [items, setItems] = useState<ModerationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    const data = await adminService.listModeration().catch(() => []);
    setItems(data);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function approve(id: string) {
    setActionId(id);
    await adminService.approve(id).catch(() => null);
    setItems((list) => list.filter((i) => i.id !== id));
    setActionId(null);
  }

  async function reject(id: string) {
    setActionId(id);
    await adminService.reject(id).catch(() => null);
    setItems((list) => list.filter((i) => i.id !== id));
    setActionId(null);
  }

  if (loading) {
    return <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Inbox className="w-14 h-14 text-muted-foreground/30 mb-4" />
        <h3 className="font-extrabold text-lg mb-2">Inbox Zero</h3>
        <p className="text-muted-foreground text-sm">No pending submissions to review.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-w-3xl">
      <div className="text-xs text-muted-foreground font-semibold mb-4">{items.length} pending review</div>
      {items.map((item) => (
        <div key={item.id} className="rounded-xl border border-border bg-card p-5 flex items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-extrabold uppercase text-muted-foreground">{item.entity_type ?? "submission"}</span>
              {item.severity && (
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full uppercase ${
                  item.severity === "high" ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground"
                }`}>{item.severity}</span>
              )}
            </div>
            <p className="font-semibold text-sm mb-1 line-clamp-2">{item.reason ?? "Manual submission pending review"}</p>
            <p className="text-xs text-muted-foreground">
              {new Date(item.created_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              onClick={() => approve(item.id)}
              disabled={actionId === item.id}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-green-500/10 text-green-600 text-xs font-bold hover:bg-green-500/20 transition-colors disabled:opacity-50"
            >
              <CheckCircle className="w-4 h-4" /> Approve
            </button>
            <button
              onClick={() => reject(item.id)}
              disabled={actionId === item.id}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-destructive/10 text-destructive text-xs font-bold hover:bg-destructive/20 transition-colors disabled:opacity-50"
            >
              <XCircle className="w-4 h-4" /> Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
