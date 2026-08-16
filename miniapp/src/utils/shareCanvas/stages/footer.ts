import { footer as drawFooter } from "../primitives";
import type { DrawStage } from "../pipeline";

export const footerStage: DrawStage = {
  name: "footer",
  steps: [
    {
      name: "footer",
      condition: () => true,
      // measure 不需要，因为 pipeline.measureHeight 会自动添加 footer.height
      execute: (_ctx, pipe, y) => {
        // footer 绘制在画布底部区域
        const H = y + pipe.config.footer.height;
        drawFooter(_ctx, H);
        return y;
      },
    },
  ],
};
