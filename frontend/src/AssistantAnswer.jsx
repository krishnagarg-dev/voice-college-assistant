import React from 'react';
import { cleanAssistantText } from './assistantText.js';

const INLINE_MARKDOWN = /\[([^\]]+)\]\(([^)\s]+)\)|\*\*(.+?)\*\*|__(.+?)__|\*([^*\n]+)\*|_([^_\n]+)_|`([^`]+)`/g;

function safeHref(value) {
  try {
    const baseUrl = typeof window === 'undefined' ? 'https://www.kiet.edu/' : window.location.href;
    const url = new URL(value, baseUrl);
    return url.protocol === 'https:' && (url.hostname === 'kiet.edu' || url.hostname.endsWith('.kiet.edu')) ? url.href : null;
  } catch {
    return null;
  }
}

function renderInline(text, keyPrefix) {
  text = text.replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1');
  const nodes = [];
  let lastIndex = 0;
  let match;
  INLINE_MARKDOWN.lastIndex = 0;
  while ((match = INLINE_MARKDOWN.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    const key = `${keyPrefix}-${match.index}`;
    if (match[1] !== undefined) {
      const href = safeHref(match[2]);
      nodes.push(href
        ? <a key={key} href={href} target="_blank" rel="noopener noreferrer">{match[1]}</a>
        : match[1]);
    } else if (match[3] !== undefined || match[4] !== undefined) {
      nodes.push(<strong key={key}>{match[3] ?? match[4]}</strong>);
    } else if (match[5] !== undefined || match[6] !== undefined) {
      nodes.push(<em key={key}>{match[5] ?? match[6]}</em>);
    } else {
      nodes.push(<code key={key}>{match[7]}</code>);
    }
    lastIndex = INLINE_MARKDOWN.lastIndex;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

export default function AssistantAnswer({ text }) {
  const lines = cleanAssistantText(text).split('\n');
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const rawLine = lines[index].trim();
    const line = rawLine.replace(/^>\s?/, '');
    if (!line) { index += 1; continue; }

    if (/^```/.test(line)) {
      const codeLines = [];
      index += 1;
      while (index < lines.length && !/^\s*```/.test(lines[index])) codeLines.push(lines[index++]);
      if (index < lines.length) index += 1;
      blocks.push(<pre className="assistant-code-block" key={`code-${index}`}><code>{codeLines.join('\n')}</code></pre>);
      continue;
    }

    if (/^(?:-{3,}|_{3,}|\*{3,})$/.test(line)) {
      blocks.push(<hr key={`rule-${index}`} />);
      index += 1;
      continue;
    }

    const cells = (value) => value.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim());
    const isTableRule = (value) => cells(value).length > 1 && cells(value).every((cell) => /^:?-{3,}:?$/.test(cell));
    if (line.includes('|') && index + 1 < lines.length && isTableRule(lines[index + 1].trim())) {
      const headers = cells(line);
      index += 2;
      const rows = [];
      while (index < lines.length && lines[index].trim().includes('|')) {
        rows.push(cells(lines[index]));
        index += 1;
      }
      blocks.push(<div className="assistant-table-scroll" role="region" aria-label="Answer data table" tabIndex="0" key={`table-${index}`}><table className="assistant-table"><thead><tr>{headers.map((cell, cellIndex) => <th scope="col" key={cellIndex}>{renderInline(cell, `table-head-${index}-${cellIndex}`)}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{headers.map((_, cellIndex) => <td key={cellIndex}>{renderInline(row[cellIndex] || '', `table-cell-${index}-${rowIndex}-${cellIndex}`)}</td>)}</tr>)}</tbody></table></div>);
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length, 4) + 1;
      const Tag = `h${level}`;
      blocks.push(<Tag key={`heading-${index}`}>{renderInline(heading[2], `heading-${index}`)}</Tag>);
      index += 1;
      continue;
    }

    const listItem = line.match(/^(?:[-+*]|\d+[.)])\s+(.+)$/);
    if (listItem) {
      const ordered = /^\d+[.)]/.test(line);
      const items = [];
      while (index < lines.length) {
        const item = lines[index].trim().match(/^(?:[-+*]|\d+[.)])\s+(.+)$/);
        if (!item || /^\d+[.)]/.test(lines[index].trim()) !== ordered) break;
        items.push(<li key={`item-${index}`}>{renderInline(item[1], `item-${index}`)}</li>);
        index += 1;
      }
      const List = ordered ? 'ol' : 'ul';
      blocks.push(<List key={`list-${index}`}>{items}</List>);
      continue;
    }

    const paragraphLines = [line];
    index += 1;
    while (index < lines.length && lines[index].trim() && !/^(?:#{1,6}\s+|[-+*]\s+|\d+[.)]\s+)/.test(lines[index].trim())) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    const paragraph = paragraphLines.join(' ');
    blocks.push(<p key={`paragraph-${index}`}>{renderInline(paragraph, `paragraph-${index}`)}</p>);
  }

  return <div className="assistant-answer">{blocks}</div>;
}
