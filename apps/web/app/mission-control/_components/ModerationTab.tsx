"use client";

import { useEffect, useState } from "react";
import { adminService, type ModerationItem } from "@/lib/admin-api";
import { Loader2, ExternalLink, CheckCircle, XCircle, AlertTriangle, RefreshCw } from "lucide-react";

const REASON_LABELS: Record<string, string> = {
  low_confidence: "Low AI Confidence",
  not_lucknow: "Not Lucknow-related",
  duplicate: "Possible Duplicate",
  missing_date: "Missing Date",
  nsfw: "Flagged Content",
};

const SEVERITY_COLORS: Record<string, string> = {
  low: "bg-yellow-500/10 text-yellow-600 border-yellow-500/20",
  medium: "bg-orange-500/10 text-orange-600 border-orange-500/20",
  high: "bg-red-500/10 text-red-600 border-red-500/20",
};

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

  async function handleApprove(id: string) {
    setActionId(id);
    await adminService.approveModeration(id).catch(() => null);
    setItems((list) => list.filter((i) => i.id !== id));
    setActionId(null);
  }

  async function handleReject(id: string) {
    setActionId(id);
    await adminService.rejectModeration(id).catch(() => null);
    setItems((list) => list.filter((i) => i.id !== id));
    setActionId(null);
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground py-12">
        <Loader2 className="w-5 h-5 animate-spin" /> Loading moderation queue…
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-extrabold text-lg">Moderation Queue</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Events flagged for low AI confidence or data quality issues. Review and approve or reject.
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-primary transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <CheckCircle className="w-12 h-12 text-green-500 mb-3" />
          <p className="font-extrabold text-base">Queue is clear</p>
          <p className="text-sm text-muted-foreground mt-1">No items pending review.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const isActioning = actionId === item.id;
            const severityClass = SEVERITY_COLORS[item.severity ?? "low"] ?? SEVERITY_COLORS.low;
            const reasonLabel = REASON_LABELS[item.reason ?? ""] ?? item.reason ?? "Review needed";

            return (
              <div
                key={item.id}
                className="rounded-xl border border-border bg-card p-5 flex flex-col gap-4"
              >
                {/* Header row */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span
                        className={`inline-flex items-center gap-1 text-[10px] font-extrabold px-2 py-0.5 rounded-full border uppercase ${severityClass}`}
                      >
                        <AlertTriangle className="w-3 h-3" />
                        {reasonLabel}
                      </span>
                      {item.preview_confidence != null && (
                        <span className="text-[10px] font-semibold text-muted-foreground">
                          AI confidence: {Math.round(item.preview_confidence * 100)}%
                        </span>
                      )}
                      {item.entity_type && (
                        <span className="text-[10px] font-semibold text-muted-foreground capitalize">
                          {item.entity_type.replace("_", " ")}
                        </span>
                      )}
                    </div>

                    {/* Event title */}
                    <p className="font-bold text-sm leading-tight truncate">
                      {item.preview_title ?? "(No title extracted)"}
                    </p>

                    {/* Community / organizer */}
                    {item.preview_community && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        by <span className="font-semibold text-foreground">{item.preview_community}</span>
                      </p>
                    )}

                    {/* Source URL */}
                    {item.preview_url && (
                      <a
                        href={item.preview_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-1.5 inline-flex items-center gap-1 text-xs text-primary hover:underline truncate max-w-full"
                      >
                        <ExternalLink className="w-3 h-3 flex-shrink-0" />
                        <span className="truncate">{item.preview_url}</span>
                      </a>
                    )}

                    {/* Notes */}
                    {item.notes && (
                      <p className="mt-2 text-xs text-muted-foreground italic">
                        &quot;{item.notes}&quot;
                      </p>
                    )}
                  </div>

                  {/* Timestamp */}
                  <p className="text-[11px] text-muted-foreground whitespace-nowrap flex-shrink-0">
                    {new Date(item.created_at).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>

                {/* Action buttons */}
                <div className="flex gap-2 border-t border-border pt-3">
                  <button
                    onClick={() => handleApprove(item.id)}
                    disabled={isActioning}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-green-500/10 text-green-600 text-xs font-bold border border-green-500/20 hover:bg-green-500/20 transition-colors disabled:opacity-50"
                  >
                    {isActioning ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle className="w-3.5 h-3.5" />
                    )}
                    Approve & Publish
                  </button>
                  <button
                    onClick={() => handleReject(item.id)}
                    disabled={isActioning}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-500/10 text-destructive text-xs font-bold border border-destructive/20 hover:bg-red-500/20 transition-colors disabled:opacity-50"
                  >
                    {isActioning ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5" />
                    )}
                    Reject
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
