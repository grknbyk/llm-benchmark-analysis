| endeks | ağırlıklar | en iyi model | ucuz alternatif |
|---|---|---|---|
| Overall | `0.3*scicode + 0.25*tbench4 + 0.15*lcr + 0.15*nh + 0.15*acc` | GPT-6 Astra (max) (86.12) | GLM-5.3 (max) (77.03, 9.09 geride, 9.3x kat ucuz) |
| Toplu taşıma | `0.25*code_mig + 0.2*pass1 + 0.2*scicode + 0.15*tbench4 + 0.1*lcr + 0.1*nh` | GPT-6 Astra (max) (77.54) | uygun model yok |
| Etkileşimli düzenleme döngüsü | `0.3*scicode + 0.2*tbench4 + 0.2*nh + 0.15*e2e [inverse_log_minmax] + 0.15*price [inverse_log_minmax]` | GLM-5.3 (max) (69.52) | uygun model yok |
| Yalnızca kalite | `0.4*scicode + 0.3*tbench4 + 0.3*nh` | Claude Fable 5.1 (Max) (74.55) | GLM-5.3 (max) (73.88, 0.67 geride, 9.3x kat ucuz) |
