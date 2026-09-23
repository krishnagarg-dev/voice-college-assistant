const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function askAssistant(message) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
  } catch {
    throw new Error('Could not reach the KIET assistant service. Check that the backend is running, then try again.');
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(response.status === 400
      ? 'Please check your question and try again.'
      : 'The KIET assistant is temporarily unavailable. Please try again shortly.');
  }
  if (typeof data.answer !== 'string' || !data.answer.trim()) {
    throw new Error('The assistant returned an empty answer.');
  }
  return data;
}
