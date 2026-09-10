import { useState, useEffect, useRef, useMemo } from 'react';
import { toPng } from 'html-to-image';
import { Check, Download, Layers, RotateCcw } from 'lucide-react';
import cardsData from './data/cards.json';
import type { Photocard } from './types/card';

const STORAGE_KEY = 'vanner_collected_cards';

export default function App() {
  const cards: Photocard[] = cardsData as Photocard[];
  const [selectedMember, setSelectedMember] = useState<string>('All');
  const [selectedEra, setSelectedEra] = useState<string>('All');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [isExporting, setIsExporting] = useState<boolean>(false);

  // Initialize owned cards from localStorage
  const [ownedCards, setOwnedCards] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });

  // Sync collection status to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(ownedCards)));
  }, [ownedCards]);

  const templateRef = useRef<HTMLDivElement>(null);

  // Dynamic filter values
  const members = useMemo(() => ['All', ...Array.from(new Set(cards.map((c) => c.member)))], [cards]);
  const eras = useMemo(() => ['All', ...Array.from(new Set(cards.map((c) => c.era)))], [cards]);
  const categories = useMemo(() => ['All', ...Array.from(new Set(cards.map((c) => c.category)))], [cards]);

  // Toggle card collection state
  const toggleCard = (id: string) => {
    setOwnedCards((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Reset all selections
  const handleReset = () => {
    if (window.confirm('Clear all collected card selections?')) {
      setOwnedCards(new Set());
    }
  };

  // Filtered card list
  const filteredCards = useMemo(() => {
    return cards.filter((card) => {
      const matchMember = selectedMember === 'All' || card.member === selectedMember;
      const matchEra = selectedEra === 'All' || card.era === selectedEra;
      const matchCat = selectedCategory === 'All' || card.category === selectedCategory;
      return matchMember && matchEra && matchCat;
    });
  }, [cards, selectedMember, selectedEra, selectedCategory]);

  // Export current grid view as PNG
  const handleExport = async () => {
    if (!templateRef.current) return;
    setIsExporting(true);
    try {
      const dataUrl = await toPng(templateRef.current, {
        cacheBust: true,
        pixelRatio: 2,
        backgroundColor: '#ffffff',
      });
      const link = document.createElement('a');
      link.download = `photocard-template-${Date.now()}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 pb-16">
      {/* Top Navigation */}
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur border-b border-slate-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Layers className="h-6 w-6 text-indigo-600" />
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              VANNER PHOTOCARD ARCHIVE
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
              Collected: <span className="text-indigo-600 font-bold">{ownedCards.size}</span> / {cards.length}
            </span>

            <button
              onClick={handleReset}
              title="Reset progress"
              className="p-2 text-slate-500 hover:text-red-600 hover:bg-slate-100 rounded-lg transition"
            >
              <RotateCcw className="h-4 w-4" />
            </button>

            <button
              onClick={handleExport}
              disabled={isExporting}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition shadow-sm"
            >
              <Download className="h-4 w-4" />
              {isExporting ? 'Exporting...' : 'Export PNG'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-6 pt-6">
        {/* Filter Controls */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs mb-6 flex flex-col gap-3">
          {/* Members */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-slate-400 uppercase w-20">Member</span>
            {members.map((m) => (
              <button
                key={m}
                onClick={() => setSelectedMember(m)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                  selectedMember === m
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          {/* Eras */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-slate-400 uppercase w-20">Era</span>
            {eras.map((e) => (
              <button
                key={e}
                onClick={() => setSelectedEra(e)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                  selectedEra === e
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {e}
              </button>
            ))}
          </div>

          {/* Categories */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-slate-400 uppercase w-20">Category</span>
            {categories.map((c) => (
              <button
                key={c}
                onClick={() => setSelectedCategory(c)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                  selectedCategory === c
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {/* Capturable Card Grid Container */}
        <div
          ref={templateRef}
          className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4"
        >
          {filteredCards.map((card) => {
            const isOwned = ownedCards.has(card.id);
            return (
              <div
                key={card.id}
                onClick={() => toggleCard(card.id)}
                className={`group relative flex flex-col rounded-xl overflow-hidden border cursor-pointer select-none transition-all duration-150 ${
                  isOwned
                    ? 'border-indigo-600 ring-2 ring-indigo-500/20 shadow-sm opacity-100'
                    : 'border-slate-200 opacity-40 hover:opacity-75'
                }`}
              >
                {/* Photocard Image Container */}
                <div className="aspect-[2/3] bg-slate-100 relative overflow-hidden">
                  <img
                    src={card.imageUrl}
                    alt={card.name}
                    className="w-full h-full object-cover pointer-events-none"
                    loading="lazy"
                  />
                  {isOwned && (
                    <div className="absolute top-2 right-2 bg-indigo-600 text-white p-1 rounded-full shadow">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                  )}
                </div>

                {/* Metadata */}
                <div className="p-2.5 bg-white flex flex-col flex-1 justify-between">
                  <p className="text-xs font-semibold text-slate-800 line-clamp-1">{card.name}</p>
                  <div className="flex justify-between items-center text-[10px] text-slate-400 mt-1">
                    <span>{card.member}</span>
                    <span>{card.category}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}