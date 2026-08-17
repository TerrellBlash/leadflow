# BARLY 🍸

**Your bar. Smarter.**

A nano-banana powered, on-device cocktail assistant that generates cocktails from ingredients you have on hand.

Scan what you have → make a great drink in under 60 seconds.

---

## ✨ Core Features

- **Ingredient Scanning** — Camera + manual input
- **Cocktail Generation** — Ingredient-first discovery
- **Smart Substitutions** — Don't have lime? Use lemon.
- **Taste Controls** — Dial in sweet/strong to your preference
- **Visual Pour Guide** — Never over-pour again
- **Offline-First** — Works without internet

## 📱 Platforms

| Platform | Stack | Status |
|----------|-------|--------|
| iOS | SwiftUI + CoreML | 🚧 MVP in progress |
| Android | Jetpack Compose + TFLite | 📋 Planned |
D
## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      BARLY App                          │
├─────────────────────────────────────────────────────────┤
│  Views: Home → Scan → Results → Detail → Pour Guide    │
├─────────────────────────────────────────────────────────┤
│  State: AppState (ObservableObject)                     │
├─────────────────────────────────────────────────────────┤
│  Logic: FlavorEngine + SubstitutionEngine               │
├─────────────────────────────────────────────────────────┤
│  Data: CocktailDatabase (offline-first)                 │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### iOS Development

```bash
cd ios/BarlyApp
open BarlyApp.xcodeproj
# or
xed .
```

**Requirements:**
- Xcode 15.0+
- iOS 17.0+ deployment target
- Swift 5.9+

### Running Tests

```bash
cd ios/BarlyApp
xcodebuild test -scheme BarlyApp -destination 'platform=iOS Simulator,name=iPhone 15 Pro'
```

## 📂 Project Structure

```
barly/
├── README.md
├── LICENSE
├── .gitignore
│
├── docs/
│   ├── PRD.md                 # Product requirements
│   ├── UX_Flows.md            # User journey documentation
│   ├── AI_Architecture.md    # On-device AI design
│   ├── Sprint_Plan.md        # 6-week development plan
│   └── Pitch_Deck.md         # Investor/pitch materials
│
├── design/
│   ├── figma/
│   │   ├── frames.json       # Screen definitions
│   │   └── components.json   # Reusable components
│   └── assets/               # Icons, images, etc.
│
├── ios/
│   └── BarlyApp/             # SwiftUI application
│
├── android/
│   └── app/                  # Jetpack Compose app (planned)
│
└── backend/
    └── api/
        └── openapi.yaml      # Optional API spec
```

## 🧪 Core User Loop

1. **Home** — "What can I make?" with quick actions
2. **Scan** — Capture or select ingredients
3. **Results** — Cocktails you can make right now
4. **Detail** — Recipe with taste adjustments
5. **Pour** — Visual step-by-step guidance

## 🎯 Design Philosophy

- **Offline-first**: Everything works without internet
- **Explainable AI**: Rules-based logic, not black-box ML
- **Fast**: Sub-second response times on-device
- **Respectful**: No accounts required, no data harvesting

## 📋 Roadmap

### MVP (Week 1-6)
- [x] Core navigation flow
- [x] Ingredient input (manual)
- [x] Cocktail generation engine
- [x] Taste sliders (sweet/strong)
- [x] Substitution suggestions
- [ ] Visual pour guide
- [ ] Camera scanning
- [ ] TestFlight beta

### v1.1
- [ ] Favorites & history
- [ ] Advanced taste profiles
- [ ] Ingredient inventory tracking

### v2.0
- [ ] Android launch
- [ ] On-device vision classifier
- [ ] Community recipes

## 🤝 Contributing

This is currently a solo project, but feedback is welcome! Open an issue for bug reports or feature requests.

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

**Built with 🍌 Nano-Banana AI**
