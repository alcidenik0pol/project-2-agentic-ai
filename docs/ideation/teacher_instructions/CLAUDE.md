# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This directory stores the teacher's project instructions for Columbia Agentic AI Project 2. The goal is to understand and rank requirements by importance and difficulty.

## Key Files

- `src/instructions.md` - Full project specification (grading criteria, core/elective requirements)

## Priority Analysis

When reviewing requirements, maintain rankings in README.md for:
1. **Importance** - What matters most for the project grade
2. **Difficulty** - What will be hardest to implement (focus efforts here)
3. **Clarifications** - Any ambiguities that need resolution

## Grading Summary (30 pts total)

| Component | Points | Key Focus |
|-----------|--------|-----------|
| Step 1: Collect | 5 | Real data, runtime retrieval, dynamic to questions |
| Step 2: Explore (EDA) | 5 | Tool calls over data, surfaces specific findings |
| Step 3: Hypothesize | 5 | Data-grounded, cites evidence, explains reasoning |
| Core Requirements | 10 | Frontend (2), framework (1), tools (1), dataset (1), multi-agent (2), deployed (2), README (1) |
| Grab Bag (2 items) | 5 | 2.5 pts per elective concept |

## Critical Constraints

- Data cannot be hard-coded in system prompts
- Dataset must be too large to load entirely into context
- At least two agents with different system prompts
- Must pick ≥2 elective concepts from grab-bag list
