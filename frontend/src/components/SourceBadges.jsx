import React from "react";

export default function SourceBadges({ sources, label, variant = "clinical" }) {
  if (!sources || sources.length === 0) return null;
  const styles =
    variant === "remedy"
      ? "border-sage/25 bg-sage/[0.06] text-sage hover:bg-sage/10"
      : "border-indigo/15 bg-indigo/[0.04] text-indigo hover:bg-indigo/10";
  return (
    <div className="mt-3 pt-3 border-t border-black/5">
      <p className="text-xs uppercase tracking-wide text-ink/40 mb-1.5 font-body">{label}</p>
      <div className="flex flex-wrap gap-2">
        {sources.map((s) => (
          <a
            key={s.url}
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition ${styles}`}
          >
            <span aria-hidden>{variant === "remedy" ? "🌿" : "✓"}</span>
            {s.name}
          </a>
        ))}
      </div>
    </div>
  );
}
