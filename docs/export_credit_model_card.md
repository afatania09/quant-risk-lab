# Export Credit Portfolio Model Card

## Purpose

Estimate loss distributions, concentrations, exposure-limit utilisation and
decision metrics for a portfolio of export-credit guarantees, loans and insurance.

## Intended users

- Portfolio risk analysts
- Credit analysts
- Operational researchers
- Model developers and validators
- Senior decision-makers reviewing aggregate risk

## Inputs

Each deal requires country, sector, product, exposure at default, annual
probability of default, loss given default, guarantee share, premium rate and
country exposure limit. IFRS 9 analysis additionally uses maturity and stage.

## Method

Defaults are generated through a latent-factor structure:

\[
Z_i =
\sqrt{\rho_G}G+
\sqrt{\rho_C}C_{c(i)}+
\sqrt{\rho_S}S_{s(i)}+
\sqrt{1-\rho_G-\rho_C-\rho_S}\epsilon_i.
\]

Deal \(i\) defaults when \(Z_i < \Phi^{-1}(PD_i)\). Its claim is:

\[
L_i = D_i \times EAD_i \times GuaranteeShare_i \times LGD_i.
\]

The portfolio distribution produces:

- expected loss;
- loss-at-risk at a selected confidence;
- Expected Shortfall;
- unexpected loss;
- conditional deal-level tail contributions.

## Key assumptions

- PDs are one-period unconditional inputs.
- Global, country and sector factor correlations are fixed.
- LGD is deterministic within each simulation run.
- Claim timing and recoveries are compressed into LGD.
- Exchange rates and discounting are not explicitly simulated.
- Defaults follow a Gaussian latent-factor dependence structure.

## Validation

- Analytical expected loss is reconciled against the simulated mean.
- Concentration reports reconcile to total covered exposure.
- Tail contributions reconcile to total tail contribution.
- Fixed random seeds make results reproducible.
- Input ranges, scenario weights and unique deal identifiers are validated.
- Automated tests cover normal results, accounting identities and invalid inputs.

## Principal limitations

Gaussian dependence may understate extreme joint defaults. Static PD and LGD
inputs do not capture rating migration, macroeconomic feedback, FX effects or
time-varying recovery. The reverse stress test changes LGD while holding other
assumptions fixed. Premium adequacy is illustrative and not an OECD pricing model.

## Appropriate use

Educational portfolio analysis, prototyping, sensitivity testing, model discussion
and demonstration of a controlled analytical workflow.

## Inappropriate use

Live underwriting, regulatory reporting, statutory accounts, sovereign-limit
setting or pricing without independent validation, approved data and governance.