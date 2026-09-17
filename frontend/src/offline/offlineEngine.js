import { retrieve, getEntryById, checkGlobalEmergency, checkTopicRedFlags, DISCLAIMER, EMERGENCY_NUMBERS } from "./retrieval.js";

/**
 * On-device fallback for the "offline messaging" feature: when there is no
 * connectivity (or the backend request fails/times out), the chat keeps
 * working using this module instead of showing an error. It mirrors
 * backend/app/conversation.py's stage machine and backend/app/safety_layer.py's
 * escalation rules closely enough that the answer a user gets offline is
 * the SAME shape and carries the SAME citations as the answer they'd get
 * online — it just runs entirely in the browser against the bundled copy
 * of knowledge_base.json (kept in sync via scripts/sync-knowledge-base.js).
 */

const DURATION_OPTIONS = {
  en: [["today", "Just started today", 0], ["2_3_days", "2-3 days", 2], ["4_7_days", "4-7 days", 5], ["over_week", "More than a week", 10]],
  hi: [["today", "आज ही शुरू हुआ", 0], ["2_3_days", "2-3 दिन", 2], ["4_7_days", "4-7 दिन", 5], ["over_week", "एक हफ्ते से ज़्यादा", 10]],
};
const SEVERITY_OPTIONS = {
  en: [["mild", "Mild - barely noticeable"], ["moderate", "Moderate - noticeable but manageable"], ["severe", "Severe - hard to bear / limits activity"]],
  hi: [["mild", "हल्का"], ["moderate", "मध्यम"], ["severe", "गंभीर"]],
};
const AGE_OPTIONS = {
  en: [["infant", "Under 1 year"], ["child", "1-12 years"], ["teen", "13-17 years"], ["adult", "18-59 years"], ["senior", "60+ years"]],
  hi: [["infant", "1 साल से कम"], ["child", "1-12 साल"], ["teen", "13-17 साल"], ["adult", "18-59 साल"], ["senior", "60+ साल"]],
};
const YES_NO_OPTIONS = {
  en: [["yes", "Yes, that's right"], ["no", "No, let me rephrase"]],
  hi: [["yes", "हां, यह सही है"], ["no", "नहीं"]],
};

const chips = (options, lang) => options[lang].map(([id, label]) => ({ id, label }));
const labelFor = (options, lang, id) => (options[lang].find(([oid]) => oid === id) || [null, id])[1];
const daysFor = (id) => {
  for (const lang of Object.values(DURATION_OPTIONS)) {
    const found = lang.find(([oid]) => oid === id);
    if (found) return found[2];
  }
  return 0;
};

export function newOfflineSession(language) {
  return {
    stage: "AWAITING_SYMPTOM",
    language,
    matchedTopicId: null,
    matchConfidence: null,
    durationDays: null,
    durationLabel: null,
    severity: null,
    severityLabel: null,
    ageGroup: null,
    ageLabel: null,
    redFlags: [],
    rephraseAttempts: 0,
    originalMessage: "",
  };
}

function escalate(base, severity, durationDays, ageGroup, alwaysUrgent) {
  if (base === "EMERGENCY") return "EMERGENCY";
  if (alwaysUrgent) return "URGENT";
  let level = base;
  const vulnerable = ageGroup === "infant" || ageGroup === "senior";
  if (severity === "severe") level = "URGENT";
  else if (severity === "moderate" && vulnerable) level = "URGENT";
  else if (durationDays >= 7) level = level === "SELF_CARE" ? "ROUTINE" : level;
  else if (vulnerable && level === "SELF_CARE") level = "ROUTINE";
  return level;
}

function buildRecap(session) {
  const lang = session.language;
  const entry = getEntryById(session.matchedTopicId);
  const topicLabel = entry ? entry.title[lang] : session.originalMessage;
  if (lang === "hi") {
    let text = `आपने बताया: ${topicLabel}, ${session.durationLabel} से, गंभीरता: ${session.severityLabel}, आयु वर्ग: ${session.ageLabel}।`;
    if (session.redFlags.length) text += " आपने यह भी बताया: " + session.redFlags.join("; ");
    return text;
  }
  let text = `Here's what you told me: ${topicLabel}, present for ${session.durationLabel}, severity: ${session.severityLabel}, age group: ${session.ageLabel}.`;
  if (session.redFlags.length) text += " You also flagged: " + session.redFlags.join("; ");
  return text;
}

function buildEmergencyBanner(language, flags, isCrisis) {
  const n = EMERGENCY_NUMBERS;
  if (isCrisis) {
    return language === "hi"
      ? `यह एक संवेदनशील पल लग रहा है। कृपया अभी Tele-MANAS हेल्पलाइन ${n.india_mental_health_telemanas} पर कॉल करें।`
      : `This sounds like a difficult moment. Please call the Tele-MANAS helpline ${n.india_mental_health_telemanas} right now.`;
  }
  const flagsText = flags.join("; ");
  return language === "hi"
    ? `आपातकालीन चेतावनी: ${flagsText}\nकृपया तुरंत ${n.india_ambulance} (एम्बुलेंस) या ${n.india_general} पर कॉल करें।`
    : `Urgent warning signs detected: ${flagsText}\nPlease call ${n.india_ambulance} (ambulance) or ${n.india_general} right now.`;
}

function finalAnswer(session) {
  const lang = session.language;
  const entry = getEntryById(session.matchedTopicId);
  const alwaysUrgent = !!(entry && entry.always_urgent);
  let level = escalate("SELF_CARE", session.severity, session.durationDays, session.ageGroup, alwaysUrgent);
  if (session.redFlags.length) level = alwaysUrgent ? "EMERGENCY" : "URGENT";

  const sections = [buildRecap(session)];
  if (entry) sections.push(entry.overview[lang]);

  if ((level === "EMERGENCY" || level === "URGENT") && session.redFlags.length) {
    sections.push(buildEmergencyBanner(lang, session.redFlags, false));
  } else if (level === "ROUTINE") {
    sections.push(lang === "hi" ? "अगर जल्द सुधार न हो, तो डॉक्टर से जांच करवाना बेहतर होगा।" : "It's a good idea to get this checked by a doctor if it doesn't improve soon.");
  }

  let homeRemedies = [];
  let remedySources = [];
  let remedyCaution = null;

  if (entry && (level === "SELF_CARE" || level === "ROUTINE")) {
    const header = lang === "hi" ? "आप क्या कर सकते हैं (WHO / NHS / MoHFW मार्गदर्शन):" : "What you can do (WHO / NHS / MoHFW guidance):";
    sections.push(header + "\n" + entry.self_care[lang].map((t) => `- ${t}`).join("\n"));

    if (entry.home_remedies) {
      homeRemedies = entry.home_remedies[lang];
      remedySources = entry.remedy_sources || [];
      remedyCaution = entry.remedy_caution ? entry.remedy_caution[lang] : null;
      const rHeader = lang === "hi" ? "पारंपरिक घरेलू उपाय (आयुष मंत्रालय):" : "Traditional home remedies (Ministry of AYUSH):";
      sections.push(rHeader + "\n" + homeRemedies.map((t) => `- ${t}`).join("\n") + `\n\n${lang === "hi" ? "सावधानी" : "Caution"}: ${remedyCaution}`);
    }
  }

  if (entry) {
    const rfHeader = lang === "hi" ? "अगर ये दिखे तो तुरंत डॉक्टर से मिलें:" : "Seek medical care promptly if you notice:";
    sections.push(rfHeader + "\n" + entry.red_flags[lang].map((t) => `- ${t}`).join("\n"));
  }

  sections.push(DISCLAIMER[lang]);

  return {
    triage_level: level,
    reply_text: sections.join("\n\n"),
    quick_replies: [],
    matched_topic: session.matchedTopicId,
    match_confidence: session.matchConfidence,
    recap: buildRecap(session),
    red_flags_detected: session.redFlags,
    sources: entry ? entry.sources : [],
    home_remedies: homeRemedies,
    remedy_sources: remedySources,
    remedy_caution: remedyCaution,
    emergency_numbers: level === "EMERGENCY" || level === "URGENT" ? EMERGENCY_NUMBERS : null,
    is_final: true,
    offline: true,
  };
}

/** Mirrors backend conversation.handle_message, returns {session, response}. */
export function handleOfflineMessage(session, message) {
  const lang = session.language;

  const emergency = checkGlobalEmergency(message, lang);
  if (emergency) {
    return {
      session: { ...session, stage: "DONE" },
      response: {
        triage_level: "EMERGENCY",
        reply_text: buildEmergencyBanner(lang, emergency.matchedFlags, emergency.isCrisis),
        quick_replies: [],
        matched_topic: session.matchedTopicId,
        red_flags_detected: emergency.matchedFlags,
        sources: [],
        home_remedies: [],
        remedy_sources: [],
        emergency_numbers: EMERGENCY_NUMBERS,
        is_final: true,
        offline: true,
      },
    };
  }

  if (session.stage === "AWAITING_SYMPTOM") {
    const hits = retrieve(message);
    if (!hits.length) {
      return {
        session: { ...session, originalMessage: message },
        response: {
          triage_level: "NEED_MORE_INFO",
          reply_text: lang === "hi"
            ? "मैं इसे किसी मौजूदा विषय से ठीक से नहीं जोड़ पाया। कृपया अलग तरीके से बताएं।"
            : "I couldn't confidently match that to a topic I currently cover. Could you describe it differently?",
          quick_replies: [],
          offline: true,
        },
      };
    }
    const { entry, score } = hits[0];
    const next = {
      ...session,
      originalMessage: message,
      matchedTopicId: entry.id,
      matchConfidence: Math.round(score * 100) / 100,
      redFlags: [...session.redFlags, ...checkTopicRedFlags(entry, message, lang)],
      stage: "AWAITING_TOPIC_CONFIRMATION",
    };
    return {
      session: next,
      response: {
        triage_level: "NEED_MORE_INFO",
        reply_text: lang === "hi" ? `समझ गया - यह ${entry.title[lang]} से संबंधित लगता है। क्या यह सही है?` : `Got it - this sounds related to ${entry.title[lang]}. Is that right?`,
        quick_replies: chips(YES_NO_OPTIONS, lang),
        matched_topic: entry.id,
        match_confidence: next.matchConfidence,
        offline: true,
      },
    };
  }

  if (session.stage === "AWAITING_TOPIC_CONFIRMATION") {
    if (message === "no") {
      const next = { ...newOfflineSession(lang), rephraseAttempts: session.rephraseAttempts + 1 };
      return {
        session: next,
        response: {
          triage_level: "NEED_MORE_INFO",
          reply_text: lang === "hi" ? "माफ़ कीजिए - कृपया लक्षण को फिर से बताएं।" : "Sorry about that - please describe the symptom again in your own words.",
          quick_replies: [],
          offline: true,
        },
      };
    }
    const next = { ...session, stage: "AWAITING_DURATION" };
    return {
      session: next,
      response: {
        triage_level: "NEED_MORE_INFO",
        reply_text: lang === "hi" ? "यह कब से हो रहा है?" : "How long has this been going on?",
        quick_replies: chips(DURATION_OPTIONS, lang),
        matched_topic: session.matchedTopicId,
        offline: true,
      },
    };
  }

  if (session.stage === "AWAITING_DURATION") {
    const next = { ...session, durationDays: daysFor(message), durationLabel: labelFor(DURATION_OPTIONS, lang, message), stage: "AWAITING_SEVERITY" };
    return {
      session: next,
      response: {
        triage_level: "NEED_MORE_INFO",
        reply_text: lang === "hi" ? "यह कितना गंभीर महसूस हो रहा है?" : "How severe would you say it is?",
        quick_replies: chips(SEVERITY_OPTIONS, lang),
        matched_topic: session.matchedTopicId,
        offline: true,
      },
    };
  }

  if (session.stage === "AWAITING_SEVERITY") {
    const next = { ...session, severity: message, severityLabel: labelFor(SEVERITY_OPTIONS, lang, message), stage: "AWAITING_AGE" };
    return {
      session: next,
      response: {
        triage_level: "NEED_MORE_INFO",
        reply_text: lang === "hi" ? "यह जानकारी किसके लिए है?" : "Who is this for?",
        quick_replies: chips(AGE_OPTIONS, lang),
        matched_topic: session.matchedTopicId,
        offline: true,
      },
    };
  }

  if (session.stage === "AWAITING_AGE") {
    const next = { ...session, ageGroup: message, ageLabel: labelFor(AGE_OPTIONS, lang, message), stage: "AWAITING_REDFLAG_CHECK" };
    const entry = getEntryById(session.matchedTopicId);
    const flags = entry.red_flags[lang];
    const chipsOut = flags.map((f, i) => ({ id: `flag::${i}`, label: f }));
    chipsOut.push({ id: "none", label: lang === "hi" ? "इनमें से कोई नहीं" : "None of these" });
    return {
      session: next,
      response: {
        triage_level: "NEED_MORE_INFO",
        reply_text: lang === "hi" ? "आखिरी सवाल - क्या अभी आपको इनमें से कोई लक्षण महसूस हो रहा है?" : "Last check - are you noticing any of these right now?",
        quick_replies: chipsOut,
        matched_topic: session.matchedTopicId,
        offline: true,
      },
    };
  }

  if (session.stage === "AWAITING_REDFLAG_CHECK") {
    let next = { ...session, stage: "DONE" };
    if (message.startsWith("flag::")) {
      const entry = getEntryById(session.matchedTopicId);
      const idx = parseInt(message.split("::")[1], 10);
      next.redFlags = [...session.redFlags, entry.red_flags[lang][idx]];
    }
    return { session: next, response: finalAnswer(next) };
  }

  // DONE -> start fresh
  const fresh = newOfflineSession(lang);
  return handleOfflineMessage(fresh, message);
}
