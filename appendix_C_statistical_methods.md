# Appendix C. Statistical Methods and Error Formulae

Every point estimate in this report carries a standard error and a 95% CI (mean ± error, below); every hypothesis test result cited in Sections 4/5 additionally has an exact p-value, computed by `analysis_significance.py` and cross-checked against `analysis_output/significance.json`. No scipy in this project's `.venv`; every formula below is closed-form or exact-combinatorial, implemented from stdlib (`math`, `statistics`, `itertools`, `random`) in `analysis_deviation_gap.py`, `analysis_moral_metrics.py`, `analysis_eval_awareness.py`, and `analysis_significance.py`.

*Error bars on a mean (deviation rates, eigenscores, per-cell aggregates throughout Section 4).* For a sample of $n$ per-trial values with sample mean $\bar{x}$ and sample standard deviation $s$ (Bessel-corrected, $n-1$ denominator):

$$\text{SEM} = \frac{s}{\sqrt{n}}, \qquad \text{CI}_{95} = \bar{x} \pm t_{0.975,\,n-1} \cdot \text{SEM}$$

where $t_{0.975,\,n-1}$ is the two-sided 97.5th-percentile Student's-t critical value for $n-1$ degrees of freedom (`_t_critical_95`, `analysis_deviation_gap.py`, a hardcoded table for df 1-30, since every cell in this project's design has $n \le 40$ trials/cell). Trial-level, not round-level: `deviation_rate` is one number per completed game, so $n$ is the trial count for that cell, avoiding pseudoreplication from within-trial round autocorrelation (Figure 2).

*Wilson score interval (manipulation-check pass rates, Appendix A5).* For $x$ successes of $n$ Bernoulli trials with $z=1.96$ (95%):

$$\hat{p} = x/n, \qquad \text{CI}_{95} = \frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$

Preferred over the naive Wald interval ($\hat p \pm z\sqrt{\hat p(1-\hat p)/n}$, `wald_sem`) because Wald under-covers and can extend past [0,1] near $\hat p \approx 0$ or $1$: exactly the regime the manipulation check's near-100%-pass-rate cells sit in (`wilson_ci`, `analysis_moral_metrics.py`).

*Bootstrap CI (eigenjesus-lite/eigenmoses-lite, Table A3).* No closed-form sampling distribution for a PageRank-style score over an observed cooperation graph, so `bootstrap_eigen_scores` (`analysis_moral_metrics.py`) resamples trials with replacement 500 times (`random.Random`, fixed seed for reproducibility), recomputes the score on each resample, and reports the 2.5th/97.5th empirical percentiles of the resample distribution as the CI.

*Fisher z-transform CI (point-biserial r, Sections 4.3/4.4).* For a correlation $r$ estimated from $n$ pairs ($n \ge 4$, $|r|<1$):

$$z = \operatorname{artanh}(r) = \tfrac{1}{2}\ln\!\frac{1+r}{1-r}, \qquad \text{SE}_z = \frac{1}{\sqrt{n-3}}, \qquad \text{CI}_{95} = \tanh\!\big(z \pm 1.96\,\text{SE}_z\big)$$

used because $r$'s own sampling distribution is skewed near $\pm1$ while $\operatorname{artanh}(r)$ is approximately normal (`point_biserial_ci95`, `analysis_eval_awareness.py`).

*Permutation test (Altruist vs. Baseline deviation rate, per model, Section 4.1).* $H_0$: the two personas' per-trial deviation rates are exchangeable draws from the same distribution. Observed statistic $\hat\Delta = \bar x_{\text{altruist}} - \bar x_{\text{baseline}}$ over the pooled $n_1+n_2$ trial values, re-split into groups of size $n_1,n_2$ either by exact enumeration of all $\binom{n_1+n_2}{n_1}$ splits (when $\le 200{,}000$) or by $100{,}000$ random shuffles otherwise (seeded, `random.Random(0)`):

$$p = \frac{\#\{\text{splits with } |\Delta_{\text{split}}| \ge |\hat\Delta|\}}{\#\text{splits examined}}$$

Chosen because it assumes nothing about the shape of the deviation-rate distribution, unlike a t-test (`permutation_test_diff_means`, `analysis_significance.py`).

*Exact sign test (cross-model replication of the Altruist>Baseline direction, Section 4.1).* $H_0$: $P(\text{Altruist}>\text{Baseline})=0.5$ per model, independently across the $n=5$ models. With $k$ of $5$ models showing the direction:

$$p_{\text{one-sided}} = \sum_{i=k}^{n}\binom{n}{i}0.5^n, \qquad p_{\text{two-sided}} = \sum_{i:\,\Pr(X=i)\le \Pr(X=k)}\binom{n}{i}0.5^n$$

One-sided is primary since the direction was preregistered (`preregistration.md` Section 4, prediction #1); the model, not the pooled trial, is the independent unit here (`binomial_test_one_sided_ge`/`binomial_test_two_sided`, `analysis_significance.py`).

*Two-proportion z-test (matched- vs. mismatched-persona hold rate, Section 4.4).* $H_0$: the two independent groups (matched trials, mismatched trials) share one true hold-rate. Pooled proportion $\hat p = (x_1+x_2)/(n_1+n_2)$:

$$z = \frac{\hat p_1 - \hat p_2}{\sqrt{\hat p(1-\hat p)\left(\frac{1}{n_1}+\frac{1}{n_2}\right)}}, \qquad p = 2\big(1-\Phi(|z|)\big)$$

with $\Phi$ the standard normal CDF via `math.erf` (`two_proportion_z_test`, `analysis_significance.py`).

*McNemar's exact test (mid-game vs. end-game hold rate within the same trial, Section 4.4).* Paired binary outcome (same trial probed twice), so a two-proportion test would be wrong: only the discordant pairs (held at one timepoint, not the other) carry information. With $b$ = gained, $c$ = lost, $H_0$: $b,c$ are drawn from Binomial$(b+c, 0.5)$:

$$p = P\big(K \le \min(b,c)\big) + P\big(K \ge \max(b,c)\big), \quad K\sim\text{Binomial}(b+c,\,0.5)$$

computed as the exact two-sided binomial test on the discordant count rather than the usual $\chi^2$-with-continuity-correction approximation, since $b+c$ is small here (`mcnemar_exact`, `analysis_significance.py`).

*Fisher-z hypothesis test for $r=0$ (eval-awareness null, Sections 4.3/4.4).* Same transform as the CI above, evaluated as a test statistic against $0$ directly: $z = \operatorname{artanh}(r)\sqrt{n-3}$, $p = 2(1-\Phi(|z|))$, guaranteed consistent with the CI (CI excludes 0 iff $p<.05$) since both come from the same `fisher_z_test_r` call.

*Scope.* These tests back four specific claims already stated in the report (Altruist vs. Baseline per-model and cross-model; matched-vs-mismatched hold rate; mid-vs-end hold-rate stability; eval-awareness null), chosen because each matches the real independence/pairing structure of that specific claim, not from an exhaustive per-cell scan of the ~200-cell main-sweep or ~16-cell cross-persona-injection grid, and none of it corrects for multiple comparisons across those four tests or the many secondary per-opponent/per-framing cells reported only as means with CIs (see Limitations). Full numeric output: `analysis_output/significance.json`; regenerate with `python3 analysis_significance.py --json-out analysis_output/significance.json`.
