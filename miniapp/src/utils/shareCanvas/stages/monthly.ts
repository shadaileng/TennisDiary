import { white, statBlock, GRAY, font, LIME } from "../primitives";
import type { DrawStage } from "../pipeline";

function sumCosts(costs: { amount: number }[]): number {
  return costs.reduce((s, c) => s + (Number(c.amount) || 0), 0);
}

function fmtMoney(n: number): string {
  return n % 1 === 0 ? `¥${n}` : `¥${n.toFixed(2)}`;
}

export const monthlyStage: DrawStage = {
  name: "monthly",
  steps: [
    {
      name: "stats-cards",
      condition: (pipe) => pipe.tpl === "月度战报",
      measure: (_y, _pipe) => {
        // 月度战报：两行卡片，每行高300，间距380
        // topY=480, 第一行到 480+300=780, 第二行从 480+380=860 到 860+300=1160
        return 1160;
      },
      execute: (_ctx, pipe, y) => {
        const { monthDiaries, MOOD } = pipe;
        const cfg = pipe.config.monthlyStats;

        const mins = monthDiaries.reduce((s, d) => s + d.duration, 0);
        const cost = monthDiaries.reduce((s, d) => s + sumCosts(d.costs), 0);

        white(_ctx, cfg.leftX, cfg.topY, cfg.cardWidth, cfg.cardHeight);
        statBlock(_ctx, cfg.leftX + 50, cfg.labelY, "本月打球", String(monthDiaries.length), "次");

        white(_ctx, cfg.rightX, cfg.topY, cfg.cardWidth, cfg.cardHeight);
        statBlock(_ctx, cfg.rightX + 50, cfg.labelY, "挥拍时长", (mins / 60).toFixed(1), "小时");

        white(_ctx, cfg.leftX, cfg.topY + cfg.gap, cfg.cardWidth, cfg.cardHeight);
        statBlock(_ctx, cfg.leftX + 50, cfg.labelY + cfg.gap, "投入花费", fmtMoney(cost));

        const avgMood = monthDiaries.length
          ? monthDiaries.reduce((s, d) => s + d.mood, 0) / monthDiaries.length
          : 0;
        const moodEmoji = MOOD[Math.max(0, Math.round(avgMood) - 1)]?.emoji ?? "😄";

        white(_ctx, cfg.rightX, cfg.topY + cfg.gap, cfg.cardWidth, cfg.cardHeight);
        _ctx.fillStyle = GRAY;
        _ctx.font = font(500, 30);
        _ctx.fillText("平均心情", cfg.rightX + 50, cfg.labelY + cfg.gap);
        _ctx.font = "90px sans-serif";
        _ctx.fillText(moodEmoji, cfg.rightX + 50, cfg.emojiY + cfg.gap);

        return 1160;
      },
    },
  ],
};
