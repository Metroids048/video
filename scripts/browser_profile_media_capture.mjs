#!/usr/bin/env node

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { spawn } from "node:child_process";

const args = process.argv.slice(2);
const arg = (name, fallback = undefined) => {
  const index = args.indexOf(name);
  return index >= 0 && args[index + 1] !== undefined ? args[index + 1] : fallback;
};

const videoUrl = arg("--url");
const videoId = arg("--video-id");
const outDir = path.resolve(arg("--out-dir", "."));
const segmentSeconds = Math.max(15, Number(arg("--segment-seconds", "90")) || 90);
const profileDir = process.env.AVS_BROWSER_PROFILE_DIR;

const emit = (payload, code = 0) => {
  process.stdout.write(JSON.stringify(payload) + "\n");
  process.exitCode = code;
};

const run = (command, commandArgs) => new Promise((resolve, reject) => {
  const child = spawn(command, commandArgs, { stdio: ["ignore", "pipe", "pipe"], windowsHide: true });
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", chunk => { stdout += chunk; });
  child.stderr.on("data", chunk => { stderr += chunk; });
  child.on("error", reject);
  child.on("close", code => resolve({ code, stdout, stderr }));
});

const loadPlaywright = () => {
  const candidates = [
    process.env.AVS_PLAYWRIGHT_CORE_PATH,
    path.join(os.homedir(), ".cache", "codex-runtimes", "codex-primary-runtime", "dependencies", "node", "node_modules", "playwright-core"),
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      const req = createRequire(path.join(candidate, "package.json"));
      return req("playwright-core");
    } catch (_) {
      // Try the next runtime location.
    }
  }
  try {
    return createRequire(import.meta.url)("playwright-core");
  } catch (_) {
    throw new Error("playwright-core is unavailable; set AVS_PLAYWRIGHT_CORE_PATH");
  }
};

const chromePath = process.env.AVS_CHROME_EXECUTABLE || (
  process.platform === "win32"
    ? "C:/Program Files/Google/Chrome/Application/chrome.exe"
    : "google-chrome"
);

async function waitForAdToFinish(page) {
  let adDetected = false;
  let adSkipped = false;
  for (let i = 0; i < 60; i += 1) {
    const state = await page.evaluate(() => ({
      showing: Boolean(document.querySelector(".ad-showing, .video-ads.ad-interrupting")),
      title: document.title,
    })).catch(() => ({ showing: false, title: "" }));
    if (!state.showing) return { adDetected, adSkipped };
    adDetected = true;
    const skip = page.locator(".ytp-ad-skip-button, .ytp-ad-skip-button-modern").first();
    if (await skip.count().catch(() => 0)) {
      await skip.click().catch(() => {});
      adSkipped = true;
      continue;
    }
    await page.waitForTimeout(1000);
  }
  return { adDetected, adSkipped };
}

async function main() {
  if (!videoUrl || !videoId) return emit({ ok: false, error_code: "INVALID_ARGUMENT", retryable: false }, 2);
  if (!profileDir) return emit({ ok: false, error_code: "BROWSER_PROFILE_UNAVAILABLE", retryable: true }, 2);
  await fs.mkdir(outDir, { recursive: true });
  const mergedPath = path.join(outDir, `${videoId}.browser.wav`);
  try {
    const existing = await fs.stat(mergedPath);
    if (existing.size > 4096) return emit({ ok: true, path: mergedPath, source: "REAL_MEDIA", access_mode: "BROWSER_PROFILE_MEDIA_CAPTURE", resumed: true });
  } catch (_) {}

  const chunksDir = path.join(outDir, "chunks");
  await fs.mkdir(chunksDir, { recursive: true });
  const { chromium } = loadPlaywright();
  let context;
  let launchError;
  for (let attempt = 0; attempt < 4 && !context; attempt += 1) {
    try {
      context = await chromium.launchPersistentContext(profileDir, {
        executablePath: chromePath,
        headless: false,
        args: ["--profile-directory=" + (process.env.AVS_BROWSER_PROFILE_NAME || "Profile"), "--disable-blink-features=AutomationControlled"],
      });
    } catch (error) {
      launchError = error;
      if (attempt < 3) await new Promise(resolve => setTimeout(resolve, 8000));
    }
  }
  if (!context) throw launchError || new Error("BROWSER_PROFILE_LAUNCH_FAILED");
  const page = context.pages()[0] || await context.newPage();
  const writeChunk = async (name, b64) => {
    await fs.appendFile(path.join(chunksDir, name), Buffer.from(b64, "base64"));
  };
  await page.exposeFunction("avsWriteChunk", writeChunk);
  try {
    await page.goto(videoUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(5000);
    const ad = await waitForAdToFinish(page);
    const state = await page.evaluate(() => {
      const response = window.ytplayer?.getPlayerResponse?.() || window.ytInitialPlayerResponse || {};
      const video = document.querySelector("video");
      return {
        id: response.videoDetails?.videoId,
        duration: Number(response.videoDetails?.lengthSeconds || video?.duration || 0),
        hasCaptureStream: Boolean(video?.captureStream),
        hasAudio: Boolean(video?.captureStream?.().getAudioTracks?.().length),
        title: response.videoDetails?.title || document.title,
      };
    });
    if (state.id && state.id !== videoId) throw new Error(`VIDEO_ID_MISMATCH:${state.id}`);
    if (!state.duration || !state.hasCaptureStream || !state.hasAudio) throw new Error("REAL_MEDIA_UNAVAILABLE");
    const totalSegments = Math.ceil(state.duration / segmentSeconds);
    const existingWavs = new Set((await fs.readdir(chunksDir)).filter(name => /^part-\d+\.wav$/.test(name)));
    for (let index = 0; index < totalSegments; index += 1) {
      const start = index * segmentSeconds;
      const end = Math.min(state.duration, start + segmentSeconds);
      const wavName = `part-${String(index).padStart(4, "0")}.wav`;
      if (existingWavs.has(wavName)) continue;
      const webmName = `part-${String(index).padStart(4, "0")}.webm`;
      const webmPath = path.join(chunksDir, webmName);
      await fs.rm(webmPath, { force: true });
      const result = await page.evaluate(async ({ start, end, webmName }) => {
        const video = document.querySelector("video");
        video.pause();
        video.muted = false;
        video.volume = 1;
        video.currentTime = start;
        await new Promise(resolve => setTimeout(resolve, 250));
        const tracks = video.captureStream().getAudioTracks();
        if (!tracks.length) return { error: "NO_AUDIO_TRACK" };
        const recorder = new MediaRecorder(new MediaStream(tracks), { mimeType: "audio/webm;codecs=opus", audioBitsPerSecond: 128000 });
        let queue = Promise.resolve();
        let bytes = 0;
        recorder.ondataavailable = event => {
          if (!event.data.size) return;
          queue = queue.then(async () => {
            const array = new Uint8Array(await event.data.arrayBuffer());
            let binary = "";
            for (let i = 0; i < array.length; i += 0x8000) binary += String.fromCharCode(...array.subarray(i, i + 0x8000));
            await window.avsWriteChunk(webmName, btoa(binary));
            bytes += array.length;
          });
        };
        const stopped = new Promise(resolve => { recorder.onstop = async () => { await queue; resolve({ bytes, currentTime: video.currentTime }); }; });
        recorder.start(1000);
        await video.play();
        const deadline = Date.now() + Math.max(120000, (end - start) * 3000);
        while (video.currentTime < end - 0.25 && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 300));
        video.pause();
        recorder.stop();
        return await stopped;
      }, { start, end, webmName });
      if (result.error || !result.bytes) throw new Error(result.error || "EMPTY_CAPTURE_SEGMENT");
      const converted = await run("ffmpeg", ["-y", "-v", "error", "-i", webmPath, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", path.join(chunksDir, wavName)]);
      if (converted.code !== 0) throw new Error("FFMPEG_SEGMENT_FAILED");
    }
    const listPath = path.join(chunksDir, "concat.txt");
    const wavNames = (await fs.readdir(chunksDir)).filter(name => /^part-\d+\.wav$/.test(name)).sort();
    if (!wavNames.length) throw new Error("NO_CAPTURE_SEGMENTS");
    await fs.writeFile(listPath, wavNames.map(name => `file '${path.join(chunksDir, name).replaceAll("'", "'\\''")}'`).join("\n") + "\n", "utf8");
    const merged = await run("ffmpeg", ["-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", listPath, "-c", "copy", mergedPath]);
    if (merged.code !== 0) throw new Error("FFMPEG_MERGE_FAILED");
    const probe = await run("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", mergedPath]);
    const duration = Number.parseFloat(probe.stdout.trim());
    if (!Number.isFinite(duration) || duration <= 0) throw new Error("MERGED_AUDIO_INVALID");
    emit({ ok: true, path: mergedPath, source: "REAL_MEDIA", access_mode: "BROWSER_PROFILE_MEDIA_CAPTURE", duration, video_duration: state.duration, ad_detected: ad.adDetected, ad_skipped: ad.adSkipped, segments: wavNames.length });
  } catch (error) {
    emit({ ok: false, error_code: String(error?.message || error).slice(0, 160), retryable: true }, 2);
  } finally {
    await context.close().catch(() => {});
  }
}

main().catch(error => emit({ ok: false, error_code: String(error?.message || error).slice(0, 160), retryable: true }, 2));
