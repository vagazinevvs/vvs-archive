export interface Photocard {
  id: string;
  name: string;
  member: string | string[];
  era?: string;
  category?: string;
  imageUrl: string;
  backImageUrl?: string;
}