import React, { useEffect, useRef, useState } from "react";
import Header from "./components/Header.jsx";
import Sidebar from "./components/Sidebar.jsx";
import MessageBubble from "./components/MessageBubble.jsx";
import QuickReplies from "./components/QuickReplies.jsx";
import VoiceButton from "./components/VoiceButton.jsx";
import { UI } from "./i18n.js";
import api from "./api.js";
import { newOfflineSession, handleOfflineMessage } from "./offline/offlineEngine.js";

export default function App() {
  const [language, setLanguage] = useState("en");
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [quickReplies, setQuickReplies] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sourcesCount, setSourcesCount] = useState(10);
  const [error, setError] = useState(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [usingOffline, setUsingOffline] = useState(false);
  const scrollRef = useRef(null);
  const offlineSessionRef = useRef(newOfflineSession("en"));
  const offlineTranscriptRef = useRef([]);
  const uiText = UI[language];

  const pushMessage = (msg) => setMessages((prev) => [...prev, msg]);

  const toAssistantMessage = (res) => ({
    role: "assistant",
    text: res.reply_text,
    triageLevel: res.triage_level,
    triageLabel: UI[language].triage[res.triage_level],
    sources: res.sources,
    remedySources: res.remedy_sources,
    matchConfidence: res.match_confidence,
    emergencyNumbers: res.emergency_numbers,
    offline: !!res.offline,
  });

  const goOffline = (lang) => {
    setUsingOffline(true);
    offlineSessionRef.current = newOfflineSession(lang);
    offlineTranscriptRef.current = [];
  };

  const beginConversation = async (lang) => {
    setError(null);
    setUsingOffline(false);
    if (!navigator.onLine) {
      goOffline(lang);
      const welcome = lang === "hi"
        ? "नमस्ते 🙏 मैं SwasthyaSetu AI हूं (ऑफ़लाइन मोड)। मुझे बताइए आपको क्या तकलीफ महसूस हो रही है।"
        : "Hi 🙏 I'm SwasthyaSetu AI (offline mode). Tell me what symptom you're experiencing.";
      setMessages([{ role: "assistant", text: welcome, offline: true }]);
      setQuickReplies([]);
      return;
    }
    try {
      const res = await api.startChat(lang);
      setSessionId(res.session_id);
      setMessages([{ role: "assistant", text: res.message }]);
      setQuickReplies([]);
    } catch (e) {
      goOffline(lang);
      setMessages([{
        role: "assistant",
        offline: true,
        text: lang === "hi"
          ? "बैकएंड से संपर्क नहीं हो पाया — मैं अभी डिवाइस पर ऑफ़लाइन मोड में जवाब दूंगा।"
          : "Couldn't reach the backend — I'll answer in on-device offline mode for now.",
      }]);
    }
  };

  useEffect(() => {
    beginConversation(language);
    api.getSources().then((s) => setSourcesCount(s.length)).catch(() => {});

    const handleOnline = () => {
      setIsOnline(true);
      // Best-effort background sync of whatever happened offline — never
      // blocks the UI and never fails loudly if the backend isn't reachable.
      if (offlineTranscriptRef.current.length > 0 && sessionId) {
        api
          .sendSync?.(sessionId, language, offlineTranscriptRef.current)
          .catch(() => {});
      }
    };
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, quickReplies]);

  const handleLanguageChange = (lang) => {
    setLanguage(lang);
    beginConversation(lang);
  };

  const handleNewChat = () => beginConversation(language);

  const recordOfflineTurn = (role, res) => {
    offlineTranscriptRef.current.push({
      role,
      text: res?.reply_text ?? "",
      triage_level: res?.triage_level,
      matched_topic: res?.matched_topic,
    });
  };

  const sendMessage = async (rawText, displayText) => {
    if (sending || !rawText.trim()) return;
    setSending(true);
    setError(null);
    pushMessage({ role: "user", text: displayText ?? rawText });
    setQuickReplies([]);
    setInput("");

    if (usingOffline || !navigator.onLine) {
      const { session: nextSession, response } = handleOfflineMessage(offlineSessionRef.current, rawText);
      offlineSessionRef.current = nextSession;
      recordOfflineTurn("user", { reply_text: rawText });
      recordOfflineTurn("assistant", response);
      pushMessage(toAssistantMessage(response));
      setQuickReplies(response.quick_replies || []);
      setSending(false);
      return;
    }

    try {
      const res = await api.sendMessage(sessionId, rawText, language);
      pushMessage(toAssistantMessage(res));
      setQuickReplies(res.quick_replies || []);
    } catch (e) {
      // Network dropped mid-conversation: seamlessly continue on-device with
      // the SAME message the user just sent, rather than losing their turn.
      goOffline(language);
      const { session: nextSession, response } = handleOfflineMessage(offlineSessionRef.current, rawText);
      offlineSessionRef.current = nextSession;
      recordOfflineTurn("user", { reply_text: rawText });
      recordOfflineTurn("assistant", response);
      pushMessage({ role: "assistant", text: uiText.offlineBanner, offline: true });
      pushMessage(toAssistantMessage(response));
      setQuickReplies(response.quick_replies || []);
    } finally {
      setSending(false);
    }
  };

  const handleQuickReply = (optionId) => {
    const label = quickReplies.find((q) => q.id === optionId)?.label ?? optionId;
    sendMessage(optionId, label);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="flex h-screen flex-col">
      <Header
        language={language}
        onLanguageChange={handleLanguageChange}
        onNewChat={handleNewChat}
        uiText={uiText}
      />

      {usingOffline && (
        <div className="bg-amber-light border-b border-amber/30 px-5 py-2 text-center text-sm text-amber-dark font-body sm:px-8">
          📴 {isOnline ? uiText.backOnlineBanner : uiText.offlineBanner}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <main className="flex flex-1 flex-col overflow-hidden">
          <div className="border-b border-black/5 px-5 py-4 sm:px-8">
            <h1 className="font-display text-2xl text-indigo">{uiText.tagline}</h1>
            <p className="mt-1 max-w-2xl text-sm text-ink/60 font-body">{uiText.subtitle}</p>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-5 sm:px-8">
            <div className="mx-auto flex max-w-2xl flex-col gap-3">
              {messages.map((m, i) => (
                <MessageBubble key={i} message={m} uiText={uiText} />
              ))}

              {sending && (
                <div className="flex justify-start">
                  <div className="rounded-chat rounded-tl-sm bg-white border border-black/5 px-4 py-3 flex gap-1">
                    <span className="typing-dot h-1.5 w-1.5 rounded-full bg-indigo/40" style={{ animationDelay: "0s" }} />
                    <span className="typing-dot h-1.5 w-1.5 rounded-full bg-indigo/40" style={{ animationDelay: "0.15s" }} />
                    <span className="typing-dot h-1.5 w-1.5 rounded-full bg-indigo/40" style={{ animationDelay: "0.3s" }} />
                  </div>
                </div>
              )}

              {!sending && quickReplies.length > 0 && (
                <QuickReplies options={quickReplies} onSelect={handleQuickReply} disabled={sending} />
              )}

              {error && (
                <p className="text-sm text-emergency font-body bg-emergency-light rounded-lg px-3 py-2">{error}</p>
              )}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="border-t border-black/5 bg-paper/95 px-5 py-4 sm:px-8">
            <div className="mx-auto flex max-w-2xl items-center gap-2">
              <VoiceButton language={language} onResult={(t) => setInput(t)} uiText={uiText} />
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={uiText.inputPlaceholder}
                className="flex-1 rounded-full border border-indigo/15 bg-white px-4 py-2.5 text-[15px] font-body text-ink placeholder:text-ink/35 focus:border-indigo/40 outline-none"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="rounded-full bg-indigo px-5 py-2.5 text-sm font-semibold text-paper hover:bg-indigo-light transition disabled:opacity-40 font-body"
              >
                {uiText.send}
              </button>
            </div>
            <p className="mx-auto mt-2 max-w-2xl text-center text-[11px] text-ink/40 font-body">
              {uiText.footerNote}
            </p>
          </form>
        </main>

        <Sidebar uiText={uiText} sourcesCount={sourcesCount} />
      </div>
    </div>
  );
}
