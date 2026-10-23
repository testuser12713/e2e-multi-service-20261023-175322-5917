# Design — Project Identity

> This document is project-long-lived. Tokens are not changed without
> the Architect's approval. Developers MUST use these tokens
> instead of improvising their own colors/spacings.

## Style Direction

Clean, calm light dashboard in the spirit of Linear/Stripe: neutral grey canvas, white cards with hairline borders, one indigo accent, and clearly distinguishable semantic status colors; Inter for UI, JetBrains Mono for ids and figures, all fonts self-hosted.

## Colors

- `--color-bg`: **#F7F8FA**
- `--color-surface`: **#FFFFFF**
- `--color-fg`: **#111827**
- `--color-muted`: **#6B7280**
- `--color-border`: **#E5E7EB**
- `--color-accent`: **#4F46E5**
- `--color-accent_hover`: **#4338CA**
- `--color-accent_active`: **#3730A3**
- `--color-accent_soft`: **#EEF2FF**
- `--color-focus_ring`: **#A5B4FC**
- `--color-status_pending_bg`: **#FEF3C7**
- `--color-status_pending_fg`: **#92400E**
- `--color-status_running_bg`: **#DBEAFE**
- `--color-status_running_fg`: **#1E40AF**
- `--color-status_done_bg`: **#DCFCE7**
- `--color-status_done_fg`: **#166534**
- `--color-status_failed_bg`: **#FEE2E2**
- `--color-status_failed_fg`: **#991B1B**
- `--color-danger`: **#B91C1C**
- `--color-danger_bg`: **#FEF2F2**
- `--color-code_bg`: **#F3F4F6**

## Typography

- `font_family`: "Inter", system-ui, "Segoe UI", Roboto, Arial, sans-serif
- `heading_font`: "Inter", system-ui, "Segoe UI", Roboto, Arial, sans-serif
- `mono_font`: "JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, "Liberation Mono", monospace
- `heading_weight`: 600
- `body_weight`: 400
- `font_files`: Self-hosted only: design/fonts/inter/font.css and design/fonts/jetbrains-mono/font.css, bundled into the frontend; no third-party font/CDN requests
- `size_xs`: 12px
- `size_sm`: 13px
- `size_base`: 15px
- `size_lg`: 18px
- `size_xl`: 24px
- `line_height`: 1.5
- Inter files: `design/fonts/inter/` — `font.css` holds its @font-face rules, `OFL.txt` its licence
- JetBrains Mono files: `design/fonts/jetbrains-mono/` — `font.css` holds its @font-face rules, `OFL.txt` its licence

## Spacing Scale

- `--space-0`: 4px
- `--space-1`: 8px
- `--space-2`: 12px
- `--space-3`: 16px
- `--space-4`: 24px
- `--space-5`: 32px
- `--space-6`: 48px

## Border-Radii

- `--radius-sm`: 4px
- `--radius-md`: 8px
- `--radius-lg`: 12px
- `--radius-pill`: 999px

## Components

### Button

Primary: bg=accent, fg=#FFFFFF, font 15px/600, padding 12px 20px, radius md, min-height 44px, no border. Hover bg=accent_hover; active bg=accent_active + translateY(1px); focus-visible 3px ring focus_ring with 2px offset; disabled opacity 0.55, cursor not-allowed, no hover effect. While a submission is in flight the button is disabled and label reads 'Wird gesendet…' with a 14px inline spinner. Secondary: bg=surface, fg=fg, 1px border, hover bg=code_bg, same size and states. Full width on mobile in the form.

### Textarea

bg=surface, 1px border, radius md, padding 12px, font 15px, min-height 160px, vertical resize only. Hover border #D1D5DB; focus border accent + 3px focus_ring; error state border=danger. Label above (13px/600) 'Text'. Placeholder in muted. Typing state is never reset by polling or re-renders. Below right: char counter '0 / 20000' in mono 12px muted, turns danger above 20000.

### Select

Native <select> styled like Textarea: height 44px, padding 0 12px, radius md, 1px border, custom chevron icon, same hover/focus/disabled states. Label 'Analyse'. Options exactly: 'Wörter zählen' (word_count), 'Häufigste Wörter' (top_words), 'Lesezeit schätzen' (reading_time). Default is the first option.

### FieldError

Inline message under a field: 13px, color=danger, with a 14px alert icon, role=alert. Shown ONLY after the user tried to submit with invalid input (e.g. 'Bitte gib einen Text ein.'); never on initial render or while untouched; disappears once the field is valid. Nothing is sent to the API in the error case.

### StatusBadge

Pill (radius pill), padding 2px 10px, font 12px/600, height 24px, with a 6px leading dot. Labels in German: 'wartend' (bg status_pending_bg, fg status_pending_fg), 'in Arbeit' (status_running_*, dot pulses 1.2s), 'fertig' (status_done_*), 'fehlgeschlagen' (status_failed_*). Status is conveyed by label plus color, never color alone.

### JobCard

One row/card per job: bg=surface, 1px border, radius lg, padding 16px, gap 12px between rows, hover border #D1D5DB. Header row: id in mono '#42' (muted, 13px), analysis label (13px/500, e.g. 'Häufigste Wörter'), StatusBadge right-aligned, timestamp below/next in muted 12px. Body: text preview (max 140 chars, ellipsis, 2-line clamp, fg 15px) rendered as plain escaped text node. Footer: ResultBlock or ErrorBlock separated by 1px top border. Newly created jobs get a 300ms fade-in highlight (accent_soft background fading out); status changes update in place without remounting.

### ResultBlock

Readable result in code_bg box, radius md, padding 12px, 14px. word_count: 'Wörter: 42' (figure in mono 600). reading_time: 'ca. 1,2 Min.' plus muted '(240 Wörter)'. top_words: ordered list of up to 5 rows 'word … count' with word in 500 weight and count in mono right-aligned, small horizontal proportion bar (accent_soft fill, 4px high) behind the count. Pending/running jobs show muted placeholder 'Ergebnis folgt…' (running: with small spinner). All values are text nodes, never HTML.

### ErrorBlock

For failed jobs: bg=danger_bg, fg=status_failed_fg, 1px border #FECACA, radius md, padding 12px, 14px; prefix 'Fehler:' in 600 followed by the short error message as plain text. No stacktrace, no paths, no job text.

### StatTile

Compact KPI tile: bg=surface, 1px border, radius lg, padding 16px. Label (12px uppercase muted, letter-spacing .04em), value in mono 24px/600, small colored dot matching the status color. Four tiles: Wartend, In Arbeit, Fertig, Fehlgeschlagen — counts derived from the loaded job list, updated on each poll. Number format de-DE.

### ErrorBanner

Non-blocking notice at the top of the content area (not a modal, does not hide content): bg=danger_bg, 1px border #FECACA, radius md, padding 12px 16px, alert icon, text 'Verbindung zur API fehlgeschlagen. Neuer Versuch in wenigen Sekunden …', role=status/aria-live=polite. The job list stays visible with the last known data. Disappears automatically (200ms fade) after the next successful poll.

### EmptyState

Centered inside a dashed-border (1px dashed border) card, padding 48px 24px: 40px muted icon, heading 'Noch keine Jobs' (18px/600), hint 'Lege links einen Text an, um die erste Analyse zu starten.' (muted). No action button needed (the form is next to it); on mobile hint says 'oben'.

### JobCardSkeleton

Initial-load placeholder: 3 cards of the JobCard dimensions with shimmering grey bars (code_bg to border, 1.4s), shown only until the first fetch completes.

### AppHeader

Top bar 64px high, bg=surface, 1px bottom border. Left: 28px accent rounded-square logo mark + product name 'Job-Verarbeitung' (18px/600). Right: live indicator pill 'Aktualisiert alle 3 Sekunden' with a small green dot (turns danger-colored dot and 'Offline' when the last poll failed). Not sticky on mobile.

### Card

Generic container: bg=surface, 1px border, radius lg, padding 24px (16px on mobile), no heavy shadow (optional 0 1px 2px rgba(17,24,39,.04)). Card title 18px/600 with optional muted subtitle 13px.

## Layout Principles

- Container max-width 1120px, centered, horizontal padding 24px (16px below 640px); page bg=bg, cards on surface.
- Breakpoints: mobile <640px (single column, full-width buttons), tablet 640-1023px (single column, stat tiles 4 across), desktop >=1024px (two columns: form 380px fixed + list fluid, gap 24px).
- Spacing uses only the scale 4/8/12/16/24/32/48; vertical gap between page sections 24px, between job cards 12px.
- Every interactive element has a minimum touch/click target of 44px height and a visible focus-visible ring.
- Dates and times: always shown in the user's local time as 'TT.MM.JJJJ, HH:mm' (24h, de-DE, e.g. '07.03.2025, 14:05'), derived from the ISO 8601 UTC string; no seconds. Job ids as '#<int>' in the mono font.
- Numbers and amounts use de-DE formatting (decimal comma, thousands separator '.'); reading time as 'ca. 1,2 Min.' (one decimal); counts as plain integers; character counter as '1.234 / 20.000'.
- All user-provided content (text, result, error) is rendered as plain text nodes only; long words wrap with overflow-wrap:anywhere.
- Polling updates must not reset form state, scroll position or focus; list updates happen in place keyed by job id.
- No third-party assets: fonts, icons (inline SVG) and scripts are all served from the own origin.
- Motion is subtle (150-300ms) and respects prefers-reduced-motion by disabling pulse/shimmer/fade.
