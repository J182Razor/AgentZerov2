import os
import json
import tempfile
from python.helpers.tool import Tool, Response


class DesignTools(Tool):
    """Combined Design OS + design-memory tool for product design workflows."""

    async def execute(self, **kwargs) -> Response:
        method = self.method if hasattr(self, "method") and self.method else "plan"

        if method == "plan":
            return await self._plan(**kwargs)
        elif method == "extract":
            return await self._extract(**kwargs)
        elif method == "handoff":
            return await self._handoff(**kwargs)
        else:
            return Response(message=f"Unknown method: {method}", break_loop=False)

    async def _plan(self, **kwargs) -> Response:
        description = self.args.get("description", "") or kwargs.get("description", "")
        if not description:
            return Response(
                message="Error: 'description' parameter is required. Provide a product description to generate a design plan.",
                break_loop=False,
            )

        # Write the product description to a temp file for reference
        tmp_dir = os.path.join("tmp", "design")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_file = os.path.join(tmp_dir, "product_brief.md")
        with open(tmp_file, "w") as f:
            f.write(f"# Product Brief\n\n{description}\n")

        prompt = f"""You are a senior product designer. Given the following product description, generate a structured design plan.

Product Description:
{description}

Respond with a structured plan in the following format:

## Product Vision
(A clear, concise vision statement for the product)

## Target Users & Personas
(Define 2-3 key user personas with their goals, pain points, and behaviors)

## Key Features
(List the core features prioritized by user value, with brief descriptions)

## User Flows
(Outline the primary user journeys through the product)

## Design Principles
(3-5 guiding design principles for this product)

## Success Metrics
(Key metrics to measure the design's effectiveness)
"""

        try:
            response = await self.agent.call_utility_model(prompt)
            result_text = str(response) if response else "No response from utility model."
            result = f"Design plan saved to: {tmp_file}\n\n{result_text}"
            return Response(message=result[:4000], break_loop=False)
        except Exception as e:
            return Response(message=f"Error generating design plan: {str(e)}"[:4000], break_loop=False)

    async def _extract(self, **kwargs) -> Response:
        url = self.args.get("url", "") or kwargs.get("url", "")
        if not url:
            return Response(
                message="Error: 'url' parameter is required. Provide a website URL to extract design tokens from.",
                break_loop=False,
            )

        instructions = f"""## Design Token Extraction

To extract design tokens from **{url}**, you can use the `design-memory` npm package.

### Quick Setup
```bash
npm install -g design-memory
```

### Extract Design Tokens
Run the following via the `code_execution` tool:
```bash
npx design-memory extract "{url}" --output tmp/design/tokens.json
```

### What Gets Extracted
- **Colors**: Primary, secondary, accent, background, text colors
- **Typography**: Font families, sizes, weights, line heights
- **Spacing**: Margin and padding scales
- **Border Radius**: Corner radius values
- **Shadows**: Box shadow definitions
- **Breakpoints**: Responsive design breakpoints

### Manual Alternative
If `design-memory` is not available, you can use the `code_execution` tool to run a headless browser script that extracts computed styles from the page:

```bash
node -e "
const puppeteer = require('puppeteer');
(async () => {{
  const browser = await puppeteer.launch({{headless: true}});
  const page = await browser.newPage();
  await page.goto('{url}');
  const styles = await page.evaluate(() => {{
    const cs = getComputedStyle(document.body);
    return {{
      fontFamily: cs.fontFamily,
      fontSize: cs.fontSize,
      color: cs.color,
      backgroundColor: cs.backgroundColor
    }};
  }});
  console.log(JSON.stringify(styles, null, 2));
  await browser.close();
}})();
"
```
"""
        return Response(message=instructions[:4000], break_loop=False)

    async def _handoff(self, **kwargs) -> Response:
        specs = self.args.get("specs", "") or kwargs.get("specs", "")
        if not specs:
            return Response(
                message="Error: 'specs' parameter is required. Provide design specifications for the developer handoff.",
                break_loop=False,
            )

        prompt = f"""You are a design systems engineer preparing a developer handoff document. Given the following design specifications, create a structured, implementation-ready handoff document.

Design Specifications:
{specs}

Format the handoff document with the following sections:

## Component Inventory
(List all UI components with their variants and states)

## Design Tokens
(CSS custom properties / variables for colors, typography, spacing, etc.)

## Layout Specifications
(Grid system, breakpoints, container widths, spacing rules)

## Component Specifications
(For each component: props/API, dimensions, spacing, colors, typography, states, accessibility notes)

## Interaction Specifications
(Animations, transitions, hover/focus states, loading states)

## Accessibility Requirements
(ARIA labels, keyboard navigation, color contrast ratios, screen reader notes)

## Asset List
(Icons, images, fonts needed with format specifications)
"""

        try:
            response = await self.agent.call_utility_model(prompt)
            result_text = str(response) if response else "No response from utility model."

            # Save handoff document
            tmp_dir = os.path.join("tmp", "design")
            os.makedirs(tmp_dir, exist_ok=True)
            handoff_file = os.path.join(tmp_dir, "developer_handoff.md")
            with open(handoff_file, "w") as f:
                f.write(result_text)

            result = f"Developer handoff document saved to: {handoff_file}\n\n{result_text}"
            return Response(message=result[:4000], break_loop=False)
        except Exception as e:
            return Response(message=f"Error generating handoff document: {str(e)}"[:4000], break_loop=False)
