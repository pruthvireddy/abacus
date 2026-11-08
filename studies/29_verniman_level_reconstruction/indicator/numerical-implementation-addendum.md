# Numerical implementation addendum — before native market results

The first native compile attempt failed with a Pine method return-type mismatch;
no pivot values were observed. The method now ends with an explicit volume return.
Synthetic parity review also exposed extra floating-point rounding when dividing
every histogram row by total volume before N1 threshold comparisons.

N1 will therefore use the original histogram masses internally for prominence,
growth and relative-height comparisons. All these operations are homogeneous
under positive scaling, so this implements the same frozen mathematical rules
while removing that avoidable division. Retain normalized node masses for the
candidate ledger. No threshold, session, selector or date-specific setting is
changed. IEEE floating-point arithmetic remains a platform limitation.

The frozen original specification remains unchanged; this additive record is an
implementation correction made before the first successful native chart result.
