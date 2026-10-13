"""The wellness posters as the planner's supporting pages: which posters, in what order, the money framing line under each, and which claims the owner should check.

The owner's 44 "DID YOU KNOW" posters (assets/planner/wellness/) are wellness that goes hand in hand with money, so each page carries a short line that ties it to money decisions
and a not-medical-advice note. Four of the owner's posters repeat another one and are left out, which leaves 40; twelve more are typeset by the studio (planner_poster_make.py), so each of the 52 weeks ends with one "Wellness break" page.

`REVIEW` lists the posters whose text makes quantified, hormonal or clinical claims the studio has not checked (rule 1: every number is true). They are the owner's words and stay as made;
the page adds the disclaimer, and the owner should read these before the planner is sold. Nothing here edits a poster.
"""

from __future__ import annotations

from faceless import planner_posters

NOT_MEDICAL = ("Wellness information for education only, not medical advice. Check with a qualified health professional before changing your diet, exercise or "
               "health routine, especially if you have a health condition.")

# position (wellness-NNN) -> (topic, the line that ties it to money). Hedged on purpose: "can", "tends to", never a promise.
POSTERS: dict[int, tuple[str, str]] = {
    1: ("Time in nature", "Stress makes spending easier to justify. A walk under trees is a cheap way to cool down before you open a shopping app."),
    2: ("Sprints", "Short, hard effort feels like a lot and costs nothing. Money habits work the same way: small, intense, regular bursts beat rare heroic ones."),
    3: ("Yawning cools the brain", "A tired brain decides badly. If you are drowsy, put the big money decision off until you are sharp."),
    4: ("Copper jar water", "A free habit done every day beats an expensive one done once. Look for the daily habit that costs nothing and notice what it does for you."),
    5: ("Grip strength", "Strength is built in small, repeated efforts. So is savings: the amount matters less than showing up."),
    6: ("Skipping", "Playful movement lifts your mood for free. Moods drive spending, so a good mood on a cheap activity is money you keep."),
    7: ("Citrus peels", "The part we throw away can be the most valuable. Check what you throw away in your budget: forgotten subscriptions, unused things, small fees."),
    9: ("Baking soda and creatine", "Cheap basics often beat flashy products. Before paying more, ask what the plain version does."),
    10: ("Grounding", "Feet on the ground, mind off the screen. A few minutes without notifications is a few minutes without an impulse buy."),
    11: ("Aristotle's walking lectures", "Thinking while walking is free. Take a money question for a walk: What do I really want? Is this a need?"),
    12: ("REM sleep", "Poor sleep can cost money: more impulse buys, more takeaway, worse choices. Protecting your sleep is one of the cheapest money habits there is."),
    13: ("Cacao", "A small treat you plan is better than a big one you regret. Put it in your wants budget and enjoy it without guilt."),
    14: ("Testosterone and the brain", "Your body and your decisions are connected. Look after the basics (sleep, food, movement) and you tend to make steadier money choices."),
    15: ("Morning sunlight", "A morning routine you can repeat is a system. The same goes for money: a weekly hour, a transfer on payday, a simple check-in."),
    16: ("Neck exercises", "Small, regular posture habits add up. Small, regular money habits add up the same way."),
    17: ("Beef liver", "Nutrient-dense, low-cost food is cheaper than it sounds. Look at your food spending for choices that give more for less."),
    18: ("Cycling", "Moving yourself instead of paying for transport can lower costs and clear your head. Check what one trip a week would save."),
    19: ("Moringa tea", "Swapping a habit is not the same as paying more for it. Compare the cost of your daily drink with a cheaper one that you like just as much."),
    20: ("Watercress", "Everyday food can be the best value in the shop. Look for the plain, cheap item that does the job."),
    21: ("Humming", "A free calming habit you can do anywhere. Try it before a big purchase: when you are calm you tend to choose better."),
    22: ("Brisk walking", "A brisk walk costs nothing and is a good place to sort out worries. Many money worries look smaller after twenty minutes outside."),
    23: ("Cayenne pepper", "Spice is cheap flavour. Cooking at home with simple ingredients is one of the most reliable ways to cut food costs."),
    24: ("DNA data storage", "Huge amounts of information can sit in tiny places. Your money records can too: one folder, one page, one list of accounts."),
    26: ("Coffee and bananas", "Plan your fuel and you spend less on convenience. A banana in your bag is cheaper than a snack bought in a hurry."),
    27: ("Laughter", "Time with people you enjoy is cheap and good for you. Many of the best things in life cost very little."),
    28: ("Wild rice", "Pantry staples stretch a budget. A few good basics on hand means fewer expensive, last-minute meals."),
    29: ("Tomatoes are fruits", "What something is called does not change what it does. Ask the same of money: what does this actually do for me?"),
    32: ("Box breathing", "Four counts in, four hold, four out, four hold. Do it before you pay for something that was not on your list."),
    33: ("Neck training", "Strength comes from steady, boring repetition. So do your savings: the dull, regular transfer wins."),
    34: ("Playing the piano", "Learning a skill is one of the best uses of spare time, and skills are one of the best uses of spare money. They are what you can build income from."),
    35: ("The number 23", "Patterns are everywhere once you look. Look for patterns in your own spending: the same day, the same shop, the same trigger."),
    36: ("Walking backwards", "Trying something a little different keeps your mind sharp. Try one small change in your money routine this week."),
    37: ("The mirror", "We rarely see ourselves as others do. Look at your money the same way: ask a trusted friend what they would notice."),
    38: ("Wall sits", "Holding steady under discomfort is a skill. Staying with a plan when it feels dull is the same skill."),
    39: ("Cold showers", "Doing something hard on purpose builds the habit of doing hard things. Pay the bill you are avoiding first."),
    40: ("Forest bathing", "Time among trees is free. Many of the best ways to recover from a stressful week cost nothing."),
    41: ("Myostatin and follistatin", "Complex systems balance each other out. Your budget does too: more in one place means less in another."),
    42: ("Water with watermelon", "Hydration is cheap. Many drinks you buy out of habit are not what your body asked for."),
    43: ("Dogs and stress", "Pets cost money, and so do the things we buy to cope with stress. Notice what really helps you relax and what only feels like it."),
    44: ("Looking forward", "Looking forward to something can feel as good as having it. Plan a small treat and save for it: the anticipation is free."),
    # 45 to 56 are weeks 41 to 52: made by the studio in the owner's style (planner_poster_make.py), hedged, no clinical figures
    45: ("Sleep and impulse buys", "A tired brain finds it harder to say no. Put any unplanned purchase off until you have slept on it."),
    46: ("Shopping hungry", "Hungry shoppers tend to put more in the basket. Eat first, shop with a list, and keep the receipt for what you planned."),
    47: ("Gratitude", "Noticing what you already have can take the edge off wanting more. Write down three things before you open a shopping app."),
    48: ("Comparison", "Comparing your real life with other people's highlights can push you to spend to keep up. Compare yourself with last year's you instead."),
    49: ("A quiet hour", "A notification-free hour gives you space to look at your money without the pull of an offer. Try it once this week."),
    50: ("Stretch breaks", "Movement breaks cost nothing and clear your head. Take one before you make a money decision you have been putting off."),
    51: ("Meal planning", "A plan for the week's meals makes a shopping list easy and wasted food rare. It is one of the simplest ways to trim a food budget."),
    52: ("Walking with a friend", "Time with people you like is some of the cheapest good time there is. Suggest a walk in place of a paid outing."),
    53: ("Writing worries down", "A worry on paper is easier to size up than one in your head. Write the number next to it, then choose one small next step."),
    54: ("The pause", "Wait a day before an unplanned purchase. If you still want it tomorrow and it fits your plan, you can buy it calmly."),
    55: ("Giving", "Some research suggests that giving can feel rewarding. A small, planned gift line in your budget lets you be generous without strain."),
    56: ("Rest", "Rest is part of the plan, not a reward for finishing it. A rested mind makes steadier money choices and a year of them adds up."),
}
MADE = tuple(range(45, 57))                           # posters typeset by the studio; the other 40 are the owner's artwork
DUPLICATES = {8: 3, 25: 19, 30: 18, 31: 9}            # dropped position -> the poster it repeats (kept)
REVIEW = {2: "growth hormone rise stated as a percentage", 4: "claim about copper and bacteria", 5: "grip strength and testosterone", 9: "performance claims for baking soda and creatine",
          10: "grounding", 12: "dementia percentages", 13: "cacao and blood pressure figures", 14: "hormone claims (estrogen, aromatase)", 17: "beef liver, nutrient and toxicity claims",
          19: "moringa versus green tea", 20: "watercress and carcinogens", 21: "humming and nasal nitric oxide", 23: "cayenne and metabolism", 33: "neck training and androgen receptors",
          38: "wall sits and blood pressure figures", 40: "forest bathing and immune cells", 41: "myostatin and follistatin", 42: "bicarbonate in water"}


def kept() -> list[int]:
    """Poster positions in the order they appear: the 40 unique ones."""
    return sorted(POSTERS)


def week_poster(week: int) -> int | None:
    k = kept()
    return k[week - 1] if 1 <= week <= len(k) else None


def poster_path(pos: int):
    return planner_posters.CROPPED / f"wellness-{pos:03d}.jpg"


def check() -> list[str]:
    """Problems with the manifest: a missing poster file, a dropped one still listed, a line over 40 words, a duplicate that is not accounted for."""
    bad = []
    for pos, (_t, line) in POSTERS.items():
        if not poster_path(pos).exists():
            bad.append(f"wellness-{pos:03d} has no cropped file")
        if len(line.split()) > 40:
            bad.append(f"wellness-{pos:03d}: the line is over 40 words")
    if set(POSTERS) & set(DUPLICATES):
        bad.append("a dropped duplicate is still listed")
    if set(POSTERS) | set(DUPLICATES) != set(range(1, 57)):
        bad.append(f"positions not accounted for: {sorted(set(range(1, 57)) - set(POSTERS) - set(DUPLICATES))}")
    return bad
