import { useState, useEffect, useRef, useMemo } from 'react';
import { toPng } from 'html-to-image';
import {
  Check,
  Heart,
  Download,
  RotateCcw,
  Loader2,
  Search,
  X,
  ExternalLink,
  Globe,
} from 'lucide-react';
import type { Photocard } from './types/card';
import {
  type Language,
  STORAGE_KEY_LANG,
  getInitialLanguage,
  I18N,
  parseMembers,
  formatMemberName,
  formatMultiMemberString,
} from './i18n';

const STORAGE_KEY_OWNED = 'vanner_collected_cards';
const STORAGE_KEY_WANTED = 'vanner_wanted_cards';
const SUBMISSION_FORM_URL = import.meta.env.VITE_FORM_URL || 'https://forms.gle/iTWDSb1ddmCRPBiV7';

interface SocialLinkItem {
  label: string;
  subLabel: string;
  url: string;
  platform: 'youtube' | 'x' | 'instagram';
}

const SOCIAL_LINKS: SocialLinkItem[] = [
  {
    label: '혜성국',
    subLabel: '@HyesungKook',
    url: 'http://x.com/HyesungKook',
    platform: 'x',
  },
  {
    label: '뭐혜성국',
    subLabel: 'YouTube',
    url: 'https://www.youtube.com/channel/UCLfafqmR8Ku3_8ZCarWxYIQ',
    platform: 'youtube',
  },
  {
    label: '박혜성 𝗣𝗮𝗿𝗸 𝗛𝘆𝗲 𝗦𝘂𝗻𝗴',
    subLabel: '@phey._.s',
    url: 'http://instagram.com/phey._.s',
    platform: 'instagram',
  },
  {
    label: '성국',
    subLabel: '@_sungkook',
    url: 'http://x.com/_sungkook',
    platform: 'x',
  },
  {
    label: '성국 Sungkook',
    subLabel: '@imtjdrnr',
    url: 'https://www.instagram.com/imtjdrnr',
    platform: 'instagram',
  },
  {
    label: '고태운',
    subLabel: '@kotaewoon_',
    url: 'https://x.com/kotaewoon_',
    platform: 'x',
  },
  {
    label: '고태운',
    subLabel: '@ofwoon',
    url: 'https://www.instagram.com/ofwoon',
    platform: 'instagram',
  },
];

const getMemberBadgeColor = (memberName: string) => {
  const name = memberName.toLowerCase();
  if (name.includes('taehwan') || name.includes('泰煥') || name.includes('고태운')) {
    return 'bg-red-950/70 border-red-800 text-red-300';
  }
  if (name.includes('hyesung') || name.includes('慧成') || name.includes('박혜성')) {
    return 'bg-amber-950/70 border-amber-800 text-amber-300';
  }
  if (name.includes('sungkook') || name.includes('成國')) {
    return 'bg-purple-950/70 border-purple-800 text-purple-300';
  }
  return 'bg-indigo-950/70 border-indigo-800 text-indigo-300';
};

const formatImageUrl = (url?: string): string => {
  if (!url) return '';

  if (url.startsWith('./') || url.startsWith('cards/')) {
    const cleanPath = url.replace(/^\.\/?/, '');
    return `${import.meta.env.BASE_URL}${cleanPath}`;
  }

  const matchDrive = url.match(/(?:id=|\/d\/)([a-zA-Z0-9_-]+)/);
  if (matchDrive && matchDrive[1]) {
    const directUrl = `https://lh3.googleusercontent.com/d/${matchDrive[1]}`;
    return `https://wsrv.nl/?url=${encodeURIComponent(directUrl)}`;
  }

  if (url.includes('twimg.com') || url.includes('twitter.com')) {
    return `https://wsrv.nl/?url=${encodeURIComponent(url)}`;
  }

  return url;
};

export default function App() {
  const [cards, setCards] = useState<Photocard[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const [currentLang, setCurrentLang] = useState<Language>(getInitialLanguage);
  const t = I18N[currentLang];

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedMembers, setSelectedMembers] = useState<Set<string>>(new Set(['All']));
  const [selectedEra, setSelectedEra] = useState<string>('All');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [previewCard, setPreviewCard] = useState<Photocard | null>(null);

  const [ownedCards, setOwnedCards] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_OWNED);
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });

  const [wantedCards, setWantedCards] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_WANTED);
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    const loadCards = async () => {
      try {
        const response = await fetch(`${import.meta.env.BASE_URL}cards.json?t=${Date.now()}`);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        const data: Photocard[] = await response.json();
        if (isMounted) {
          setCards(data.filter((c) => c.id && c.name));
        }
      } catch (err) {
        console.error('Failed to load cards.json:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadCards();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_OWNED, JSON.stringify(Array.from(ownedCards)));
  }, [ownedCards]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_WANTED, JSON.stringify(Array.from(wantedCards)));
  }, [wantedCards]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_LANG, currentLang);
  }, [currentLang]);

  const templateRef = useRef<HTMLDivElement>(null);

  const memberList = useMemo(() => {
    const extracted = new Set<string>();
    cards.forEach((card) => {
      parseMembers(card.member).forEach((m) => extracted.add(m));
    });
    return ['All', ...Array.from(extracted)];
  }, [cards]);

  const eras = useMemo(() => ['All', ...Array.from(new Set(cards.map((c) => c.era).filter(Boolean)))], [cards]);
  const categories = useMemo(() => {
    const extracted = new Set(cards.map((c) => c.category || (c as any).catagory).filter(Boolean));
    return ['All', ...Array.from(extracted)];
  }, [cards]);

  const toggleMember = (member: string) => {
    setSelectedMembers((prev) => {
      const next = new Set(prev);
      if (member === 'All') return new Set(['All']);

      next.delete('All');
      if (next.has(member)) {
        next.delete(member);
        if (next.size === 0) return new Set(['All']);
      } else {
        next.add(member);
      }
      return next;
    });
  };

  const toggleHave = (id: string) => {
    setOwnedCards((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        setWantedCards((wPrev) => {
          const wNext = new Set(wPrev);
          wNext.delete(id);
          return wNext;
        });
      }
      return next;
    });
  };

  const toggleWant = (id: string) => {
    setWantedCards((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        setOwnedCards((oPrev) => {
          const oNext = new Set(oPrev);
          oNext.delete(id);
          return oNext;
        });
      }
      return next;
    });
  };

  const handleReset = () => {
    if (window.confirm(t.resetConfirm)) {
      setOwnedCards(new Set());
      setWantedCards(new Set());
    }
  };

  const filteredCards = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return cards.filter((card) => {
      const cardMembers = parseMembers(card.member);
      const cardCat = card.category || (card as any).catagory || '';

      const matchMember =
        selectedMembers.has('All') || cardMembers.some((m) => selectedMembers.has(m));

      const matchEra = selectedEra === 'All' || card.era === selectedEra;
      const matchCat = selectedCategory === 'All' || cardCat === selectedCategory;

      const localizedMember = formatMultiMemberString(card.member, currentLang).toLowerCase();
      const matchSearch =
        !query ||
        card.name.toLowerCase().includes(query) ||
        card.id.toLowerCase().includes(query) ||
        card.member.toLowerCase().includes(query) ||
        localizedMember.includes(query);

      return matchMember && matchEra && matchCat && matchSearch;
    });
  }, [cards, selectedMembers, selectedEra, selectedCategory, searchQuery, currentLang]);

  const filteredStats = useMemo(() => {
    let haveCount = 0;
    let wantCount = 0;
    filteredCards.forEach((card) => {
      if (ownedCards.has(card.id)) haveCount++;
      if (wantedCards.has(card.id)) wantCount++;
    });
    return {
      have: haveCount,
      want: wantCount,
      total: filteredCards.length,
    };
  }, [filteredCards, ownedCards, wantedCards]);

  const handleExport = async () => {
    if (!templateRef.current) return;
    setIsExporting(true);
    try {
      const dataUrl = await toPng(templateRef.current, {
        cacheBust: true,
        pixelRatio: 2,
        backgroundColor: '#09090b',
      });

      const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

      if (isMobile) {
        const newWindow = window.open();
        if (newWindow) {
          newWindow.document.write(`
            <html>
              <head><title>VVS Archive Export</title></head>
              <body style="margin:0; background:#09090b; display:flex; justify-content:center; align-items:center; height:100vh;">
                <img src="${dataUrl}" style="max-width:100%; max-height:100%; object-fit:contain;" alt="Exported Checklist" />
              </body>
            </html>
          `);
          newWindow.document.close();
        } else {
          window.location.href = dataUrl;
        }
      } else {
        const link = document.createElement('a');
        link.download = `vvs-archive-${new Date().toISOString().slice(0, 10)}.png`;
        link.href = dataUrl;
        link.click();
      }
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 pb-16 selection:bg-indigo-500 selection:text-white">
      <header className="sticky top-0 z-30 bg-neutral-950/80 backdrop-blur-md border-b border-neutral-800/80 px-4 sm:px-8 py-3.5 shadow-md">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-neutral-900 border border-neutral-800 p-1.5 shadow-sm">
              <img
                src={`${import.meta.env.BASE_URL}VVS_logo.svg`}
                alt="VVS Logo"
                className="h-full w-full object-contain"
              />
            </div>
            <div>
              <h1 className="text-base sm:text-lg font-black tracking-wider text-neutral-100 leading-tight uppercase">
                {t.title}
              </h1>
              <p className="text-[11px] text-neutral-400 font-medium hidden sm:block">
                {t.subtitle}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 self-end sm:self-auto">
            <div className="flex items-center gap-2 bg-neutral-900 border border-neutral-800 px-3.5 py-1.5 rounded-full text-xs font-semibold">
              <span className="flex items-center gap-1 text-indigo-400">
                <Check className="h-3 w-3 stroke-[3]" /> Have: {filteredStats.have}
              </span>
              <span className="text-neutral-700">|</span>
              <span className="flex items-center gap-1 text-rose-400">
                <Heart className="h-3 w-3 fill-current" /> Want: {filteredStats.want}
              </span>
              <span className="text-neutral-700">/</span>
              <span className="text-neutral-400 font-medium">{filteredStats.total}</span>
            </div>

            <button
              onClick={handleReset}
              title="Reset"
              className="p-2 text-neutral-400 hover:text-red-400 hover:bg-neutral-800/60 rounded-lg transition border border-transparent hover:border-neutral-700"
            >
              <RotateCcw className="h-4 w-4" />
            </button>

            <button
              onClick={handleExport}
              disabled={isExporting || loading}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-600 text-white text-xs font-bold rounded-lg hover:bg-indigo-500 active:scale-98 disabled:opacity-50 transition shadow-sm shadow-indigo-600/30"
            >
              <Download className="h-3.5 w-3.5" />
              {isExporting ? t.exporting : t.export}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-8 pt-6">
        <div className="bg-neutral-900/70 backdrop-blur-sm p-4 sm:p-5 rounded-2xl border border-neutral-800/90 shadow-sm mb-6 flex flex-col gap-3.5">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
            <input
              type="text"
              placeholder={t.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-neutral-800 bg-neutral-950/60 py-2 pl-9 pr-4 text-xs sm:text-sm text-neutral-100 placeholder-neutral-500 focus:border-indigo-500 focus:bg-neutral-950 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span className="text-[11px] font-bold text-neutral-400 uppercase w-16 shrink-0">
              {t.member} {selectedMembers.has('All') ? '' : `(${selectedMembers.size})`}
            </span>
            <div className="flex flex-wrap gap-1.5">
              {memberList.map((m) => {
                const isSelected = selectedMembers.has(m);
                const label = m === 'All' ? t.all : formatMemberName(m, currentLang);
                
                const getFilterButtonStyle = (memberKey: string, active: boolean) => {
                  if (memberKey === 'All') {
                    return active
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'bg-neutral-800/80 text-neutral-300 hover:bg-neutral-700/80 hover:text-white';
                  }
                  const name = memberKey.toLowerCase();
                  if (name.includes('taehwan') || name.includes('泰煥') || name.includes('고태운')) {
                    return active
                      ? 'bg-red-600 text-white shadow-xs shadow-red-600/30'
                      : 'bg-red-950/40 border border-red-900/60 text-red-300 hover:bg-red-900/50 hover:text-white';
                  }
                  if (name.includes('hyesung') || name.includes('慧成') || name.includes('박혜성')) {
                    return active
                      ? 'bg-amber-600 text-white shadow-xs shadow-amber-600/30'
                      : 'bg-amber-950/40 border border-amber-900/60 text-amber-300 hover:bg-amber-900/50 hover:text-white';
                  }
                  if (name.includes('sungkook') || name.includes('成國')) {
                    return active
                      ? 'bg-purple-600 text-white shadow-xs shadow-purple-600/30'
                      : 'bg-purple-950/40 border border-purple-900/60 text-purple-300 hover:bg-purple-900/50 hover:text-white';
                  }
                  return active
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-neutral-800/80 text-neutral-300 hover:bg-neutral-700/80 hover:text-white';
                };

                return (
                  <button
                    key={m}
                    onClick={() => toggleMember(m)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${getFilterButtonStyle(m, isSelected)}`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {eras.length > 1 && (
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="text-[11px] font-bold text-neutral-400 uppercase w-16 shrink-0">{t.era}</span>
              <div className="flex flex-wrap gap-1.5">
                {eras.map((e) => (
                  <button
                    key={e}
                    onClick={() => setSelectedEra(e)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                      selectedEra === e
                        ? 'bg-neutral-100 text-neutral-900 font-bold shadow-xs'
                        : 'bg-neutral-800/80 text-neutral-300 hover:bg-neutral-700/80 hover:text-white'
                    }`}
                  >
                    {e === 'All' ? t.all : e}
                  </button>
                ))}
              </div>
            </div>
          )}

          {categories.length > 1 && (
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="text-[11px] font-bold text-neutral-400 uppercase w-16 shrink-0">{t.category}</span>
              <div className="flex flex-wrap gap-1.5">
                {categories.map((c) => (
                  <button
                    key={c}
                    onClick={() => setSelectedCategory(c)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                      selectedCategory === c
                        ? 'bg-neutral-100 text-neutral-900 font-bold shadow-xs'
                        : 'bg-neutral-800/80 text-neutral-300 hover:bg-neutral-700/80 hover:text-white'
                    }`}
                  >
                    {c === 'All' ? t.all : c}
                  </button>
                ))}
              </div>
            </div>
          )}

          {(!selectedMembers.has('All') || selectedEra !== 'All' || selectedCategory !== 'All' || searchQuery.trim() !== '') && (
            <div className="flex justify-end pt-2 border-t border-neutral-800/80">
              <button
                onClick={() => {
                  setSelectedMembers(new Set(['All']));
                  setSelectedEra('All');
                  setSelectedCategory('All');
                  setSearchQuery('');
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-semibold transition"
              >
                <X className="h-3.5 w-3.5" />
                <span>Clear Filters</span>
              </button>
            </div>
          )}
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-28 text-neutral-500">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-500 mb-3" />
            <p className="text-sm font-semibold">{t.loading}</p>
          </div>
        ) : filteredCards.length === 0 ? (
          <div className="bg-neutral-900/50 rounded-2xl border border-neutral-800/80 p-12 text-center text-neutral-500">
            <p className="text-sm font-medium">{t.noCards}</p>
          </div>
        ) : (
          <div className="bg-neutral-900/60 p-4 sm:p-6 rounded-2xl border border-neutral-800 shadow-sm grid grid-cols-2 sm:grid-cols-5 gap-3 sm:gap-4">
            {filteredCards.map((card) => {
              const isOwned = ownedCards.has(card.id);
              const isWanted = wantedCards.has(card.id);
              const imgSrc = formatImageUrl(card.imageUrl || (card as any).photo);
              const cardCat = card.category || (card as any).catagory;
              const displayMember = formatMultiMemberString(card.member, currentLang);

              return (
                <div
                  key={card.id}
                  onClick={() => setPreviewCard(card)}
                  className={`group relative flex flex-col rounded-xl overflow-hidden cursor-pointer select-none transition-all duration-200 ${
                    isOwned
                      ? 'border-2 border-indigo-500 ring-4 ring-indigo-500/20 shadow-xl shadow-indigo-500/10 bg-neutral-900 -translate-y-1'
                      : isWanted
                      ? 'border-2 border-rose-500 ring-4 ring-rose-500/20 shadow-xl shadow-rose-500/10 bg-neutral-900 -translate-y-1'
                      : 'border border-neutral-800 bg-neutral-900/90 hover:border-neutral-700 hover:shadow-lg'
                  }`}
                >
                  <div className="aspect-[55/85] w-full bg-neutral-950 relative overflow-hidden">
                    {imgSrc ? (
                      <img
                        src={imgSrc}
                        alt={card.name}
                        crossOrigin="anonymous"
                        loading="lazy"
                        className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-neutral-600 text-xs">
                        {t.noImage}
                      </div>
                    )}

                    <button
                      type="button"
                      title="Have"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleHave(card.id);
                      }}
                      className={`absolute top-2 left-2 z-10 flex h-7 w-7 items-center justify-center rounded-full transition-all active:scale-90 ${
                        isOwned
                          ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/50 scale-105'
                          : 'bg-black/60 text-neutral-400 hover:text-white hover:bg-black/80 backdrop-blur-xs border border-white/10'
                      }`}
                    >
                      <Check className="h-4 w-4 stroke-[3]" />
                    </button>

                    <button
                      type="button"
                      title="Want"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleWant(card.id);
                      }}
                      className={`absolute top-2 right-2 z-10 flex h-7 w-7 items-center justify-center rounded-full transition-all active:scale-90 ${
                        isWanted
                          ? 'bg-rose-600 text-white shadow-lg shadow-rose-600/50 scale-105'
                          : 'bg-black/60 text-neutral-400 hover:text-rose-400 hover:bg-black/80 backdrop-blur-xs border border-white/10'
                      }`}
                    >
                      <Heart className={`h-4 w-4 ${isWanted ? 'fill-current' : ''}`} />
                    </button>
                  </div>

                  <div
                    className={`p-2.5 flex flex-col flex-1 justify-between transition-colors ${
                      isOwned
                        ? 'bg-indigo-950/30 border-t border-indigo-900/50'
                        : isWanted
                        ? 'bg-rose-950/30 border-t border-rose-900/50'
                        : 'bg-neutral-900 border-t border-neutral-800/80'
                    }`}
                  >
                    <p
                      className={`text-xs font-bold truncate ${
                        isOwned
                          ? 'text-indigo-200'
                          : isWanted
                          ? 'text-rose-200'
                          : 'text-neutral-200'
                      }`}
                      title={card.name}
                    >
                      {card.name}
                    </p>
                    <div className="flex justify-between items-center text-[10px] text-neutral-400 mt-1">
                      <span className="truncate pr-1 font-medium text-neutral-400">{displayMember}</span>
                      {cardCat && (
                        <span
                          className={`shrink-0 px-1.5 py-0.5 rounded font-medium ${
                            isOwned
                              ? 'bg-indigo-950 text-indigo-300 border border-indigo-800/60'
                              : isWanted
                              ? 'bg-rose-950 text-rose-300 border border-rose-800/60'
                              : 'bg-neutral-800 text-neutral-400 border border-neutral-700/50'
                          }`}
                        >
                          {cardCat}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* 隱藏的 5 欄專屬匯出模板（包含篩選條件、計數器與完美 5 欄網格，供截圖使用） */}
      <div className="absolute -z-50 opacity-0 pointer-events-none left-0 top-0 overflow-hidden">
        <div
          ref={templateRef}
          className="bg-neutral-900 p-6 rounded-2xl border border-neutral-800 flex flex-col gap-4 w-[1200px]"
        >
          <div className="flex items-center justify-between border-b border-neutral-800 pb-4 px-1">
            <div className="flex flex-col gap-1">
              <h2 className="text-base font-black tracking-wider text-neutral-100 uppercase">
                {t.title} - CHECKLIST
              </h2>
              <div className="flex items-center gap-2 text-xs text-neutral-400 font-medium">
                <span>
                  {t.member}: {selectedMembers.has('All') ? t.all : Array.from(selectedMembers).map(m => formatMemberName(m, currentLang)).join(', ')}
                </span>
                <span>•</span>
                <span>{t.era}: {selectedEra === 'All' ? t.all : selectedEra}</span>
                <span>•</span>
                <span>{t.category}: {selectedCategory === 'All' ? t.all : selectedCategory}</span>
                {searchQuery && <><span>•</span><span>Keyword: "{searchQuery}"</span></>}
              </div>
            </div>
            <div className="flex items-center gap-2 bg-neutral-950 border border-neutral-800 px-4 py-2 rounded-full text-xs font-semibold">
              <span className="flex items-center gap-1 text-indigo-400">
                <Check className="h-3.5 w-3.5 stroke-[3]" /> Have: {filteredStats.have}
              </span>
              <span className="text-neutral-700">|</span>
              <span className="flex items-center gap-1 text-rose-400">
                <Heart className="h-3.5 w-3.5 fill-current" /> Want: {filteredStats.want}
              </span>
              <span className="text-neutral-700">/</span>
              <span className="text-neutral-300 font-medium">{filteredStats.total}</span>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-4">
            {filteredCards.map((card) => {
              const isOwned = ownedCards.has(card.id);
              const isWanted = wantedCards.has(card.id);
              const imgSrc = formatImageUrl(card.imageUrl || (card as any).photo);
              const cardCat = card.category || (card as any).catagory;
              const displayMember = formatMultiMemberString(card.member, currentLang);

              return (
                <div
                  key={`export-${card.id}`}
                  className={`flex flex-col rounded-xl overflow-hidden bg-neutral-900 ${
                    isOwned
                      ? 'border-2 border-indigo-500 ring-4 ring-indigo-500/25'
                      : isWanted
                      ? 'border-2 border-rose-500 ring-4 ring-rose-500/25'
                      : 'border border-neutral-800'
                  }`}
                >
                  <div className="aspect-[55/85] w-full bg-neutral-950 relative overflow-hidden">
                    {imgSrc && (
                      <img
                        src={imgSrc}
                        alt={card.name}
                        crossOrigin="anonymous"
                        className="w-full h-full object-cover"
                      />
                    )}
                    {isOwned && (
                      <div className="absolute top-2 left-2 flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-white shadow-lg">
                        <Check className="h-4 w-4 stroke-[3]" />
                      </div>
                    )}
                    {isWanted && (
                      <div className="absolute top-2 right-2 flex h-7 w-7 items-center justify-center rounded-full bg-rose-600 text-white shadow-lg">
                        <Heart className="h-4 w-4 fill-current" />
                      </div>
                    )}
                  </div>
                  <div
                    className={`p-2.5 flex flex-col flex-1 justify-between ${
                      isOwned
                        ? 'bg-indigo-950/30 border-t border-indigo-900/50 text-indigo-200'
                        : isWanted
                        ? 'bg-rose-950/30 border-t border-rose-900/50 text-rose-200'
                        : 'bg-neutral-900 border-t border-neutral-800 text-neutral-200'
                    }`}
                  >
                    <p className="text-xs font-bold truncate">{card.name}</p>
                    <div className="flex justify-between items-center text-[10px] text-neutral-400 mt-1">
                      <span className="truncate pr-1 font-medium">{displayMember}</span>
                      {cardCat && <span className="shrink-0 px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400">{cardCat}</span>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <footer className="mt-16 border-t border-neutral-800/80 bg-neutral-950 py-12 text-center text-xs text-neutral-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col items-center gap-8">
          <div className="flex flex-col items-center gap-3 w-full">
            <span className="text-[11px] font-bold text-neutral-400 uppercase tracking-wider">
              Members Links
            </span>
            <div className="flex flex-wrap items-center justify-center gap-2 max-w-2xl">
              {SOCIAL_LINKS.map((item) => (
                <a
                  key={`${item.platform}-${item.url}`}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 rounded-xl border border-neutral-800/90 bg-neutral-900/80 px-3 py-2 text-neutral-300 hover:border-neutral-700 hover:bg-neutral-800 hover:text-white transition active:scale-98 shadow-xs"
                >
                  {item.platform === 'youtube' && (
                    <svg className="h-4 w-4 fill-red-500 shrink-0" viewBox="0 0 24 24">
                      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                    </svg>
                  )}

                  {item.platform === 'instagram' && (
                    <svg
                      className="h-4 w-4 stroke-rose-400 shrink-0"
                      viewBox="0 0 24 24"
                      fill="none"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
                      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
                      <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
                    </svg>
                  )}

                  {item.platform === 'x' && (
                    <span className="font-bold text-sm leading-none text-neutral-200 shrink-0">𝕏</span>
                  )}

                  <div className="text-left leading-tight">
                    <p className="text-xs font-bold">{item.label}</p>
                    <p className="text-[10px] text-neutral-500">{item.subLabel}</p>
                  </div>
                </a>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2 border-t border-neutral-900 w-full max-w-md">
            <div className="flex items-center rounded-lg border border-neutral-800 bg-neutral-900 p-1 text-xs">
              <Globe className="h-3.5 w-3.5 text-neutral-500 ml-1.5 mr-1" />
              {(['en', 'zh', 'ko'] as const).map((lang) => (
                <button
                  key={lang}
                  onClick={() => setCurrentLang(lang)}
                  className={`rounded-md px-2.5 py-1 font-semibold transition ${
                    currentLang === lang
                      ? 'bg-neutral-800 text-white shadow-xs'
                      : 'text-neutral-400 hover:text-neutral-200'
                  }`}
                >
                  {lang === 'en' ? 'EN' : lang === 'zh' ? '繁中' : '한국어'}
                </button>
              ))}
            </div>

            <a
              href={SUBMISSION_FORM_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 border border-neutral-700 bg-neutral-900 hover:bg-neutral-800 hover:text-white text-neutral-300 text-xs font-semibold rounded-lg transition active:scale-98"
            >
              <ExternalLink className="h-3.5 w-3.5 text-neutral-400" />
              <span>{t.contribute}</span>
            </a>
          </div>

          <div>
            <p className="font-medium text-neutral-400">
              Copyright ⓒ 2026 VVS Archive
            </p>
            <p className="mt-1 text-[11px] text-neutral-500">
              {t.copyrightSub}
            </p>
          </div>
        </div>
      </footer>

      {previewCard && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 animate-in fade-in"
          onClick={() => setPreviewCard(null)}
        >
          <div
            className="relative flex flex-col items-center max-w-xs w-full bg-neutral-900 border border-neutral-800 rounded-2xl p-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setPreviewCard(null)}
              className="absolute right-3 top-3 rounded-full p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-neutral-100 transition"
            >
              <X className="h-4 w-4" />
            </button>

            <div className="aspect-[55/85] w-full rounded-xl overflow-hidden border border-neutral-800 bg-neutral-950 shadow-inner mt-2">
              <img
                src={formatImageUrl(previewCard.imageUrl || (previewCard as any).photo)}
                alt={previewCard.name}
                className="w-full h-full object-cover"
              />
            </div>

            <div className="w-full mt-3.5 text-left">
              <h3 className="text-sm font-bold text-neutral-100 truncate mb-2">{previewCard.name}</h3>
              
              <div className="flex flex-wrap gap-1.5 text-[11px]">
                <span className={`rounded border px-2 py-0.5 font-semibold ${getMemberBadgeColor(previewCard.member)}`}>
                  {formatMultiMemberString(previewCard.member, currentLang)}
                </span>
                {previewCard.era && (
                  <span className="rounded bg-neutral-800/60 border border-neutral-700/60 text-neutral-400 px-2 py-0.5 font-medium">
                    {previewCard.era}
                  </span>
                )}
                {(previewCard.category || (previewCard as any).catagory) && (
                  <span className="rounded bg-neutral-800 border border-neutral-700 text-neutral-300 px-2 py-0.5 font-medium">
                    {previewCard.category || (previewCard as any).catagory}
                  </span>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-neutral-800 flex gap-2">
                <button
                  onClick={() => toggleHave(previewCard.id)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold transition active:scale-95 ${
                    ownedCards.has(previewCard.id)
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                      : 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700'
                  }`}
                >
                  <Check className="h-4 w-4 stroke-[2.5]" />
                  <span>{t.have}</span>
                </button>
                <button
                  onClick={() => toggleWant(previewCard.id)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold transition active:scale-95 ${
                    wantedCards.has(previewCard.id)
                      ? 'bg-rose-600 text-white shadow-md shadow-rose-600/30'
                      : 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700'
                  }`}
                >
                  <Heart className={`h-4 w-4 ${wantedCards.has(previewCard.id) ? 'fill-current' : ''}`} />
                  <span>{t.want}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}