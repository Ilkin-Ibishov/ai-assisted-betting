#!/usr/bin/env node

import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");
const requireFromDashboard = createRequire(
  path.join(projectRoot, "dashboard", "package.json"),
);
const { chromium } = requireFromDashboard("playwright");

const DEFAULT_URL = "https://www.misli.az/idman-novleri/futbol";
const DEFAULT_SPORT = "football";
const DEFAULT_TIMEOUT_MS = 30_000;

const args = parseArgs(process.argv.slice(2));
const url = args.url ?? DEFAULT_URL;
const sport = args.sport ?? DEFAULT_SPORT;
const outPath = args.out ? path.resolve(process.cwd(), args.out) : null;
const postUrl = args.postUrl ?? null;
const token = args.token ?? process.env.SNAPSHOT_INGEST_TOKEN ?? null;

assertAllowedPublicMisliUrl(url);
if (postUrl) assertAllowedSnapshotPostUrl(postUrl);
if (postUrl && !token) {
  throw new Error("--token or SNAPSHOT_INGEST_TOKEN is required with --post-url.");
}

const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage({
    locale: "az-AZ",
    timezoneId: "Asia/Baku",
  });

  await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: DEFAULT_TIMEOUT_MS,
  });
  await page.waitForSelector(".bulletinItemRow", { timeout: DEFAULT_TIMEOUT_MS });
  await page.waitForSelector(".odssRate .oddValue", { timeout: DEFAULT_TIMEOUT_MS });
  await page.waitForTimeout(2_000);

  const snapshot = await page.evaluate(
    ({ pageUrl, sportName }) => {
      const clean = (value) => (value || "").replace(/\s+/g, " ").trim();
      const numericOdd = (value) => {
        const normalized = clean(value).replace(",", ".");
        if (normalized === "-") return null;
        const parsed = Number.parseFloat(normalized);
        return Number.isFinite(parsed) ? parsed : null;
      };
      const eventIdFromHref = (href) => {
        const match = clean(href).match(/\/([^/?#]+)(?:[?#].*)?$/);
        return match?.[1] || null;
      };
      const selectionMap = new Map([
        ["1", "HOME"],
        ["X", "DRAW"],
        ["2", "AWAY"],
      ]);
      const marketFromLabel = (label) => {
        if (selectionMap.has(label)) return "1X2";
        if (/ALT|UST|ÜST/.test(label)) return "OVER_UNDER_2_5";
        return "UNKNOWN";
      };
      const selectionFromLabel = (label) => selectionMap.get(label) || label;

      const events = [];
      const skippedRows = [];
      let currentDateLabel = null;
      let currentDate = null;
      let currentLeague = null;

      for (const node of Array.from(document.querySelectorAll(".bulletinLeagueWrapper, .bulletinItemRow"))) {
        if (node.classList.contains("bulletinLeagueWrapper")) {
          currentDateLabel = clean(node.querySelector(".dateText, .bulletinDay")?.textContent);
          currentDate = clean(node.querySelector(".fullDate")?.textContent);
          currentLeague = clean(
            node.querySelector(".leagueName, .bulletinLeagueName, h4, span:last-child")?.textContent,
          );
          const nodeText = clean(node.textContent);
          if (!currentLeague && nodeText) {
            currentLeague = nodeText.replace(currentDateLabel || "", "").replace(currentDate || "", "").trim();
          }
          continue;
        }

        const eventId = node.getAttribute("data-event-id") || null;
        const href = node.querySelector("a[href*='idman-novleri-canli-merc-teferruati']")?.href || null;
        const homeTeam = clean(node.querySelector(".bulletinHomeTeam")?.textContent);
        const awayTeam = clean(node.querySelector(".bulletinAwayTeam")?.textContent);
        const kickoffTime = clean(node.querySelector(".bulletinDate")?.textContent);
        const rowLeague = clean(node.querySelector(".bulletinTime")?.getAttribute("data-tooltip"));

        if (!eventId || !homeTeam || !awayTeam || !kickoffTime) {
          skippedRows.push({
            reason: "missing event id, team, or kickoff time",
            raw_text: clean(node.textContent),
          });
          continue;
        }

        const odds = Array.from(node.querySelectorAll(".odssRate"))
          .map((oddNode, oddIndex) => {
            const label = clean(oddNode.querySelector(".oddName, .marketType, .oddType")?.textContent)
              || ["1", "X", "2"][oddIndex]
              || "";
            const currentText = clean(oddNode.querySelector(".oddValue")?.textContent);
            const previousText = clean(oddNode.querySelector(".prevOdd strong")?.textContent);
            const finalText = clean(oddNode.querySelector(".currentOdd strong")?.textContent);
            const oddsDecimal = numericOdd(currentText || finalText);

            if (!label || oddsDecimal === null) {
              return null;
            }

            return {
              market: marketFromLabel(label),
              selection: selectionFromLabel(label),
              label,
              odds_decimal: oddsDecimal,
              previous_odds_decimal: numericOdd(previousText),
              final_odds_decimal: numericOdd(finalText),
              raw_text: clean(oddNode.textContent),
            };
          })
          .filter(Boolean);
        const primaryOdds = odds.filter((odd) => odd.market === "1X2");
        const primarySelections = new Set(primaryOdds.map((odd) => odd.selection));
        if (
          !["HOME", "DRAW", "AWAY"].every((selection) => primarySelections.has(selection))
          || primaryOdds.some((odd) => odd.odds_decimal <= 1)
        ) {
          skippedRows.push({
            reason: "missing or non-actionable 1X2 odds",
            raw_text: clean(node.textContent),
          });
          continue;
        }

        events.push({
          source: "misli_public",
          sport: sportName,
          event_id: eventId,
          source_match_id: `misli:${sportName}:${eventId}`,
          detail_url: href,
          home_team: homeTeam,
          away_team: awayTeam,
          kickoff_date_label: currentDateLabel,
          kickoff_date: currentDate,
          kickoff_time: kickoffTime,
          league: rowLeague || currentLeague,
          odds,
          raw_text: clean(node.textContent),
        });
      }

      return {
        source: "misli_public",
        page_url: pageUrl,
        scraped_at: new Date().toISOString(),
        title: document.title,
        event_count: events.length,
        extraction_summary: {
          row_count: document.querySelectorAll(".bulletinItemRow").length,
          event_count: events.length,
          skipped_rows_count: skippedRows.length,
          skipped_rows: skippedRows.slice(0, 20),
        },
        events,
      };
    },
    { pageUrl: url, sportName: sport },
  );

  const json = `${JSON.stringify(snapshot, null, 2)}\n`;
  if (outPath) {
    await mkdir(path.dirname(outPath), { recursive: true });
    await writeFile(outPath, json, "utf8");
  } else if (!postUrl) {
    process.stdout.write(json);
  }
  if (postUrl) {
    await postSnapshot(postUrl, token, snapshot);
  }
} finally {
  await browser.close();
}

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--url") parsed.url = argv[++index];
    else if (arg === "--sport") parsed.sport = argv[++index];
    else if (arg === "--out") parsed.out = argv[++index];
    else if (arg === "--post-url") parsed.postUrl = argv[++index];
    else if (arg === "--token") parsed.token = argv[++index];
    else if (arg === "--help" || arg === "-h") {
      process.stdout.write(
        [
          "Usage: node tools/misli-public-snapshot.mjs [--url URL] [--sport NAME] [--out PATH] [--post-url URL] [--token TOKEN]",
          "",
          "Collects a read-only JSON snapshot from public unauthenticated Misli.az sports pages.",
          "When --post-url is provided, posts the snapshot JSON to the API snapshot ingest endpoint.",
        ].join("\n"),
      );
      process.exit(0);
    }
  }
  return parsed;
}

async function postSnapshot(postUrl, bearerToken, snapshot) {
  const response = await fetch(postUrl, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${bearerToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(snapshot),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Snapshot POST failed: ${response.status} ${response.statusText} ${body}`);
  }
  process.stdout.write(`snapshot_posted=${postUrl}\n`);
}

function assertAllowedPublicMisliUrl(candidateUrl) {
  const parsed = new URL(candidateUrl);
  const allowedHost = parsed.hostname === "www.misli.az" || parsed.hostname === "misli.az";
  const blockedPathPatterns = [
    /^\/hesabim(?:\/|$)/,
    /^\/uyelik(?:\/|$)/,
    /^\/sayt-parametrleri/,
    /^\/idman-novleri-canli-merc-detal(?:\/|$)/,
    /^\/paylasilan-kupon(?:\/|$)/,
  ];

  if (parsed.protocol !== "https:" || !allowedHost) {
    throw new Error("Only https://www.misli.az public pages are allowed.");
  }
  if (blockedPathPatterns.some((pattern) => pattern.test(parsed.pathname))) {
    throw new Error(`Blocked Misli.az path for public snapshot: ${parsed.pathname}`);
  }
}

function assertAllowedSnapshotPostUrl(candidateUrl) {
  const parsed = new URL(candidateUrl);
  if (
    parsed.protocol !== "https:"
    && parsed.hostname !== "127.0.0.1"
    && parsed.hostname !== "localhost"
  ) {
    throw new Error("Snapshot post URL must be HTTPS, localhost, or 127.0.0.1.");
  }
  if (!/^\/api\/live\/snapshots\/latest\//.test(parsed.pathname)) {
    throw new Error("Snapshot post URL must target /api/live/snapshots/latest/<provider>.");
  }
}
