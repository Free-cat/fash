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
        "You have *{free_credits} free try-ons*.\n\n"
        "👉 *Send a clothing photo* — dress, jacket, anything — and see it on *you*."
    ),
    generating="Styling your look… this takes about 15 sec ✨",
    result_caption="This is *you* in that outfit 🔥",
    paywall=(
        "You've tried 2 looks — and one was fire 🔥\n"
        "Keep going: 5 try-ons for 356⭐\n\n"
        "Not ready to pay? Show a friend how you look in this — "
        "+1 free when they try it ✨"
    ),
    deficit=(
        "Out again? You must be into this 😏\n"
        "This time — Popular: 15 try-ons for 799⭐ "
        "(cheaper per try-on than last time)"
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
        "Show a friend how you look in this outfit — let them try it themselves ✨\n"
        "(and when they complete their first try-on — you get +1 free)"
    ),
    share_inline_query="Look what I'd wear! Try it yourself →",
    btn_try_on="Try on clothing",
    btn_balance="My balance",
    btn_buy="Buy credits",
    btn_my_photos="📷 My photos",
    btn_see_on_me="✨ See it on me",
    btn_add_item="➕ Add another item",
    btn_add_to_look="➕ Add item",
    btn_clear_look="🗑 Clear look",
    btn_help="Help",
    btn_photo_guide="📸 Photo guide",
    btn_upload_person="📷 Upload my photo",
    btn_choose_outfit="👗 Choose an outfit",
    btn_try_another="👗 Try another",
    btn_invite="💫 Invite friends",
    btn_share="📤 Share with friends",
    btn_buy_credits="⭐ Buy credits",
    btn_style_guide="✨ Full styling — 3",
    btn_style_guide_showcase="✨ Full styling — 1",
    btn_use_photo="✓ Use this for try-ons",
    btn_photo_active="✓ Active for try-ons",
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
    premium_offer_v1=(
        "9 looks for 3 try-ons — less per look than a regular try-on. "
        "Your palette + shoes, bag, and accessories for this piece."
    ),
    premium_offer_v2=(
        'Want people to ask "do you have a stylist?" 👀\n'
        "9 looks with this piece, exact palette, accessory picks — "
        "the full pro-styling package."
    ),
    premium_showcase_offer_v1=(
        "Your first full styling — 9 looks, palette & accessories "
        "for this piece. *Just 1 try-on.*"
    ),
    premium_showcase_offer_v2=(
        "Try the full pro-styling package once — 9 looks with this piece, "
        "your palette & accessory picks. *1 try-on today.*"
    ),
    premium_offer_preview_caption=(
        "Here's what you get — yours will be styled with this look"
    ),
    premium_offer_cross_sell=(
        "Full styling takes {cost} try-ons — you have {balance}. "
        "Grab a pack or invite a friend, then give it a go 👇"
    ),
    premium_style_guide_failed=(
        "Couldn't put the styling board together — I've refunded all 3 try-ons. "
        "Want to try again?"
    ),
    premium_showcase_failed=(
        "Couldn't put the styling board together — I've refunded your try-on. "
        "Want to try again?"
    ),
    shop_most_chosen="Most chosen",
    help_text=(
        "How FitRoom works:\n"
        "1. Upload one full-body photo of yourself.\n"
        "2. Send a clothing photo to see it on you.\n"
        "3. Each look costs 1 try-on.\n\n"
        "*My photos*\n"
        "Save full-body photos — tap 📷 My photos to manage them. "
        "One photo is active for try-ons at a time.\n\n"
        "*Look cart*\n"
        "Send one or several clothing photos to build a look (up to 5 items). "
        "Tap ✨ See it on me when ready — 1 try-on for the whole look.\n\n"
        "*After a try-on*\n"
        "Tap ✨ What to pair with this for a style board — pairings, colors & accessories (1 try-on).\n\n"
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
    balance_text=(
        "You have *{balance} try-on(s)* left.\n\n"
        "Top up now — bigger packs cost less per look 👇"
    ),
    balance_empty=(
        "You're out of try-ons 👀\n\n"
        "Grab a pack and keep styling — bigger packs cost less per look.\n"
        "Or invite a friend for *+1 free* ✨"
    ),
    balance_line="1 try-on = 1 look on you.",
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
    photo_limit_reached="You can keep adding photos — one stays active for try-ons.",
    photo_saved_send_garment="Photo saved. Send a clothing photo to try it on.",
    photo_progress_optional=(
        "Photo saved ({count} in My photos). "
        "Send a clothing photo or upload another reference."
    ),
    reupload_prompt=(
        "Send a full-body photo to add to My photos. "
        "Your latest photo becomes the active try-on reference."
    ),
    delete_confirmation="All your photos and data have been deleted.",
    stop_reminders="Reminders stopped. You won't receive follow-up messages.",
    stop_reminders_done="You won't receive follow-up messages.",
    shop_header="✨ Get more try-ons",
    shop_subheader="Bigger packs cost less per photo — pick what fits you.",
    shop_credit_line="1 credit = 1 try-on generation.",
    invoice_description="Virtual clothing try-on credits for FitRoom.",
    invoice_credits_title="{credits} Try-On Credits",
    invoice_discount_note=("{anchor}⭐ → {stars}⭐ · save {pct}%\n"),
    payment_success=(
        "Payment successful! +{credits} credits added.\nNew balance: {balance} credit(s)."
    ),
    payment_duplicate="Payment already processed. Balance: {balance} credit(s).",
    credit_packs=(
        CreditPack(
            id="single",
            credits=1,
            stars=89,
            label="Single — 1 try-on",
            qty_label="1 try-on",
        ),
        CreditPack(
            id="starter",
            credits=5,
            stars=356,
            label="Starter — 5 try-ons",
            qty_label="5 try-ons",
            anchor_stars=445,
        ),
        CreditPack(
            id="popular",
            credits=15,
            stars=799,
            label="Popular — 15 try-ons",
            qty_label="15 try-ons",
            highlight=True,
            anchor_stars=1335,
            badge="most people's pick",
            emoji="🔥",
        ),
        CreditPack(
            id="best",
            credits=40,
            stars=1780,
            label="Best Value — 40 try-ons",
            qty_label="40 try-ons",
            anchor_stars=3560,
            badge="lowest price per photo",
            emoji="💎",
        ),
    ),
    drip_messages={
        "T1": (
            "Still thinking about that look? Send another outfit — "
            "{balance} free try-on(s) left 👗"
        ),
        "T2": (
            "That outfit looked great on you. Try 3 more before checkout — "
            "Popular pack 799⭐"
        ),
        "T3": "Your fitting room is waiting — see how that next outfit looks on you 👗",
        "T4": (
            "Shoppers love trying before they buy. Starter pack — 5 try-ons for 356⭐"
        ),
        "T5": "Out of credits! Grab *5 more try-ons for 356⭐* — takes 5 seconds.",
        "T6": (
            "Running low — only {balance} try-on(s) left. "
            "Stock up before your next outfit 👗"
        ),
        "T7": (
            "We miss you! Come back and try something new — "
            "Single try-on for 49⭐ today"
        ),
        "post_purchase_upsell": (
            "Loving your try-ons? Upgrade to *Popular — 15 try-ons* — "
            "less than half the price per photo of Starter."
        ),
    },
    referral_returning="Welcome back! You have {balance} credit(s).\nSend a clothing photo or use the menu below.",
    look_item_added=(
        "Got it — {count} item(s) in your look 👗\n"
        "Using Photo {active_slot} ✓ · 1 try-on when you're ready"
    ),
    look_one_item_hint="Add more for a full look, or see it on you now.",
    look_full="Look full — 5 items 🔥",
    look_cleared=(
        "Look cleared — cart, add-item wait, and this result chain are gone. "
        "Send clothing photos when you're ready 👗"
    ),
    look_add_item_prompt=(
        "Send a clothing photo to add to *this* look — "
        "I'll layer it onto your last result (1 try-on)."
    ),
    look_add_item_generating="Adding it to your look… about 15 sec ✨",
    look_add_item_no_active=(
        "No active look to add to — send a clothing photo and generate a look first 👗"
    ),
    look_generating_one="Putting it on you… about 15 sec ✨",
    look_generating_many="Putting your look on you… about 20 sec ✨",
    photo_switched="Photo {slot} is now your active photo 👍",
    gallery_header=(
        "*My photos* ({count})\n"
        "Preview: Photo {preview_slot} · Active: Photo {active_slot} ✓\n"
        "_Browse with ◀ ▶, then tap Use this for try-ons_"
    ),
    gallery_empty=(
        "*My photos*\n"
        "No photos yet — send a full-body photo to get started 📷"
    ),
    gallery_hint="Browse with ◀ ▶, then tap Use this for try-ons",
    try_on_hint_v2=(
        "Send clothing photos — one or several 👗\n"
        "Using Photo {active_slot} ✓ · add items, then See it on me · 1 try-on"
    ),
    person_photo_in_tryon="Looks like a photo of you — add it to My photos?",
    welcome_back_draft_look="Welcome back 👋\nYou have a look waiting — {count} items.",
    fallback_onboarding_person=(
        "Send a *full-body photo of yourself* here 📷\n\n"
        "Tips: good light, plain background, arms visible.\n"
        "Or tap 📸 *Photo guide* first."
    ),
    fallback_add_person_photo=(
        "Send a *full-body photo* to add to My photos 📷\n\n"
        "Plain background and good light work best."
    ),
    fallback_unknown=(
        "I didn't quite catch that 😊\n\n"
        "Here's what works:\n"
        "• Send a *clothing photo* to try it on 👗\n"
        "• Tap 📷 *My photos* to manage your reference photos\n"
        "• /help — full guide\n\n"
        "Balance: {balance} try-on(s)"
    ),
    fallback_unknown_with_cart=(
        "I didn't quite catch that 😊\n\n"
        "You have *{count} item(s)* in your look — tap ✨ *See it on me* "
        "when ready.\n"
        "Or send another clothing photo to add to the look 👗\n\n"
        "Balance: {balance} try-on(s)"
    ),
    admin_grant_prompt_user=(
        "🎁 *Grant try-ons*\n\n"
        "Send the user's *Telegram ID* (numbers only).\n"
        "Or /cancel to abort."
    ),
    admin_grant_invalid_id="That doesn't look like a Telegram ID. Send numbers only.",
    admin_grant_pick_amount=(
        "User `{telegram_id}` — current balance: *{balance}*.\n"
        "How many try-ons to add?"
    ),
    admin_grant_success=(
        "Done ✅ Added *{amount}* try-on(s) to `{telegram_id}`.\n"
        "New balance: *{balance}*"
    ),
    admin_grant_amount_invalid="Amount must be between 1 and 100.",
)
