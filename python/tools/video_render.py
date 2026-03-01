import os
from python.helpers.tool import Tool, Response


class VideoRender(Tool):
    """Remotion programmatic video rendering tool."""

    async def execute(self, **kwargs) -> Response:
        method = self.method if hasattr(self, "method") and self.method else "compose"

        if method == "compose":
            return await self._compose(**kwargs)
        elif method == "render":
            return await self._render(**kwargs)
        else:
            return Response(message=f"Unknown method: {method}", break_loop=False)

    async def _compose(self, **kwargs) -> Response:
        description = self.args.get("description", "") or kwargs.get("description", "")
        if not description:
            return Response(
                message="Error: 'description' parameter is required. Describe the video you want to compose.",
                break_loop=False,
            )

        duration_secs = self.args.get("duration", 10) or kwargs.get("duration", 10)
        fps = self.args.get("fps", 30) or kwargs.get("fps", 30)
        width = self.args.get("width", 1920) or kwargs.get("width", 1920)
        height = self.args.get("height", 1080) or kwargs.get("height", 1080)

        system = "You are an expert Remotion (React video framework) developer. Generate complete, runnable Remotion components as raw TSX code only — no explanation, no markdown fences."
        prompt = f"""Generate a complete Remotion component based on the following description.

Description: {description}

Requirements:
- Duration: {duration_secs} seconds at {fps} FPS (total frames: {int(duration_secs) * int(fps)})
- Resolution: {width}x{height}
- Use Remotion's useCurrentFrame(), useVideoConfig(), interpolate(), spring(), Sequence, AbsoluteFill
- Include inline styles (no external CSS)
- Make it visually polished with smooth animations
- Export the component as default

Generate ONLY the complete React/Remotion component code, ready to save as a .tsx file. Include all necessary imports from 'remotion'.
"""

        try:
            response = await self.agent.call_utility_model(system=system, message=prompt)
            component_code = str(response) if response else ""

            if not component_code:
                return Response(message="Error: Failed to generate component code.", break_loop=False)

            # Save the component to a file
            tmp_dir = os.path.join("tmp", "remotion")
            os.makedirs(tmp_dir, exist_ok=True)
            component_file = os.path.join(tmp_dir, "Composition.tsx")
            with open(component_file, "w") as f:
                f.write(component_code)

            result = f"""Remotion component generated and saved to: {component_file}

Configuration:
- Duration: {duration_secs}s @ {fps}fps ({int(duration_secs) * int(fps)} frames)
- Resolution: {width}x{height}

--- Component Code ---
{component_code}

--- Next Steps ---
Use the video_render:render method to generate the render command, or edit the component file as needed.
"""
            return Response(message=result[:4000], break_loop=False)
        except Exception as e:
            return Response(message=f"Error generating Remotion component: {str(e)}"[:4000], break_loop=False)

    async def _render(self, **kwargs) -> Response:
        component_path = self.args.get("component", "") or kwargs.get("component", "")
        output_path = self.args.get("output", "") or kwargs.get("output", "")

        if not component_path:
            component_path = os.path.join("tmp", "remotion", "Composition.tsx")

        if not output_path:
            output_dir = os.path.join("tmp", "remotion", "output")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "video.mp4")

        codec = self.args.get("codec", "h264") or kwargs.get("codec", "h264")
        composition_id = self.args.get("composition_id", "MainComposition") or kwargs.get("composition_id", "MainComposition")

        render_cmd = (
            f"npx remotion render {component_path} {composition_id} {output_path} "
            f"--codec {codec}"
        )

        instructions = f"""## Remotion Render Instructions

### Render Command
Execute the following via the `code_execution` tool:

```bash
{render_cmd}
```

### Prerequisites
Make sure you have a Remotion project set up:
```bash
# If starting fresh:
npx create-video@latest my-video
cd my-video
npm install

# Copy your composition into the src/ directory
cp {component_path} src/Composition.tsx
```

### Configuration
- **Component**: {component_path}
- **Output**: {output_path}
- **Codec**: {codec}
- **Composition ID**: {composition_id}

### Alternative Render Options
```bash
# Render as GIF
npx remotion render {component_path} {composition_id} output.gif --codec gif

# Render specific frames
npx remotion render {component_path} {composition_id} {output_path} --frames=0-90

# Render with custom resolution
npx remotion render {component_path} {composition_id} {output_path} --width 1280 --height 720

# Render with transparency (WebM)
npx remotion render {component_path} {composition_id} output.webm --codec vp8
```

### Programmatic Render (Node.js)
```javascript
const {{bundle, renderMedia, getCompositions}} = require('@remotion/bundler');
const {{webpackOverride}} = require('./webpack-override');

const bundled = await bundle({{
  entryPoint: require.resolve('./src/index'),
  webpackOverride,
}});

const compositions = await getCompositions(bundled);
const composition = compositions.find(c => c.id === '{composition_id}');

await renderMedia({{
  composition,
  serveUrl: bundled,
  codec: '{codec}',
  outputLocation: '{output_path}',
}});
```
"""
        return Response(message=instructions[:4000], break_loop=False)
