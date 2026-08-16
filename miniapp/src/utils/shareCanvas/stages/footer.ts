import { footer as drawFooter } from "../primitives";
import type { DrawStage } from "../pipeline";

export const footerStage: DrawStage = {
  name: "footer",
  steps: [
    {
      name: "footer",
      condition: () => true,
      measure: (y, pipe) => y + pipe.config.footer.height,
      execute: (_ctx, pipe, _y) => {
        const H = _y + pipe.config.footer.height;
        drawFooter(_ctx, H);
        return _y;
      },
    },
  ],
};
