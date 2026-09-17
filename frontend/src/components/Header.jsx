import React from "react";

export default function Header({ language, onLanguageChange, onNewChat, uiText }) {
  return (
    <header className="flex items-center justify-between border-b border-black/5 bg-paper/90 backdrop-blur px-5 py-3 sm:px-8">
      <div className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo text-marigold-light font-display text-lg">
          स
        </div>
        <div className="leading-tight">
          <p className="font-display text-lg text-indigo">SwasthyaSetu AI</p>
          <p className="hidden sm:block text-[11px] text-ink/50 font-body -mt-0.5">{uiText.disclaimerShort}</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onNewChat}
          className="hidden sm:inline text-sm font-medium text-indigo/70 hover:text-indigo transition font-body"
        >
          {uiText.newChat}
        </button>
        <div className="flex rounded-full border border-indigo/15 p-0.5 bg-white">
          {["en", "hi"].map((code) => (
            <button
              key={code}
              onClick={() => onLanguageChange(code)}
              className={`px-3 py-1 rounded-full text-sm font-semibold font-body transition ${
                language === code ? "bg-indigo text-paper" : "text-indigo/60 hover:text-indigo"
              }`}
            >
              {code === "en" ? "EN" : "हिं"}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
