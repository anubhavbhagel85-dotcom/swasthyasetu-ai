import React from "react";

const STYLES = {
  EMERGENCY: {
    bg: "bg-emergency-light",
    border: "border-emergency",
    text: "text-emergency",
    icon: "🚨",
  },
  URGENT: {
    bg: "bg-urgent-light",
    border: "border-urgent",
    text: "text-urgent",
    icon: "⚠️",
  },
  ROUTINE: {
    bg: "bg-amber-light",
    border: "border-amber",
    text: "text-amber-dark",
    icon: "🩺",
  },
  SELF_CARE: {
    bg: "bg-sage-light",
    border: "border-sage",
    text: "text-sage",
    icon: "🌿",
  },
};

export default function TriageBanner({ level, label, emergencyNumbers, uiText }) {
  const style = STYLES[level];
  if (!style) return null;

  return (
    <div
      className={`flex items-start gap-3 rounded-chat border ${style.border} ${style.bg} px-4 py-3 mb-3`}
      role={level === "EMERGENCY" ? "alert" : "status"}
    >
      <span className="text-xl leading-none mt-0.5">{style.icon}</span>
      <div className="flex-1">
        <p className={`font-semibold ${style.text} font-body`}>{label}</p>
        {emergencyNumbers && (level === "EMERGENCY" || level === "URGENT") && (
          <div className="mt-2 flex flex-wrap gap-2 text-sm">
            <a
              href={`tel:${emergencyNumbers.india_ambulance}`}
              className="rounded-full bg-white/70 px-3 py-1 font-semibold text-emergency hover:bg-white transition"
            >
              📞 {uiText.ambulance}: {emergencyNumbers.india_ambulance}
            </a>
            <a
              href={`tel:${emergencyNumbers.india_general}`}
              className="rounded-full bg-white/70 px-3 py-1 font-semibold text-emergency hover:bg-white transition"
            >
              📞 {uiText.national}: {emergencyNumbers.india_general}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
