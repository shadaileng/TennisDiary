import type { Analysis, Diary } from "@/types";

const W = 1080;
const H = 1350;
const LIME = "#C8DA2B";
const OLIVE = "#242B1F";
const PAPER = "#F2F2EF";
const INK = "#171B14";
const GRAY = "#9AA096";
const FONT = "sans-serif";

export type ShareTemplate = "月度战报" | "今日日记" | "技术评分";
export const SHARE_TEMPLATES: readonly ShareTemplate[] = ["月度战报", "今日日记", "技术评分"] as const;

interface ShareData {
  diaries: Diary[]
  analysis?: Analysis
}

interface MoodItem {
  v: number
  label: string
  emoji: string
}

interface IntensityItem {
  v: number
  label: string
  emoji: string
}

function font(weight: number, size: number): string {
  return `${weight} ${size}px ${FONT}`;
}

/** 圆角矩形路径（Canvas 2d 无 roundRect 时兜底） */
function rr(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/** 按宽度折行（中文按字符测量） */
function wrap(ctx: CanvasRenderingContext2D, text: string, maxW: number): string[] {
  const out: string[] = [];
  let line = "";
  for (const ch of text.replace(/\n/g, " ")) {
    if (ctx.measureText(line + ch).width > maxW && line) {
      out.push(line);
      line = ch;
    } else line += ch;
  }
  if (line) out.push(line);
  return out;
}

function monthKey(dateStr: string): string {
  return dateStr.slice(0, 7);
}

function todayStr(): string {
  const d = new Date();
  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function fmtDuration(min: number): string {
  if (min < 60) return `${min}分钟`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h}小时${m}分` : `${h}小时`;
}

function fmtMoney(n: number): string {
  return n % 1 === 0 ? `¥${n}` : `¥${n.toFixed(2)}`;
}

function sumCosts(costs: { amount: number }[]): number {
  return costs.reduce((s, c) => s + (Number(c.amount) || 0), 0);
}

function white(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number) {
  ctx.fillStyle = "#fff";
  ctx.shadowColor = "rgba(23,27,20,0.08)";
  ctx.shadowBlur = 24;
  rr(ctx, x, y, w, h, 40);
  ctx.fill();
  ctx.shadowBlur = 0;
}

function statBlock(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  label: string,
  value: string,
  unit = "",
) {
  ctx.fillStyle = GRAY;
  ctx.font = font(500, 30);
  ctx.fillText(label, x, y);
  ctx.fillStyle = INK;
  ctx.font = font(800, 76);
  ctx.fillText(value, x, y + 90);
  if (unit) {
    const vw = ctx.measureText(value).width;
    ctx.font = font(500, 30);
    ctx.fillStyle = GRAY;
    ctx.fillText(unit, x + vw + 12, y + 90);
  }
}

/** 顶部橄榄绿头图 + 品牌 */
function header(ctx: CanvasRenderingContext2D, title: string, sub: string) {
  ctx.fillStyle = OLIVE;
  ctx.fillRect(0, 0, W, 420);
  // 青柠网球装饰
  ctx.fillStyle = LIME;
  ctx.beginPath();
  ctx.arc(W - 130, 130, 150, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,0.55)";
  ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.arc(W - 260, 130, 190, -0.5, 0.7);
  ctx.stroke();
  // 标题
  ctx.fillStyle = LIME;
  ctx.font = font(600, 34);
  ctx.fillText("TENNIS DIARY 🎾", 70, 120);
  ctx.fillStyle = "#fff";
  ctx.font = font(700, 84);
  ctx.fillText(title, 70, 230);
  ctx.fillStyle = "rgba(255,255,255,0.65)";
  ctx.font = font(400, 34);
  ctx.fillText(sub, 70, 300);
}

/** 底部品牌标语 */
function footer(ctx: CanvasRenderingContext2D) {
  ctx.fillStyle = GRAY;
  ctx.font = font(500, 30);
  ctx.fillText("用 Tennis Diary 记录我的网球成长 🎾", 70, H - 80);
}

function emptyCard(ctx: CanvasRenderingContext2D, text: string) {
  ctx.fillStyle = "#fff";
  rr(ctx, 70, 480, 940, 700, 40);
  ctx.fill();
  ctx.fillStyle = INK;
  ctx.font = font(700, 44);
  ctx.fillText(text, 70, 830);
}

/**
 * 绘制分享卡片到 Canvas 2d 上下文（1080×1350 逻辑尺寸）。
 * 调用方需自行 scale(dpr)。
 */
export function drawShareCard(
  ctx: CanvasRenderingContext2D,
  tpl: ShareTemplate,
  data: ShareData,
  MOOD: readonly MoodItem[],
  INTENSITY: readonly IntensityItem[],
) {
  ctx.fillStyle = PAPER;
  ctx.fillRect(0, 0, W, H);

  const thisMonth = monthKey(todayStr());
  const monthDiaries = data.diaries.filter((d) => monthKey(d.date) === thisMonth);
  const latestDiary = data.diaries[0];
  const latestAnalysis = data.analysis;

  if (tpl === "月度战报") {
    header(
      ctx,
      `${Number(thisMonth.slice(5))} 月打球战报`,
      `${thisMonth.replace("-", " / ")} · 坚持的第 ${data.diaries.length} 次记录`,
    );
    const mins = monthDiaries.reduce((s, d) => s + d.duration, 0);
    const cost = monthDiaries.reduce((s, d) => s + sumCosts(d.costs), 0);
    white(ctx, 70, 480, 450, 300);
    statBlock(ctx, 120, 570, "本月打球", String(monthDiaries.length), "次");
    white(ctx, 560, 480, 450, 300);
    statBlock(ctx, 610, 570, "挥拍时长", (mins / 60).toFixed(1), "小时");
    white(ctx, 70, 820, 450, 300);
    statBlock(ctx, 120, 910, "投入花费", fmtMoney(cost));
    const avgMood = monthDiaries.length
      ? monthDiaries.reduce((s, d) => s + d.mood, 0) / monthDiaries.length
      : 0;
    const moodEmoji = MOOD[Math.max(0, Math.round(avgMood) - 1)]?.emoji ?? "😄";
    white(ctx, 560, 820, 450, 300);
    ctx.fillStyle = GRAY;
    ctx.font = font(500, 30);
    ctx.fillText("平均心情", 610, 910);
    ctx.font = "90px sans-serif";
    ctx.fillText(moodEmoji, 610, 1015);
  } else if (tpl === "今日日记") {
    if (!latestDiary) {
      header(ctx, "今日日记", todayStr());
      emptyCard(ctx, "还没有日记，先记一篇吧～");
    } else {
      const inten = INTENSITY.find((i) => i.v === latestDiary.intensity);
      const mood = MOOD.find((m) => m.v === latestDiary.mood);
      header(
        ctx,
        `${latestDiary.type} · ${fmtDuration(latestDiary.duration)}`,
        `${latestDiary.date} ${latestDiary.time || ""}`,
      );
      white(ctx, 70, 480, 450, 280);
      ctx.fillStyle = GRAY;
      ctx.font = font(500, 30);
      ctx.fillText("运动强度", 120, 570);
      ctx.font = "76px sans-serif";
      ctx.fillText(inten?.emoji ?? "", 120, 680);
      ctx.fillStyle = INK;
      ctx.font = font(700, 44);
      ctx.fillText(inten?.label ?? "", 240, 665);
      white(ctx, 560, 480, 450, 280);
      ctx.fillStyle = GRAY;
      ctx.font = font(500, 30);
      ctx.fillText("心情", 610, 570);
      ctx.font = "76px sans-serif";
      ctx.fillText(mood?.emoji ?? "", 610, 680);
      ctx.fillStyle = INK;
      ctx.font = font(700, 44);
      ctx.fillText(mood?.label ?? "", 730, 665);
      white(ctx, 70, 800, 940, 380);
      ctx.fillStyle = GRAY;
      ctx.font = font(500, 30);
      ctx.fillText("今日复盘", 120, 880);
      ctx.fillStyle = INK;
      ctx.font = font(400, 38);
      const text = latestDiary.notes || "专注每一次挥拍 🎾";
      let line = "";
      let ty = 950;
      for (const ch of text) {
        if (ctx.measureText(line + ch).width > 820 || ty > 1120) {
          ctx.fillText(line, 120, ty);
          ty += 58;
          line = ch;
          if (ty > 1120) {
            line += "…";
            break;
          }
        } else line += ch;
      }
      ctx.fillText(line, 120, ty);
    }
  } else {
    // 技术评分
    if (!latestAnalysis?.report) {
      header(ctx, "技术评分", "AI 教练分析");
      emptyCard(ctx, "还没有分析报告，先去做一次分析吧～");
    } else {
      const r = latestAnalysis.report;
      header(
        ctx,
        `${latestAnalysis.kind}技术评分`,
        `AI 教练分析 · ${latestAnalysis.date}`,
      );
      white(ctx, 70, 480, 940, 700);
      // 大评分球
      ctx.fillStyle = LIME;
      ctx.beginPath();
      ctx.arc(270, 700, 130, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = INK;
      ctx.font = font(800, 110);
      ctx.textAlign = "center";
      ctx.fillText(String(latestAnalysis.score || "—"), 270, 740);
      ctx.textAlign = "left";
      // 六维进度条
      let sy = 620;
      const dims = (r.dimensions || []).slice(0, 6);
      for (const d of dims) {
        ctx.font = font(500, 34);
        ctx.fillStyle = INK;
        ctx.fillText(d.name, 480, sy);
        ctx.fillStyle = "#E8E8E4";
        rr(ctx, 480, sy + 16, 420, 14, 7);
        ctx.fill();
        ctx.fillStyle = LIME;
        rr(ctx, 480, sy + 16, 420 * Math.min(1, Number(d.score || 0) / 100), 14, 7);
        ctx.fill();
        ctx.fillStyle = "#7A8272";
        ctx.font = font(700, 32);
        ctx.fillText(String(d.score ?? 0), 920, sy + 5);
        sy += 96;
      }
    }
  }

  footer(ctx);
}

/** 分享文案生成（本地模板，可编辑） */
export function genCaption(tpl: ShareTemplate, data: ShareData): string {
  const thisMonth = monthKey(todayStr());
  const monthDiaries = data.diaries.filter((d) => monthKey(d.date) === thisMonth);
  const latestDiary = data.diaries[0];
  const latestAnalysis = data.analysis;

  if (tpl === "月度战报") {
    const mins = monthDiaries.reduce((s, d) => s + d.duration, 0);
    const cost = monthDiaries.reduce((s, d) => s + sumCosts(d.costs), 0);
    return `🎾 ${Number(thisMonth.slice(5))}月网球月报\n\n本月打球 ${monthDiaries.length} 次，挥拍 ${(mins / 60).toFixed(1)} 小时，投入 ${fmtMoney(cost)}。\n每一次上场都是和自己的对话，慢慢来，比较快。\n\n#网球 #网球日记 #运动打卡`;
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
  return `🤖 AI 教练给我的${latestAnalysis.kind}打了 ${latestAnalysis.score || "—"} 分！\n\n${latestAnalysis.summary || ""}\n最强项：${best?.name || "—"}（${best?.score || 0}分）💪\n${issue ? `下一步改进：${issue}` : ""}\n\n#网球 #AI教练 #网球技术 #网球日记`;
}