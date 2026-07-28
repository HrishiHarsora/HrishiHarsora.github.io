---
title: Teaching a search tree to grow crystals
date: 2026-06-23
---
A MOCVD reactor is an expensive way to ask a question. Every run costs hours, precursor gases, and a wafer — and the answer is a single data point in a process space with dozens of dimensions. So the obvious move is to ask a simulator instead, and the less obvious move is to let a search algorithm do the asking.

The setup I've been working with has two layers:

1. A **kinetic Monte Carlo** model of the growing GaAs surface — adsorption, desorption, diffusion, incorporation, each with its own rate.
2. A **Monte Carlo Tree Search** on top, treating a growth recipe as a sequence of decisions: temperature here, V/III ratio there.

The tree search only ever sees a scalar reward at the end of a simulated growth. That turns out to be the hard part — not the search, the *question*. If you reward smoothness, it grows slowly. If you reward speed, it grows rubble. The reward function is where all the domain knowledge actually lives, and getting it wrong is invisible until you look at the surfaces the search is proudly presenting you. The search is never wrong — it answers exactly the question you asked, which is rarely the question you meant.

The current loop runs a few thousand simulated growths per search, fanned out across cores. Whether the recipes it finds survive contact with a real reactor is the next chapter.
