# ELTA Corporate Design System & UI Style Guide

This comprehensive reference document defines the visual design system, color palette, typography, layout architecture, navigation, and component specifications extracted directly from the reference ELTA project (`/workspace/gui_serverAI`).

Use this guide as the authoritative standard when designing, building, refactoring, or reviewing any user interface component for ELTA hardware control and telemetry applications.

---

## 1. Visual Philosophy & Identity

ELTA's industrial interface language is engineered for high-reliability aerospace and defense hardware monitoring. The visual hierarchy balances:
1. **High Information Density**: Clean 2-column layout structures that present comprehensive hardware metrics, register maps, and diagnostic logs without unnecessary whitespace or decorative bloat.
2. **Instant Status Cognition**: Prominent, glowing industrial LEDs (`.led-green`, `.led-orange`, `.led-red`) and status indicators providing immediate normal/warning/alarm situational awareness.
3. **Unified Curvature & Beveled Precision**: Uniform 6px curvature (`border-radius: 6px !important`) across all text boxes, select dropdowns, action buttons, popovers, and containers. Capsule/pill shapes are strictly prohibited for interactive buttons.
4. **Professional Material Symbols**: Standardized Google Material Symbols (`:material/speed:`, `:material/tune:`, `:material/science:`, `:material/bolt:`, `:material/hub:`) replacing emojis for a sleek, serious industrial defense aesthetic.
5. **Tiered Surface Elevation Hierarchy**: Slate-blue tinted surface elevations (Level 0 through Level 3) derived from the harmonized 228° hue palette, maintaining soft, eye-friendly contrast.
6. **Dual Typography Model**: Clean sans-serif (`-apple-system`, `Segoe UI`, `Roboto`) for UI chrome, paired with sharp monospace (`Courier New`, `Consolas`) for hardware addresses, registers, test matrix badges, and telemetry values.

---

## 2. Complete Color System

### 2.1 The Harmonized 6-Color ColorKit System Palette
The system is anchored by the 6-color monochromatic blue palette (aligned at 228° hue):
Palette URL: `https://colorkit.co/palette/1c48f0-03081b-081546-0d2270-122f9b-173bc5/`

| Token Name | Hex / RGBA Code | Visual Swatch Role & Usage | Contrast Ratio |
| :--- | :--- | :--- | :--- |
| `$brand-pitch-navy` | `#03081b` | Pitch Dark Midnight Navy — Live status badge background, active button states, dark outlines | — |
| `$brand-dark-navy` | `#081546` | Deep Space Navy — Headings (`h1`–`h6`), section titles, top device bar background, log panel headers | 17.5:1 (AAA) |
| `$brand-rich-navy` | `#0d2270` | Midnight Navy Blue — Hover button states, dropdown headers | 13.5:1 (AAA) |
| `$brand-deep-royal` | `#122f9b` | Deep Royal Blue — Primary buttons, selection badges, matrix stat pills, interactive highlights | 11.0:1 (AAA) |
| `$brand-royal-blue` | `#173bc5` | Royal Blue — Header borders, input focus outlines, active card strokes | 8.5:1 (AAA) |
| `$brand-electric-cobalt` | `#1c48f0` | Electric Cobalt — Top Header Navigation Panel banner, tab active top accents, cyber strip accent lines | 6.56:1 (AA / AAA Large) |

### 2.2 Shell & Navigation Elements
| Element | Hex / RGBA Code | Role & Usage |
| :--- | :--- | :--- |
| **Header Banner Panel** | `#1c48f0` | Main top navigation bar background (Electric Cobalt) |
| **Header Banner Border** | `#173bc5` | 1.5px outline border for header panel |
| **Header Accent Line** | `#60a5fa` | Bottom 3px highlight accent line on the header panel |
| **Header Action Buttons** | `rgba(255, 255, 255, 0.16)` | Semi-transparent white frosted tint with `backdrop-filter: blur(4px)`, white text (`#ffffff`), border `rgba(255, 255, 255, 0.35)` |
| **Header Buttons Hover** | `rgba(255, 255, 255, 0.28)` | Frosted white hover state with `rgba(255, 255, 255, 0.7)` border |
| **Header Buttons Active** | `rgba(255, 255, 255, 0.38)` | Pressed frosted state with solid `#ffffff` border |
| **Header Corporate Logo** | `transform: translateY(-3px)` | Vertically centered relative to uppercase title text |
| **Device Selector Bar** | `#081546` | Secondary top bar for device selection (border-bottom `3px solid #1c48f0`) |
| **Device Selector Dropdown**| `#0d2270` | Select inputs inside the device bar (border `#173bc5`, text `#ffffff`) |
| **Tab Navigation Strip** | `#ffffff` | Clean white tab bar background with `#cddbe9` border |
| **Active Tab** | `#f0f5fc` | Active tab background with `3px solid #1c48f0` top line and `#081546` text |

### 2.3 Tiered Surface Elevation Hierarchy (Calibrated Slate-Blue Tints)

To ensure the interface is accessible, legible, and gentle on the eyes without large oversaturated blue surfaces, background surfaces use calibrated light slate-blue tints derived directly from the 228° hue:

| Elevation Level | Token / Element | Surface Hex | Border Hex | Role & Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Level 0 (Canvas)** | Global App Canvas | `#f4f7fb` | None | Application window & background canvas |
| **Level 1 (Outer Card)** | `.elta-main-card`, `.card` | `#f0f5fc` | `#cddbe9` (1.5px) | Top-level containers (Telemetry wrapper, R/W Card, Tests matrix card) |
| **Level 2 (Sub-Frame)** | `.elta-sub-frame` | `#e5eef9` | `#a8c4e6` (1.5px) | Major internal inspection block nested inside Level 1 card |
| **Level 2 (Section Plate)** | `.futuristic-panel-head` | `#dbe8f7` | `#95b8e0` (1.2px) | Section header plate inside cards, title `#081546`, badge `#122f9b` |
| **Level 2 (Input Box)** | `.dropzone`, `.file-chip` | `#f0f5fc` / `#e5eef9` | `#a8c4e6` (1.5px) | File dropzone and input container |
| **Level 3 (Metric Box)** | `.elta-stat-box` | `#d8e6f5` | `#95b8e0` (1.2px) | Statistical metric block nested inside Level 2 sub-frame |
| **Elevated Cards** | `.elta-channel-card` (idle) | `#ffffff` | `#bdd3ec` (1.2px) | Idle telemetry channel card resting on Level 1 surface |
| **Active Cards** | `.elta-channel-card.selected` | `#dce8fc` | `#173bc5` (2.0px) | Selected / active channel card with royal blue highlight stroke |
| **Console / Log Box** | `.console-box`, `.table-container` | `#ffffff` | `#a8c4e6` (1.5px) | Clean white log & data tables for optimal legibility |
| **Status Strip** | `.elta-status-strip` | `#e5eef9` | `#a8c4e6` (1.5px) | Bottom status bar, high-contrast `#081546` text |

### 2.4 Action & Interactive Control Palette

| Token Name | Hex Code | Role & Usage |
| :--- | :--- | :--- |
| `$btn-primary-bg` | `#122f9b` | Primary action button background, run button, selection badges |
| `$btn-primary-hover` | `#173bc5` | Primary action button hover state |
| `$btn-primary-active` | `#0d2270` | Primary action button pressed/active state |
| `$btn-secondary-bg` | `#ffffff` | Secondary button background (text `#081546`, border `#cbd5e1`) |
| `$input-focus-stroke` | `#173bc5` | Focus ring and stroke for inputs, selects, and textareas |
| `$checkbox-accent` | `#122f9b` | Checkbox and radio button accent color |

### 2.5 Status & Industrial LED Indicators (Safety Semantics)

| Status State | Color | Glow Box-Shadow | Meaning |
| :--- | :--- | :--- | :--- |
| **Normal / Alive / Pass** | `#16a34a` / `#15803d` | `0 0 10px rgba(22, 163, 74, 0.6)` | Nominal hardware state, test passed |
| **Warning / Caution** | `#d97706` | `0 0 10px rgba(217, 119, 6, 0.6)` | Range warning, non-critical event |
| **Alarm / Fail / Critical** | `#dc2626` | `0 0 10px rgba(220, 38, 38, 0.6)` | Out-of-bounds, disconnect, test failed |
| **Selected Channel** | `#173bc5` | `0 0 10px rgba(23, 59, 197, 0.6)` | Active inspection channel |
| **Unrun / Dormant** | `#64748b` | `inset 0 0 5px rgba(0, 0, 0, 0.4)` | Inactive indicator / dormant state |

---

## 3. Typography & Text Hierarchy

### 3.1 Font Families
- **UI Chrome & Navigation**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`
- **Hardware Values & Addresses**: `'Courier New', Consolas, SFMono-Regular, Liberation Mono, monospace`

### 3.2 Font Styles & Sizes

| Element | Size | Weight | Color | Transform |
| :--- | :--- | :--- | :--- | :--- |
| **Header App Title** | `22px - 26px` | Bold (`800`) | `#ffffff` | Uppercase |
| **Section Panel Header** | `14px - 16px` | Bold (`700`) | `#081546` | Uppercase |
| **Badge Pill Text** | `11px - 12px` | Bold (`700`) | `#ffffff` on `#122f9b` | Uppercase |
| **Sub-Heading / Label** | `12px - 13px` | Semi-bold (`600`) | `#081546` | Title Case / Uppercase |
| **Table Headers** | `11px` | Semi-bold (`600`) | `#081546` | Uppercase |
| **Body / Labels** | `12px - 14px` | Normal (`400`) | `#1e293b` | None |
| **Muted Metadata** | `11px - 12px` | Normal (`400`) | `#475569` | None |
| **Hardware Data Values** | `13px - 15px` | Bold (`700`) | `#15803d` / `#ffffff` | Monospace |

---

## 4. Header & Top Navigation Architecture

The top navigation bar anchors the application and provides instant access to global system popovers.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [ELTA LOGO]               FPGA CONTROL CENTER            [● Online] [Net] [Info] [Logs] │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Structural Specifications
- **Container Class**: `div.st-key-elta_header_wrapper`, `.top-nav-card`
- **Height**: `54px` – `60px`
- **Background**: Solid Electric Cobalt `#1c48f0` with `1.5px solid #173bc5` border and `3px solid #60a5fa` bottom accent line.
- **Left Zone**:
  - ELTA Corporate Logo (`.elta-header-logo-img`): `height: 38px; transform: translateY(-3px)` for optical vertical centering with the title text.
  - App Title (`.elta-header-title-text`): `font-size: 1.45rem; font-weight: 800; color: #ffffff; letter-spacing: 2px; text-transform: uppercase;`.
- **Right Zone (Header Action Buttons & Popover Triggers)**:
  - Frosted semi-transparent white tint: `background: rgba(255, 255, 255, 0.16) !important;`
  - Backdrop blur: `backdrop-filter: blur(4px) !important;`
  - Outline stroke: `border: 1px solid rgba(255, 255, 255, 0.35) !important;`
  - Text & Icon: `color: #ffffff !important; fill: #ffffff !important; font-weight: 700 !important;`
  - Uniform radius: `border-radius: 6px !important;`
  - Hover: `background: rgba(255, 255, 255, 0.28) !important; border-color: rgba(255, 255, 255, 0.7) !important;`
  - Active: `background: rgba(255, 255, 255, 0.38) !important; border-color: #ffffff !important;`
- **Live Status Badge Button (`hdr_live_status_badge`)**:
  - `background: rgba(255, 255, 255, 0.18) !important; border: 1px solid rgba(255, 255, 255, 0.4);` with green glowing LED indicator.

---

## 5. Main Tab Navigation

Primary functional pages are navigated via a clean tab bar positioned directly under the device bar.

```
┌──────────────────┬──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ :material/speed: │ :material/tune:  │:material/science:│ :material/bolt:  │  :material/hub:  │
│    TELEMETRY     │    READ-WRITE    │      TESTS       │   POWER SUPPLY   │  BLOCK DIAGRAM   │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

### 5.1 Tab Icon & Label Standards
Tabs utilize Google Material Symbols to maintain a clean defense aesthetic:
- **Telemetry**: `:material/speed: Telemetry`
- **Read-Write**: `:material/tune: Read-Write`
- **Tests**: `:material/science: Diagnostic Tests`
- **Power Supply**: `:material/bolt: Power Supply`
- **Block Diagram**: `:material/hub: Block Diagram`

---

## 6. Unified 2-Column Component Architecture

All primary functional pages (Telemetry, Read-Write, Diagnostic Tests) follow the unified 2-column layout format:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🟢 DEVICE BAR: [Device 0 (Xilinx UltraScale+)]      Status: ONLINE (300 MHz)│
├──────────────────────────────────────────┬──────────────────────────────────┤
│ LEFT COLUMN (Controls & Selection)       │ RIGHT COLUMN (Diagnostic Logs)   │
│ ┌──────────────────────────────────────┐ │ ┌──────────────────────────────┐ │
│ │ 🔷 Section Panel Header               │ │ │ 🔷 Diagnostic Log & Results  │ │
│ │ ┌──────────────────────────────────┐ │ │ ┌──────────────────────────┐ │ │
│ │ │ Controls / Matrix / Inputs       │ │ │ │ │ Monospace Code Console   │ │ │
│ │ └──────────────────────────────────┘ │ │ │ └──────────────────────────┘ │ │
│ └──────────────────────────────────────┘ │ └──────────────────────────────┘ │
└──────────────────────────────────────────┴──────────────────────────────────┘
```

### 6.1 Top Cyber Device Bar
- **Class**: `.device-bar`
- **Background**: Deep Space Navy `#081546` with `3px solid #1c48f0` bottom accent stroke.
- **Components**: Active device selector dropdown (`#0d2270` background, `#ffffff` text), live LED status indicator (`● Online`), and system clock badge (`300 MHz`).

### 6.2 Left Column (Controls & Matrix)
- Contains section cards framed by `.futuristic-panel-head` headers (`#dbe8f7` background, `#081546` title, `.futuristic-badge-pill` `#122f9b`).
- Level 3 `.elta-stat-box` metric blocks (`#d8e6f5` surface) with `.elta-matrix-badge` pills (`Passed`, `Failed`, `Total`, `Pass Rate`).

### 6.3 Right Column (Sticky Diagnostic Console)
- **Container**: Sticky container (`position: sticky; top: 1rem;`).
- **Header**: Panel head titled `DIAGNOSTIC LOG & RESULTS` with clear log / export CSV buttons (`:material/download:` icon).
- **Log Console**: White background (`#ffffff`), `border: 1px solid #a8c4e6`, font family monospace (`Courier New`), line-height `1.5`, with timestamped color-coded logs (`[PASS]` green, `[FAIL]` red, `[INFO]` blue).

---

## 7. Component Design Patterns

### 7.1 Buttons (`st.button`, `.btn`, `.btn-primary`)

> [!IMPORTANT]
> **Uniform 6px Curvature Standard**: All buttons—including header buttons, popover triggers, tab controls, form buttons, and dialog buttons—must use `border-radius: 6px !important` to match input boxes. Capsule/pill buttons (`border-radius: 20px` or `12px`) are strictly prohibited for interactive buttons.

> [!IMPORTANT]
> **Strict Accessibility & High Contrast**:
> - **Never place dark/black text over blue, cyan, or dark backgrounds**.
> - Primary buttons (`kind="primary"`) must enforce pure white text: `color: #ffffff !important;` across all child elements (`*`, `p`, `span`, `svg`, `path`).
> - Secondary / standard buttons use solid white surface (`#ffffff`) with `#081546` dark navy text and `#cbd5e1` border.

```css
/* Primary Action Button (Deep Royal Blue + Pure White Text) */
button[kind="primary"], div.stButton > button[kind="primary"] {
    background-color: #122f9b !important;
    border: 1px solid #173bc5 !important;
    border-radius: 6px !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 3px rgba(18, 47, 155, 0.25) !important;
}
button[kind="primary"] *, div.stButton > button[kind="primary"] * {
    color: #ffffff !important;
    fill: #ffffff !important;
}
button[kind="primary"]:hover, div.stButton > button[kind="primary"]:hover {
    background-color: #173bc5 !important;
    border-color: #60a5fa !important;
    color: #ffffff !important;
}
```

### 7.2 Dropdown Popovers (`st.popover`)
- **Popover Body**: Background `#ffffff`, border `2px solid #1c48f0`, top border `4px solid #173bc5`, radius `6px`, box-shadow `0 8px 24px rgba(28, 72, 240, 0.22)`.
- **Headings**: Deep Space Navy `#081546`, uppercase, bold (`700`).
- **Buttons inside Popovers**: Primary `#122f9b` with pure white text (`#ffffff !important;`), secondary `#f0f5fc` with `#081546` text.

### 7.3 Status LEDs
```css
.led-green {
    background-color: #16a34a;
    box-shadow: 0 0 10px rgba(22, 163, 74, 0.6);
}
.led-red {
    background-color: #dc2626;
    box-shadow: 0 0 10px rgba(220, 38, 38, 0.6);
}
.led-orange {
    background-color: #d97706;
    box-shadow: 0 0 10px rgba(217, 119, 6, 0.6);
}
```

---

## 8. Implementation Checklist for Agents

When implementing or modifying any component in ELTA style, verify:

1. [ ] **Color Palette Compliance**: Use exact ColorKit tokens (`#1c48f0`, `#173bc5`, `#122f9b`, `#0d2270`, `#081546`, `#03081b`).
2. [ ] **Header Button Glassmorphism**: Ensure header buttons use transparent white tint (`rgba(255, 255, 255, 0.16)`), backdrop blur (`blur(4px)`), and pure white text/icons (`#ffffff`).
3. [ ] **Header Logo Centering**: Verify `.elta-header-logo-img` has `transform: translateY(-3px)` for vertical optical centering.
4. [ ] **Uniform 6px Button Radius**: Apply `border-radius: 6px !important;` to all buttons and inputs. Prohibit pill/capsule shapes (`20px`).
5. [ ] **Material Symbols**: Use Material Symbols (`:material/...:`) for tab labels, actions, and dropdown icons. No raw emojis.
6. [ ] **2-Column Layout Alignment**: Ensure Telemetry, Read-Write, and Tests pages follow the unified 2-column format (Controls on left, Sticky Diagnostic Log console on right).
7. [ ] **Accessibility & Contrast**: Enforce `#ffffff` text on all blue buttons and banners. Use `#081546` dark text only on light blue tints (`#f0f5fc`) or white surfaces.
8. [ ] **Verification**: Run `pytest` to verify 100% test pass rate.