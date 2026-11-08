"""
What your test runs. ← UNIT 8, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
false positives needs your own writing. One about label coverage needs inputs
across the score range. One about the appeal path needs a real content_id.

Working that out is Milestone 3's first step, and this file is where you write
it down. `run_eval.py` runs everything here three times.

Two are filled in as examples. Replace them with what your criteria actually
need — these are a shape, not a set.

A scenario carries **either** of these:

    "texts"   a list of strings. Each is sent as {"text": ..., "creator_id": ...}
              with a creator_id made up for you. Use this for most criteria.

    "bodies"  a list of whole request bodies, sent exactly as written. Use this
              when the malformed request IS the point — empty text, no `text`
              field at all, something enormous. A bad-input criterion needs it,
              because you cannot express "the field is missing" as a string.
"""

# Clearly AI-generated: I had Claude write these in the default "explainer"
# register, with no editing. Used for criterion 4 (the AI half of the gap).
CLEAR_AI = [
    "Effective time management is a crucial skill for students and professionals alike. By prioritizing tasks and setting clear goals, individuals can significantly enhance their productivity and reduce stress. One widely used strategy is the Eisenhower Matrix, which categorizes tasks based on their urgency and importance. Additionally, breaking larger projects into smaller, manageable steps can help maintain momentum and prevent procrastination. It is also important to schedule regular breaks, as research suggests that short periods of rest can improve focus and overall performance. Furthermore, leveraging digital tools such as calendars and task management applications can streamline planning. Ultimately, developing strong time management habits requires consistency, self-awareness, and a willingness to adapt strategies as circumstances change.",
    "Climate change represents one of the most pressing challenges facing humanity today. Rising global temperatures are contributing to more frequent extreme weather events, including droughts, floods, and wildfires. These changes have significant implications for ecosystems, agriculture, and human health. To address this issue, governments and organizations around the world are implementing a range of mitigation and adaptation strategies. Transitioning to renewable energy sources such as solar and wind power is essential for reducing greenhouse gas emissions. In addition, improving energy efficiency and protecting natural carbon sinks like forests can play a vital role. Ultimately, meaningful progress will require collaboration across sectors and a sustained commitment to sustainable practices at every level of society.",
    "Regular physical activity offers numerous benefits for both physical and mental health. Engaging in exercise helps strengthen the cardiovascular system, improve muscle tone, and maintain a healthy body weight. Moreover, physical activity has been shown to reduce symptoms of anxiety and depression by promoting the release of endorphins. Experts generally recommend at least 150 minutes of moderate aerobic activity per week, combined with muscle-strengthening exercises on two or more days. It is important to choose activities that are enjoyable, as this increases the likelihood of long-term adherence. Additionally, incorporating movement into daily routines, such as walking or cycling to work, can make it easier to stay active. Overall, regular exercise is a key component of a balanced and healthy lifestyle.",
    "Artificial intelligence is rapidly transforming the landscape of modern education. Adaptive learning platforms can tailor content to the needs of individual students, providing personalized feedback and support. This approach has the potential to improve learning outcomes and increase student engagement. However, the integration of artificial intelligence in education also raises important ethical considerations. Concerns about data privacy, algorithmic bias, and the role of teachers must be carefully addressed. Educators and policymakers should work together to establish clear guidelines that ensure these technologies are used responsibly. Furthermore, it is essential to provide training for teachers so they can effectively incorporate new tools into their classrooms. By striking the right balance, schools can harness the benefits of artificial intelligence while minimizing potential risks.",
    "Reading regularly provides a wide range of cognitive and emotional benefits. It enhances vocabulary, improves concentration, and strengthens analytical thinking skills. Furthermore, reading fiction has been linked to increased empathy, as it allows readers to experience the perspectives of different characters. In today's fast-paced digital world, many people find it challenging to set aside time for reading. However, establishing a consistent routine, such as reading for twenty minutes before bed, can make a significant difference. Additionally, joining a book club or setting personal reading goals can provide motivation and accountability. Ultimately, cultivating a reading habit is a valuable investment in personal growth and lifelong learning, offering both knowledge and enjoyment.",
]

# My own writing, taken from coursework I wrote myself (files in my Downloads
# folder, named beside each piece). Copied as written, typos and all; only
# the assignment's own prompt text was cut out. Where one section was under
# 100 words, it is joined to the next section of the same assignment.
MY_WRITING = [
    # reflection 7, para 1
    "This week’s reading helped me really understand and see that our food system was built off the backs of immigrants, and how it not only connects historically but in modern day as well. In Fresh Fruit, Broken Bodies Holmes explains the physical and emotional toll that migrants struggle with when working as a farmworker which include bent backs, injured knees, the pain and hardship they go through is all to keep the food we take for granted for as low as possible to benefit the consumer and the farmers. How Holmes explains the migrant workers who harvest our fruits and vegetables are seen as disposable even though they do so much for America.",
    # reflection 7, paras 2-3
    "The United Farm Workers underlined that with action of organizing can help fight against these injustices like what Cesar Chavez and Dolores Huerta did. But as the articles from Civil Eats and FWD.us underlines these problems still persist today. Immigrants that work for farms are still in unsafe conditions, still deal with wage theft, and food insecurity which is ironic since they work to feed the country. Reading this made me see how we can easily forget the human suffering behind the abundance we take advantage of. It also emphasized that empathy doesn’t change injustices we have to stand for policy change and spread awareness. Personally, this week changed how I view “essential work”. My family business experience has shown me the value of treating employees with fairness and holding each other accountable. Now I see those principles aren’t really reflected in agriculture. The agricultural and life sciences industries depend not only on technology but also people, nevertheless they don’t show the ethical importance of acknowledging their workers assistance. I think going forward integrating a better approach that is beneficial to all sides of the agriculture process is important to prevent injustices in the development of the food we eat.",
    # Labreport4, procedures
    "For the experiment, we set up a cart on a flat track and tied a string to it that went over a pulley with a weight hanging down. A motion sensor tracked how the cart moved when we let go of it. We did this a few times, changing the weight each time by moving 5g off from the cart starting from 25g to the hangar until there was no more weight on the cart. After each run, we looked at the data to see how fast the cart was going and how it sped up. Finally, we saw the graph through the capstone software to see how the weight and acceleration were related.",
    # Labreport4, intro + conclusion
    "In this lab, We did an experiment that proved Newton’s second law of motion, which states that how fast the acceleration is depends on the force and how heavy the mass is. We used a cart on a track and a hanging weight to see how changing the weight affects the cart’s speed. We also tried to determine gravity's value by looking at how the cart moved. This helped us gain a greater understanding of how force and mass work together in the real world. This lab taught us that Newton’s Second Law is true because the more weight we hung, the faster the cart sped up, and the heavier the cart was, the slower it went. We also got a close value for gravity, though it wasn’t perfect because of small mistakes due to friction or the sensor not picking up motion perfectly. Even so, I learned a lot from this lab and got to see how force and mass could relate to the real world.",
    # HW2 Redesign, part 1
    "Previously in Homework 1, my negative emotional experience I identified was TikTok. As we all know TikTok is our go to form of social media now, but it’s also highly addictive, Its algorithm is personalized to each user to make it difficult to stop scrolling. This design leads to hours of lost time and feelings of guilt afterwards. The endless feed and autoplay design reduces users sense of control over time, resulting in a negative emotional impact. 1. Specific break reminders Periodic pop-ups reminding the user how long they’ve been watching and suggesting a break 2. Timer Customization Allows user to set their own daily scrolling limits. Which would then lock the app preventing them from scrolling 3. Positive Reflection To counter act the guilty feeling a reflection screen for the user telling them how many times they laughed or how many new topics they explored, helping shift the focus from time wasted to value gained. 4. Smart Queue Replaces infinite scroll with a stop after 10 – 15 videos, The app then asks three options “continue watching, short break, daily recap” 5. Calming mode Theme changes softer colors and slows down overstimulation by slowing animations and choosing fewer stimulating videos to help the user to get off the app by slowing down dopamine and scrolling compulsion.",
    # HW2 Redesign, part 2
    "I chose to focus on Idea 1. Specific break Reminder, 2. Timer Customization, and 4. Smart Queue because they help let the user control and keep track of time on the app while still being able to use and enjoy TikTok. - Feedback The Specific reminder makes the user aware of the exact time usage to keep track of how much time is being wasted - Control and Autonomy Allowing user to set their time limit on the app to help keep them self-accountable. - Emotional design By the reminder given whilst endlessly scrolling with the 3 options from the smart queue changes the app to exploitative to empathetic. - Consistency These features would fit naturally with TikTok’s interface to lower learning efforts - Affordance The Buttons that say “Continue, Pause, Recap” are labeled to help encourage mindfulness With all of these UX principles/guidelines will help transform the app for entertainment with a balance of accountability rather than jut endless consumption and guilt.",
    # The Plan, cause + goal
    "My agent of change cause is using my knowledge as a computer science student to advocate for more accessible and human centered systems especially in healthcare and humanitarian context. The region I’d like to highlight is Palestine, where inaccessible healthcare systems, broken digital infrastructure, and lack of usable technology has made the crisis even worse. By underlining these problems, I hope to achieve improved care, coordination, and aid for these civilians. The goal of this data narrative is to raise awareness of the humanitarian crisis in Palestine and encourage action in the form of donations and engagement. By the end of the narrative’s viewers should understand the scale of civilian suffering and humanitarian need. Success will be measured by viewer engagement and interactions with linked aid resources.",
    # Podcast Planning, section 1
    "The issue I will be looking at is the humanitarian crisis faced by Palestinian civilians (particularly those living in Gaza) who are suffering from a lack of food, clean water, basic medical supplies, and shelter. There are many instances of spikes in media coverage when global events occur, but the media’s focus usually disappears once the event is no longer newsworthy even when every day people are still struggling with their reality. This podcast will emphasize the need to understand the ongoing humanitarian crisis and how it requires persistent attention, rather than just outrage, from people all over the world. This issue is very similar to the general subject of my photo essay (“Life Under Crisis”) and to my data narrative (“The Human Cost of Conflict”) from earlier in the semester. This podcast will be specifically focused on the connection between the digital activity of the average consumer and the act of advocating for humanitarian aid for Palestine.",
    # Podcast Planning, section 5a
    "The ability to mobilize communities and create global impact for Palestine is unprecedented through the use of social media. During the 2021 and 2023-2024 escalations there were using social media the hashtags related to Palestine trended worldwide and millions of people participated in Boycotts online. This type of mobilization has translated into direct actions through physical protests, advocating for policy changes, and donations for Palestinian causes. At the same time, social media platforms have been limiting Palestinian users' content. According to the research conducted by Human Rights Watch there was substantial systematic suppression of Palestinian voices on Facebook and Instagram by Meta through their algorithms. This has created a fundamental question: when we rely on algorithmic feeds in our digital habits, do we have an accurate picture of the humanitarian crises taking place?",
    # Prototype toolbox, all three answers
    "My Prototype was a toolbox with two side pockets. The main body holds larger tools, while the side pockets are used to hold smaller items like screws and nails. It has a handle for carrying its primary use is for the organization and transport of utility tools. I chose a toolbox as my design because I needed something to hold my tools rather than bag where everything doesn’t seem as organized. Adding the additional side pockets makes gives me extra organization space. This project also helped me improve and practice assembling multiple parts. I believe the Limitations of the design was how it all holds into place there are no screws or anything to make everything stable or keep everything connected. As for the design it does not include latches, hinges or a fastener like a real toolbox has and the handle is simple with no real grip so it could be difficult to hold it when the toolbox gets heavy.",
]

# Criterion 4's human half: five of the pieces above. My own writing is the
# text I'm most confident a person wrote, so it is reused here on purpose.
CLEAR_HUMAN = [MY_WRITING[i] for i in (0, 2, 6, 7, 9)]

# Criterion 5: short plain pieces of mine, all under 100 words. Two of them
# (the lab conclusion and the toolbox limitations) are also part of longer
# pieces in MY_WRITING; here they are sent on their own.
SHORT_PLAIN_HUMAN = [
    # Proudest work
    "I wound say my proudest work so far would be that I was the Product Manager for a dungeon crawler game, where I defined the vision and turned gameplay ideas into clear development tasks. I prioritized core features like enemy AI, progression systems, and level design, making sure we balanced what was technically possible with what would be fun to play. I focused on breaking down complex systems and keeping the team aligned on what mattered most.",
    # The Plan, audience
    "The primary audience is anyone with social media access most likely young adults upwards. Since there is no defined age to help someone I feel as though this question doesn’t fit because anyone from any age group, location, education, or income can help even if it comes to spreading awareness rather than donations.",
    # Podcast Planning, section 5b
    "I have seen this first hand. When news stories about Palestine were being reported on, my social media feeds were filled with content about Palestine. However as soon as the news shifted, the algorithm would bury that content. The attention economy discussed throughout the podcast serves as a primary argument supporting the podcast's belief that our digital habits are not objective and that we need to actively seek out information.",
    # Labreport4, conclusion
    "This lab taught us that Newton’s Second Law is true because the more weight we hung, the faster the cart sped up, and the heavier the cart was, the slower it went. We also got a close value for gravity, though it wasn’t perfect because of small mistakes due to friction or the sensor not picking up motion perfectly. Even so, I learned a lot from this lab and got to see how force and mass could relate to the real world.",
    # Prototype, limitations
    "I believe the Limitations of the design was how it all holds into place there are no screws or anything to make everything stable or keep everything connected. As for the design it does not include latches, hinges or a fastener like a real toolbox has and the handle is simple with no real grip so it could be difficult to hold it when the toolbox gets heavy.",
]

# Criterion 3 only needs real content_ids to appeal, so what the text says
# doesn't matter. Ten short AI-written texts, each over 10 words.
APPEAL_TEXTS = [
    f"This is appeal test submission number {n}. It exists so that the service "
    f"returns a content id, which the appeal can then be sent against."
    for n in range(1, 11)
]

SCENARIOS = [
    {
        "name": "c1 my own writing",
        "criterion": 1,
        "texts": MY_WRITING,
    },
    {
        "name": "c2 bad input",
        "criterion": 2,
        # Raw request bodies, sent exactly as written. Each creator_id is
        # different so the rate limiter doesn't get in the way of the test.
        "bodies": [
            {"creator_id": "c2_missing_text"},                          # no text field
            {"text": "", "creator_id": "c2_empty_text"},                # empty
            {"text": "   \n\t  ", "creator_id": "c2_whitespace_text"},  # whitespace only
            {"text": "only five words right here", "creator_id": "c2_short_text"},  # < 10 words
            {"text": "word " * 5000, "creator_id": "c2_huge_text"},     # 25,000 chars
            ["text", "creator_id"],                                     # not a JSON object
        ],
    },
    {
        "name": "c3 appeals",
        "criterion": 3,
        "appeal": True,   # run_eval.py appeals each content_id and checks the log
        "texts": APPEAL_TEXTS,
    },
    {
        "name": "c4 clear AI",
        "criterion": 4,
        "texts": CLEAR_AI,
    },
    {
        "name": "c4 clear human",
        "criterion": 4,
        "texts": CLEAR_HUMAN,
    },
    {
        "name": "c5 short plain human",
        "criterion": 5,
        "texts": SHORT_PLAIN_HUMAN,
    },
]


def validate() -> list[str]:
    """
    Complain about anything malformed, before a long run rather than during.

    A "bodies" scenario is deliberately exempt from the empty check — an empty
    string is the whole point of a bad-input case, and refusing to run one
    would make that criterion untestable.
    """
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("name"):
            problems.append(f"scenario {i} has no name")

        texts = scenario.get("texts")
        bodies = scenario.get("bodies")

        if texts and bodies:
            problems.append(
                f"scenario {i} ('{scenario.get('name')}') has both texts and "
                f"bodies — pick one"
            )
            continue

        if bodies:
            for j, body in enumerate(bodies, 1):
                # A list is allowed on purpose: "the body isn't a JSON object"
                # is one of criterion 2's cases.
                if not isinstance(body, (dict, list)):
                    problems.append(
                        f"scenario {i}, body {j} is not a dict or list — bodies are "
                        f"whole request bodies, like {{'text': '', 'creator_id': 'x'}}"
                    )
            continue

        if not texts:
            problems.append(f"scenario {i} has no texts and no bodies")
            continue

        for j, text in enumerate(texts, 1):
            if not str(text).strip():
                problems.append(
                    f"scenario {i}, text {j} is empty — if an empty submission is what "
                    f"you're testing, use 'bodies' instead of 'texts'"
                )
            elif str(text).startswith("REPLACE ME"):
                problems.append(
                    f"scenario {i} ('{scenario.get('name')}'), text {j} is still "
                    f"the placeholder"
                )
    return problems
