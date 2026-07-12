---
name: Fortune Minimalist Dark
philosophy: Intentional Subtraction meets Material Design 3
---

# Design System: Fortune

## 1. Core Philosophy
Our design system merges **intentional subtraction** with **Material Design 3 (M3) principles**. Every element must earn its place while adhering to M3's adaptive, accessible, and dynamic standards. If it does not clarify or reinforce the user's goal of tracking and managing job applications effectively, it is removed.

### Principles
*   **Form Follows Function (Intentional Subtraction):** The utility of managing job applications comes first. Aesthetics support structure. No redundant elements, colors, or interactions.
*   **Adaptive (M3):** Layouts and components must fluidly adapt to different screen sizes and devices, ensuring a consistent experience on desktop, tablet, and mobile.
*   **Accessible (M3):** Follow strict M3 accessibility standards. Ensure high text contrast ratios and adequate touch targets (minimum 48x48dp for interactive elements).
*   **Dynamic Color (M3):** Utilize the M3 color system for theming, systematically mapping our minimalist dark palette to M3 roles (Surface, Primary, Error, etc.).
*   **Visual Hierarchy & Balance:** Use white space and a structured grid to manage layout without visual clutter, guiding the user's eye naturally to key information.

## 2. Base Tokens & Theming

### Colors
We utilize the M3 color system mapped to our restricted "darkish" palette (slate/blue undertones) to maintain focus, reduce eye strain, and provide a premium, modern feel.
- **Surface (Main Background):** `#0F172A` (Deep slate)
- **Surface Variant (Cards/Panels):** `#1E293B` (Slightly lighter slate for elevation without shadows)
- **On-Surface (Primary Text):** `#F8FAFC` (High contrast, highly legible off-white)
- **On-Surface Variant (Secondary Text):** `#94A3B8` (Used for metadata, dates, or lesser-importance text)
- **Primary Action:** `#3B82F6` (Vibrant blue, used *only* for primary buttons or active states)
- **Outline / Border:** `#334155` (Subtle structural lines for separation)
- **Status Accents:** (Tuned for dark mode contrast)
  - Success / Tertiary (Offer/Interview): `#10B981`
  - Warning / Custom (Pending/Action Required): `#F59E0B`
  - Error (Rejected/Archived): `#EF4444`

### Typography
A single, highly legible sans-serif typeface to ensure consistency and readability.
- **Font Family:** `Inter` (or system UI stack)
- **Display / Headings:** Semi-bold. Used sparingly for page titles.
- **Body:** Regular, 14px - 16px. Used for job descriptions and lists.
- **Labels / Meta:** Medium, 12px, uppercase tracking. Used for tags, statuses, and small metadata.

### Spacing & Sizing
A consistent baseline grid following M3 spatial guidelines.
- **Base Unit:** 4px
- **Standard Padding:** 16px (4 units)
- **Border Radius:** 6px (Slightly softened corners, M3 shape system adapted for a sharper minimalist look)

## 3. Components (M3-Compliant)

Use M3-compliant components and patterns, refined for our dark minimalist theme.

### Buttons & Inputs
- **Primary Button (M3 Filled Button):** Solid primary color (`#3B82F6`), white text (`#FFFFFF`), 6px radius. No drop shadows. Must meet M3 touch target sizes.
- **Secondary Button (M3 Outlined Button):** Transparent background, 1px solid border (`#334155`), primary text color (`#F8FAFC`).
- **Inputs:** 1px solid border (`#334155`), background (`#0F172A`), subtle focus ring (Primary color at 50% opacity).

### Navigation
- **Top/Side Bar:** Clean, border-separated (not shadow-separated) from the main content. Adaptive behavior that shifts based on screen size (e.g., side rail on desktop, bottom navigation or drawer on mobile).
- **Active State:** Indicated by bright primary text and a simple left-border or underline, avoiding heavy background fills.

### Cards & Data
- **Job Cards (M3 Outlined Cards):** 1px solid border (`#334155`), surface variant background (`#1E293B`). No elevation/shadows. Relies entirely on border and subtle background contrast.
- **Status Badges:** Small, subtle background tint (15% opacity of status color) with matching vibrant text color.

## 4. Do's and Don'ts
- **DO** use the Primary color extremely sparingly to highlight the single most important action on a page.
- **DO** ensure all layouts are adaptive and test them across different screen sizes.
- **DO** verify that touch targets are accessible (48x48dp) and text contrast meets M3 standards.
- **DON'T** use generic gradients, heavy shadows, or decorative illustrations that distract from the data.
- **DON'T** mix multiple font families or introduce unnecessary font weights.
