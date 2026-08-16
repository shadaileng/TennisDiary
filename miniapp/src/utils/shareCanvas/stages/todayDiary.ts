import { white, emptyCard, font, GRAY, INK } from "../primitives";
import type { DrawStage } from "../pipeline";

export const todayDiaryStage: DrawStage = {
  name: "todayDiary",
  steps: [
    {
      name: "empty-state",
      condition: (pipe) => pipe.tpl === "今日日记" && !pipe.latestDiary,
      measure: (_y, _pipe) => {
        // 空状态：emptyCard 高度 700，从 y=480 到 1180
        return 1180;
      },
      execute: (_ctx, _pipe, y) => {
        emptyCard(_ctx, "还没有日记，先记一篇吧～");
        return 1180;
      },
    },
    {
      name: "diary-content",
      condition: (pipe) => pipe.tpl === "今日日记" && !!pipe.latestDiary,
      measure: (_y, _pipe) => {
        // 今日日记：复盘卡片从 y=800 开始，高度 400，到 1200
        return 1200;
      },
      execute: (_ctx, pipe, y) => {
        const d = pipe.latestDiary!;
        const cfg = pipe.config.todayDiary;
        const inten = pipe.INTENSITY.find((i) => i.v === d.intensity);
        const mood = pipe.MOOD.find((m) => m.v === d.mood);

        white(_ctx, cfg.intensityCard.x, cfg.intensityCard.y, cfg.intensityCard.w, cfg.intensityCard.h);
        _ctx.fillStyle = GRAY;
        _ctx.font = font(500, 30);
        _ctx.fillText("运动强度", cfg.intensityCard.x + 50, cfg.labelY);
        _ctx.font = "76px sans-serif";
        _ctx.fillText(inten?.emoji ?? "", cfg.intensityCard.x + 50, cfg.emojiY);
        _ctx.fillStyle = INK;
        _ctx.font = font(700, 44);
        _ctx.fillText(inten?.label ?? "", cfg.intensityCard.x + 170, cfg.labelValueY);

        white(_ctx, cfg.moodCard.x, cfg.moodCard.y, cfg.moodCard.w, cfg.moodCard.h);
        _ctx.fillStyle = GRAY;
        _ctx.font = font(500, 30);
        _ctx.fillText("心情", cfg.moodCard.x + 50, cfg.labelY);
        _ctx.font = "76px sans-serif";
        _ctx.fillText(mood?.emoji ?? "", cfg.moodCard.x + 50, cfg.emojiY);
        _ctx.fillStyle = INK;
        _ctx.font = font(700, 44);
        _ctx.fillText(mood?.label ?? "", cfg.moodCard.x + 170, cfg.labelValueY);

        white(_ctx, cfg.reviewCard.x, cfg.reviewCard.y, cfg.reviewCard.w, cfg.reviewCard.h);
        _ctx.fillStyle = GRAY;
        _ctx.font = font(500, 30);
        _ctx.fillText("今日复盘", cfg.reviewCard.x + 50, cfg.reviewTitleY);

        _ctx.fillStyle = INK;
        _ctx.font = font(400, 38);
        const text = d.notes || "专注每一次挥拍 🎾";
        let line = "";
        let ty = cfg.reviewTextStartY;
        for (const ch of text) {
          if (_ctx.measureText(line + ch).width > cfg.reviewTextWidth || ty > cfg.reviewMaxY) {
            _ctx.fillText(line, cfg.reviewCard.x + 50, ty);
            ty += cfg.lineHeight;
            line = ch;
            if (ty > cfg.reviewMaxY) {
              line += "…";
              break;
            }
          } else line += ch;
        }
        _ctx.fillText(line, cfg.reviewCard.x + 50, ty);

        return 1200;
      },
    },
  ],
};
