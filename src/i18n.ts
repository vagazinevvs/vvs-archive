export type Language = 'en' | 'zh' | 'ko';

export const STORAGE_KEY_LANG = 'vanner_archive_lang';

// 系統預設語系偵測（優先讀取 localStorage，次之抓取系統/瀏覽器語系）
export const getInitialLanguage = (): Language => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_LANG) as Language;
    if (saved && ['en', 'zh', 'ko'].includes(saved)) {
      return saved;
    }

    const browserLang = (navigator.language || (navigator as any).userLanguage || '').toLowerCase();
    if (browserLang.startsWith('zh')) return 'zh';
    if (browserLang.startsWith('ko')) return 'ko';
    return 'en';
  } catch {
    return 'zh';
  }
};


// 1. 在對應的語言字典或獨立物件中加入 era 的翻譯
export const ERA_TRANSLATIONS: Record<Language, Record<string, string>> = {
  en: {
    swy: "Still With You",
    caf: "Caffeine",
  },
  zh: {
    swy: "Still With You",
    caf: "咖啡因",
  },
  ko: {
    swy: "Still With You",
    caf: "카페인",
  },
};

// 2. 建立格式化 Era 的函式
export const formatEraName = (eraKey: string, lang: Language): string => {
  if (!eraKey) return '';
  const lowerKey = eraKey.toLowerCase();
  return ERA_TRANSLATIONS[lang]?.[lowerKey] || eraKey;
};


// 介面文字字典
export const I18N = {
  en: {
    title: 'VVS ARCHIVE',
    subtitle: 'Click photo to zoom, click to mark HAVE/WANT',
    have: 'HAVE',
    want: 'WANT',
    all: 'All',
    member: 'Member',
    era: 'Era',
    category: 'Category',
    searchPlaceholder: 'Search card name or ID...',
    noCards: 'No matching photocards found',
    loading: 'Syncing photocard archive...',
    resetConfirm: 'Clear all marked HAVE and WANT cards?',
    contribute: 'Contribute',
    export: 'Export PNG',
    exporting: 'Exporting...',
    noImage: 'No Image',
    viewFull: 'View Full Image',
    copyrightSub: 'All Rights of Photocards Reserved by VANNER',
  },
  zh: {
    title: 'VVS ARCHIVE',
    subtitle: '點圖放大，點選標記 擁有/想要',
    have: '我有了',
    want: '我想要',
    all: '全部',
    member: '成員',
    era: '時期',
    category: '分類',
    searchPlaceholder: '搜尋小卡名稱或編號...',
    noCards: '沒有找到符合條件的小卡',
    loading: '正在同步小卡資料庫...',
    resetConfirm: '確定要清除所有標記紀錄嗎？',
    contribute: '提供小卡',
    export: '匯出清單',
    exporting: '匯出中...',
    noImage: '無圖檔',
    viewFull: '檢視大圖',
    copyrightSub: 'All Rights of Photocards Reserved by VANNER',
  },
  ko: {
    title: '삐삐 아카이브',
    subtitle: '사진을 클릭하면 확대, 클릭하여 소유/원함 표시 ',
    have: '소유',
    want: '원함',
    all: '전체',
    member: '멤버',
    era: '활동',
    category: '분류',
    searchPlaceholder: '포토카드 이름 또는 ID 검색...',
    noCards: '일치하는 포토카드가 없습니다',
    loading: '포토카드 아카이브 동기화 중...',
    resetConfirm: '모든 표시를 초기화하시겠습니까?',
    contribute: '카드 제보',
    export: '이미지 저장',
    exporting: '저장 중...',
    noImage: '이미지 없음',
    viewFull: '크게 보기',
    copyrightSub: 'All Rights of Photocards Reserved by VANNER',
  },
} as const;

// 成員多語系名稱映射表
export const MEMBER_NAME_MAP: Record<string, Record<Language, string>> = {
  taehwan: { en: 'Taehwan', zh: '泰煥', ko: '태환' },
  태환: { en: 'Taehwan', zh: '泰煥', ko: '태환' },
  泰煥: { en: 'Taehwan', zh: '泰煥', ko: '태환' },

  gon: { en: 'GON', zh: 'GON', ko: '곤' },
  곤: { en: 'GON', zh: 'GON', ko: '곤' },

  hyesung: { en: 'Hyesung', zh: '慧成', ko: '혜성' },
  혜성: { en: 'Hyesung', zh: '慧成', ko: '혜성' },
  慧成: { en: 'Hyesung', zh: '慧成', ko: '혜成' },

  sungkook: { en: 'Sungkook', zh: '成國', ko: '성국' },
  성국: { en: 'Sungkook', zh: '成國', ko: '성국' },
  成國: { en: 'Sungkook', zh: '成國', ko: '성국' },

  yeongkwang: { en: 'Yeongkwang', zh: '泳光', ko: '영광' },
  영광: { en: 'Yeongkwang', zh: '泳光', ko: '영광' },
  泳光: { en: 'Yeongkwang', zh: '泳光', ko: '영광' },

  other: { en: 'Other', zh: '其他', ko: '기타' },
 
  
};

// // 分割多人欄位輔助函式
// export const parseMembers = (memberStr: string): string[] => {
//   if (!memberStr) return [];
//   return memberStr
//     .split(/[,/&]+/)
//     .map((m) => m.trim())
//     .filter(Boolean);
// };

// // 格式化單一成員名稱
// export const formatMemberName = (name: string, lang: Language): string => {
//   const cleanKey = name.trim().toLowerCase();
//   if (MEMBER_NAME_MAP[cleanKey]) {
//     return MEMBER_NAME_MAP[cleanKey][lang];
//   }
//   return name;
// };

// // 格式化複合成員字串（例如 "Hyesung, Sungkook"）
// export const formatMultiMemberString = (memberStr: string, lang: Language): string => {
//   if (!memberStr) return '';
//   const parsed = parseMembers(memberStr);
//   return parsed.map((m) => formatMemberName(m, lang)).join(', ');
// };


// 分割多人欄位輔助函式（相容字串與陣列）
export const parseMembers = (memberInput: string | string[]): string[] => {
  if (!memberInput) return [];
  if (Array.isArray(memberInput)) {
    return memberInput.map((m) => String(m).trim()).filter(Boolean);
  }
  return memberInput
    .split(/[,/&]+/)
    .map((m) => m.trim())
    .filter(Boolean);
};

// 格式化單一成員名稱
export const formatMemberName = (name: string, lang: Language): string => {
  const cleanKey = name.trim().toLowerCase();
  if (MEMBER_NAME_MAP[cleanKey]) {
    return MEMBER_NAME_MAP[cleanKey][lang];
  }
  return name;
};

// 格式化複合成員字串
export const formatMultiMemberString = (memberInput: string | string[], lang: Language): string => {
  if (!memberInput) return '';
  const parsed = parseMembers(memberInput);
  return parsed.map((m) => formatMemberName(m, lang)).join(', ');
};