# Interview guide

## Why can Expected Shortfall be more informative than VaR?

VaR estimates a loss threshold but says nothing about how severe losses become
after that threshold is crossed. Expected Shortfall averages the losses in the
tail and is coherent under standard conditions, including subadditivity.

## Why compare several VaR methods?

Agreement increases confidence; disagreement is useful diagnostic information.
Historical VaR preserves observed non-normality but depends on the sample.
Parametric VaR is transparent and fast but distribution-dependent. Monte Carlo
is flexible but only as realistic as its dynamics and calibration.

## What does a VaR breach mean?

The realised loss exceeded the forecast VaR. At 99% confidence, occasional
breaches are expected. Too many breaches imply poor coverage; clustered breaches
suggest changing volatility or dependence that the model failed to capture.

## Why does component VaR matter?

Portfolio VaR alone does not identify what drives risk. Euler component VaR
allocates total risk across holdings, allowing limits, hedging and capital to
target the actual concentrations.

## What is the difference between expected and unexpected credit loss?

Expected loss is the average loss and can be priced or provisioned. Unexpected
loss measures adverse deviation around the mean and is a capital concern.

## What is CVA?

CVA is the reduction in a derivative portfolio's value due to the possibility
that the counterparty defaults while the portfolio has positive exposure.
Exposure, discounting, default probability and recovery all matter. Netting,
collateral and wrong-way risk can materially alter the result.
