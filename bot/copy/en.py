from bot.config import CreditPack
from bot.copy import Copy

COPY = Copy(
    locale="en",
    brand_name="FitRoom",
    tagline="See it on you",
    welcome_new=(
        "Ever wondered how that outfit would look on *you*?\n\n"
        "Let's build your personal fitting room ✨\n"
        "Upload a photo of yourself — or tap 📸 Photo guide first."
    ),
    welcome_back=(
        "Welcome back to FitRoom! You have {balance} credit(s).\n"
        "Send a clothing photo or use the menu below."
    ),
    demo_caption=(
        "See any outfit on *you* before you buy ✨\n"
        "Left: your photo + clothing. Right: the result."
    ),
    photo_ready=(
        "Your fitting room is ready 🎉\n"
        "You have *{free_credits} free try-ons*. Send any clothing photo!"
    ),
    generating="Styling your look… this takes about 15 sec ✨",
    result_caption="This is *you* in that outfit 🔥",
    paywall=(
        "This is *you* in that outfit 🔥\n"
        "That's your last free try-on — and it looked great on you.\n"
        "Keep going: 5 more try-ons for 50⭐ (~10 sec to set up)."
    ),
    deficit="Out of try-ons! Grab 5 more for 50⭐ — 5 seconds and you're back 👗",
    privacy_note=(
        "🔒 Photos are stored securely and used only for try-on. "
        "Delete anytime with /delete_my_data"
    ),
    drip_opt_out="Stop reminders",
    guide_caption=(
        "*Photo Guide for Best Try-On Results*\n\n"
        "✅ *Full body* • *Good light* • *Plain background* • *Clothing alone*\n\n"
        "⚠️ Garment on a model works, but try-on is less accurate."
    ),
    guide_text_fallback=(
        "📸 *Photo guide*\n\n"
        "👤 *Your photo — DO:* full body, front-facing, arms visible, "
        "good light, plain background.\n\n"
        "👤 *DON'T:* cropped, blurry, dark, or side angle.\n\n"
        "👗 *Garment — DO:* item alone on plain background, clear and well-lit.\n\n"
        "👗 *DON'T:* busy backgrounds or multiple items. "
        "On a model works, but alone is best."
    ),
    guide_next_person="Great — now send your full-body photo here 📷",
    guide_next_garment="Ready! Now send a clothing photo to see it on you 👗",
    try_another="Love it? Try another 👗",
    low_balance="⚠ {count} try-on(s) left — make them count 👗",
    invite_text=(
        "Invite friends and earn +1 credit when they complete their first try-on."
    ),
    share_inline_query="Look what I'd wear! Try it yourself →",
    btn_try_on="Try on clothing",
    btn_balance="My balance",
    btn_buy="Buy credits",
    btn_reupload="Re-upload photos",
    btn_help="Help",
    btn_photo_guide="📸 Photo guide",
    btn_upload_person="📷 Upload my photo",
    btn_choose_outfit="👗 Choose an outfit",
    btn_try_another="👗 Try another",
    btn_invite="💫 Invite friends",
    btn_share="📤 Share with friends",
    btn_buy_credits="⭐ Buy credits",
    btn_style_guide="✨ What to pair with this",
    style_guide_offer=(
        "Love this look? 🔥 Get a style board for this piece — "
        "what to pair, colors & accessories. *1 try-on.*"
    ),
    style_guide_generating="Putting your style board together… about 20 sec ✨",
    style_guide_caption="Your style board — pairings, colors & accessories for this look 👗",
    style_guide_already="You've already got a style board for this look 👇",
    style_guide_failed=(
        "That one didn't come through — and I've refunded your try-on. "
        "Mind giving it another go?"
    ),
    style_guide_not_found=(
        "I can't find that try-on anymore. Send a clothing photo and let's style something new 👗"
    ),
    shop_most_chosen="Most chosen",
    help_text=(
        "How FitRoom works:\n"
        "1. Upload one full-body photo of yourself.\n"
        "2. Send a clothing photo to see it on you.\n"
        "3. Each try-on costs 1 credit.\n\n"
        "Tips for better results:\n"
        "• Stand straight, arms visible, good lighting.\n"
        "• Use a plain background for your photos.\n"
        "• Garment photo should show the item clearly on a neutral background.\n\n"
        "Commands:\n"
        "/start — restart onboarding\n"
        "/guide — photo tips\n"
        "/balance — check credits\n"
        "/shop — buy credit packs with Telegram Stars\n"
        "/photos — re-upload your photos"
    ),
    balance_text="Balance: {balance} credit(s).\n1 credit = 1 try-on.",
    balance_line="1 credit = 1 try-on.",
    try_on_hint="Send a clothing photo to try it on 👗\n1 try-on · Balance: {balance}",
    circuit_open=(
        "The fitting room's briefly busy 🙈 Give it a couple of minutes and try again — your try-ons are safe."
    ),
    concurrent="One look at a time 😊 I'm still finishing your last try-on — hang tight a few seconds.",
    not_enough_credits="Not enough try-ons left.",
    generation_failed="That one didn't come through — and I've refunded your try-on. Mind giving it another go?",
    photo_too_small="Hmm, that photo's a little small to work with. Send a clearer one (at least 256px wide) and we're good 📷",
    photo_bad_format="I couldn't open that image. Send it as a JPG or PNG photo and I'll take it from there 📷",
    garment_too_small="That item photo's a bit small. Send a clearer product shot and I'll style it on you 👗",
    send_start_first="Send /start first.",
    upload_photos_first="Upload your photos first. Send /start to begin onboarding.",
    no_saved_photos="No saved photos found. Send /photos to upload again.",
    photo_limit_reached=(
        "Photo limit reached ({limit}). Your latest saved photo is used for try-ons."
    ),
    photo_saved_send_garment="Photo saved. Send a clothing photo to try it on.",
    photo_progress_optional=(
        "Photo updated ({count}/{limit}). "
        "Send a clothing photo or upload another reference."
    ),
    reupload_prompt=(
        "Send new photos (up to {limit} stored). "
        "Your latest photo becomes the primary try-on reference."
    ),
    delete_confirmation="All your photos and data have been deleted.",
    stop_reminders="Reminders stopped. You won't receive follow-up messages.",
    stop_reminders_done="You won't receive follow-up messages.",
    shop_header="Buy try-on credits with Telegram Stars:",
    shop_credit_line="1 credit = 1 try-on generation.",
    invoice_description="Virtual clothing try-on credits for FitRoom.",
    invoice_credits_title="{credits} Try-On Credits",
    payment_success=(
        "Payment successful! +{credits} credits added.\nNew balance: {balance} credit(s)."
    ),
    payment_duplicate="Payment already processed. Balance: {balance} credit(s).",
    credit_packs=(
        CreditPack(id="single", credits=1, stars=20, label="Single — 1 try-on"),
        CreditPack(id="starter", credits=5, stars=50, label="Starter — 5 try-ons"),
        CreditPack(
            id="popular",
            credits=15,
            stars=120,
            label="Popular — 15 try-ons",
            highlight=True,
        ),
        CreditPack(id="best", credits=40, stars=250, label="Best Value — 40 try-ons"),
    ),
    drip_messages={
        "T1": (
            "Still thinking about that look? Send another outfit — "
            "{balance} free try-on(s) left 👗"
        ),
        "T2": (
            "That outfit looked great on you. Try 3 more before checkout — "
            "Popular pack 120⭐"
        ),
        "T3": "Your fitting room is waiting — see how that next outfit looks on you 👗",
        "T4": (
            "Shoppers love trying before they buy. Starter pack — 5 try-ons for 50⭐"
        ),
        "T5": "Out of credits! Grab *5 more try-ons for 50⭐* — takes 5 seconds.",
        "T6": (
            "Running low — only {balance} try-on(s) left. "
            "Stock up before your next outfit 👗"
        ),
        "T7": (
            "We miss you! Come back and try something new — "
            "Single try-on for 10⭐ today"
        ),
        "post_purchase_upsell": (
            "Loving your try-ons? Upgrade to *Popular — 15 try-ons* "
            "for just +70⭐ more than Starter!"
        ),
    },
    referral_returning="Welcome back! You have {balance} credit(s).\nSend a clothing photo or use the menu below.",
)
