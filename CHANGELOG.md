# Changelog

## [0.3.0] - 2026-04-03

### Fixed
- Hover tooltip now snaps vertically (same logic as cursor mode), preventing spurious tooltips when the pointer is near the data in X but far in Y
- Zoom box snaps to full axis extent when the selection covers ≥85% of the axis width or height (Plotly-style behavior), for easy single-axis zoom
- Corrected snap/ratio evaluation order so a tall narrow drag box is treated as an X-only zoom rather than a vertical zoom
- Buttons are now hidden while a figure is being saved

### Changed
- Adjusted zoom aspect-ratio threshold for more intuitive horizontal/vertical zoom detection

## [0.2.0] - 2026-03-14

### Added
- Custom plot library support with `target_ax` parameter for directing plots to specific axes
- Hidden flag for curves to control visibility programmatically
- Scrollable sidebar for handling many curves
- Enable/disable toggle for individual plot curves
- Full zoom-out button to reset view
- Division line between subplots in fit view
- Show selected fit name near the equation text box in the fit window
- TEST_PLAN.md documenting manual test procedures

### Fixed
- Legend breaking zoom and running away from cursor
- Modebar overlapping bottom subplot axis labels

## [0.1.0] - 2024-01-01

### Added
- Initial release: interactive matplotlib toolbar with zoom, pan, link-X, grid, log scale
- Curve fitting with multiple fit types
- Hover tooltips
- SI units support on axes
- Optional footer
- Simple and improved cursor modes
