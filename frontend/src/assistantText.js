const META_INTRO = /^\s*(?:based on (?:the )?(?:provided|available) context|according to (?:the )?(?:provided|available) (?:context|information)|here is (?:the )?information|the provided context states|from the available sources)\s*[,.:;-]?\s*/i;

function unescapeMarkdown(text) {
  return text.replace(/\\([\\`*_{}\[\]()#+.!|>-])/g, '$1');
}

export function cleanAssistantText(text) {
  let cleaned = String(text ?? '')
    .replace(/\r\n?/g, '\n')
    .replace(/<\/?[a-z][^>]*>/gi, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'");
  cleaned = unescapeMarkdown(cleaned).replace(META_INTRO, '').trim();
  cleaned = cleaned.replace(/~~/g, '');
  return cleaned;
}

export function sanitizeTextForSpeech(text) {
  return cleanAssistantText(text)
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/(^|\n)[ \t]*\|?[ \t]*:?-{3,}(?:[ \t]*\|[ \t]*:?-{3,})+[ \t]*\|?[ \t]*(?=\n|$)/g, '$1')
    .replace(/(^|\n)[ \t]*\|?[ \t]*([^|\n]+(?:\|[^|\n]+)+)[ \t]*\|?[ \t]*(?=\n|$)/g, (_match, prefix, row) => `${prefix}${row.split('|').map((cell) => cell.trim()).join(', ')}`)
    .replace(/(^|\n)\s{0,3}#{1,6}\s*/g, '$1')
    .replace(/(^|\n)\s*>\s?/g, '$1')
    .replace(/(^|\n)\s*(?:[-+*]|\d+[.)])\s+/g, '$1')
    .replace(/\*\*|__|~~|[*_`#|\\]/g, '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .join('. ')
    .replace(/\s+/g, ' ')
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/([.!?])(?:\s*[.!?])+/g, '$1')
    .trim();
}

export function buildNoInformationSpeech(answer, category) {
  const nextStep = category === 'admissions'
    ? "You can connect with a KIET admission counsellor if you'd like."
    : "You can connect with the KIET team if you'd like.";
  return `${sanitizeTextForSpeech(answer)} ${nextStep}`.trim();
}

export function selectRelevantSources(question, ragSources = [], toolSources = []) {
  const normalized = String(question ?? '').toLowerCase();
  const sources = [
    ...ragSources,
    ...toolSources.map((source) => ({ document: source.name, url: source.url })),
  ];
  let allowed = null;
  let priority = [];
  if (/placement|placed|package|crpc|training|internship|iipc/.test(normalized)) {
    allowed = new Set(['placements']);
    if (/\bmca\b/.test(normalized)) allowed.add('programs');
    priority = /\bmca\b/.test(normalized) ? ['programs', 'placements'] : ['placements'];
  } else if (/admission|eligibility|entrance|scholarship|fee/.test(normalized)) {
    allowed = new Set(['admissions', 'fees', 'scholarships']);
    if (/\bmca\b/.test(normalized)) allowed.add('programs');
    priority = ['admissions', 'fees', 'scholarships', 'programs'];
  } else if (/program|programme|course/.test(normalized)) {
    allowed = new Set(['programs', 'admissions']);
    priority = ['programs', 'admissions'];
  }

  const selected = sources
    .filter((source) => source && source.document)
    .map((source) => {
      let url;
      let path = '';
      try {
        const parsed = new URL(source.url);
        path = parsed.pathname.toLowerCase();
        if (parsed.protocol === 'https:' && (parsed.hostname === 'kiet.edu' || parsed.hostname.endsWith('.kiet.edu'))) url = parsed.href;
      } catch { /* Keep the readable citation label without linking an invalid URL. */ }
      const title = String(source.document).toLowerCase();
      const category = String(source.category || (
        /placements\//.test(path) ? 'placements'
          : /scholarship/.test(path + title) ? 'scholarships'
            : /fee/.test(path + title) ? 'fees'
              : /admission/.test(path + title) ? 'admissions'
                : /program|mca|course/.test(path + title) ? 'programs' : ''
      )).toLowerCase();
      return { document: String(source.document), url, page: source.page, category };
    })
    .filter((source) => {
      if (!allowed || allowed.has(source.category)) {
        if (allowed?.has('programs') && /placement|placed|package|crpc|training|internship|iipc/.test(normalized) && /\bmca\b/.test(normalized)) {
          return source.category !== 'programs' || /mca/i.test(`${source.document} ${source.url || ''}`);
        }
        return true;
      }
      return false;
    })
    .sort((left, right) => {
      const leftPriority = priority.indexOf(String(left.category ?? '').toLowerCase());
      const rightPriority = priority.indexOf(String(right.category ?? '').toLowerCase());
      return (leftPriority < 0 ? priority.length : leftPriority) - (rightPriority < 0 ? priority.length : rightPriority);
    });

  const unique = [];
  const seen = new Set();
  for (const source of selected) {
    const key = source.url || source.document;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(source);
    if (unique.length === 3) break;
  }
  return unique;
}
