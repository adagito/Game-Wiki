/**
 * Reusable Global Omni-Search engine.
 * Game modules register typed entity records:
 *   { id, type, typeLabel, title, subtitle, keywords, route }
 */
export class OmniSearch {
  constructor() {
    this.entities = [];
    this.scopeLabel = 'Hub';
  }

  clear(scopeLabel = 'Hub') {
    this.entities = [];
    this.scopeLabel = scopeLabel;
  }

  registerEntities(items) {
    for (const item of items) {
      this.entities.push({
        ...item,
        _haystack: `${item.title || ''} ${item.id || ''} ${item.subtitle || ''} ${item.keywords || ''}`.toLowerCase()
      });
    }
  }

  query(term, limit = 40) {
    const q = String(term || '').trim().toLowerCase();
    if (!q) return [];
    const tokens = q.split(/\s+/).filter(Boolean);
    const scored = [];

    for (const entry of this.entities) {
      let allMatch = true;
      for (const tok of tokens) {
        if (!entry._haystack.includes(tok)) {
          allMatch = false;
          break;
        }
      }
      if (!allMatch) continue;

      const titleLower = (entry.title || '').toLowerCase();
      const idLower = (entry.id || '').toLowerCase();
      let score = 10;
      if (idLower === q || titleLower === q) score = 100;
      else if (titleLower.startsWith(q) || idLower.startsWith(q)) score = 75;
      else if (titleLower.includes(q)) score = 50;

      scored.push({ entry, score });
    }

    scored.sort((a, b) => b.score - a.score || a.entry.title.localeCompare(b.entry.title));
    return scored.slice(0, limit).map((s) => s.entry);
  }
}
