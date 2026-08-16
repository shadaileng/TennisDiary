import { white, emptyCard, drawRadar, font, rr, wrap, GRAY, INK, LIME } from "../primitives";
import type { DrawStage } from "../pipeline";

const radarStage: DrawStage = {
  name: "techScore-radar",
  steps: [
    {
      name: "radar-empty",
      condition: (pipe) => pipe.tpl === "技术评分" && !pipe.latestAnalysis?.report,
      execute: (_ctx, _pipe, y) => {
        emptyCard(_ctx, "还没有分析报告，先去做一次分析吧～");
        return y;
      },
    },
    {
      name: "radar-hexagon",
      condition: (pipe) => {
        if (pipe.tpl !== "技术评分" || !pipe.latestAnalysis?.report) return false;
        const dims = (pipe.latestAnalysis.report.dimensions || []).slice(0, 6);
        return dims.length >= 3;
      },
      measure: (_y, pipe) => {
        const cfg = pipe.config.techScore;
        const r = pipe.latestAnalysis!.report!;
        const dims = (r.dimensions || []).slice(0, 6);
        const dimListH = dims.length * cfg.progressZone.itemHeight;
        const summaryH = r.summary ? cfg.summaryZone.height + 40 : 0;
        const totalH = cfg.radarZone.height + dimListH + summaryH + 40;
        return cfg.cardTop + totalH;
      },
      execute: (_ctx, pipe, _y) => {
        const r = pipe.latestAnalysis!.report!;
        const dims = (r.dimensions || []).slice(0, 6);
        const cfg = pipe.config.techScore;

        const dimListH = dims.length * cfg.progressZone.itemHeight;
        const summaryH = r.summary ? cfg.summaryZone.height + 40 : 0;
        const totalH = cfg.radarZone.height + dimListH + summaryH + 40;

        white(_ctx, 70, cfg.cardTop, 940, totalH);

        drawRadar(_ctx, cfg.radar.cx, cfg.radar.cy, cfg.radar.radius, dims);

        return cfg.cardTop + cfg.radarZone.height;
      },
    },
    {
      name: "score-ball-fallback",
      condition: (pipe) => {
        if (pipe.tpl !== "技术评分" || !pipe.latestAnalysis?.report) return false;
        const dims = (pipe.latestAnalysis.report.dimensions || []).slice(0, 6);
        return dims.length < 3;
      },
      execute: (_ctx, pipe, y) => {
        const a = pipe.latestAnalysis!;
        const cfg = pipe.config.techScore;

        white(_ctx, cfg.scoreBallCard.x, cfg.scoreBallCard.y, cfg.scoreBallCard.w, cfg.scoreBallCard.h);

        _ctx.fillStyle = LIME;
        _ctx.beginPath();
        _ctx.arc(cfg.radar.cx, cfg.scoreBall.cy, cfg.scoreBall.radius, 0, Math.PI * 2);
        _ctx.fill();

        _ctx.fillStyle = INK;
        _ctx.font = font(800, cfg.scoreBall.fontSize);
        _ctx.textAlign = "center";
        _ctx.fillText(String(a.score || "—"), cfg.radar.cx, cfg.scoreBall.cy + 40);
        _ctx.textAlign = "left";

        return y;
      },
    },
  ],
};

const progressStage: DrawStage = {
  name: "techScore-progress",
  steps: [
    {
      name: "progress-bars",
      condition: (pipe) => {
        if (pipe.tpl !== "技术评分" || !pipe.latestAnalysis?.report) return false;
        const dims = (pipe.latestAnalysis.report.dimensions || []).slice(0, 6);
        return dims.length >= 3;
      },
      measure: (_y, pipe) => {
        const r = pipe.latestAnalysis!.report!;
        const dims = (r.dimensions || []).slice(0, 6);
        const cfg = pipe.config.techScore;
        return cfg.progressZone.top + dims.length * cfg.progressZone.itemHeight;
      },
      execute: (_ctx, pipe, _y) => {
        const r = pipe.latestAnalysis!.report!;
        const dims = (r.dimensions || []).slice(0, 6);
        const cfg = pipe.config.techScore;

        let sy = cfg.progressZone.top;
        for (const d of dims) {
          _ctx.font = font(600, 28);
          _ctx.fillStyle = INK;
          _ctx.textAlign = "left";
          _ctx.fillText(d.name, cfg.dimNameX, sy);

          _ctx.font = font(700, 30);
          _ctx.fillStyle = LIME;
          _ctx.textAlign = "right";
          _ctx.fillText(String(d.score ?? 0), cfg.dimScoreX, sy);

          _ctx.fillStyle = "#E8E8E4";
          rr(_ctx, cfg.barX, sy + 12, cfg.barWidth, cfg.barHeight, cfg.barRadius);
          _ctx.fill();

          _ctx.fillStyle = LIME;
          rr(_ctx, cfg.barX, sy + 12, cfg.barWidth * Math.min(1, Number(d.score || 0) / 100), cfg.barHeight, cfg.barRadius);
          _ctx.fill();

          if (d.comment) {
            _ctx.font = font(400, cfg.commentFontSize);
            _ctx.fillStyle = "#7A8272";
            _ctx.textAlign = "left";
            const commentLines = wrap(_ctx, d.comment, 860);
            let cy = sy + cfg.commentStartOffset;
            for (const line of commentLines.slice(0, cfg.commentMaxLines)) {
              _ctx.fillText(line, cfg.dimNameX, cy);
              cy += cfg.commentLineHeight;
            }
          }
          sy += cfg.progressZone.itemHeight;
        }

        return sy;
      },
    },
  ],
};

const summaryStage: DrawStage = {
  name: "techScore-summary",
  steps: [
    {
      name: "summary-text",
      condition: (pipe) => {
        if (pipe.tpl !== "技术评分" || !pipe.latestAnalysis?.report) return false;
        return !!pipe.latestAnalysis!.summary;
      },
      measure: (y, pipe) => {
        const cfg = pipe.config.techScore;
        return y + cfg.summaryZone.height + 40;
      },
      execute: (_ctx, pipe, y) => {
        const cfg = pipe.config.techScore;

        const summaryTop = y + 40;

        _ctx.font = font(500, 28);
        _ctx.fillStyle = "#7A8272";
        _ctx.textAlign = "center";
        const lines = wrap(_ctx, pipe.latestAnalysis!.summary!, 860);
        let summaryY = summaryTop;
        for (const line of lines.slice(0, 2)) {
          _ctx.fillText(line, pipe.config.canvas.width / 2, summaryY);
          summaryY += cfg.summaryZone.lineHeight;
        }
        _ctx.textAlign = "left";

        return summaryTop + cfg.summaryZone.height;
      },
    },
  ],
};

export { radarStage, progressStage, summaryStage };
