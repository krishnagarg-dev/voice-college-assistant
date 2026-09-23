import React, { useEffect, useRef, useState } from 'react';
import { askAssistant } from './services/api.js';
import AssistantAnswer from './AssistantAnswer.jsx';
import HumanEscalation from './HumanEscalation.jsx';
import { buildNoInformationSpeech, sanitizeTextForSpeech, selectRelevantSources } from './assistantText.js';

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const LOGO_URL = 'https://www.kiet.edu/_next/image/?url=%2Fassets%2Fimages%2Flogo%2FKIET-Logo.webp&w=640&q=75';

const siteLinks = [
  { label: 'About', href: 'https://www.kiet.edu/about/Overview/' },
  { label: 'Academics', href: 'https://www.kiet.edu/academics/team/' },
  { label: 'Programs', href: 'https://www.kiet.edu/programs/postgraduate-programs/' },
  { label: 'Admissions', href: 'https://www.kiet.edu/admissions/admission-procedure/' },
  { label: 'Events', href: 'https://www.kiet.edu/events/events/' },
];

const utilityLinks = [
  { label: 'Announcements', href: 'https://www.kiet.edu/announcements' },
  { label: 'Library', href: 'https://www.kiet.edu/library' },
  { label: 'Contact us', href: 'https://www.kiet.edu/contact-us' },
];

const knowledgeAreas = [
  'Academics', 'Programs', 'Admissions', 'Research', 'Placements', 'Events',
  'Campus Life', 'Student Welfare', 'Circulars & Notices', 'Syllabus',
  'Rules & Regulations', 'Academic Calendar', 'Faculty', 'Scholarships', 'Fees',
];

function MicrophoneIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3m-4 0h8" /></svg>;
}

function AssistantStateIcon({ state }) {
  if (state === 'listening') return <MicrophoneIcon />;
  if (state === 'processing') return <span className="thinking-icon" aria-hidden="true">✦</span>;
  if (state === 'speaking') return <span className="speaking-icon" aria-hidden="true">◖))</span>;
  if (state === 'error') return <span className="error-icon" aria-hidden="true">!</span>;
  return <span className="welcome-wave" aria-hidden="true">✦</span>;
}

function App() {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [voiceState, setVoiceState] = useState('idle');
  const [voiceSessionActive, setVoiceSessionActive] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [logoFailed, setLogoFailed] = useState(false);
  const recognitionRef = useRef(null);
  const retryTimerRef = useRef(null);
  const sessionActiveRef = useRef(false);
  const turnInProgressRef = useRef(false);
  const requestIdRef = useRef(0);
  const speechGenerationRef = useRef(0);
  const synthesisSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  useEffect(() => () => {
    sessionActiveRef.current = false;
    speechGenerationRef.current += 1;
    window.clearTimeout(retryTimerRef.current);
    recognitionRef.current?.stop();
    window.speechSynthesis?.cancel();
  }, []);

  function stopRecognition() {
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    try { recognition?.stop(); } catch { /* Recognition may already have ended. */ }
  }

  function scheduleListening(delay = 450) {
    window.clearTimeout(retryTimerRef.current);
    if (!sessionActiveRef.current || turnInProgressRef.current) return;
    retryTimerRef.current = window.setTimeout(() => {
      if (sessionActiveRef.current && !turnInProgressRef.current) startRecognition();
    }, delay);
  }

  function finishSpeech() {
    if (!sessionActiveRef.current) return;
    turnInProgressRef.current = false;
    setVoiceState('listening');
    scheduleListening(350);
  }

  function speak(text, { forVoiceSession = sessionActiveRef.current } = {}) {
    if (!synthesisSupported) {
      setError('Speech playback is not supported in this browser.');
      setVoiceState('error');
      if (forVoiceSession) {
        turnInProgressRef.current = false;
        scheduleListening(1200);
      }
      return;
    }

    window.clearTimeout(retryTimerRef.current);
    stopRecognition();
    const speechGeneration = ++speechGenerationRef.current;
    window.speechSynthesis.cancel();
    const speechText = sanitizeTextForSpeech(text);
    if (!speechText) {
      if (forVoiceSession) finishSpeech();
      return;
    }
    const utterance = new SpeechSynthesisUtterance(speechText);
    utterance.lang = 'en-IN';
    utterance.onstart = () => {
      if (speechGeneration === speechGenerationRef.current && forVoiceSession && sessionActiveRef.current) setVoiceState('speaking');
    };
    utterance.onend = () => {
      if (speechGeneration === speechGenerationRef.current) finishSpeech();
    };
    utterance.onerror = (event) => {
      if (speechGeneration !== speechGenerationRef.current || event.error === 'canceled') return;
      setError('Speech playback could not finish. I will continue listening.');
      setVoiceState('error');
      finishSpeech();
    };
    if (forVoiceSession && sessionActiveRef.current) setVoiceState('speaking');
    window.speechSynthesis.speak(utterance);
  }

  async function submitQuestion(value = draft, fromVoice = false) {
    const question = value.trim();
    if (loading) return;
    if (!question) {
      if (fromVoice) {
        turnInProgressRef.current = false;
        scheduleListening();
      }
      return;
    }

    const requestId = ++requestIdRef.current;
    const speakResponse = fromVoice && sessionActiveRef.current;
    setError('');
    setHasInteracted(true);
    setDraft('');
    setMessages((current) => [...current, { role: 'user', text: question }]);
    setVoiceState(speakResponse ? 'processing' : 'idle');
    setLoading(true);
    try {
      const result = await askAssistant(question);
      if (requestId !== requestIdRef.current) return;
      setMessages((current) => [...current, {
        role: 'assistant', text: result.answer, source: result.source,
        sources: result.sources || [], toolSources: result.tool_sources || [],
        responseType: result.response_type || 'answer',
        escalationCategory: result.escalation_category || 'general',
        question,
      }]);
      const speechAnswer = result.response_type === 'no_information'
        ? buildNoInformationSpeech(result.answer, result.escalation_category)
        : result.answer;
      if (speakResponse && sessionActiveRef.current) speak(speechAnswer, { forVoiceSession: true });
    } catch (requestError) {
      if (requestId !== requestIdRef.current) return;
      setError(requestError.message || 'Could not reach the KIET assistant service. Check that the backend is running, then try again.');
      if (speakResponse && sessionActiveRef.current) {
        setVoiceState('error');
        turnInProgressRef.current = false;
        scheduleListening(1800);
      }
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  }

  function startRecognition() {
    if (!sessionActiveRef.current || !SpeechRecognition || recognitionRef.current) return;
    let recognition;
    try {
      recognition = new SpeechRecognition();
      recognition.lang = 'en-IN';
      recognition.interimResults = true;
      recognition.continuous = false;
    } catch {
      setError('Speech recognition could not start. Please check browser permissions and try again.');
      sessionActiveRef.current = false;
      setVoiceSessionActive(false);
      setVoiceState('error');
      return;
    }

    recognition.onstart = () => {
      if (sessionActiveRef.current) setVoiceState('listening');
    };
    recognition.onresult = (event) => {
      const finalTranscript = Array.from(event.results)
        .filter((result) => result.isFinal)
        .map((result) => result[0]?.transcript || '')
        .join(' ')
        .trim();
      if (!finalTranscript || turnInProgressRef.current) return;

      turnInProgressRef.current = true;
      setDraft(finalTranscript);
      setVoiceState('processing');
      stopRecognition();
      void submitQuestion(finalTranscript, true);
    };
    recognition.onerror = (event) => {
      if (recognitionRef.current !== recognition) return;
      recognitionRef.current = null;
      if (event.error === 'aborted' && !sessionActiveRef.current) return;
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setError('Microphone permission is required for voice conversation.');
        sessionActiveRef.current = false;
        setVoiceSessionActive(false);
        turnInProgressRef.current = false;
        setVoiceState('error');
        return;
      }
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      if (sessionActiveRef.current) {
        setError('Speech recognition had a problem. Please try speaking again.');
        sessionActiveRef.current = false;
        setVoiceSessionActive(false);
        turnInProgressRef.current = false;
        setVoiceState('error');
      }
    };
    recognition.onend = () => {
      if (recognitionRef.current === recognition) recognitionRef.current = null;
      if (sessionActiveRef.current && !turnInProgressRef.current) scheduleListening(500);
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;
      setError('The microphone could not be started. Please check browser permissions and try again.');
      sessionActiveRef.current = false;
      setVoiceSessionActive(false);
      setVoiceState('error');
    }
  }

  function startConversation() {
    setError('');
    if (!SpeechRecognition) {
      setError('Voice conversation is not supported in this browser. Please use Chrome or Edge.');
      setVoiceState('error');
      return;
    }
    sessionActiveRef.current = true;
    turnInProgressRef.current = false;
    setVoiceSessionActive(true);
    setHasInteracted(true);
    setVoiceState('listening');
    startRecognition();
  }

  function stopConversation() {
    sessionActiveRef.current = false;
    turnInProgressRef.current = false;
    requestIdRef.current += 1;
    speechGenerationRef.current += 1;
    window.clearTimeout(retryTimerRef.current);
    stopRecognition();
    window.speechSynthesis?.cancel();
    setVoiceSessionActive(false);
    setVoiceState('idle');
    setHasInteracted(false);
    setError('');
    setDraft('');
    setLoading(false);
  }

  function askAbout(area) {
    setDraft(`What information is available about ${area}?`);
    document.getElementById('question-input')?.focus();
  }

  const stateCopy = {
    idle: { title: 'Welcome to KIET AI Assistant', subtitle: 'How can I help you today?', detail: 'Ask about academics, programs, admissions, rules, syllabus, notices and more.' },
    listening: { title: 'Listening...', subtitle: 'Speak naturally to continue.', detail: 'I’m ready for your question.' },
    processing: { title: 'Thinking...', subtitle: 'Finding information from KIET sources.', detail: 'Please wait while I prepare an answer.' },
    speaking: { title: 'Speaking...', subtitle: 'Here is your answer.', detail: 'Your microphone is paused while I speak.' },
    error: { title: 'Let’s try that again', subtitle: 'The voice session needs attention.', detail: 'You can retry or type your question below.' },
  }[voiceState];
  const visibleVoiceState = voiceState === 'processing' ? 'THINKING' : voiceState.toUpperCase();

  return (
    <div className="site-shell">
      <div className="utility-bar">
        <div className="utility-inner">
          <span className="utility-label">KIET DEEMED TO BE UNIVERSITY</span>
          <div className="utility-links">{utilityLinks.map((link) => <a key={link.label} href={link.href} target="_blank" rel="noreferrer">{link.label}</a>)}</div>
        </div>
      </div>

      <header className="site-header">
        <a className="institution-brand" href="https://www.kiet.edu/" target="_blank" rel="noreferrer" aria-label="KIET Deemed to be University website">
          {!logoFailed && <img src={LOGO_URL} alt="KIET Deemed to be University" onError={() => setLogoFailed(true)} />}
          {logoFailed && <span className="brand-fallback"><strong>KIET</strong><small>DEEMED TO BE UNIVERSITY</small></span>}
        </a>
        <nav className="main-navigation" aria-label="KIET website navigation">{siteLinks.map((link) => <a key={link.label} href={link.href} target="_blank" rel="noreferrer">{link.label}<span>↗</span></a>)}</nav>
        <a className="header-action" href="#assistant">Ask KIET AI <span>↓</span></a>
      </header>

      <main>
        <section className="intro-band">
          <div className="content-width">
            <div className="breadcrumb"><a href="https://www.kiet.edu/" target="_blank" rel="noreferrer">Home</a><span>/</span><strong>KIET AI Assistant</strong></div>
            <div className="intro-copy">
              <div className="intro-mark" aria-hidden="true"><span>KIET</span><b>AI</b></div>
              <div><div className="section-kicker"><span /> STUDENT INFORMATION ASSISTANT</div><h1>KIET AI Assistant</h1><p>Your voice-first guide to information available from KIET sources.</p></div>
            </div>
          </div>
        </section>

        <section className="content-width assistant-section" id="assistant">
          <section className={`assistant-card voice-assistant-card ${voiceSessionActive ? 'session-active' : ''}`} aria-labelledby="assistant-title" aria-busy={loading}>
            <div className="assistant-card-head">
              <div className="assistant-card-title"><span className="title-emblem">K<span>AI</span></span><div><p className="mini-kicker">KIET AI</p><h2 id="assistant-title">College Information Assistant</h2></div></div>
              <span className={`status-label ${voiceState === 'listening' ? 'status-listening' : ''}`}><i />{visibleVoiceState}</span>
            </div>

            <section className={`voice-stage state-${voiceState}`} aria-live="polite" aria-label={`Assistant ${voiceState}`}>
              <div className={`assistant-orb ${voiceState === 'listening' || voiceState === 'speaking' ? 'orb-active' : ''}`}><AssistantStateIcon state={voiceState} /></div>
              <h2>{stateCopy.title}</h2>
              <p className="stage-subtitle">{stateCopy.subtitle}</p>
              <p className="stage-detail">{stateCopy.detail}</p>
              {error && <p className="error-message stage-error" role="alert"><b>Unable to continue</b>{error}</p>}
              {voiceSessionActive ? (
                <button className="session-button stop-session" onClick={stopConversation}><span className="stop-square" />Stop Conversation</button>
              ) : (
                <button className="session-button start-session" onClick={startConversation}><MicrophoneIcon />Start Conversation</button>
              )}
            </section>

            {!hasInteracted && !voiceSessionActive && (
              <div className="welcome-topics" aria-label="Information topics">
                <span>Explore KIET information</span><div>{['Academics', 'Programs', 'Admissions', 'Syllabus', 'Notices'].map((area) => <button key={area} onClick={() => askAbout(area)}>{area}</button>)}</div>
              </div>
            )}

            {hasInteracted && messages.length > 0 && (
              <div className="conversation" aria-live="polite">
                {messages.map((message, index) => (
                  <article className={`message ${message.role}`} key={`${index}-${message.role}`}>
                    <span className="message-label">{message.role === 'user' ? 'YOU' : 'KIET AI'}</span>
                    {message.role === 'assistant' ? <AssistantAnswer text={message.text} /> : <p>{message.text}</p>}
                    {message.role === 'assistant' && <div className="answer-actions"><div className="source-list" aria-label="Answer sources">{selectRelevantSources(message.question, message.sources, message.toolSources).map((source) => <span className="source-chip" key={`${source.url || source.document}-${source.page ?? 'none'}`}>▤ {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.document}</a> : source.document}{source.page ? ` · p. ${source.page}` : ''}</span>)}</div>
                      {!voiceSessionActive && <button onClick={() => speak(message.text, { forVoiceSession: false })} aria-label="Read answer aloud" title="Read answer aloud"><span>◖))</span></button>}
                    </div>}
                    {message.role === 'assistant' && message.responseType === 'no_information' && (
                      <HumanEscalation category={message.escalationCategory} question={message.question} answer={message.text} sources={selectRelevantSources(message.question, message.sources, message.toolSources)} voiceSessionActive={voiceSessionActive} />
                    )}
                  </article>
                ))}
              </div>
            )}

            <div className="typed-question">
              <label htmlFor="question-input">{voiceSessionActive ? 'Voice conversation is active' : 'Or type your question'}</label>
              <form className="question-form" onSubmit={(event) => { event.preventDefault(); void submitQuestion(); }}>
                <input id="question-input" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about KIET…" aria-label="Your question" disabled={voiceSessionActive} />
                <button type="submit" disabled={!draft.trim() || voiceSessionActive || loading} aria-label="Send question" title="Send question"><span>➜</span></button>
              </form>
              {loading && !voiceSessionActive && <p className="loading-row" role="status"><span className="loader" aria-hidden="true" />Checking KIET sources…</p>}
            </div>
            <p className="privacy-note">KIET information assistant · Prototype</p>
          </section>
        </section>
      </main>

      <footer className="site-footer"><div className="content-width footer-inner"><div className="footer-brand"><span>KIET <b>AI</b></span><small>Deemed to be University</small></div><p>College Information Assistant <span>·</span> MCA CA1 Prototype</p><a href="https://www.kiet.edu/" target="_blank" rel="noreferrer">Visit kiet.edu ↗</a></div></footer>
    </div>
  );
}

export default App;
