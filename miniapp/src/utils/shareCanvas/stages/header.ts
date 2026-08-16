import { header as drawHeader } from "../primitives";
import type { DrawStage } from "../pipeline";

export const headerStage: DrawStage = {
  name: "header",
  steps: [
    {
      name: "monthly-header",
      condition: (pipe) => pipe.tpl === "月度战报",
      execute: (_ctx, pipe, y) => {
        const month = Number(pipe.monthKey.slice(5));
        const sub = `${pipe.monthKey.replace("-", " / ")} · 坚持的第 ${pipe.data.diaries.length} 次记录`;
        drawHeader(_ctx, `${month} 月打球战报`, sub);
        return y;
      },
    },
    {
      name: "today-empty-header",
      condition: (pipe) => pipe.tpl === "今日日记" && !pipe.latestDiary,
      execute: (_ctx, pipe, y) => {
        const today = new Date();
        const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
        const todayStr = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
        drawHeader(_ctx, "今日日记", todayStr);
        return y;
      },
    },
    {
      name: "today-header",
      condition: (pipe) => pipe.tpl === "今日日记" && !!pipe.latestDiary,
      execute: (_ctx, pipe, y) => {
        const d = pipe.latestDiary!;
        const inten = pipe.INTENSITY.find((i) => i.v === d.intensity);
        const duration = d.duration;
        const h = Math.floor(duration / 60);
        const m = duration % 60;
        const durationStr = h > 0 ? (m ? `${h}小时${m}分` : `${h}小时`) : `${duration}分钟`;
        drawHeader(_ctx, `${d.type} · ${durationStr}`, `${d.date} ${d.time || ""}`);
        return y;
      },
    },
    {
      name: "tech-empty-header",
      condition: (pipe) => pipe.tpl === "技术评分" && !pipe.latestAnalysis?.report,
      execute: (_ctx, _pipe, y) => {
        drawHeader(_ctx, "技术评分", "教练分析");
        return y;
      },
    },
    {
      name: "tech-header",
      condition: (pipe) => pipe.tpl === "技术评分" && !!pipe.latestAnalysis?.report,
      execute: (_ctx, pipe, y) => {
        const a = pipe.latestAnalysis!;
        drawHeader(_ctx, `${a.kind}技术评分`, `教练分析 · ${a.date}`);
        return y;
      },
    },
  ],
};
