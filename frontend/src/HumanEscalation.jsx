import React, { useEffect, useRef, useState } from 'react';
import { cleanAssistantText } from './assistantText.js';

const configuredNumber = String(import.meta.env.VITE_ADMISSIONS_WHATSAPP_NUMBER || '').replace(/\D/g, '');
const whatsappAvailable = /^91[6-9]\d{9}$/.test(configuredNumber);

function isIndianMobileNumber(value) {
  const digits = value.replace(/\D/g, '');
  const mobile = digits.length === 12 && digits.startsWith('91') ? digits.slice(2) : digits;
  return /^[6-9]\d{9}$/.test(mobile);
}

function EscalationDialog({ mode, category, question, answer, sources, onClose }) {
  const [form, setForm] = useState({ name: '', phone: '', programme: '', preferredTime: '', message: question || '' });
  const [phoneError, setPhoneError] = useState('');
  const [formMessage, setFormMessage] = useState('');
  const dialogRef = useRef(null);
  const phoneRef = useRef(null);
  const department = category === 'admissions' ? 'KIET Admissions' : 'the KIET team';
  const [waMessage, setWaMessage] = useState(() => [
    `Hello ${department === 'KIET Admissions' ? 'Admissions' : 'KIET'} Team,`,
    '',
    'Question:', String(question || '').slice(0, 1200),
    '',
    'KIET AI Assistant response:', cleanAssistantText(answer || '').slice(0, 1200),
    ...(sources.length ? ['', 'Official KIET sources:', ...sources.filter((source) => source.url).map((source) => `- ${source.document}: ${source.url}`)] : []),
    '', 'Please help me with this query.',
  ].join('\n').slice(0, 4096));
  const whatsappHref = whatsappAvailable
    ? `https://wa.me/${configuredNumber}?text=${encodeURIComponent(waMessage)}`
    : undefined;

  useEffect(() => {
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const panel = dialogRef.current;
    const focusable = () => panel?.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled])') || [];
    focusable()[0]?.focus();
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      } else if (event.key === 'Tab') {
        const items = Array.from(focusable());
        if (!items.length) return;
        if (event.shiftKey && document.activeElement === items[0]) {
          event.preventDefault();
          items.at(-1).focus();
        } else if (!event.shiftKey && document.activeElement === items.at(-1)) {
          event.preventDefault();
          items[0].focus();
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus?.();
    };
  }, [onClose]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    if (field === 'phone' && phoneError) setPhoneError('');
    if (formMessage) setFormMessage('');
  }

  function handleRequestCall(event) {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    if (!form.name.trim() || !form.programme.trim() || !form.preferredTime) {
      setFormMessage('Complete each required field to continue.');
      return;
    }
    if (!isIndianMobileNumber(form.phone)) {
      setPhoneError('Enter a valid Indian mobile number (10 digits, optionally preceded by +91).');
      phoneRef.current?.focus();
      return;
    }
    setFormMessage('Counsellor request integration is not configured yet. Your details have not been sent or saved.');
  }

  return (
    <div className="escalation-overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="escalation-dialog" role="dialog" aria-modal="true" aria-labelledby="escalation-dialog-title" ref={dialogRef}>
        <button className="dialog-close" type="button" onClick={onClose} aria-label="Close dialog">×</button>
        {mode === 'whatsapp' ? (
          <>
            <p className="dialog-kicker">KIET AI ASSISTANT</p>
            <h2 id="escalation-dialog-title">Continue on WhatsApp</h2>
            <p className="dialog-intro">Review or edit the message before opening WhatsApp. It will open as a draft; you choose whether to send it.</p>
            <label className="whatsapp-message-label" htmlFor="whatsapp-message">Message preview</label>
            <textarea id="whatsapp-message" className="whatsapp-preview" rows="10" maxLength={4096} value={waMessage} onChange={(event) => setWaMessage(event.target.value)} />
            <div className="dialog-actions">
              <button type="button" className="secondary-action" onClick={onClose}>Cancel</button>
              {whatsappHref && <a className="primary-action" href={whatsappHref} target="_blank" rel="noopener noreferrer">Open WhatsApp draft ↗</a>}
            </div>
            <p className="dialog-privacy">This opens a WhatsApp draft. You decide whether to send it there.</p>
          </>
        ) : (
          <>
            <p className="dialog-kicker">KIET AI ASSISTANT</p>
            <h2 id="escalation-dialog-title">{category === 'admissions' ? 'Talk to a KIET Admission Counsellor' : 'Connect with the KIET team'}</h2>
            <p className="dialog-intro">Share your preferred contact details. This prototype does not transmit or save them.</p>
            <form className="counsellor-form" onSubmit={handleRequestCall}>
              <label>Full Name <span>Required</span><input name="name" autoComplete="name" required maxLength={100} value={form.name} onChange={(event) => updateField('name', event.target.value)} /></label>
              <label>Mobile Number <span>Required</span><input ref={phoneRef} name="phone" type="tel" inputMode="tel" autoComplete="tel" aria-invalid={Boolean(phoneError)} aria-describedby={phoneError ? 'phone-error' : undefined} required maxLength={18} value={form.phone} onChange={(event) => updateField('phone', event.target.value)} placeholder="10-digit number or +91" />{phoneError && <small id="phone-error" className="field-error" role="alert">{phoneError}</small>}</label>
              <label>Programme / Course Interested In <span>Required</span><input name="programme" required maxLength={120} value={form.programme} onChange={(event) => updateField('programme', event.target.value)} /></label>
              <label>Preferred Contact Time <span>Required</span><select name="preferredTime" required value={form.preferredTime} onChange={(event) => updateField('preferredTime', event.target.value)}><option value="">Select a preference</option><option value="morning">Morning</option><option value="afternoon">Afternoon</option><option value="evening">Evening</option><option value="any">Any time</option></select></label>
              <label className="message-field">Message / Question <small>Optional</small><textarea name="message" rows="3" maxLength={1000} value={form.message} onChange={(event) => updateField('message', event.target.value)} /></label>
              {formMessage && <p className="form-notice" role="status">{formMessage}</p>}
              <div className="dialog-actions"><button type="button" className="secondary-action" onClick={onClose}>Cancel</button><button type="submit" className="primary-action">Review Request</button></div>
            </form>
            <p className="dialog-privacy">No request is sent or saved until a KIET contact integration is configured.</p>
          </>
        )}
      </section>
    </div>
  );
}

export default function HumanEscalation({ category = 'general', question = '', answer = '', sources = [], voiceSessionActive = false }) {
  const [dialogMode, setDialogMode] = useState(null);
  const closeDialog = () => setDialogMode(null);
  const admission = category === 'admissions';

  return (
    <>
      <section className="human-escalation" aria-label="Human support options">
        <div className="escalation-copy">
          <h3>{admission ? 'Need help with admission?' : 'Need more help?'}</h3>
          <p>{admission ? 'Connect with a KIET Admission Counsellor.' : 'Connect with the KIET team for further guidance.'}</p>
        </div>
        <div className="escalation-actions">
          <button type="button" className="primary-action" onClick={() => setDialogMode('request')}>
            <span aria-hidden="true">☎</span> {admission ? 'Talk to an Admission Counsellor' : 'Contact the KIET team'}
          </button>
          <div className="whatsapp-action-wrap">
            <button type="button" className="whatsapp-action" disabled={!whatsappAvailable} onClick={() => setDialogMode('whatsapp')}>
              <span aria-hidden="true">◉</span> Continue on WhatsApp
            </button>
            {!whatsappAvailable && <small>WhatsApp contact is not configured.</small>}
          </div>
        </div>
        {!voiceSessionActive && <button type="button" className="ask-another-action" onClick={() => document.getElementById('question-input')?.focus()}>Ask another question</button>}
      </section>
      {dialogMode && <EscalationDialog mode={dialogMode} category={category} question={question} answer={answer} sources={sources} onClose={closeDialog} />}
    </>
  );
}
