# Reading market mood

Each dot represents one stock. Its inward motion shows how often it shared a move with its neighbours. The layout uses a fixed first-window distance map per network mode. Each later date scales a stock's radius by one minus 0.9 times its average positive-clipped peer affinity. The picture illustrates the measured relationships. Its radius is a visual encoding, so a compact map is not independent evidence of a crash.

We sort observed trading dates, align adjusted IEX closing prices, fill up to three consecutive missing observations and exclude symbols with more than 10% missing prices after filling or constant price histories. A gap exceeding seven calendar days resets filling and returns. A rolling window requires finite, varying returns on all included stocks. Excluded symbols appear in the status banner. Entirely missing exchange sessions cannot be identified from this feed alone.

For daily log price differences, compute the Pearson correlation matrix over the trailing T sessions. Average its strict upper triangle. The eigenvalues sum to N because the diagonal consists of ones. The largest eigenvalue divided by N gives the fraction of standardized variation in the strongest common factor. The independent-noise approximation has upper edge (1 + √(N/T))². Serial dependence, heavy tails and a changing universe affect that comparison.

Panic level is 100 times the fraction of **earlier** valid windows with a smaller variance share, counting ties half. The opening observation is neutral at 50. An exact 50 or 80 is NERVOUS. Early readings have little reference history. Overlapping windows are dependent. Stocks may rally together as well as fall together.

Threshold links keep correlations at or above the chosen cutoff. The spanning tree connects the basket with N−1 edges minimizing total √(2(1−ρ)) distance. All-links mode retains signed pair weights in the matrix and draws negative, smaller positive and stronger positive links in three tones. Sector assignments describe the supplied universe and are static. New symbols appear in a neutral color.
