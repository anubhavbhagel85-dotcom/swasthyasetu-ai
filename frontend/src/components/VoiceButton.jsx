import React, { useRef, useState } from "react";

/**
 * Voice input for the bonus "Voice and Hindi" feature.
 *
 * For the hackathon demo we default to the browser's built-in
 * Web Speech API (SpeechRecognition) because it needs zero backend
 * setup and works instantly on stage. It supports both 'en-IN' and
 * 'hi-IN' out of the box in Chrome/Edge.
 *
 * A production build can instead route audio to POST /api/voice/transcribe
 * (see backend/app/translation.py), which uses the Government of India's
 * Bhashini ASR models for higher-accuracy Hindi recognition. Swap the
 * `useWebSpeech` flag below to false once Bhashini credentials are set.
 */
export default function VoiceButton({ language, onResult, uiText }) {
  const [listening, setListening] = useState(false);
  const [unsupported, setUnsupported] = useState(false);
  const recognitionRef = useRef(null);

  const handleClick = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setUnsupported(true);
      setTimeout(() => setUnsupported(false), 3000);
      return;
    }

    if (listening) {
      recognitionRef.current?.stop();
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = language === "hi" ? "hi-IN" : "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      onResult(transcript);
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={handleClick}
        aria-label="Voice input"
        className={`flex h-10 w-10 items-center justify-center rounded-full border transition ${
          listening
            ? "border-urgent bg-urgent-light text-urgent animate-pulse"
            : "border-indigo/20 bg-white text-indigo hover:bg-indigo/5"
        }`}
      >
        {listening ? "●" : "🎤"}
      </button>
      {listening && (
        <span className="absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap text-xs text-indigo/70 font-body">
          {uiText.listening}
        </span>
      )}
      {unsupported && (
        <span className="absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap text-xs text-urgent font-body">
          {uiText.voiceUnsupported}
        </span>
      )}
    </div>
  );
}
