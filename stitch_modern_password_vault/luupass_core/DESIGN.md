---
name: LuuPass Core
colors:
  surface: '#12131b'
  surface-dim: '#12131b'
  surface-bright: '#383842'
  surface-container-lowest: '#0d0e16'
  surface-container-low: '#1a1b23'
  surface-container: '#1f1f27'
  surface-container-high: '#292932'
  surface-container-highest: '#34343d'
  on-surface: '#e3e1ed'
  on-surface-variant: '#c6c5d7'
  inverse-surface: '#e3e1ed'
  inverse-on-surface: '#2f3039'
  outline: '#8f8fa0'
  outline-variant: '#454655'
  surface-tint: '#bec2ff'
  primary: '#bec2ff'
  on-primary: '#000da4'
  primary-container: '#5865f2'
  on-primary-container: '#fffdff'
  inverse-primary: '#3f4cda'
  secondary: '#ddb7ff'
  on-secondary: '#490080'
  secondary-container: '#6f00be'
  on-secondary-container: '#d6a9ff'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#00865c'
  on-tertiary-container: '#fafff9'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e0e0ff'
  primary-fixed-dim: '#bec2ff'
  on-primary-fixed: '#000569'
  on-primary-fixed-variant: '#222fc2'
  secondary-fixed: '#f0dbff'
  secondary-fixed-dim: '#ddb7ff'
  on-secondary-fixed: '#2c0051'
  on-secondary-fixed-variant: '#6900b3'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#12131b'
  on-background: '#e3e1ed'
  surface-variant: '#34343d'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style

The design system is engineered for **LuuPass**, a premium password management utility. The brand personality is rooted in **digital vault security**, blending a sense of impenetrable protection with high-velocity efficiency. 

The aesthetic is **Modern Minimalist with Glassmorphic accents**. We utilize a deep, layered dark mode strategy that avoids pure black to maintain depth and reduce eye strain. The UI evokes a "Command Center" feel—highly organized, technically precise, and reassuringly professional. Key visual drivers include:
- **Stealth Foundations:** Deep charcoal surfaces that provide a stable, calm backdrop.
- **Electric Precision:** High-vibrancy accents to guide the user toward primary actions like saving or generating passwords.
- **Modern Clarity:** Refined typography and generous negative space to ensure sensitive data is easily scannable and never overwhelming.

## Colors

This design system utilizes a **layered dark palette** to create a sense of physical depth.
- **Primary (Electric Blue):** Used for the most critical actions, such as "Save" or "Add New." It represents trust and technical capability.
- **Secondary (Cyber Purple):** Used for secondary interactive elements, progress indicators, and visual flair to distinguish the product from traditional enterprise tools.
- **Tertiary (Secure Green):** Reserved for success states, "Strong Password" indicators, and vault-unlocked confirmations.
- **Neutrals:** The palette is built on "Rich Charcoal" (#0B0E14) for the base, with "Slate Gray" variants for surface containers. This avoids the "flatness" of #000000 and allows for subtle border definitions.

## Typography

The typographic system prioritizes **legibility and technical rigor**. 
- **Plus Jakarta Sans** is used for headlines to provide a modern, slightly rounded, and welcoming character to the high-security environment. 
- **Inter** is the workhorse for all body copy and input fields, chosen for its exceptional readability at small sizes and its neutral, systematic feel.
- **JetBrains Mono** (Optional) is introduced for actual password strings and recovery keys to ensure distinct character recognition (e.g., distinguishing '1', 'l', and 'I').

**Scale Strategy:** 
On mobile, `display-lg` should be avoided. Use `headline-lg` as the maximum heading size to ensure UI density remains functional on smaller screens.

## Layout & Spacing

The design system uses a **Fixed-Fluid Hybrid Grid**. 
- **Sidebar:** Fixed at 280px for desktop. 
- **Main Content:** Fluid width with a maximum container cap of 1200px to maintain scannability.
- **Grid:** A 12-column grid system is used for the detail view, allowing for complex input arrangements (e.g., username and password fields side-by-side on desktop, stacked on mobile).

**Spacing Rhythm:** 
An 8px-based linear scale drives all dimensions. Gutters are consistently 16px to maintain a compact, "utility-first" feel that maximizes the amount of information visible without feeling cluttered.

## Elevation & Depth

In this dark-themed environment, depth is communicated through **Tonal Layering and Glassmorphism** rather than heavy shadows.

1.  **Level 0 (Background):** #0B0E14 - The lowest layer.
2.  **Level 1 (Sidebars/Lists):** #161B22 - A slightly lighter slate to differentiate navigation zones.
3.  **Level 2 (Active Cards/Detail View):** #1D242C - The primary interaction surface.
4.  **Glass Layers:** Semi-transparent overlays (20% opacity white tint with a 12px backdrop-blur) are used for floating action bars and modal headers to maintain context of the content underneath.

**Borders:** Instead of shadows, use 1px solid borders in `rgba(255, 255, 255, 0.08)` to define element edges. For active/focused states, these borders transition to the Primary Electric Blue.

## Shapes

The shape language balances professional rigidity with modern approachability. 
- **Standard Radius:** 8px (base) for inputs and smaller UI components.
- **Large Radius:** 16px for cards, detail panels, and modal containers.
- **Buttons:** Use a consistent 12px radius to feel substantial and clickable.

Avoid 0px (sharp) corners as they appear too aggressive for a consumer-facing tool. Avoid full-pill shapes except for status tags (e.g., "Weak," "Moderate," "Strong").

## Components

### Buttons
- **Primary:** Electric Blue background, white text. No shadow; uses a subtle inner-glow on hover.
- **Secondary:** Transparent background with a 1px Slate border. 
- **Action Icons:** 40x40px touch targets. Icons should be 20px (e.g., "Copy," "Show Password").

### Input Fields
- **Default State:** Deep slate background (#161B22) with a subtle 1px border.
- **Focus State:** Border color changes to Electric Blue with a 2px outer glow (Primary Blue at 20% opacity).
- **Labels:** Positioned above the field in `label-md` style, using a secondary text color (Slate 400).

### Cards & List Items
- **Vault Item:** Uses a horizontal layout with a high-contrast icon (e.g., Google, Netflix logo) on the left.
- **Selected State:** A 2px vertical accent line of Primary color on the far left edge and a subtle background tint change.

### Password Strength Meter
- A segmented bar (4 segments) that transitions from Red -> Orange -> Yellow -> Green. Each segment has a 2px gap to maintain the technical, grid-like aesthetic.

### Glass Modals
- High backdrop blur (20px) with a semi-transparent surface. Borders are mandatory for visibility against dark backgrounds.