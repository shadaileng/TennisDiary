import { PAPER } from "./config";
import type { PipelineContext } from "./context";

export interface DrawStep {
  name: string;
  condition: (ctx: PipelineContext) => boolean;
  measure?: (y: number, ctx: PipelineContext) => number;
  execute: (ctx: CanvasRenderingContext2D, pipe: PipelineContext, y: number) => number;
}

export interface DrawStage {
  name: string;
  steps: DrawStep[];
}

export class DrawPipeline {
  private stages: DrawStage[] = [];

  addStage(stage: DrawStage): this {
    this.stages.push(stage);
    return this;
  }

  measureHeight(pipe: PipelineContext): number {
    let y = pipe.config.content.top;
    for (const stage of this.stages) {
      for (const step of stage.steps) {
        if (step.condition(pipe)) {
          if (step.measure) {
            y = step.measure(y, pipe);
          }
          // 如果没有 measure，使用 execute 的返回值逻辑（但不实际绘制）
          break; // 每个 stage 只执行第一个匹配的 step
        }
      }
    }
    return y + pipe.config.footer.height;
  }

  execute(ctx: CanvasRenderingContext2D, pipe: PipelineContext): number {
    const H = this.measureHeight(pipe);

    ctx.fillStyle = PAPER;
    ctx.fillRect(0, 0, pipe.config.canvas.width, H);

    let y = pipe.config.content.top;
    for (const stage of this.stages) {
      for (const step of stage.steps) {
        if (step.condition(pipe)) {
          y = step.execute(ctx, pipe, y);
          break; // 每个 stage 只执行第一个匹配的 step
        }
      }
    }

    return H;
  }
}
