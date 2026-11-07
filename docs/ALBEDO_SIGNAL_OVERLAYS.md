# EXODIA Emotional Signal Layer — 2026-11-02
All 33 state entries in the **production** portrait_registry.json now include signal_overlay. The renderer maps state-specific auras without changing portrait image bytes or anchor positions.
Allowed signals: none, warning_pulse, focus_resonance, strain_glitch, triumphant_halo, casting_arcana, low_hp.
At runtime use window.dispatchEvent(new CustomEvent('exodia:companion-signal',{detail:{hp:0.18,alert:false,specialCasting:false,strained:false}})).
Priority: alert > HP <=25% > special casting > strain > registered state default.
The production visual layer is mounted only if the original 33-state release gate succeeds. It does NOT authorize missing assets or bypass owner sign-off.
Pointing is flagged for new independent true pointing-hand master; portrait previews are not certified or ingested.
