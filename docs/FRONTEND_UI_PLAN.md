# ConseQ Frontend UI Plan

## Product direction

Build a polished operations console for exploring an architecture graph and reviewing what-if assessments. Keep the interface calm and readable, with glass panels and restrained glow used to signal focus and impact rather than decorate every surface.

## Main screen

- **Top bar:** ConseQ wordmark, graph/environment selector, backend health, and profile/settings menu.
- **Left rail:** searchable architecture entities, saved scenarios, and a compact legend for services, APIs, databases, providers, and teams.
- **Center canvas:** interactive dependency graph with pan/zoom, fit-to-view, label filters, and node selection. Use color and a soft glow on hover; use clear red/orange impact states during an outage result.
- **Right inspector:** selected node details, owning team, direct dependencies, and available actions.
- **Bottom prompt dock:** natural-language scenario input with a few preset chips and a clear run button.

## Simulation results

Open a results drawer or split panel after a run. Show the scenario and target first, followed by blast-radius score (for outage runs), impacted services/endpoints/clients, affected teams, and evidence-backed recommendations. Upgrade and recovery screens should be labeled as assessments until the backend executes those interventions. Do not display a recovery percentage while it is unmeasured.

## Visual system

- Dark navy/charcoal foundation with high-contrast text and a small set of semantic colors.
- Frosted glass panels: translucent surfaces, subtle backdrop blur, thin borders, and restrained shadows.
- Hover glow only on actionable controls and the currently focused graph node or edge.
- Short transitions for hover, selection, and drawer movement; respect `prefers-reduced-motion`.
- Keep graph labels and report text readable without relying on glow, blur, or color alone.
- Provide a light theme only after the dark theme’s contrast and graph states are established.

## Implementation sequence

1. Establish design tokens, app shell, responsive layout, and loading/error/empty states.
2. Connect health, graph stats, topology, preset scenarios, and simulation endpoints.
3. Add graph selection, filtering, zoom controls, and impact highlighting.
4. Build the results panel and render backend metrics, teams, and recommendations.
5. Add keyboard navigation, reduced-motion behavior, and accessibility checks; then tune glass and glow details.

## Suggested frontend stack

Use React with TypeScript and Vite, a graph visualization library such as `react-force-graph`, and CSS variables with a small component layer. Keep API types aligned with the Pydantic response schemas and surface request IDs in error details for support.
