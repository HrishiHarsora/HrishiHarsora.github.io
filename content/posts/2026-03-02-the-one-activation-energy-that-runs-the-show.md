---
title: The one activation energy that runs the show
date: 2026-03-02
---
A KMC model of crystal growth might have thirty rate constants. A reasonable person would assume the model's behaviour depends on all of them, roughly equally. A reasonable person would be wrong.

Run a sensitivity analysis — nudge each activation energy, watch what the film does — and the picture that emerges is closer to a dictatorship than a parliament. In my GaAs model, one barrier dominates the degree of rate control across essentially the whole temperature window I care about. Move it a little, and growth rate, roughness, everything shifts. Move most of the others and the film barely notices.

This is good news twice over:

- **For calibration** — you don't need thirty precise numbers from quantum chemistry, you need two or three, and DFT time is better spent there.
- **For search** — a recipe optimiser exploring process conditions is really navigating the landscape carved by that one barrier. Knowing which one collapses the effective dimensionality of the problem.

The general lesson isn't about GaAs. It's that *models are cheap to interrogate and we mostly don't bother*. A day of sensitivity analysis told me more about my own simulation than a month of staring at its outputs.
