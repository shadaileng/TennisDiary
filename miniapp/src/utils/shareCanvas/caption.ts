import type { PipelineContext } from "./context";
import { fmtDuration, fmtMoney, sumCosts } from "./primitives";

export function genCaption(pipe: PipelineContext): string {
  const { tpl, monthDiaries, latestDiary, latestAnalysis, monthKey } = pipe;

  if (tpl === "月度战报") {
    const mins = monthDiaries.reduce((s, d) => s + d.duration, 0);
    const cost = monthDiaries.reduce((s, d) => s + sumCosts(d.costs), 0);
    return `🎾 ${Number(monthKey.slice(5))}月网球月报\n\n本月打球 ${monthDiaries.length} 次，挥拍 ${(mins / 60).toFixed(1)} 小时，投入 ${fmtMoney(cost)}。\n每一次上场都是和自己的对话，慢慢来，比较快。\n\n#网球 #网球日记 #运动打卡`;
  }

  if (tpl === "今日日记") {
    if (!latestDiary) return "还没有日记，先去记一篇吧～";
    return `🎾 今日份网球\n\n${latestDiary.date} ${latestDiary.type} ${fmtDuration(latestDiary.duration)}\n${latestDiary.notes || "手感渐入佳境，继续加油！"}\n\n#网球 #网球日记 #网球初学者`;
  }

  if (!latestAnalysis?.report) return "还没有分析报告，先去做一次分析吧～";
  const best = [...(latestAnalysis.report.dimensions || [])].sort(
    (a, b) => Number(b.score || 0) - Number(a.score || 0),
  )[0];
  const issue = latestAnalysis.report.improvements?.[0]?.issue;
  return `🤖 教练给我的${latestAnalysis.kind}打了 ${latestAnalysis.score || "—"} 分！\n\n${latestAnalysis.summary || ""}\n最强项：${best?.name || "—"}（${best?.score || 0}分）💪\n${issue ? `下一步改进：${issue}` : ""}\n\n#网球 #教练 #网球技术 #网球日记`;
}
