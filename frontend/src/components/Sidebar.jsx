import React from "react";

export default function Sidebar({ uiText, sourcesCount }) {
  return (
    <aside className="hidden lg:flex w-72 shrink-0 flex-col gap-4 border-l border-black/5 bg-white/40 p-5">
      <div className="rounded-chat border border-emergency/25 bg-emergency-light/60 p-4">
        <p className="font-display text-sm text-emergency font-semibold mb-2">{uiText.emergencyNumbers}</p>
        <ul className="space-y-1.5 text-sm font-body text-ink/80">
          <li className="flex justify-between"><span>{uiText.ambulance}</span><a href="tel:108" className="font-semibold text-emergency">108</a></li>
          <li className="flex justify-between"><span>{uiText.national}</span><a href="tel:112" className="font-semibold text-emergency">112</a></li>
          <li className="flex justify-between"><span>{uiText.mentalHealth}</span><a href="tel:14416" className="font-semibold text-emergency">14416</a></li>
        </ul>
      </div>

      <div className="rounded-chat border border-indigo/10 bg-white p-4">
        <p className="font-display text-sm text-indigo font-semibold mb-1.5">{uiText.sourcesPanelTitle}</p>
        <p className="text-sm font-body text-ink/70 leading-relaxed">{uiText.sourcesPanelBody}</p>
        <p className="mt-3 text-xs font-body text-ink/40">
          {sourcesCount} {sourcesCount === 1 ? "reference" : "references"} in the knowledge base
        </p>
      </div>
    </aside>
  );
}
