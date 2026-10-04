"""Record the shipped local simulation; do not replace its UI or responses."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

BASE = "16043242dc259e20e13cea0a51cf2cdb7526772a"
OUT = Path("docs/demo/2026-10-04")
OUT.mkdir(parents=True, exist_ok=False)
RAW = Path("recording-evidence")
RAW.mkdir(exist_ok=True)
subprocess.run(["git", "diff", "--exit-code", BASE, "--", "homeops_relay"], check=True)
responses, blocked, scenes = [], [], []
server_log = (RAW / "server.log").open("w")
server = subprocess.Popen([sys.executable, "-u", "-m", "homeops_relay.simulation", "--port", "8765"], stdout=server_log, stderr=subprocess.STDOUT)
try:
    for attempt in range(100):
        if server.poll() is not None:
            raise RuntimeError("simulation server exited")
        try:
            with urlopen("http://127.0.0.1:8765/", timeout=1) as reply:
                if reply.status == 200:
                    break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("simulation server did not start")
    with sync_playwright() as pw:
        executable = os.environ.get("CHROME_BIN") or shutil.which("google-chrome") or shutil.which("chromium")
        if not executable:
            raise RuntimeError("no installed Chromium browser")
        browser = pw.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(RAW / "raw-video"), record_video_size={"width": 1280, "height": 720}, reduced_motion="reduce")
        def route(request):
            if request.request.url.startswith("http://127.0.0.1:8765/"):
                request.continue_()
            else:
                blocked.append(request.request.url)
                request.abort()
        context.route("**/*", route)
        started = time.monotonic()
        page = context.new_page()
        video = page.video
        def response(reply):
            if "/api/" in reply.url:
                responses.append({"elapsed": round(time.monotonic()-started, 3), "path": reply.url.split("8765", 1)[-1], "request": reply.request.post_data_json, "status": reply.status, "body": reply.json()})
        page.on("response", response)
        page.goto("http://127.0.0.1:8765/", wait_until="networkidle")
        page.locator("#status .banner").wait_for()
        def hold(text, seconds, shot):
            begin = time.monotonic()-started
            page.screenshot(path=str(RAW / (shot + ".png")))
            page.wait_for_timeout(seconds * 1000)
            scenes.append({"start": round(begin, 3), "end": round(time.monotonic()-started, 3), "caption": text, "screenshot": shot + ".png"})
        def click(selector):
            with page.expect_response(lambda r: r.url.endswith("/api/step") or r.url.endswith("/api/reset")) as result:
                page.locator(selector).click()
            assert result.value.status == 200
            page.wait_for_timeout(350)
            return result.value.json()
        def focus(title):
            card = page.locator("#status .card").filter(has=page.get_by_role("heading", name=title, exact=True))
            card.evaluate("e => e.scrollIntoView({block:'center',behavior:'instant'})")
            page.wait_for_timeout(250)
        hold("HomeOps Relay: a fictional Alexa+ workflow.\nThis is the actual local browser app, not a live Alexa or provider connection.", 7, "01-introduction")
        click('[data-step="intake"]'); focus("Issue intake")
        hold("Capture what was observed and its evidence.\nA water leak is recorded without inventing a diagnosis.", 7, "02-observation")
        click('[data-step="quotes"]'); focus("Synthetic quotes")
        hold("Compare $245 and $310 example quotes.\nBoth remain explicitly synthetic and unverified.", 9, "03-quotes")
        click('[data-step="plan"]'); focus("Deterministic plan")
        hold("Build the plan from the retained case and quote evidence.\nPlanning does not choose or contact a provider.", 10, "04-plan")
        pending = click('[data-step="request"]'); focus("Contact proposal")
        assert pending["action"]["state"] == "PENDING_OWNER_REVIEW"
        hold("The proposed contact stops at PENDING_OWNER_REVIEW.\nNothing has been sent, booked, purchased or paid.", 10, "05-review")
        approved = click('[data-decision="APPROVE"]'); focus("Owner decision")
        assert approved["decision"]["state"] == "APPROVED_NOT_EXECUTED"
        hold("The fictional owner approves the proposal.\nThe ledger records APPROVED_NOT_EXECUTED, not a completed external action.", 10, "06-approval")
        approval_receipt = click('[data-step="snapshot"]'); focus("Replay-verifiable receipt")
        assert approval_receipt["verification"]["verified"] is True
        assert approval_receipt["event_count"] == 5
        assert approval_receipt["snapshot"]["authority"]["external_effect"] is False
        hold("Replay verifies all five events and exposes the receipt digest.\nVerification proves this local event chain, not contractor work or payment.", 10, "07-approval-receipt")
        click("#reset")
        for step in ("intake", "quotes", "plan", "request"):
            click('[data-step="' + step + '"]')
            page.wait_for_timeout(500)
        rejected = click('[data-decision="REJECT"]'); focus("Owner decision")
        assert rejected["decision"]["state"] == "REJECTED"
        hold("A separate reset of the fictional scenario demonstrates rejection.\nThe proposal becomes REJECTED and still has no external effect.", 9, "08-rejection")
        rejection_receipt = click('[data-step="snapshot"]'); focus("Replay-verifiable receipt")
        assert rejection_receipt["verification"]["verified"] is True
        assert rejection_receipt["event_count"] == 5
        assert rejection_receipt["snapshot"]["authority"]["external_effect"] is False
        hold("The rejection also produces a replay-verifiable receipt.\nObservation, provenance, owner control and an inspectable record stay together.", 9, "09-rejection-receipt")
        hold("Recorded from HomeOps source 16043242 on October 4, 2026.\nSimulation only: no external service, account, booking or payment was used.", 6, "10-close")
        context.close()
        raw_video = Path(video.path())
        browser.close()
finally:
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill(); server.wait()
    server_log.close()

assert not blocked, blocked
assert len(responses) == 14, len(responses)
(OUT / "interactions.json").write_text(json.dumps(responses, indent=2) + "\n")
(OUT / "scenes.json").write_text(json.dumps(scenes, indent=2) + "\n")
def stamp(value):
    total = int(round(value * 1000))
    return f"{total//3600000:02}:{total//60000%60:02}:{total//1000%60:02},{total%1000:03}"
srt = "\n\n".join(f"{i}\n{stamp(s['start'])} --> {stamp(s['end'])}\n{s['caption']}" for i, s in enumerate(scenes, 1)) + "\n"
(OUT / "captions.srt").write_text(srt)
(OUT / "transcript.md").write_text("# HomeOps Relay: recorded simulation\n\nEnglish captions for the actual browser walkthrough. Source: `" + BASE + "`.\n\n" + "\n\n".join(f"## {stamp(s['start'])}\n\n{s['caption'].replace(chr(10), ' ')}" for s in scenes) + "\n")
movie = OUT / "homeops-simulation.mp4"
subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(raw_video), "-vf", "pad=1280:832:0:0:black,subtitles=" + str(OUT / "captions.srt") + ":force_style='FontName=DejaVu Sans,FontSize=18,Outline=1,Alignment=2,MarginV=10'", "-an", "-r", "25", "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(movie)], check=True)
probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(movie)]))
duration = float(probe["format"]["duration"])
assert 80 < duration < 180, duration
shutil.copy2(__file__, OUT / "capture.py")
shutil.copy2(RAW / "07-approval-receipt.png", OUT / "approval-receipt.png")
shutil.copy2(RAW / "08-rejection.png", OUT / "rejection.png")
manifest = {"source_commit":BASE, "workflow_run":os.environ.get("GITHUB_RUN_ID"), "workflow_commit":os.environ.get("GITHUB_SHA"), "duration_seconds":duration, "video_width":1280, "video_height":832, "captions_language":"en", "audio":False, "method":"Playwright video of the unchanged local simulation; FFmpeg adds a separate English caption band", "browser_external_requests":len(blocked), "interaction_count":len(responses), "approval":{"state":approved["decision"]["state"], "events":approval_receipt["event_count"], "verified":approval_receipt["verification"]["verified"], "receipt":approval_receipt["event_receipt"]}, "rejection":{"state":rejected["decision"]["state"], "events":rejection_receipt["event_count"], "verified":rejection_receipt["verification"]["verified"], "receipt":rejection_receipt["event_receipt"]}, "external_effect":False, "files":{p.name:{"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in sorted(OUT.iterdir()) if p.is_file()}}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
(OUT / "README.md").write_text("# HomeOps recorded simulation\n\n[Watch the captioned MP4](homeops-simulation.mp4) · [English transcript](transcript.md) · [Source and file manifest](manifest.json) · [Actual HTTP interactions](interactions.json).\n\nThis is a real browser recording of the unchanged simulation at `" + BASE + "`, not a staged mockup or live Alexa/provider integration. Two fictional runs show the approve and reject branches of the real Dispatcher/HomeOpsLedger. Both five-event chains verify; external effects remain false. The MP4 is silent and has burned-in English captions; the SRT is also included. Duration: " + str(round(duration, 2)) + " seconds.\n\nThe workflow records the browser once; it does not run a test suite or modify application source. `capture.py` preserves the recording procedure; it requires Python, Playwright 1.57.0 with its FFmpeg helper, an installed Chromium browser, and system FFmpeg. Run from the source-pinned repository with a fresh output directory.\n\n## Submission boundary\n\nThis GitHub-hosted MP4 is an entrant-ready artifact, not a submitted contest entry or a substitute for the required public YouTube/Vimeo URL. The original entrant still owns video-host publication, actual product feedback, eligibility/terms and registration/submission. Preserve the existing HomeOps versus Hearthline distinction. No provider was contacted, no account was changed, and no award or payment is asserted.\n")
print(json.dumps(manifest, indent=2))
