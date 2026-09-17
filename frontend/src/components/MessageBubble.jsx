import React from "react";
import TriageBanner from "./TriageBanner.jsx";
import SourceBadges from "./SourceBadges.jsx";

export default function MessageBubble({ message, uiText }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end msg-enter">
        <div className="max-w-[80%] rounded-chat rounded-tr-sm bg-indigo text-paper px-4 py-2.5 font-body text-[15px] leading-relaxed shadow-sm">
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start msg-enter">
      <div className="max-w-[85%] rounded-chat rounded-tl-sm bg-white border border-black/5 px-4 py-3.5 shadow-sm">
        {message.offline && (
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-amber-light px-2.5 py-0.5 text-[11px] font-semibold text-amber-dark font-body">
            📴 {uiText.offlineAnswerTag}
          </div>
        )}
        {message.triageLevel && message.triageLabel && (
          <TriageBanner
            level={message.triageLevel}
            label={message.triageLabel}
            emergencyNumbers={message.emergencyNumbers}
            uiText={uiText}
          />
        )}
        <div className="font-body text-[15px] leading-relaxed text-ink whitespace-pre-line">
          {message.text}
        </div>
        <SourceBadges sources={message.sources} label={uiText.verifiedSources} variant="clinical" />
        <SourceBadges sources={message.remedySources} label={uiText.remedySourceLabel} variant="remedy" />
        {typeof message.matchConfidence === "number" && (
          <p className="mt-2 text-[11px] text-ink/35 font-body">
            {uiText.matchConfidenceLabel}: {Math.round(message.matchConfidence * 100)}%
          </p>
        )}
      </div>
    </div>
  );
}
