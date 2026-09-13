import { useState, useEffect, useRef, useMemo } from 'react';
import { toJpeg } from 'html-to-image';
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
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon,
  ArrowUpDown,
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
  formatEraName,
} from './i18n';

const STORAGE_KEY_OWNED = 'vanner_collected_cards';
const STORAGE_KEY_WANTED = 'vanner_wanted_cards';
const SUBMISSION_FORM_URL = import.meta.env.VITE_FORM_URL || 'https://forms.gle/iTWDSb1ddmCRPBiV7';
const CARDS_PER_PAGE = 30;

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
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest');
  const [showBothLabeled, setShowBothLabeled] = useState<boolean>(false);
  const [isDark, setIsDark] = useState<boolean>(() => {
    return localStorage.getItem('theme') !== 'light';
  });

  const [currentLang, setCurrentLang] = useState<Language>(getInitialLanguage);
  const t = I18N[currentLang];

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedMembers, setSelectedMembers] = useState<Set<string>>(new Set(['All']));
  const [selectedEra, setSelectedEra] = useState<string>('All');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [previewCard, setPreviewCard] = useState<Photocard | null>(null);
  const [exportedImageUrl, setExportedImageUrl] = useState<string | null>(null);

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
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }, [isDark]);

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
    setCurrentPage(1);
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

  // Base filtered list based on metadata filters (Member, Era, Category, Search Query) - ignoring showBothLabeled for stats calculation
  const baseFilteredCards = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const filtered = cards.filter((card) => {
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
        localizedMember.includes(query);

      return matchMember && matchEra && matchCat && matchSearch;
    });

    return filtered.sort((a, b) => {
      if (sortOrder === 'newest') {
        return cards.indexOf(b) - cards.indexOf(a);
      } else {
        return cards.indexOf(a) - cards.indexOf(b);
      }
    });
  }, [cards, selectedMembers, selectedEra, selectedCategory, searchQuery, currentLang, sortOrder]);

  const filteredStats = useMemo(() => {
    let haveCount = 0;
    let wantCount = 0;
    baseFilteredCards.forEach((card) => {
      if (ownedCards.has(card.id)) haveCount++;
      if (wantedCards.has(card.id)) wantCount++;
    });
    return {
      have: haveCount,
      want: wantCount,
      total: baseFilteredCards.length,
    };
  }, [baseFilteredCards, ownedCards, wantedCards]);

  // Final displayed cards after applying showBothLabeled filter
  const filteredCards = useMemo(() => {
    return baseFilteredCards.filter((card) => {
      const matchBothLabeled =
        !showBothLabeled || (ownedCards.has(card.id) || wantedCards.has(card.id));
      return matchBothLabeled;
    });
  }, [baseFilteredCards, showBothLabeled, ownedCards, wantedCards]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedEra, selectedCategory, showBothLabeled]);

  const totalPages = Math.ceil(filteredCards.length / CARDS_PER_PAGE) || 1;

  const paginatedCards = useMemo(() => {
    const start = (currentPage - 1) * CARDS_PER_PAGE;
    return filteredCards.slice(start, start + CARDS_PER_PAGE);
  }, [filteredCards, currentPage]);

  const handleExport = async () => {
    if (!templateRef.current) return;
    setIsExporting(true);
    try {
      // Ensure all images in the hidden template are fully loaded before capturing
      const images = Array.from(templateRef.current.querySelectorAll('img'));
      await Promise.all(
        images.map((img) => {
          if (img.complete && img.naturalHeight !== 0) return Promise.resolve();
          return new Promise((resolve) => {
            img.onload = resolve;
            img.onerror = resolve;
            // Timeout fallback after 3 seconds in case an image fails
            setTimeout(resolve, 3000);
          });
        })
      );

      const dataUrl = await toJpeg(templateRef.current, {
        cacheBust: true,
        pixelRatio: 1.5,
        backgroundColor: isDark ? '#09090b' : '#ffffff',
        quality: 0.90,
      });

      const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

      if (isMobile) {
        setExportedImageUrl(dataUrl);
      } else {
        const link = document.createElement('a');
        link.download = `vvs-archive-page-${currentPage}-${new Date().toISOString().slice(0, 10)}.jpg`;
        link.href = dataUrl;
        link.click();
      }
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const ThemeToggle = () => (
    <button
      onClick={() => setIsDark(!isDark)}
      className={`p-2 rounded-xl transition border cursor-pointer ${
        isDark 
          ? 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/60 border-neutral-800' 
          : 'text-neutral-600 hover:text-black hover:bg-neutral-100 border-neutral-200'
      }`}
      title="Toggle Theme"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );

  return (
    <div className={`min-h-screen w-full ${isDark ? 'bg-neutral-950 text-neutral-100' : 'bg-neutral-50 text-neutral-900'} pb-16 selection:bg-indigo-500 selection:text-white flex flex-col items-center transition-colors`}>
      <header className={`sticky top-0 z-30 w-full ${isDark ? 'bg-neutral-950/90 border-neutral-800/80' : 'bg-white/90 border-neutral-200'} backdrop-blur-md border-b px-3 sm:px-8 py-3 shadow-md transition-colors`}>
        <div className="max-w-7xl mx-auto w-full flex flex-col gap-2.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className={`flex h-8 w-8 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-xl border p-1.5 shadow-sm ${isDark ? 'bg-neutral-900 border-neutral-800' : 'bg-white border-neutral-200'}`}>
                <img
                  src={`${import.meta.env.BASE_URL}VVS_logo.svg`}
                  alt="VVS Logo"
                  className="h-full w-full object-contain"
                />
              </div>
              <div className="min-w-0">
                <h1 className={`text-xs sm:text-lg font-black tracking-wider leading-tight uppercase truncate ${isDark ? 'text-neutral-100' : 'text-neutral-900'}`}>
                  {t.title}
                </h1>
                <p className="text-[10px] sm:text-[11px] text-neutral-500 font-medium truncate hidden sm:block">
                  {t.subtitle}
                </p>
              </div>
            </div>

            <button
              onClick={handleExport}
              disabled={isExporting || loading}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 text-white text-xs font-bold rounded-xl hover:bg-indigo-500 active:scale-98 disabled:opacity-50 transition shadow-sm shadow-indigo-600/30 shrink-0 cursor-pointer"
            >
              <Download className="h-4 w-4" />
              <span>{isExporting ? t.exporting : t.export}</span>
            </button>
          </div>
          
          <div className="flex items-center justify-between gap-2 pt-2 border-t border-neutral-200/60 dark:border-neutral-800/80">
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <button
                onClick={() => setSortOrder((prev) => (prev === 'newest' ? 'oldest' : 'newest'))}
                className={`p-2 rounded-xl border transition cursor-pointer flex items-center justify-center ${
                  sortOrder === 'oldest'
                    ? isDark ? 'bg-neutral-700 border-neutral-600 text-neutral-100 shadow-xs' : 'bg-neutral-800 border-neutral-700 text-white shadow-xs'
                    : isDark 
                      ? 'bg-neutral-900 border-neutral-800 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800' 
                      : 'bg-white border-neutral-200 text-neutral-600 hover:text-black hover:bg-neutral-100'
                }`}
                title={`Sort: ${sortOrder}`}
              >
                <ArrowUpDown className="h-4 w-4" />
              </button>
            </div>

            <div className="flex items-center gap-2">
              <div
                onClick={() => setShowBothLabeled(!showBothLabeled)}
                className={`flex items-center gap-1.5 border px-3 py-1.5 rounded-full text-[11px] sm:text-xs font-semibold cursor-pointer transition-colors ${
                  showBothLabeled
                    ? isDark ? 'bg-neutral-800 border-neutral-600 text-neutral-100 shadow-sm' : 'bg-neutral-200 border-neutral-400 text-neutral-900 shadow-sm'
                    : isDark ? 'bg-neutral-900 border-neutral-800 text-neutral-300' : 'bg-white border-neutral-200 text-neutral-700 shadow-xs'
                }`}
                title="Toggle filter for labeled cards"
              >
                <span className="flex items-center gap-1 text-indigo-500">
                  <Check className="h-3 w-3 stroke-[3]" /> {filteredStats.have}
                </span>
                <span className={isDark ? 'text-neutral-700' : 'text-neutral-300'}>|</span>
                <span className="flex items-center gap-1 text-rose-500">
                  <Heart className="h-3 w-3 fill-current" /> {filteredStats.want}
                </span>
                <span className={isDark ? 'text-neutral-700' : 'text-neutral-300'}>/</span>
                <span className="font-medium">
                  {filteredStats.total}
                </span>
              </div>

              <button
                onClick={handleReset}
                title="Reset"
                className={`p-2 rounded-xl transition border cursor-pointer flex items-center justify-center ${isDark ? 'text-neutral-400 hover:text-red-400 hover:bg-neutral-800/60 border-neutral-800' : 'text-neutral-600 hover:text-red-600 hover:bg-neutral-100 border-neutral-200'}`}
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl w-full mx-auto px-3 sm:px-8 pt-4 sm:pt-6">
        <div className={`backdrop-blur-sm p-3.5 sm:p-5 rounded-2xl border shadow-sm mb-6 flex flex-col gap-3 transition-colors ${isDark ? 'bg-neutral-900/70 border-neutral-800/90' : 'bg-white/80 border-neutral-200'}`}>
          
          <div className="flex items-center gap-2 w-full">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
              <input
                type="text"
                placeholder={t.searchPlaceholder}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={`w-full rounded-xl border py-2 pl-9 pr-4 text-xs sm:text-sm transition focus:outline-none focus:ring-1 focus:ring-indigo-500/30 ${
                  isDark 
                    ? 'border-neutral-800 bg-neutral-950/60 text-neutral-100 placeholder-neutral-500 focus:border-indigo-500 focus:bg-neutral-950' 
                    : 'border-neutral-200 bg-neutral-50 text-neutral-900 placeholder-neutral-400 focus:border-indigo-500 focus:bg-white'
                }`}
              />
            </div>

            {(!selectedMembers.has('All') || selectedEra !== 'All' || selectedCategory !== 'All' || searchQuery.trim() !== '') && (
              <button
                onClick={() => {
                  setSelectedMembers(new Set(['All']));
                  setSelectedEra('All');
                  setSelectedCategory('All');
                  setSearchQuery('');
                }}
                className={`inline-flex items-center justify-center p-2 rounded-xl text-xs font-semibold transition cursor-pointer shrink-0 ${isDark ? 'bg-neutral-800 hover:bg-neutral-700 text-neutral-300' : 'bg-neutral-200 hover:bg-neutral-300 text-neutral-700'}`}
                title="Clear Filters"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span className="text-[11px] font-bold text-neutral-500 uppercase w-16 shrink-0">
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
                      : isDark ? 'bg-neutral-800/80 text-neutral-300 hover:bg-neutral-700/80 hover:text-white' : 'bg-neutral-200 text-neutral-700 hover:bg-neutral-300 hover:text-black';
                  }
                  const name = memberKey.toLowerCase();
                  if (name.includes('taehwan') || name.includes('泰煥') || name.includes('고태운') || name.includes('테환')) {
                    return active
                      ? 'bg-red-600 text-white shadow-xs shadow-red-600/30'
                      : isDark ? 'bg-red-950/40 border border-red-900/60 text-red-300 hover:bg-red-900/50 hover:text-white' : 'bg-red-50 border border-red-200 text-red-700 hover:bg-red-100';
                  }
                  if (name.includes('hyesung') || name.includes('慧成') || name.includes('혜성')) {
                    return active
                      ? 'bg-amber-600 text-white shadow-xs shadow-amber-600/30'
                      : isDark ? 'bg-amber-950/40 border border-amber-900/60 text-amber-300 hover:bg-amber-900/50 hover:text-white' : 'bg-amber-50 border border-amber-200 text-amber-700 hover:bg-amber-100';
                  }
                  if (name.includes('sungkook') || name.includes('成國') || name.includes('성국')) {
                    return active
                      ? 'bg-purple-600 text-white shadow-xs shadow-purple-600/30'
                      : isDark ? 'bg-purple-950/40 border border-purple-900/60 text-purple-300 hover:bg-purple-900/50 hover:text-white' : 'bg-purple-50 border border-purple-200 text-purple-700 hover:bg-purple-100';
                  }
                  return active
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : isDark ? 'bg-neutral-800/80 text-neutral-300 hover:bg-neutral-700/80 hover:text-white' : 'bg-neutral-200 text-neutral-700 hover:bg-neutral-300';
                };

                return (
                  <button
                    key={m}
                    onClick={() => toggleMember(m)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${getFilterButtonStyle(m, isSelected)}`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {eras.length > 1 && (
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="text-[11px] font-bold text-neutral-500 uppercase w-16 shrink-0">{t.era}</span>
              <div className="flex flex-wrap gap-1.5">
                {eras.map((e) => (
                  <button
                    key={e}
                    onClick={() => setSelectedEra(e)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                      selectedEra === e
                        ? isDark ? 'bg-neutral-100 text-neutral-900 font-bold shadow-xs' : 'bg-neutral-900 text-white font-bold shadow-xs'
                        : isDark ? 'bg-neutral-800/80 text-neutral-300 hover:bg-neutral-700/80 hover:text-white' : 'bg-neutral-200 text-neutral-700 hover:bg-neutral-300 hover:text-black'
                    }`}
                  >
                    {e === 'All' ? t.all : formatEraName(e, currentLang)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {categories.length > 1 && (
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="text-[11px] font-bold text-neutral-500 uppercase w-16 shrink-0">{t.category}</span>
              <div className="flex flex-wrap gap-1.5">
                {categories.map((c) => (
                  <button
                    key={c}
                    onClick={() => setSelectedCategory(c)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                      selectedCategory === c
                        ? isDark ? 'bg-neutral-100 text-neutral-900 font-bold shadow-xs' : 'bg-neutral-900 text-white font-bold shadow-xs'
                        : isDark ? 'bg-neutral-800/80 text-neutral-300 hover:bg-neutral-700/80 hover:text-white' : 'bg-neutral-200 text-neutral-700 hover:bg-neutral-300 hover:text-black'
                    }`}
                  >
                    {c === 'All' ? t.all : c}
                  </button>
                ))}
              </div>
            </div>
          )}

        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-28 text-neutral-400">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-500 mb-3" />
            <p className="text-sm font-semibold">{t.loading}</p>
          </div>
        ) : filteredCards.length === 0 ? (
          <div className={`rounded-2xl border p-12 text-center text-neutral-400 ${isDark ? 'bg-neutral-900/50 border-neutral-800/80' : 'bg-white border-neutral-200 shadow-xs'}`}>
            <p className="text-sm font-medium">{t.noCards}</p>
          </div>
        ) : (
          <>
            <div className={`p-3 sm:p-6 rounded-2xl border shadow-sm grid grid-cols-3 sm:grid-cols-5 gap-2 sm:gap-4 transition-colors ${isDark ? 'bg-neutral-900/60 border-neutral-800' : 'bg-white border-neutral-200'}`}>
              {paginatedCards.map((card) => {
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
                        ? 'border-2 border-indigo-500 ring-4 ring-indigo-500/20 shadow-xl shadow-indigo-500/10 -translate-y-1'
                        : isWanted
                        ? 'border-2 border-rose-500 ring-4 ring-rose-500/20 shadow-xl shadow-rose-500/10 -translate-y-1'
                        : isDark ? 'border border-neutral-800 bg-neutral-900/90 hover:border-neutral-700 hover:shadow-lg' : 'border border-neutral-200 bg-white hover:border-neutral-300 hover:shadow-md'
                    }`}
                  >
                    <div className={`aspect-[55/85] w-full relative overflow-hidden ${isDark ? 'bg-neutral-950' : 'bg-neutral-100'}`}>
                      {imgSrc ? (
                        <img
                          src={imgSrc}
                          alt={card.name}
                          crossOrigin="anonymous"
                          loading="lazy"
                          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-neutral-400 text-xs">
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
                        className={`absolute top-1.5 left-1.5 sm:top-2 sm:left-2 z-10 flex h-6 w-6 sm:h-7 sm:w-7 items-center justify-center rounded-full transition-all active:scale-90 cursor-pointer ${
                          isOwned
                            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/50 scale-105'
                            : 'bg-black/60 text-neutral-300 hover:text-white hover:bg-black/80 backdrop-blur-xs border border-white/10'
                        }`}
                      >
                        <Check className="h-3.5 w-3.5 sm:h-4 sm:w-4 stroke-[3]" />
                      </button>

                      <button
                        type="button"
                        title="Want"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleWant(card.id);
                        }}
                        className={`absolute top-1.5 right-1.5 sm:top-2 sm:right-2 z-10 flex h-6 w-6 sm:h-7 sm:w-7 items-center justify-center rounded-full transition-all active:scale-90 cursor-pointer ${
                          isWanted
                            ? 'bg-rose-600 text-white shadow-lg shadow-rose-600/50 scale-105'
                            : 'bg-black/60 text-neutral-300 hover:text-rose-400 hover:bg-black/80 backdrop-blur-xs border border-white/10'
                        }`}
                      >
                        <Heart className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${isWanted ? 'fill-current' : ''}`} />
                      </button>
                    </div>

                    <div
                      className={`p-1.5 sm:p-2.5 flex flex-col flex-1 justify-between transition-colors ${
                        isOwned
                          ? isDark ? 'bg-indigo-950/30 border-t border-indigo-900/50' : 'bg-indigo-50 border-t border-indigo-100'
                          : isWanted
                          ? isDark ? 'bg-rose-950/30 border-t border-rose-900/50' : 'bg-rose-50 border-t border-rose-100'
                          : isDark ? 'bg-neutral-900 border-t border-neutral-800/80' : 'bg-white border-t border-neutral-200'
                      }`}
                    >
                      <p
                        className={`text-[11px] sm:text-xs font-bold truncate ${
                          isOwned
                            ? isDark ? 'text-indigo-200' : 'text-indigo-900'
                            : isWanted
                            ? isDark ? 'text-rose-200' : 'text-rose-900'
                            : isDark ? 'text-neutral-200' : 'text-neutral-800'
                        }`}
                        title={card.name}
                      >
                        {card.name}
                      </p>
                      <div className="flex justify-between items-center text-[9px] sm:text-[10px] text-neutral-500 mt-0.5 sm:mt-1">
                        <span className="truncate pr-1 font-medium">{displayMember}</span>
                        {cardCat && (
                          <span
                            className={`shrink-0 px-1 py-0.2 sm:px-1.5 sm:py-0.5 rounded font-medium ${
                              isOwned
                                ? isDark ? 'bg-indigo-950 text-indigo-300 border border-indigo-800/60' : 'bg-indigo-100 text-indigo-800 border border-indigo-200'
                                : isWanted
                                ? isDark ? 'bg-rose-950 text-rose-300 border border-rose-800/60' : 'bg-rose-100 text-rose-800 border border-rose-200'
                                : isDark ? 'bg-neutral-800 text-neutral-400 border border-neutral-700/50' : 'bg-neutral-100 text-neutral-600 border border-neutral-200'
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

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3 mt-6">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                  disabled={currentPage === 1}
                  className={`p-2 rounded-xl border transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
                    isDark
                      ? 'bg-neutral-900 border-neutral-800 text-neutral-300 hover:bg-neutral-800'
                      : 'bg-white border-neutral-200 text-neutral-700 hover:bg-neutral-100'
                  }`}
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs font-semibold text-neutral-400">
                  {currentPage} / {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className={`p-2 rounded-xl border transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
                    isDark
                      ? 'bg-neutral-900 border-neutral-800 text-neutral-300 hover:bg-neutral-800'
                      : 'bg-white border-neutral-200 text-neutral-700 hover:bg-neutral-100'
                  }`}
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </>
        )}
      </main>

      <div className="absolute left-[-9999px] top-[-9999px] w-[1200px] overflow-hidden pointer-events-none opacity-0">
        <div
          ref={templateRef}
          className={`p-6 rounded-2xl border flex flex-col gap-4 w-[1200px] ${isDark ? 'bg-neutral-900 border-neutral-800 text-neutral-100' : 'bg-white border-neutral-200 text-neutral-900'}`}
        >
          <div className={`flex items-center justify-between border-b pb-4 px-1 ${isDark ? 'border-neutral-800' : 'border-neutral-200'}`}>
            <div className="flex flex-col gap-1">
              <h2 className="text-base font-black tracking-wider uppercase">
              {t.title} - CHECKLIST {totalPages > 1 && `(${currentPage}/${totalPages})`}
              </h2>
              <div className="flex items-center gap-2 text-xs text-neutral-500 font-medium">
                <span>
                  {t.member}: {selectedMembers.has('All') ? t.all : Array.from(selectedMembers).map(m => formatMemberName(m, currentLang)).join(', ')}
                </span>
                <span>•</span>
                <span>{t.era}: {selectedEra === 'All' ? t.all : formatEraName(selectedEra, currentLang)}</span>
                <span>•</span>
                <span>{t.category}: {selectedCategory === 'All' ? t.all : selectedCategory}</span>
                {searchQuery && <><span>•</span><span>Keyword: "{searchQuery}"</span></>}
              </div>
            </div>
            <div className={`flex items-center gap-2 border px-4 py-2 rounded-full text-xs font-semibold ${isDark ? 'bg-neutral-950 border-neutral-800' : 'bg-neutral-100 border-neutral-200'}`}>
              <span className="flex items-center gap-1 text-indigo-500">
                <Check className="h-3.5 w-3.5 stroke-[3]" /> Have: {paginatedCards.filter(c => ownedCards.has(c.id)).length}
              </span>
              <span className={isDark ? 'text-neutral-700' : 'text-neutral-300'}>|</span>
              <span className="flex items-center gap-1 text-rose-500">
                <Heart className="h-3.5 w-3.5 fill-current" /> Want: {paginatedCards.filter(c => wantedCards.has(c.id)).length}
              </span>
              <span className={isDark ? 'text-neutral-700' : 'text-neutral-300'}>/</span>
              <span className="font-medium">{paginatedCards.length}</span>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-4">
            {paginatedCards.map((card) => {
              const isOwned = ownedCards.has(card.id);
              const isWanted = wantedCards.has(card.id);
              const imgSrc = formatImageUrl(card.imageUrl || (card as any).photo);
              const cardCat = card.category || (card as any).catagory;
              const displayMember = formatMultiMemberString(card.member, currentLang);

              return (
                <div
                  key={`export-${card.id}`}
                  className={`flex flex-col rounded-xl overflow-hidden ${
                    isOwned
                      ? 'border-2 border-indigo-500 ring-4 ring-indigo-500/25'
                      : isWanted
                      ? 'border-2 border-rose-500 ring-4 ring-rose-500/25'
                      : isDark ? 'border border-neutral-800 bg-neutral-900' : 'border border-neutral-200 bg-white'
                  }`}
                >
                  <div className={`aspect-[55/85] w-full relative overflow-hidden ${isDark ? 'bg-neutral-950' : 'bg-neutral-100'}`}>
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
                        ? isDark ? 'bg-indigo-950/30 border-t border-indigo-900/50 text-indigo-200' : 'bg-indigo-50 border-t border-indigo-100 text-indigo-900'
                        : isWanted
                        ? isDark ? 'bg-rose-950/30 border-t border-rose-900/50 text-rose-200' : 'bg-rose-50 border-t border-rose-100 text-rose-900'
                        : isDark ? 'bg-neutral-900 border-t border-neutral-800 text-neutral-200' : 'bg-white border-t border-neutral-200 text-neutral-800'
                    }`}
                  >
                    <p className="text-xs font-bold truncate">{card.name}</p>
                    <div className="flex justify-between items-center text-[10px] text-neutral-500 mt-1">
                      <span className="truncate pr-1 font-medium">{displayMember}</span>
                      {cardCat && <span className={`shrink-0 px-1.5 py-0.5 rounded ${isDark ? 'bg-neutral-800 text-neutral-400' : 'bg-neutral-100 text-neutral-600'}`}>{cardCat}</span>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <footer className={`mt-16 w-full border-t py-12 text-center text-xs transition-colors ${isDark ? 'border-neutral-800/80 bg-neutral-950 text-neutral-500' : 'border-neutral-200 bg-white text-neutral-600'}`}>
        <div className="max-w-7xl w-full mx-auto px-4 flex flex-col items-center gap-8">
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
                  className={`flex items-center gap-2 rounded-xl border px-3 py-2 transition active:scale-98 shadow-xs ${isDark ? 'border-neutral-800/90 bg-neutral-900/80 text-neutral-300 hover:border-neutral-700 hover:bg-neutral-800 hover:text-white' : 'border-neutral-200 bg-neutral-50 text-neutral-700 hover:border-neutral-300 hover:bg-neutral-100 hover:text-black'}`}
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
                    <span className={`font-bold text-sm leading-none shrink-0 ${isDark ? 'text-neutral-200' : 'text-neutral-800'}`}>𝕏</span>
                  )}

                  <div className="text-left leading-tight">
                    <p className={`text-xs font-bold ${isDark ? 'text-neutral-200' : 'text-neutral-900'}`}>{item.label}</p>
                    <p className="text-[10px] text-neutral-400">{item.subLabel}</p>
                  </div>
                </a>
              ))}
            </div>
          </div>

          <div className={`flex flex-wrap items-center justify-center gap-3 pt-2 border-t w-full max-w-md ${isDark ? 'border-neutral-900' : 'border-neutral-200'}`}>
            <div className={`flex items-center rounded-lg border p-1 text-xs ${isDark ? 'border-neutral-800 bg-neutral-900' : 'border-neutral-200 bg-neutral-100'}`}>
              <Globe className="h-3.5 w-3.5 text-neutral-400 ml-1.5 mr-1" />
              {(['en', 'zh', 'ko'] as const).map((lang) => (
                <button
                  key={lang}
                  onClick={() => setCurrentLang(lang)}
                  className={`rounded-md px-2.5 py-1 font-semibold transition cursor-pointer ${
                    currentLang === lang
                      ? isDark ? 'bg-neutral-800 text-white shadow-xs' : 'bg-white text-black shadow-xs'
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
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 border text-xs font-semibold rounded-lg transition active:scale-98 ${isDark ? 'border-neutral-700 bg-neutral-900 hover:bg-neutral-800 hover:text-white text-neutral-300' : 'border-neutral-300 bg-neutral-100 hover:bg-neutral-200 hover:text-black text-neutral-700'}`}
            >
              <ExternalLink className="h-3.5 w-3.5 text-neutral-400" />
              <span>{t.contribute}</span>
            </a>
          </div>

          <div>
            <p className={`font-medium ${isDark ? 'text-neutral-400' : 'text-neutral-700'}`}>
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
            className={`relative flex flex-col items-center max-w-xs w-full border rounded-2xl p-4 shadow-2xl ${isDark ? 'bg-neutral-900 border-neutral-800 text-neutral-100' : 'bg-white border-neutral-200 text-neutral-900'}`}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setPreviewCard(null)}
              className={`absolute right-3 top-3 rounded-full p-1.5 transition ${isDark ? 'text-neutral-400 hover:bg-neutral-800 hover:text-neutral-100' : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'}`}
            >
              <X className="h-4 w-4" />
            </button>

            <div className={`aspect-[55/85] w-full rounded-xl overflow-hidden border shadow-inner mt-2 ${isDark ? 'border-neutral-800 bg-neutral-950' : 'border-neutral-200 bg-neutral-100'}`}>
              <img
                src={formatImageUrl(previewCard.imageUrl || (previewCard as any).photo)}
                alt={previewCard.name}
                className="w-full h-full object-cover"
              />
            </div>

            <div className="w-full mt-3.5 text-left">
              <h3 className="text-sm font-bold truncate mb-2">{previewCard.name}</h3>
              
              <div className="flex flex-wrap gap-1.5 text-[11px]">
                {previewCard.era && (
                  <span className={`rounded border px-2 py-0.5 font-medium ${isDark ? 'bg-neutral-800/60 border-neutral-700/60 text-neutral-400' : 'bg-neutral-100 border-neutral-200 text-neutral-600'}`}>
                    {formatEraName(previewCard.era, currentLang)}
                  </span>
                )}
                {(previewCard.category || (previewCard as any).catagory) && (
                  <span className={`rounded border px-2 py-0.5 font-medium ${isDark ? 'bg-neutral-800 border-neutral-700 text-neutral-300' : 'bg-neutral-100 border-neutral-200 text-neutral-800'}`}>
                    {previewCard.category || (previewCard as any).catagory}
                  </span>
                )}
              </div>

              <div className={`mt-4 pt-3 border-t flex gap-2 ${isDark ? 'border-neutral-800' : 'border-neutral-200'}`}>
                <button
                  onClick={() => toggleHave(previewCard.id)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold transition active:scale-95 cursor-pointer ${
                    ownedCards.has(previewCard.id)
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                      : isDark ? 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700' : 'bg-neutral-200 text-neutral-800 hover:bg-neutral-300'
                  }`}
                >
                  <Check className="h-4 w-4 stroke-[2.5]" />
                  <span>{t.have}</span>
                </button>
                <button
                  onClick={() => toggleWant(previewCard.id)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold transition active:scale-95 cursor-pointer ${
                    wantedCards.has(previewCard.id)
                      ? 'bg-rose-600 text-white shadow-md shadow-rose-600/30'
                      : isDark ? 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700' : 'bg-neutral-200 text-neutral-800 hover:bg-neutral-300'
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

      {exportedImageUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 animate-in fade-in"
          onClick={() => setExportedImageUrl(null)}
        >
          <div
            className={`relative flex flex-col items-center max-w-sm w-full border rounded-2xl p-4 shadow-2xl ${isDark ? 'bg-neutral-900 border-neutral-800 text-neutral-100' : 'bg-white border-neutral-200 text-neutral-900'}`}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setExportedImageUrl(null)}
              className={`absolute right-3 top-3 rounded-full p-1.5 transition ${isDark ? 'text-neutral-400 hover:bg-neutral-800 hover:text-neutral-100' : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'}`}
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-sm font-bold mb-2">{t.longPressSave}</h3>

            <div className={`w-full overflow-hidden rounded-xl border shadow-inner p-2 flex items-center justify-center ${isDark ? 'border-neutral-800 bg-neutral-950' : 'border-neutral-200 bg-neutral-100'}`}>
              <img
                src={exportedImageUrl}
                alt="Exported Checklist"
                className="max-h-[60vh] w-auto object-contain rounded-lg"
              />
            </div>

            <button
              onClick={() => setExportedImageUrl(null)}
              className={`mt-4 w-full py-2 text-xs font-bold rounded-xl transition cursor-pointer ${isDark ? 'bg-neutral-800 hover:bg-neutral-700 text-neutral-200' : 'bg-neutral-200 hover:bg-neutral-300 text-neutral-800'}`}
            >
              {t.close}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}