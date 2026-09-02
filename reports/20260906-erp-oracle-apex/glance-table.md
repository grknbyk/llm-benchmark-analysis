| index | weights | best model | cheap alternative |
|---|---|---|---|
| Overall | `0.3*coding + 0.25*agentic + 0.15*lcr + 0.15*nh + 0.15*acc` | Claude Fable 5.1 (Max) (66.02) | Grok 4.6 (xhigh) (66, 0.01 behind, 6.7x cheaper) |
| Batch migration | `0.25*code_mig + 0.2*pass1 + 0.2*coding + 0.15*agentic + 0.1*lcr + 0.1*nh` | GPT-6 Astra (high) (68.04) | Grok 4.6 (xhigh) (63.46, 4.58 behind, 6.7x cheaper) |
| Interactive edit loop | `0.3*coding + 0.2*agentic + 0.2*nh + 0.15*e2e [inverse_log_minmax] + 0.15*price [inverse_log_minmax]` | GLM-5.3-Flash (69.15) | none qualifies |
| Quality only | `0.4*coding + 0.3*agentic + 0.3*nh` | Grok 4.6 (xhigh) (69.04) | GLM-5.3-Flash (65.76, 3.27 behind, 12.6x cheaper) |
