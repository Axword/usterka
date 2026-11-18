import { afterEach, describe, expect, it, vi } from 'vitest';
import { fmtDate, todayISO } from './dates';
import { clamp, dueLabel, isFixed, safeName, typeLabel } from './defects';
import { clearDraft, loadDraft, saveDraft, type DefectDraft } from './draft';

describe('dates', () => {
  it('formats ISO dates as DD.MM.YYYY', () => {
    expect(fmtDate('2026-11-17')).toBe('17.11.2026');
    expect(fmtDate('2026-11-17T10:00:00Z')).toBe('17.11.2026');
  });
  it('returns empty text for missing dates', () => {
    expect(fmtDate(null)).toBe('');
    expect(fmtDate(undefined)).toBe('');
  });
  it('todayISO returns a local YYYY-MM-DD date', () => {
    expect(todayISO()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe('defects helpers', () => {
  it('detects fixed defects', () => {
    expect(isFixed({ status: 'fixed' })).toBe(true);
    expect(isFixed({ status: 'open' })).toBe(false);
  });
  it('shows the clarification only for type "Inna"', () => {
    expect(typeLabel({ type: 'Inna', type_other: 'Okna' })).toBe('Inna (Okna)');
    expect(typeLabel({ type: 'Inna', type_other: '' })).toBe('Inna');
    expect(typeLabel({ type: 'Budowlana', type_other: 'x' })).toBe('Budowlana');
  });
  it('labels the due date', () => {
    expect(dueLabel({ due_mode: 'umowa', due_date: null })).toBe('Zgodnie z umową');
    expect(dueLabel({ due_mode: 'data', due_date: '2026-12-01' })).toBe('01.12.2026');
  });
  it('clamps values', () => {
    expect([clamp(5, 0, 1), clamp(-5, 0, 1), clamp(0.5, 0, 1)]).toEqual([1, 0, 0.5]);
  });
  it('builds safe file names', () => {
    expect(safeName('Osiedle: A/B "test"')).toBe('Osiedle_AB_test');
    expect(safeName('///')).toBe('projekt');
    expect(safeName('x'.repeat(200))).toHaveLength(80);
  });
});

describe('draft storage', () => {
  const draft: DefectDraft = {
    projectId: 'p', planId: 'l', defectId: null, no: null, type: 'Budowlana', typeOther: '', desc: 'opis',
    dueMode: 'umowa', dueDate: '', zoom: 0.3, x: 0.5, y: 0.5, fixedDate: '', savedAt: 1,
  };
  afterEach(() => vi.unstubAllGlobals());

  const memoryStorage = () => {
    const data = new Map<string, string>();
    return {
      getItem: (k: string) => data.get(k) ?? null,
      setItem: (k: string, v: string) => void data.set(k, v),
      removeItem: (k: string) => void data.delete(k),
    };
  };

  it('saves, loads and clears the draft', () => {
    vi.stubGlobal('localStorage', memoryStorage());
    expect(loadDraft()).toBeNull();
    saveDraft(draft);
    expect(loadDraft()).toEqual(draft);
    clearDraft();
    expect(loadDraft()).toBeNull();
  });
  it('survives a broken storage', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => '{zepsute',
      setItem: () => { throw new Error('quota'); },
      removeItem: () => {},
    });
    expect(() => saveDraft(draft)).not.toThrow();
    expect(loadDraft()).toBeNull();
  });
});
