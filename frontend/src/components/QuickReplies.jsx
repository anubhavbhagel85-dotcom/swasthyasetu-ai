import React from "react";

export default function QuickReplies({ options, onSelect, disabled }) {
  if (!options || options.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2 mt-1 mb-4 pl-1 msg-enter">
      {options.map((opt) => (
        <button
          key={opt.id}
          disabled={disabled}
          onClick={() => onSelect(opt.id)}
          className="rounded-full border border-marigold-dark/40 bg-marigold-light/40 px-4 py-1.5 text-sm font-medium text-indigo hover:bg-marigold-light hover:border-marigold-dark transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
