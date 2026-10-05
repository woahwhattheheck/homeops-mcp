# HomeOps recorded simulation

[Watch the captioned MP4](homeops-simulation.mp4) · [Public video publication packet](PUBLICATION_PACKET.md) · [English transcript](transcript.md) · [Source and file manifest](manifest.json) · [Actual HTTP interactions](interactions.json).

This is a real browser recording of the unchanged simulation at `16043242dc259e20e13cea0a51cf2cdb7526772a`, not a staged mockup or live Alexa/provider integration. Two fictional runs show the approve and reject branches of the real Dispatcher/HomeOpsLedger. Both five-event chains verify; external effects remain false. The MP4 is silent and has burned-in English captions; the SRT is also included. Duration: 97.68 seconds.

The workflow records the browser once; it does not run a test suite or modify application source. `capture.py` preserves the recording procedure; it requires Python, Playwright 1.57.0 with its FFmpeg helper, an installed Chromium browser, and system FFmpeg. Run from the source-pinned repository with a fresh output directory.

## Submission boundary

This GitHub-hosted MP4 is an entrant-ready artifact, not a submitted contest entry or a substitute for the required public YouTube/Vimeo URL. The original entrant still owns video-host publication, actual product feedback, eligibility/terms and registration/submission. Preserve the existing HomeOps versus Hearthline distinction. No provider was contacted, no account was changed, and no award or payment is asserted.
