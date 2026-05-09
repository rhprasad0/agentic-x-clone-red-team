# Reader learning-plan prompt

This file is a companion artifact for a public article about CARBOTS, the local-first synthetic agentic-engineering project in this repository.

The intended reader is curious enough to keep going, but may not yet have the background to reproduce the whole project. The goal is not to make ChatGPT build the project for them. The goal is to turn the article into a practical learning path: what to learn first, what to build in tiny slices, how to verify progress, and how to avoid becoming a copy-paste raccoon in a hoodie.

## How to use this

1. Open ChatGPT, Claude, Gemini, or another capable assistant.
2. Paste the prompt below.
3. Replace the bracketed sections with the article text, repository context, and your background.
4. If the assistant asks diagnostic questions, answer them before asking for the full plan.
5. Treat the output as a draft. Check links, verify commands, and keep the scope small enough that you can actually finish the first slice.

If you only have five sessions, ask for the minimum viable learning path. A small working artifact beats a giant syllabus graveyard.

## Copyable prompt

```text
You are an AI engineering mentor, software architecture coach, and instructional designer.

I read an article about an AI engineering project and want to build the skills needed to understand it and eventually make my own smaller version. I may not currently have all the required skills.

Your job is to create a practical learning plan that closes my knowledge gaps without pretending I can become an expert overnight.

First, ask me up to 8 diagnostic questions if you need more context. If I already provided enough context, proceed.

Use these inputs:

ARTICLE / PROJECT CONTEXT:
[paste the article, README, project summary, or repository notes here]

MY BACKGROUND:
- Programming experience:
- Web/backend experience:
- Frontend experience:
- Databases experience:
- DevOps/cloud experience:
- Security/red-team experience:
- AI/LLM/agent experience:
- Testing experience:
- Anything I already know well:

MY GOAL:
[examples: understand the article, run the repository locally, build a tiny clone, build the backend only, learn AI agents, learn security testing, deploy a demo, prepare for AI engineering interviews]

TIME BUDGET:
[examples: 30 minutes/day for 2 weeks, weekends only, 5 focused sessions, 3 months]

TOOLS I CAN USE:
[examples: ChatGPT, Claude, GitHub Copilot, local Python, Docker, AWS, no cloud budget]

PREFERRED STYLE:
[examples: hands-on projects, reading docs, videos, exercises, interview prep, build-first, explain-like-I-am-new]

Hard requirements for your output:

1. Start with a plain-English summary of what this project requires.
2. Classify my current level as beginner, intermediate, or advanced for this specific project. Explain the classification using evidence from my background, not vibes.
3. Create a knowledge map of the project:
   - core programming skills
   - backend/API skills
   - frontend/UI skills
   - database/data-modeling skills
   - testing/quality skills
   - security/threat-modeling skills
   - AI/agent/LLM skills
   - deployment/devops skills
4. Identify my likely knowledge gaps.
5. Split the plan into the right path for my level:
   - Beginner path: more scaffolding, glossary, setup recipes, tiny wins, and worked examples.
   - Intermediate path: implementation slices, debugging practice, tradeoffs, tests, and small extensions.
   - Advanced path: architecture critique, hardening, observability, deployment, scaling, threat modeling, and independent design.
6. Give me a week-by-week plan or session-by-session plan based on my time budget.
7. Every session must include:
   - objective
   - short reading or reference
   - hands-on task
   - deliverable/artifact
   - verification check
   - reflection question
8. Include a "minimum viable learning path" of only 5 sessions in case I get busy.
9. Include "AI tutor rules" so I use ChatGPT/Claude to learn instead of blindly outsourcing:
   - ask me to explain concepts back
   - make me predict before revealing answers
   - require tests or verification
   - include critique-the-AI steps
   - include at least one AI-off checkpoint per week
10. Recommend resources, but keep them short and high-leverage. Prefer official docs, small tutorials, and project-specific exercises over giant book lists.
11. Include safety/ethics guardrails:
   - use only synthetic data
   - do not attack third-party systems
   - do not use real user data or credentials
   - do not publish secrets
   - do not overclaim what the project proves
12. End with the first 3 actions I should take today.

Good output looks concrete, paced, and project-specific.
Bad output looks like generic advice such as "learn Python, watch some YouTube videos, then build an app."

Do not write the whole project for me. Teach me how to grow into it.
```

## Optional follow-up prompts

Use these after the first plan if the output is too broad, too easy, or too much like a generic internet curriculum wearing a tiny fake mustache.

### Turn the plan into a tiny starter project

```text
Using the learning plan above, design a tiny starter project I can complete in one weekend.

It should preserve the core idea of the article but reduce the scope by 90%.

Include:
- the smallest possible feature set
- file/folder structure
- setup steps
- 3 tests I should write
- what "done" looks like
- what to deliberately ignore for now
```

### Make it beginner-friendly

```text
Rewrite this learning plan for a motivated beginner.

Assume I can write basic code but get lost when projects involve APIs, databases, Docker, auth, tests, or deployment.

Add:
- glossary
- prerequisites
- warning signs that I am skipping too far ahead
- smaller practice exercises before each project task
- checkpoints where I explain the idea back in my own words
```

### Make it advanced/interview-oriented

```text
Rewrite this learning plan for an experienced developer trying to turn the project into AI Engineering interview signal.

Emphasize:
- architecture decisions
- tradeoffs
- testing strategy
- threat modeling
- observability
- public-safe evidence
- deployment choices
- how to explain the project in interviews without overclaiming
```

### Use AI without becoming a passenger

```text
Audit my learning plan for places where I might accidentally let AI do the thinking for me.

For each risky task, add:
- what I should attempt before asking AI
- what I can ask AI for
- how I should verify the answer
- what I should write down in a learning journal
- one AI-off checkpoint
```

## Why this prompt is structured this way

A good learning plan needs more than a list of topics. It needs learner context, concrete artifacts, verification checks, and pacing.

This prompt asks the assistant to diagnose the reader's starting point first, then adapt the level of scaffolding. Beginners need setup recipes, examples, and small wins. Intermediate learners need implementation slices and debugging reps. Advanced readers need architecture review, hardening, tradeoffs, and public-claim discipline.

The prompt also forces verification. That matters because AI assistants are good at sounding done before anything has been tested. The learner should leave each session with a receipt: a command that passes, a tiny feature that works, a diagram they can explain, a threat model they can defend, or a design decision they can justify.

That is the useful version of AI-assisted learning: not "the robot did my homework," but "the robot helped me find the next rung on the ladder."
