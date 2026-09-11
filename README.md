# VVS Archive 💎

A fast, responsive web archive and interactive collection checklist for **VANNER** photocards. Built with React, TypeScript, Tailwind CSS, and Vite.

[VVS archive](https://vagazinevvs.github.io/photocard-archive/)

---

## ✨ Features

- **Interactive Collection Tracking**: Mark cards as **HAVE (✅)** or **WANT (❤️)** with real-time progress calculation. States are automatically persisted via `localStorage`.
- **Mobile-Optimized UX**:
  - Direct on-card touch targets for rapid toggling without misclicks.
  - High-resolution modal lightbox with full metadata display and synchronous status switching.
- **Multi-Language Support (i18n)**:
  - Supports **English (EN)**, **繁體中文 (ZH)**, and **한국어 (KO)**.
  - Automatically detects browser/system language on initial visit with manual override persistence.
  - Automatic localization mapping for member names and composite unit cards.
- **One-Click Checklist Export**: Export your filtered card grid into a high-resolution PNG image directly from the browser using `html-to-image`.
- **Multi-Dimension Filtering**: Filter cards dynamically by Member, Era/Album, and Category, combined with live keyword search across names, IDs, and localized aliases.
- **Centralized Community Hub**: Integrated contribution links (Google Form) and direct navigation to official channels and member social accounts.

---

## 🛠 Tech Stack

- **Framework**: React 18
- **Build Tool**: Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React & Custom SVG Assets
- **Image Processing / Export**: `html-to-image`
- **Deployment**: GitHub Pages via GitHub Actions

---

## 🚀 Getting Started

### Prerequisites

- Node.js (v18 or higher recommended)
- npm or pnpm

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/vagazinevvs/photocard-archive.git
   cd photocard-archive
    ```
2. Install dependencies:

  ```bash
  npm install
  ```
3. Start the local development server:
  
  ```bash
  npm run dev
  ```

4. Build for production:
  
  ```bash
  npm run build
  ```

## 📂 Project Architecture

```text
photocard-archive/
├── public/
│   ├── cards.json         # Master database of photocard metadata
│   ├── VVS_logo.svg       # Favicon and brand icon
│   └── cards/             # Locally hosted photocard scans
├── src/
│   ├── types/
│   │   └── card.ts        # Photocard data type interfaces
│   ├── i18n.ts            # Dictionaries, member name mapping & language detection
│   ├── App.tsx            # Main application layout, filtering & grid
│   ├── main.tsx           # React entry point
│   └── index.css          # Tailwind CSS directives
├── index.html
└── vite.config.ts
```

```mermaid
graph TD
    subgraph Local [本機端：離線處理]
        A[原始圖片 raw_incoming] -->|執行 local_pipeline.py| B[裁切 & 產出 .webp]
        B --> C[更新本機 public/cards.json]
        C -->|git push| D[推送到 GitHub 倉庫]
    end

    subgraph Cloud [雲端與資料同步：GitHub Actions]
        D --> E[觸發 deploy.yml]
        E -->|執行 cloud_pipeline.py| F{Google Sheets 智慧同步}
        F -->|檢查 submit 表 status: process| G[寫入主 cards 工作表]
        F -->|比對並補登本機 cards.json 缺漏| G
        G --> H[從 cards 工作表撈取完整資料]
        H --> I[覆蓋更新 public/cards.json]
        I --> J[執行 npm run build & 部署至 GitHub Pages]
    end
```


## 🤝 Contributing
We welcome photocard scan submissions, missing data reports, and translations!

Submit Photocards: Use the Contribute button located in the footer to submit missing card scans or corrections via our submission form.

Code Contributions: Pull requests for bug fixes and UI performance enhancements are welcome.

## ⚖️ Disclaimer
Copyright ⓒ 2026 VVS Archive.

All rights to photocard artwork and related media are reserved by VANNER and their respective copyright holders. This project is a non-profit fan archive created for community collection tracking.
