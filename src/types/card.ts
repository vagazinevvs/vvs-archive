// Data definition for photocard entries
export interface Photocard {
    id: string;
    era: string;
    member: string;
    category: 'Album' | 'POB' | 'LuckyDraw' | 'Concert' | 'Event';
    name: string;
    imageUrl: string;
  }