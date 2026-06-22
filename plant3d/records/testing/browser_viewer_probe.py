import json
import sys
from io import BytesIO

from PIL import Image
from playwright.sync_api import sync_playwright


def screenshot_probe(page):
    canvas_box = page.locator("canvas").bounding_box()
    png = page.screenshot(full_page=False)
    image = Image.open(BytesIO(png)).convert("RGBA")
    width, height = image.size
    if not canvas_box:
        return {"ok": False, "reason": "no canvas box", "screenshot_size": [width, height]}

    left = max(0, int(canvas_box["x"]))
    top = max(0, int(canvas_box["y"]))
    right = min(width, int(canvas_box["x"] + canvas_box["width"]))
    bottom = min(height, int(canvas_box["y"] + canvas_box["height"]))
    crop = image.crop((left, top, right, bottom))
    sample_stride = max(1, min(crop.size) // 80)
    total = 0
    non_background = 0
    for y in range(0, crop.height, sample_stride):
        for x in range(0, crop.width, sample_stride):
            r, g, b, a = crop.getpixel((x, y))
            total += 1
            if not (r > 235 and g > 238 and b > 240 and a > 240):
                non_background += 1
    return {
        "ok": True,
        "screenshot_size": [width, height],
        "canvas_box": canvas_box,
        "sampled_pixels": total,
        "non_background_pixels": non_background,
        "non_background_ratio": round(non_background / total, 4) if total else 0,
    }


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9095/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        errors = []
        page.on(
            "console",
            lambda msg: errors.append(f"console:{msg.type}:{msg.text}") if msg.type in ("error", "warning") else None,
        )
        page.on("pageerror", lambda exc: errors.append(f"pageerror:{exc}"))
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("canvas", timeout=30000)
        try:
            page.wait_for_function(
                'document.getElementById("viewerStatus")?.textContent.includes("Loaded")',
                timeout=45000,
            )
        except Exception as exc:
            errors.append(f"wait_loaded:{exc}")
        canvas = page.locator("canvas").bounding_box()
        if canvas:
            start_x = canvas["x"] + canvas["width"] * 0.5
            start_y = canvas["y"] + canvas["height"] * 0.5
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(start_x + 160, start_y + 80, steps=12)
            page.mouse.up()
        page.wait_for_timeout(1500)
        status = page.locator("#viewerStatus").inner_text(timeout=5000)
        metrics = page.locator("#runtimeMetrics").inner_text(timeout=5000)
        screenshot_info = screenshot_probe(page)
        print(
            json.dumps(
                {
                    "url": url,
                    "status": status,
                    "metrics": metrics,
                    "canvas_box": canvas,
                    "screenshot_info": screenshot_info,
                    "errors": errors[:20],
                },
                indent=2,
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
