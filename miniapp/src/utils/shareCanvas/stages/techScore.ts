import { white, emptyCard, drawRadar, font, rr, wrap, GRAY, INK, LIME } from "../primitives";
import type { DrawStage } from "../pipeline";

export const techScoreStage: DrawStage = {
  name: "techScore",
  steps: [
    {
      name: "empty-state",
      condition: (pipe) => pipe.tpl === "技术评分" && !pipe.latestAnalysis?.report,
      execute: (_ctx, _pipe, y) => {
        emptyCard(_ctx, "还没有分析报告，先去做一次分析吧～");
        return y;
      },
    },
    {
      name: "radar-with-dims",
      condition: (pipe) => {
        if (pipe.tpl !== "技术评分" || !pipe.latestAnalysis?.report) return false;
        const dims = (pipe.latestAnalysis.report.dimensions || []).slice(0, 6);
        return dims.length >= 3;
      },
      measure: (y, pipe) => {
        const r = pipe.latestAnalysis!.report!;
        const dims = (r.dimensions || []).slice(0, 6);
        const dimListH = dims.length * pipe.config.techScore.dimItemHeight;
        const summaryH = r.summary ? 50 : 0;
        return pipe.config.techScore.dimListTop + dimListH + summaryH + 30;
      },
      execute: (_ctx, pipe, y) => {
        const r = pipe.latestAnalysis!.report!;
        const dims = (r.dimensions || []).slice(0, 6);
        const cfg = pipe.config.techScore;

        const dimListH = dims.length * cfg.dimItemHeight;
        const summaryH = r.summary ? 50 : 0;
        const cardBottom = cfg.dimListTop + dimListH + summaryH + 30;

        white(_ctx, 70, cfg.cardTop, 940, cardBottom - cfg.cardTop);

        drawRadar(_ctx, cfg.radar.cx, cfg.radar.cy, cfg.radar.radius, dims);

        let sy = cfg.dimListTop;
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
          sy += cfg.dimItemHeight;
        }

        if (r.summary) {
          _ctx.font = font(500, 26);
          _ctx.fillStyle = "#7A8272";
          _ctx.textAlign = "center";
          const lines = wrap(_ctx, r.summary, 860);
          let summaryY = cfg.dimListTop + dimListH + 24;
          for (const line of lines.slice(0, 1)) {
            _ctx.fillText(line, pipe.config.canvas.width / 2, summaryY);
            summaryY += cfg.summaryLineHeight;
          }
        }

        _ctx.textAlign = "left";
        return cardBottom;
      },
    },
    {
      name: "score-ball",
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
