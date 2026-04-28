import asyncio
import json
from playwright.async_api import async_playwright
from playstealth_actions.stealth_enhancer import generate_user_agent, inject_advanced_stealth
from playstealth_actions.human_behavior import human_scroll
from playstealth_actions.state_store import save_cli_state, save_browser_state
from playstealth_actions.diagnose_benchmark import diagnose_benchmark
from playstealth_actions.plugins.loader import load_plugins, detect_platform


async def run_demo(survey_url: str = "https://example-survey.com/start", session_id: str = "demo_001", max_steps: int = 3):
    """Full End-to-End Demo Flow für PlayStealth CLI."""
    print("🚀 PlayStealth CLI → Full Demo Flow")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        # Stealth Profil generieren und anwenden
        profile = generate_user_agent()
        ctx = await browser.new_context(
            user_agent=profile["user_agent"],
            locale=profile.get("locale", "de-DE"),
            timezone_id=profile.get("timezone", "Europe/Berlin"),
            viewport={"width": 1920, "height": 1080}
        )
        await inject_advanced_stealth(ctx)
        page = await ctx.new_page()

        # 1️⃣ Stealth-Benchmark
        print("🔍 Running stealth benchmark...")
        await page.goto("about:blank")
        bench = await diagnose_benchmark(page)
        print(f"✅ Stealth Score: {bench['stealth_score']} ({bench['percentage']}%)")
        if bench["warnings"]:
            print(f"⚠️  Warnings: {bench['warnings']}")

        # 2️⃣ Survey laden
        print(f"🌍 Navigating to survey: {survey_url}")
        await page.goto(survey_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        # 3️⃣ Plattform erkennen
        plugins = load_plugins()
        try:
            platform = await detect_platform(page, plugins)
            print(f"🎯 Detected platform: {platform.__class__.__name__}")
        except ValueError as e:
            print(f"⚠️  {e}")
            await browser.close()
            return

        # 4️⃣ Consent behandeln
        print("🍪 Handling consent...")
        await platform.handle_consent(page)

        # 5️⃣ Survey-Loop
        for step in range(1, max_steps + 1):
            print(f"\n📝 Step {step}/{max_steps}")
            try:
                q_data = await platform.get_current_step(page)
                q_preview = q_data['question'][:70] + "..." if len(q_data['question']) > 70 else q_data['question']
                print(f"   Q: {q_preview}")
                print(f"   Options: {q_data['option_count']}")

                # Auto-Antwort: erste Option (oder passe Logik an)
                ok = await platform.answer_question(page, 0)
                if not ok:
                    print("   ⚠️ Answer failed → skipping step")
                    continue

                await human_scroll(page, 600)
                nav_ok = await platform.navigate_next(page)
                if not nav_ok:
                    print("   ⚠️ Navigation failed → breaking")
                    break

                # State persistieren
                save_cli_state(session_id, {"step": step, "platform": platform.__class__.__name__})
                await save_browser_state(ctx, session_id)
                print(f"   💾 State saved (step {step})")

                if await platform.is_completed(page):
                    print("✅ Survey completed successfully!")
                    break

            except Exception as e:
                print(f"❌ Step {step} error: {e}")
                break

        # 6️⃣ Cleanup
        print("\n🧹 Closing browser...")
        await browser.close()
        print("🎉 Demo finished.")


if __name__ == "__main__":
    # Passe URL an deine Test-Umfrage an
    asyncio.run(run_demo(survey_url="https://example-survey.com/start", max_steps=4))
